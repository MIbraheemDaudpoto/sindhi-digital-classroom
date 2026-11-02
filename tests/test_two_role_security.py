"""Automated verification of Two-Role RBAC Lock (Student & Admin) and Token Security for SDC.
Tests server-side authorization enforcement, token signing, session revocation,
and verifies that query parameter authentication shortcuts cannot be used in production.
Authored under agency-application-security-engineer and agency-test-automation-engineer.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum
from src.services.auth_service import auth_service


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Ensure database is seeded with STBB test curriculum and isolated test DB."""
    test_db = tmp_path / "sdc_security_test.db"
    original_db = settings.database_path
    original_env = settings.environment
    original_query_auth = settings.allow_test_query_auth
    original_secret = settings.secret_key
    original_cors = settings.cors_allowed_origins

    settings.database_path = str(test_db)
    settings.environment = "production"  # Enforce production mode to test real security
    settings.allow_test_query_auth = False  # Strictly forbid query param auth
    settings.secret_key = "isolated-production-test-secret-at-least-32-chars"
    settings.cors_allowed_origins = "https://test.example"

    init_db(str(test_db))
    seed_sdc_curriculum(str(test_db))

    yield str(test_db)

    settings.database_path = original_db
    settings.environment = original_env
    settings.allow_test_query_auth = original_query_auth
    settings.secret_key = original_secret
    settings.cors_allowed_origins = original_cors


def test_production_rejects_query_parameter_auth_bypass():
    """CRITICAL SECURITY TEST: Ensure ?user_id=usr-super-admin-01 is strictly rejected in production."""
    orig_allow = settings.allow_test_query_auth
    try:
        settings.allow_test_query_auth = False
        client = TestClient(app)
        # Attempting to access admin users via query parameter without valid Bearer token
        resp = client.get("/api/admin/users?user_id=usr-super-admin-01")
        assert resp.status_code == 401
        assert any(msg in resp.json()["detail"] for msg in ("غير تصديق ٿيل", "Authentication required", "ڪوئري پيراميٽر ذريعي تصديق منع آهي"))
    finally:
        settings.allow_test_query_auth = orig_allow

    # Attempting to access pending quiz questions via query parameter
    quiz_resp = client.get("/api/quiz/pending?user_id=usr-super-admin-01")
    assert quiz_resp.status_code == 401


def test_hmac_signed_token_authentication():
    """Verify that a cryptographically signed HMAC token authenticates successfully."""
    client = TestClient(app)
    # Generate signed token for student
    token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "STUDENT"
    assert data["user_id"] == "usr-stu-101"
    assert "view_curriculum" in data["permissions"]


def test_tampered_token_is_rejected():
    """Verify that altering token characters breaks the HMAC signature and is rejected with 401."""
    client = TestClient(app)
    token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    # Tamper with the token string
    tampered_token = token[:-4] + "ffff"
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert "سيشن ختم ٿي چڪو آهي" in resp.json()["detail"] or "invalid" in resp.json()["detail"].lower()


def test_production_rejects_unsigned_legacy_token():
    client = TestClient(app)
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer sdc_student_usr-stu-101_sampletoken"},
    )
    assert resp.status_code == 401


def test_student_forbidden_from_admin_operations():
    """Verify student role is strictly rejected (403 Forbidden) from admin endpoints."""
    client = TestClient(app)
    student_token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    headers = {"Authorization": f"Bearer {student_token}"}

    # Student trying to list platform users
    resp = client.get("/api/admin/users", headers=headers)
    assert resp.status_code == 403
    assert "اجازت ناهي" in resp.json()["detail"] or "Forbidden" in resp.json()["detail"]

    # Student trying to view platform audit logs
    audit_resp = client.get("/api/admin/audit-logs", headers=headers)
    assert audit_resp.status_code == 403


def test_admin_authorized_for_admin_endpoints():
    """Verify admin role can access administrative endpoints with signed token."""
    client = TestClient(app)
    admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/api/admin/users", headers=headers)
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) > 0


def test_session_revocation():
    """Verify that revoking a user's sessions immediately invalidates earlier tokens."""
    client = TestClient(app)
    token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    headers = {"Authorization": f"Bearer {token}"}

    # First request works
    resp1 = client.get("/api/auth/me", headers=headers)
    assert resp1.status_code == 200

    # Revoke sessions for this user
    auth_service.revoke_user_sessions("usr-stu-101")

    # Second request fails
    resp2 = client.get("/api/auth/me", headers=headers)
    assert resp2.status_code == 401


def test_api_ready_probe_operational():
    """Verify deployment readiness probe /api/ready returns HTTP 200 with database and storage status."""
    client = TestClient(app)
    resp = client.get("/api/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"]["connected"] is True
    assert "journal_mode" in data["database"]
    assert "media_storage" in data
    assert "sms_gateway" in data


def test_api_health_probe_operational():
    """Verify system health probe /api/health returns HTTP 200 and two-role policy."""
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "TWO_ROLE" in data["roles_policy"]

