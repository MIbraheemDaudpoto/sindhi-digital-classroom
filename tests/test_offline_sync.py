"""Tests for Offline Unit Packs, Client Sync Queue, and Zero-PII CSV Export (FR-19, FR-32, FR-36).
Authored under agency-backend-architect and agency-test-automation-engineer.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum


from src.config import settings


@pytest.fixture(autouse=True)
def setup_test_db():
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "sync_test.db"
    if test_db.exists():
        test_db.unlink(missing_ok=True)
    orig = settings.database_path
    settings.database_path = str(test_db)
    init_db(str(test_db))
    seed_sdc_curriculum(str(test_db))
    yield str(test_db)
    settings.database_path = orig
    if test_db.exists():
        test_db.unlink(missing_ok=True)


def test_offline_unit_pack_generation():
    """Verify downloadable unit pack contains metadata, transcripts, and approved questions (FR-32)."""
    client = TestClient(app)
    res = client.get("/api/sync/unit-pack/lesson-sci-6-1")
    assert res.status_code == 200
    pack = res.json()

    assert "lesson" in pack
    assert pack["lesson"]["id"] == "lesson-sci-6-1"
    assert "transcripts" in pack
    assert len(pack["transcripts"]) >= 1
    assert "approved_questions" in pack
    assert len(pack["approved_questions"]) >= 1
    # Verify unapproved questions are not packaged
    for q in pack["approved_questions"]:
        assert q["status"] == "APPROVED"


def test_offline_queue_sync_processing():
    """Verify client-queued attempts and progress are processed and persisted (FR-19)."""
    client = TestClient(app)
    queue_payload = {
        "queue": [
            {
                "type": "attempt",
                "question_id": "q-sci-01",
                "selected_option": 0,
                "is_correct": True,
                "time_taken_seconds": 4.2
            },
            {
                "type": "progress",
                "lesson_id": "lesson-sci-6-1",
                "position_seconds": 240.0,
                "is_completed": True
            }
        ]
    }
    res = client.post("/api/sync/queue?user_id=usr-stu-101", json=queue_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["processed_items"] == 2
    assert data["failed_items"] == 0


def test_anonymized_pilot_csv_export_zero_pii():
    """Verify exported evaluation CSV contains learning metrics and zero student PII (FR-36)."""
    client = TestClient(app)
    res = client.get("/api/dashboards/export-anonymized?user_id=usr-super-admin-01")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    csv_text = res.text

    # Header check
    assert "school_code,district,pseudonymous_student_id,lesson_id" in csv_text
    assert "gain_score,quiz_attempts_count,accuracy_pct" in csv_text

    # Ensure no forbidden PII columns
    assert "real_name" not in csv_text
    assert "phone" not in csv_text
    assert "address" not in csv_text


def test_offline_sync_idempotency_duplicate_submission():
    """Verify duplicate submission sync (e.g. on client network retry) is handled idempotently without crash."""
    client = TestClient(app)
    queue_payload = {
        "queue": [
            {
                "type": "attempt",
                "id": "att-idemp-101",
                "question_id": "q-sci-01",
                "selected_option": 0,
                "is_correct": True,
                "time_taken_seconds": 5.0
            }
        ]
    }

    # First delivery
    res1 = client.post("/api/sync/queue?user_id=usr-stu-101", json=queue_payload)
    assert res1.status_code == 200
    assert res1.json()["processed_items"] == 1

    # Second delivery (duplicate retry)
    res2 = client.post("/api/sync/queue?user_id=usr-stu-101", json=queue_payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "ok"
    assert res2.json()["failed_items"] == 0


def test_offline_sync_progress_high_water_mark():
    """Verify out-of-order progress sync preserves highest playback position (monotonicity)."""
    from src.database.session import get_db
    client = TestClient(app)

    # First sync: position = 300s
    p1 = {
        "queue": [
            {
                "type": "progress",
                "lesson_id": "lesson-sci-6-1",
                "position_seconds": 300.0,
                "is_completed": False
            }
        ]
    }
    res1 = client.post("/api/sync/queue?user_id=usr-stu-101", json=p1)
    assert res1.status_code == 200

    # Second sync: delayed older event with position = 120s
    p2 = {
        "queue": [
            {
                "type": "progress",
                "lesson_id": "lesson-sci-6-1",
                "position_seconds": 120.0,
                "is_completed": False
            }
        ]
    }
    res2 = client.post("/api/sync/queue?user_id=usr-stu-101", json=p2)
    assert res2.status_code == 200

    with get_db() as conn:
        row = conn.execute(
            "SELECT last_position_seconds FROM progress WHERE user_id = 'usr-stu-101' AND lesson_id = 'lesson-sci-6-1'"
        ).fetchone()
        assert row is not None
        assert row["last_position_seconds"] == 300.0


def test_cross_account_offline_sync_rejected():
    """Verify that submitting queued attempts tagged for Student A using Student B's session is rejected."""
    from src.database.session import get_db
    client = TestClient(app)

    # Student 101 authenticates, but submits an item with claimed user_id = 'usr-stu-102'
    queue_payload = {
        "queue": [
            {
                "type": "attempt",
                "id": "att-hijack-test-01",
                "user_id": "usr-stu-102",
                "question_id": "q-sci-01",
                "selected_option": 1,
                "is_correct": False,
                "time_taken_seconds": 12.0
            }
        ]
    }
    res = client.post("/api/sync/queue?user_id=usr-stu-101", json=queue_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["processed_items"] == 0
    assert data["failed_items"] == 1

    # Verify attempt was NOT inserted into attempts table for either student
    with get_db() as conn:
        row = conn.execute("SELECT * FROM attempts WHERE id = 'att-hijack-test-01'").fetchone()
        assert row is None

        # Verify security audit entry was created
        audit = conn.execute(
            "SELECT * FROM audit_logs WHERE action = 'SYNC_OWNERSHIP_MISMATCH' AND user_id = 'usr-stu-101'"
        ).fetchone()
        assert audit is not None


def test_sync_unknown_question_fails_gracefully():
    """Verify queued attempts referencing nonexistent questions increment failed count and do not crash."""
    client = TestClient(app)
    queue_payload = {
        "queue": [
            {
                "type": "attempt",
                "question_id": "nonexistent-q-999",
                "selected_option": 0,
                "is_correct": True
            }
        ]
    }
    res = client.post("/api/sync/queue?user_id=usr-stu-101", json=queue_payload)
    assert res.status_code == 200
    assert res.json()["processed_items"] == 0
    assert res.json()["failed_items"] == 1


