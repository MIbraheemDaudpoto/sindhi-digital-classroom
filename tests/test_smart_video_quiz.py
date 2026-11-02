"""Tests for Smart Video Quiz Pipeline and Mandatory Teacher Approval Gate (FR-13 to FR-19).
Authored under agency-ai-engineer and agency-test-automation-engineer.
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
    test_db = test_dir / "quiz_test.db"
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


def test_teacher_approval_gate_unapproved_excluded_from_students():
    """Verify unapproved draft questions NEVER appear in student quiz bank (FR-13 Gate)."""
    client = TestClient(app)

    # 1. Check student question bank for Science lesson
    res = client.get("/api/quiz/lesson-sci-6-1/questions?student_id=usr-stu-101")
    assert res.status_code == 200
    questions = res.json()

    # Draft questions (e.g. q-sci-04-draft) MUST NOT be present
    question_ids = [q["id"] for q in questions]
    assert "q-sci-04-draft" not in question_ids
    # Only approved questions are returned
    for q in questions:
        assert q["status"] == "APPROVED"


def test_teacher_approves_draft_question():
    """Verify administrator can review and approve a draft question, releasing it to students (FR-13)."""
    client = TestClient(app)

    # 1. Fetch pending list for admin
    pend_res = client.get("/api/quiz/pending?user_id=usr-super-admin-01")
    assert pend_res.status_code == 200
    pending = pend_res.json()
    assert any(q["id"] == "q-sci-04-draft" for q in pending)

    # 2. Admin approves question
    review_payload = {
        "status": "APPROVED",
        "edited_text_sindhi": "ڪهڙي وقت ٻوٽا فوٽوسنٿيسز جو عمل سڀ کان وڌيڪ ڪن ٿا؟"
    }
    appr_res = client.post("/api/quiz/q-sci-04-draft/review?user_id=usr-super-admin-01", json=review_payload)
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "ok"

    # 3. Now question MUST be released and appear in student bank
    released_res = client.get("/api/quiz/lesson-sci-6-1/questions?student_id=usr-stu-101")
    updated_ids = [q["id"] for q in released_res.json()]
    assert "q-sci-04-draft" in updated_ids


def test_submit_quiz_attempt_auto_marking():
    """Verify student attempt auto-marking and Sindhi feedback (FR-27)."""
    client = TestClient(app)

    # Submit correct answer (option 0 is correct in seed data)
    payload = {
        "question_id": "q-sci-01",
        "selected_option": 0,
        "time_taken_seconds": 4.5
    }
    res = client.post("/api/quiz/attempt?user_id=usr-stu-101", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is True
    assert "شاباس" in data["explanation_sindhi"]

    # Submit incorrect answer
    wrong_payload = {
        "question_id": "q-sci-01",
        "selected_option": 2,
        "time_taken_seconds": 3.0
    }
    w_res = client.post("/api/quiz/attempt?user_id=usr-stu-101", json=wrong_payload)
    assert w_res.status_code == 200
    w_data = w_res.json()
    assert w_data["is_correct"] is False
    assert "غلط" in w_data["explanation_sindhi"]


def test_quiz_attempt_skip_handling():
    """Verify student skipping a question is recorded as skipped with selected_option = -1 (FR-14, FR-27)."""
    client = TestClient(app)
    skip_payload = {
        "question_id": "q-sci-01",
        "selected_option": -1,
        "time_taken_seconds": 0.0,
        "is_skipped": True
    }
    res = client.post("/api/quiz/attempt?user_id=usr-stu-101", json=skip_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is False
    assert data["selected_option"] == -1
    assert "ڇڏي" in data["explanation_sindhi"]
