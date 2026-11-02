"""Unit test suite for SDC backend scaffold and security hardening.
Verifies:
1. SQLite WAL mode, synchronous NORMAL, busy_timeout=5000, and foreign keys.
2. Complete rejection of query-parameter authentication bypass.
3. RBAC enforcement: only STUDENT and SUPER_ADMIN are active for pilot;
   other roles (TEACHER, PARENT, HEAD_TEACHER, OFFICER) receive 403 Forbidden.
4. Audit logs and Consents table recording and query safety.
5. Idempotent attempt_uuid constraint on quiz_attempts.
"""

import json
import sqlite3
import uuid
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import get_db, init_db
from src.services.auth_service import auth_service
from src.services.audit_service import audit_service


@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    """Ensure test database is initialized with tables, pragmas, and views."""
    init_db()


def test_sqlite_wal_and_connection_pragmas():
    """Verify that every connection sets WAL, synchronous=NORMAL, busy_timeout=5000, and foreign_keys=ON."""
    with get_db() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert journal_mode.lower() == "wal", f"Expected WAL mode, got {journal_mode}"

        synchronous = conn.execute("PRAGMA synchronous;").fetchone()[0]
        # 1 corresponds to NORMAL in SQLite
        assert synchronous in (1, "1", "NORMAL"), f"Expected synchronous NORMAL (1), got {synchronous}"

        busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert int(busy_timeout) == 5000, f"Expected busy_timeout 5000, got {busy_timeout}"

        foreign_keys = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert int(foreign_keys) == 1, f"Expected foreign_keys ON (1), got {foreign_keys}"


def test_auth_query_parameter_bypass_is_strictly_rejected():
    """Verify that any request attempting authentication via query parameters is rejected with 401."""
    orig_allow = settings.allow_test_query_auth
    try:
        settings.allow_test_query_auth = False
        client = TestClient(app)

        # Attempt query parameter bypass using ?user_id=
        res1 = client.get("/api/auth/me?user_id=usr-test-admin")
        assert res1.status_code == 401
        assert "ڪوئري پيراميٽر" in res1.json()["detail"]

        # Attempt query parameter bypass using ?token=
        res2 = client.get("/api/auth/me?token=sdc_fake_token")
        assert res2.status_code == 401
        assert "ڪوئري پيراميٽر" in res2.json()["detail"]

        # Attempt query parameter bypass using ?teacher_id=
        res3 = client.get("/api/auth/me?teacher_id=usr-teacher")
        assert res3.status_code == 401
    finally:
        settings.allow_test_query_auth = orig_allow


