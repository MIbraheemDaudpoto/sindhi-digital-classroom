"""Tests for Authentication, RBAC, and Child Data Privacy in SDC.
Authored under agency-application-security-engineer and agency-test-automation-engineer.
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
    """Ensure database is seeded with STBB test curriculum."""
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "sdc_test.db"
    if test_db.exists():
        test_db.unlink(missing_ok=True)
    original_db = settings.database_path
    settings.database_path = str(test_db)
    init_db(str(test_db))
    seed_sdc_curriculum(str(test_db))
    yield str(test_db)
    settings.database_path = original_db
    if test_db.exists():
        test_db.unlink(missing_ok=True)


def test_student_login_success():
    """Verify student logs in using school code + pseudonymous student code + PIN (FR-01)."""
    client = TestClient(app)
    payload = {
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    }
    resp = client.post("/api/auth/login/student", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "STUDENT"
    assert data["pseudonymous_code"] == "STU-101"
    assert "token" in data
    # Confirm no real names or sensitive child PII returned
    assert "real_name" not in data
    assert "home_address" not in data


def test_student_login_invalid_pin():
    """Verify invalid PIN is rejected."""
    client = TestClient(app)
    payload = {
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "9999"  # Incorrect PIN
    }
    resp = client.post("/api/auth/login/student", json=payload)
    assert resp.status_code == 401
    assert "غلط" in resp.json()["detail"]


def test_teacher_login_success():
    """Verify teacher logs in using email and password (FR-01, FR-02)."""
    client = TestClient(app)
    payload = {
        "identifier": "teacher@sindh.edu.pk",
        "password": "teacher123"
    }
    resp = client.post("/api/auth/login/staff", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "TEACHER"
    assert data["pseudonymous_code"] == "TCH-HYD-01"


def test_unauthenticated_request_rejected():
    """Verify unauthenticated requests to protected endpoints return 401 Unauthorized."""
    client = TestClient(app)
    resp = client.get("/api/quiz/pending")
    assert resp.status_code == 401
    assert "غير تصديق ٿيل" in resp.json()["detail"]


def test_student_role_forbidden_from_teacher_approval():
    """Verify student role is strictly rejected (403 Forbidden) from teacher approval gate (FR-13)."""
    client = TestClient(app)
    # Attempting to access pending questions with student credentials
    resp = client.get("/api/quiz/pending?user_id=usr-stu-101")
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]

    # Attempting to approve draft question with student credentials
    review_payload = {"status": "APPROVED"}
    appr_resp = client.post("/api/quiz/q-sci-04-draft/review?user_id=usr-stu-101", json=review_payload)
    assert appr_resp.status_code == 403


def test_student_dashboard_idor_prevented():
    """Verify student cannot access another student's dashboard (FR-02, IDOR prevention)."""
    client = TestClient(app)

    # Student 101 accessing their own dashboard succeeds
    own_resp = client.get("/api/dashboards/student?user_id=usr-stu-101")
    assert own_resp.status_code == 200
    assert own_resp.json()["student_code"] == "STU-101"

    # Student 101 trying to view Student 102's dashboard is rejected with 403
    # Simulating request authenticated as usr-stu-101 targeting usr-stu-102
    token_101 = "sdc_student_usr-stu-101_sampletoken"
    idor_resp = client.get(
        "/api/dashboards/student?user_id=usr-stu-102",
        headers={"Authorization": f"Bearer {token_101}"}
    )
    assert idor_resp.status_code == 403
    assert "ٻين شاگردن" in idor_resp.json()["detail"]


def test_cross_school_teacher_isolation():
    """Verify teacher role is inactive for pilot or cross-school access is rejected."""
    client = TestClient(app)

    # Teacher 2 tries to view Student 1
    token_tch_lkr = "sdc_teacher_usr-tch-02_sampletoken"
    cross_resp = client.get(
        "/api/dashboards/student?user_id=usr-stu-101",
        headers={"Authorization": f"Bearer {token_tch_lkr}"}
    )
    assert cross_resp.status_code == 403
    assert any(msg in cross_resp.json()["detail"] for msg in ("ٻئي اسڪول", "Forbidden", "پائلٽ", "inactive for pilot"))


def test_expired_token_rejected():
    """Verify session tokens older than 24 hours are rejected with 401 Unauthorized."""
    import time
    client = TestClient(app)

    old_epoch = int(time.time()) - 90000 # ~25 hours ago
    expired_token = f"sdc_student_usr-stu-101_{old_epoch}_expiredhex"

    resp = client.get(
        "/api/dashboards/student?user_id=usr-stu-101",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401
    assert "سيشن ختم ٿي چڪو آهي" in resp.json()["detail"]


