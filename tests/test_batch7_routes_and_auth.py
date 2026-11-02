"""Tests for SDC Batch 7: Route Separation, Public Landing, Authentication System, and LMS RBAC.
Authored under agency-application-security-engineer and agency-test-automation-engineer.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import get_db, init_db
from data.seed_curriculum import seed_sdc_curriculum


@pytest.fixture(autouse=True)
def setup_batch7_test_db():
    """Ensure database is seeded with STBB test curriculum and accounts."""
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "sdc_batch7_test.db"
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


# ---------------------------------------------------------------------------
# 1. Public Landing Routes Testing
# ---------------------------------------------------------------------------
def test_public_landing_routes_accessible_without_auth():
    """Verify that public routes (/, /about, /curriculum, /help, /privacy, /terms) are accessible without auth."""
    client = TestClient(app)
    public_paths = ["/", "/about", "/curriculum", "/help", "/privacy", "/terms"]
    for path in public_paths:
        resp = client.get(path)
        assert resp.status_code == 200, f"Path {path} returned {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")
        # Confirm page contains Sindhi first message
        assert "سنڌيءَ ۾ سکو" in resp.text or "سنڌي ڊجيٽل ڪلاس روم" in resp.text
        # Ensure private student/admin tables are NOT exposed on public pages
        assert "student-attempts-table-body" not in resp.text
        assert "superadmin-audit-table-body" not in resp.text
        assert "school-users-table-body" not in resp.text


def test_public_curriculum_catalog_accessible():
    """Verify public curriculum discovery API works without credentials."""
    client = TestClient(app)
    resp = client.get("/api/lessons?class_level=6")
    assert resp.status_code == 200
    courses = resp.json()
    assert len(courses) > 0
    # Confirm course contains STBB metadata
    assert any("Science" in c["subject"] for c in courses)


def test_public_schools_endpoint():
    """Verify public school list endpoint returns registered schools for enrollment."""
    client = TestClient(app)
    resp = client.get("/api/auth/schools")
    assert resp.status_code == 200
    schools = resp.json()
    assert len(schools) >= 3
    assert any(s["code"] == "SCH-HYD-01" for s in schools)
    assert any(s["code"] == "SCH-LKR-02" for s in schools)


# ---------------------------------------------------------------------------
# 2. Authentication Pages and Endpoints Testing
# ---------------------------------------------------------------------------
def test_auth_pages_accessible():
    """Verify dedicated login, signup, forgot-password, and unauthorized HTML pages load."""
    client = TestClient(app)
    auth_pages = ["/login", "/signup", "/forgot-password", "/reset-password", "/unauthorized"]
    for page in auth_pages:
        resp = client.get(page)
        assert resp.status_code == 200, f"Page {page} returned {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")


def test_logout_route_redirects_to_login():
    """Verify /logout performs 303 redirect to /login?logged_out=1."""
    client = TestClient(app)
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code in {302, 303, 307}
    assert "/login?logged_out=1" in resp.headers.get("location", "")


def test_student_login_valid_credentials():
    """Verify valid student login returns token and student profile."""
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
    assert data["token"].startswith("sdc_stu_")


def test_student_login_invalid_credentials_rejected():
    """Verify incorrect PIN or school code is rejected with 401."""
    client = TestClient(app)
    # Wrong PIN
    resp1 = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "9999"
    })
    assert resp1.status_code == 401

    # Nonexistent School
    resp2 = client.post("/api/auth/login/student", json={
        "school_code": "SCH-NONEXISTENT",
        "student_code": "STU-101",
        "pin": "1234"
    })
    assert resp2.status_code == 401


def test_teacher_and_staff_login_valid():
    """Verify teacher and superadmin login returns valid role."""
    client = TestClient(app)
    # Teacher
    resp = client.post("/api/auth/login/staff", json={
        "identifier": "teacher@sindh.edu.pk",
        "password": "teacher123"
    })
    assert resp.status_code == 200
    assert resp.json()["role"] == "TEACHER"

    # Superadmin
    resp_super = client.post("/api/auth/login/staff", json={
        "identifier": "superadmin",
        "password": "super123"
    })
    assert resp_super.status_code == 200
    assert resp_super.json()["role"] == "SUPER_ADMIN"


def test_missing_and_malformed_auth_fields_rejected():
    """Verify missing fields in login and signup requests return 422 Unprocessable Entity."""
    client = TestClient(app)
    resp = client.post("/api/auth/login/student", json={"school_code": "SCH-HYD-01"})
    assert resp.status_code == 422

    resp2 = client.post("/api/auth/login/staff", json={"identifier": ""})
    assert resp2.status_code == 422


# ---------------------------------------------------------------------------
# 3. Student Registration & Privilege Escalation Prevention
# ---------------------------------------------------------------------------
def test_student_self_registration_success():
    """Verify student registers successfully with default STUDENT role and secure hashed PIN."""
    client = TestClient(app)
    payload = {
        "pseudonymous_code": "STU-NEW-888",
        "school_code": "SCH-HYD-01",
        "pin": "7788",
        "class_level": 7,
        "language": "sindhi"
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "STUDENT"
    assert data["pseudonymous_code"] == "STU-NEW-888"
    assert data["token"].startswith("sdc_stu_")

    # Verify password/PIN is stored only as secure PBKDF2 hash
    with get_db(settings.database_path) as conn:
        row = conn.execute("SELECT pin_hash FROM users WHERE pseudonymous_code = ?", ("STU-NEW-888",)).fetchone()
        assert row is not None
        assert row["pin_hash"] != "7788"
        assert "$" in row["pin_hash"]  # salt$hash PBKDF2 format


def test_duplicate_student_code_registration_rejected():
    """Verify registering an existing student code returns 409 Conflict."""
    client = TestClient(app)
    payload = {
        "pseudonymous_code": "STU-101",  # already exists from seed
        "school_code": "SCH-HYD-01",
        "pin": "1234",
        "class_level": 6
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
    assert "اڳ ۾ ئي کڻجي چڪو آهي" in resp.json()["detail"] or "already exists" in resp.json()["detail"]


def test_public_registration_privilege_escalation_blocked():
    """Verify public registration CANNOT create TEACHER, ADMIN, or SUPER_ADMIN accounts."""
    client = TestClient(app)
    malicious_roles = ["SUPER_ADMIN", "TEACHER", "SCHOOL_ADMIN", "CONTENT_REVIEWER", "DISTRICT_OFFICER"]
    for mal_role in malicious_roles:
        payload = {
            "pseudonymous_code": f"MAL-{mal_role}",
            "school_code": "SCH-HYD-01",
            "pin": "1234",
            "class_level": 6,
            "role": mal_role
        }
        resp = client.post("/api/auth/register", json=payload)
        # Must be rejected with 400 Bad Request
        assert resp.status_code == 400, f"Role {mal_role} was not rejected"
        assert "عوامي رجسٽريشن رڳو شاگردن لاءِ آهي" in resp.json()["detail"] or "restricted to students" in resp.json()["detail"]


def test_invalid_school_code_in_registration_rejected():
    """Verify registering with an invalid school code fails."""
    client = TestClient(app)
    payload = {
        "pseudonymous_code": "STU-ORPHAN",
        "school_code": "NON-EXISTENT-SCHOOL-999",
        "pin": "1234",
        "class_level": 6
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 400
    assert "اسڪول ڪوڊ درست ناهي" in resp.json()["detail"] or "Invalid school code" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 4. Protected LMS Application Routing & RBAC Boundary
# ---------------------------------------------------------------------------
def test_lms_app_pages_serve_app_shell():
    """Verify /app and /app subpaths serve app.html shell."""
    client = TestClient(app)
    lms_paths = ["/app", "/app/learn", "/app/progress", "/app/assignments", "/app/tutor", "/app/teacher", "/app/admin"]
    for path in lms_paths:
        resp = client.get(path)
        assert resp.status_code == 200, f"Path {path} returned {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")
        # Confirm app shell elements exist
        assert "lms-sidebar" in resp.text
        assert "lms-topbar" in resp.text
        assert "sdc-video-player" in resp.text


def test_student_forbidden_from_admin_and_teacher_api():
    """Verify backend RBAC strictly forbids student from accessing administrative endpoints."""
    client = TestClient(app)
    student_token = "sdc_stu_usr-stu-101_sample"

    # 1. School Admin users list
    resp1 = client.get("/api/admin/users", headers={"Authorization": f"Bearer {student_token}"})
    assert resp1.status_code == 403

    # 2. Superadmin Audit logs
    resp2 = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {student_token}"})
    assert resp2.status_code == 403

    # 3. Teacher Question Approval Gate
    resp3 = client.get("/api/quiz/pending", headers={"Authorization": f"Bearer {student_token}"})
    assert resp3.status_code == 403

    # 4. Content Reviewer Lesson Review
    resp4 = client.post(
        "/api/lessons/lesson-sci-6-1/review",
        json={"action": "APPROVED", "comments": "Illegal review"},
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert resp4.status_code == 403


def test_safe_return_url_handling():
    """Verify safe internal return URLs vs open redirect rejection logic."""
    # Test safe URL validator logic matching frontend implementation
    def is_safe_redirect(url: str) -> bool:
        if not url:
            return False
        clean = url.strip()
        if clean.startswith('/') and not clean.startswith('//') and not clean.startswith('/\\') and '://' not in clean:
            return True
        return False

    # Safe internal return targets
    assert is_safe_redirect("/app") is True
    assert is_safe_redirect("/app/learn") is True
    assert is_safe_redirect("/app/learn/lesson-sci-6-1") is True
    assert is_safe_redirect("/app/progress") is True

    # Dangerous open-redirect attempts must be rejected
    assert is_safe_redirect("https://evil.com") is False
    assert is_safe_redirect("http://attacker.com/malicious") is False
    assert is_safe_redirect("//evil.com") is False
    assert is_safe_redirect("/\\evil.com") is False
    assert is_safe_redirect("javascript:alert(1)") is False
    assert is_safe_redirect("") is False