def test_rbac_pilot_lock_student_and_super_admin_active():
    """Verify that only STUDENT and SUPER_ADMIN roles are active during the pilot."""
    client = TestClient(app)

    # 1. Seed test users for each role
    student_id = f"test-stu-{uuid.uuid4().hex[:6]}"
    admin_id = f"test-adm-{uuid.uuid4().hex[:6]}"
    teacher_id = f"test-tch-{uuid.uuid4().hex[:6]}"
    parent_id = f"test-par-{uuid.uuid4().hex[:6]}"

    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO users (id, role, pseudonymous_code, pin_hash, language, created_at)
            VALUES 
            (?, 'STUDENT', ?, 'hash', 'sindhi', '2026-10-24'),
            (?, 'SUPER_ADMIN', ?, 'hash', 'sindhi', '2026-10-24'),
            (?, 'TEACHER', ?, 'hash', 'sindhi', '2026-10-24'),
            (?, 'PARENT', ?, 'hash', 'sindhi', '2026-10-24')
            """,
            (student_id, student_id, admin_id, admin_id, teacher_id, teacher_id, parent_id, parent_id)
        )

    # Generate session tokens
    student_token = auth_service.create_session_token(student_id, "STUDENT")
    admin_token = auth_service.create_session_token(admin_id, "SUPER_ADMIN")
    teacher_token = auth_service.create_session_token(teacher_id, "TEACHER")
    parent_token = auth_service.create_session_token(parent_id, "PARENT")

    # 2. Test STUDENT token -> Must succeed on /api/auth/me
    res_stu = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
    assert res_stu.status_code == 200
    assert res_stu.json()["role"] == "STUDENT"

    # 3. Test SUPER_ADMIN token -> Must succeed on /api/auth/me
    res_adm = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_adm.status_code == 200
    assert res_adm.json()["role"] == "SUPER_ADMIN"

    # 4. Test TEACHER token -> Must be BLOCKED with 403 Forbidden (Role deactivated for pilot)
    res_tch = client.get("/api/auth/me", headers={"Authorization": f"Bearer {teacher_token}"})
    assert res_tch.status_code == 403
    assert "inactive for pilot" in res_tch.json()["detail"]

    # 5. Test PARENT token -> Must be BLOCKED with 403 Forbidden (Role deactivated for pilot)
    res_par = client.get("/api/auth/me", headers={"Authorization": f"Bearer {parent_token}"})
    assert res_par.status_code == 403
    assert "inactive for pilot" in res_par.json()["detail"]


def test_audit_logs_and_consents_persistence():
    """Verify that audit logs and parental consents are inserted and queried correctly."""
    child_code = f"CHILD-{uuid.uuid4().hex[:6]}"
    guardian_code = f"GUARD-{uuid.uuid4().hex[:6]}"

    # Record parental consent
    consent_id = audit_service.record_consent(
        guardian_code=guardian_code,
        child_code=child_code,
        scope="LEARNING_ANALYTICS",
        is_granted=True,
    )
    assert consent_id is not None
    assert audit_service.check_consent(child_code, "LEARNING_ANALYTICS") is True
    assert audit_service.check_consent(child_code, "SPEECH_TRAINING") is False

    # Record audit event
    log_id = audit_service.log_event(
        user_id="usr-system-admin",
        action="VERIFY_PILOT_CONFIG",
        resource_type="CONFIG",
        resource_id="rbac_policy",
        details={"active_roles": ["STUDENT", "SUPER_ADMIN"]},
    )
    assert log_id is not None

    with get_db() as conn:
        row = conn.execute("SELECT * FROM audit_logs WHERE id = ?", (log_id,)).fetchone()
        assert row is not None
        assert row["action"] == "VERIFY_PILOT_CONFIG"
        details = json.loads(row["details_json"])
        assert "active_roles" in details


def test_idempotent_attempt_uuid_constraint():
    """Verify that quiz_attempts enforces UNIQUE(attempt_uuid) to prevent double-scoring."""
    test_uuid = str(uuid.uuid4())
    attempt_id1 = str(uuid.uuid4())
    attempt_id2 = str(uuid.uuid4())
    user_id = f"test-usr-{uuid.uuid4().hex[:6]}"
    course_id = f"test-crs-{uuid.uuid4().hex[:6]}"
    lesson_id = f"test-lsn-{uuid.uuid4().hex[:6]}"
    question_id = f"test-q-{uuid.uuid4().hex[:6]}"

    with get_db() as conn:
        # Seed parent records to satisfy foreign keys
        conn.execute(
            "INSERT INTO users (id, role, pseudonymous_code, pin_hash, language, created_at) VALUES (?, 'STUDENT', ?, 'hash', 'sindhi', '2026-10-24')",
            (user_id, user_id)
        )
        conn.execute(
            "INSERT INTO courses (id, class_level, subject, title_sindhi, title_english) VALUES (?, 6, 'Science', 'سائنس', 'Science')",
            (course_id,)
        )
        conn.execute(
            "INSERT INTO lessons (id, course_id, unit_number, title_sindhi, title_english, created_at) VALUES (?, ?, 1, 'سبق', 'Lesson 1', '2026-10-24')",
            (lesson_id, course_id)
        )
        conn.execute(
            "INSERT INTO questions (id, lesson_id, timestamp_seconds, text_sindhi, options_json, correct_answer_index, topic, status) VALUES (?, ?, 10.0, 'سوال', '[\"A\", \"B\"]', 0, 'Cell', 'APPROVED')",
            (question_id, lesson_id)
        )

        # First insertion succeeds
        conn.execute(
            """
            INSERT INTO attempts (id, attempt_uuid, user_id, question_id, selected_option, is_correct, created_at)
            VALUES (?, ?, ?, ?, 1, 1, '2026-10-24')
            """,
            (attempt_id1, test_uuid, user_id, question_id)
        )

        # Duplicate insertion with same attempt_uuid must raise IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO attempts (id, attempt_uuid, user_id, question_id, selected_option, is_correct, created_at)
                VALUES (?, ?, ?, ?, 1, 1, '2026-10-24')
                """,
                (attempt_id2, test_uuid, user_id, question_id)
            )

        # Using INSERT OR IGNORE must not raise and must not duplicate
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO attempts (id, attempt_uuid, user_id, question_id, selected_option, is_correct, created_at)
            VALUES (?, ?, ?, ?, 1, 1, '2026-10-24')
            """,
            (attempt_id2, test_uuid, user_id, question_id)
        )
        assert cursor.rowcount == 0  # Ignored cleanly without error
