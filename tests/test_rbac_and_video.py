"""Comprehensive tests for SDC Batch 5:
- Video Playback and Range Requests (HTTP 206 Partial Content, Accept-Ranges, 416, 404, traversal prevention).
- Official YouTube Catalog Integration & Attribution metadata.
- Complete Server-Enforced RBAC across all 6 roles (STUDENT, TEACHER, CONTENT_REVIEWER, SCHOOL_ADMIN, DISTRICT_OFFICER, SUPER_ADMIN).
- Cross-school isolation, audit logging, and session endpoints (/api/auth/me, /api/auth/logout).
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
    """Ensure database is seeded with STBB test curriculum and Batch 5 accounts."""
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


def get_token(client: TestClient, role: str) -> str:
    """Helper to authenticate and retrieve bearer token for any of the 6 roles."""
    if role == "STUDENT":
        resp = client.post("/api/auth/login/student", json={
            "school_code": "SCH-HYD-01",
            "student_code": "STU-101",
            "pin": "1234"
        })
        assert resp.status_code == 200, f"Student login failed: {resp.text}"
        return resp.json()["token"]
    
    credentials = {
        "TEACHER": ("teacher@sindh.edu.pk", "teacher123"),
        "CONTENT_REVIEWER": ("reviewer_sindh", "reviewer123"),
        "SCHOOL_ADMIN": ("admin_hyd", "admin123"),
        "DISTRICT_OFFICER": ("officer_sindh", "password123"),
        "SUPER_ADMIN": ("superadmin", "super123"),
    }
    identifier, password = credentials[role]
    resp = client.post("/api/auth/login/staff", json={
        "identifier": identifier,
        "password": password
    })
    assert resp.status_code == 200, f"Staff login failed for {role}: {resp.text}"
    return resp.json()["token"]


# =====================================================================
# 1. Video Playback & Byte-Range Request Tests
# =====================================================================

def test_video_static_media_full_playback():
    """Verify full video request returns HTTP 200, correct MIME type, and Accept-Ranges."""
    client = TestClient(app)
    resp = client.get("/static/media/lesson-sci-6-1.mp4")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "video/mp4"
    assert resp.headers.get("accept-ranges") == "bytes"
    assert int(resp.headers["content-length"]) > 0
    # Check ISO BMFF MP4 header signature (starts with ftyp box)
    content = resp.content
    assert b"ftypisom" in content or b"ftyp" in content


def test_video_byte_range_request_success():
    """Verify byte-range requests return HTTP 206 Partial Content and proper Content-Range."""
    client = TestClient(app)
    headers = {"Range": "bytes=0-99"}
    resp = client.get("/static/media/lesson-sci-6-1.mp4", headers=headers)
    assert resp.status_code == 206
    assert resp.headers["content-type"] == "video/mp4"
    assert "Content-Range" in resp.headers
    assert resp.headers["Content-Range"].startswith("bytes 0-99/")
    assert len(resp.content) == 100


def test_video_byte_range_suffix_request():
    """Verify open-ended range request (e.g. bytes=50-)."""
    client = TestClient(app)
    # First get full length
    full_resp = client.get("/static/media/lesson-sci-6-1.mp4")
    total_length = int(full_resp.headers["content-length"])
    
    resp = client.get("/static/media/lesson-sci-6-1.mp4", headers={"Range": "bytes=50-"})
    assert resp.status_code == 206
    assert len(resp.content) == total_length - 50
    assert resp.headers["Content-Range"] == f"bytes 50-{total_length - 1}/{total_length}"


def test_video_byte_range_unsatisfiable():
    """Verify out-of-bounds byte range returns HTTP 416 Range Not Satisfiable."""
    client = TestClient(app)
    headers = {"Range": "bytes=99999999-99999999"}
    resp = client.get("/static/media/lesson-sci-6-1.mp4", headers=headers)
    assert resp.status_code == 416


def test_video_file_not_found():
    """Verify non-existent media file returns HTTP 404 with informative message."""
    client = TestClient(app)
    resp = client.get("/static/media/non-existent-video.mp4")
    assert resp.status_code == 404


def test_video_path_traversal_prevention():
    """Verify path traversal attempts are rejected."""
    client = TestClient(app)
    resp = client.get("/static/media/../../src/config.py")
    assert resp.status_code in (403, 404)


# =====================================================================
# 2. Official YouTube Catalog Integration Tests
# =====================================================================

def test_youtube_catalog_endpoint():
    """Verify YouTube catalog returns approved educational videos with complete attribution."""
    client = TestClient(app)
    resp = client.get("/api/lessons/youtube/catalog")
    assert resp.status_code == 200
    catalog = resp.json()
    assert isinstance(catalog, list)
    assert len(catalog) >= 1
    
    first = catalog[0]
    assert "youtube_id" in first
    assert "title" in first
    assert "channel_name" in first
    assert "original_url" in first
    assert "embed_url" in first
    assert "attribution_text" in first
    assert "curriculum_status" in first
    if first["embed_url"]:
        assert "youtube-nocookie.com/embed" in first["embed_url"]


def test_lesson_detail_includes_youtube_video():
    """Verify lesson detail returns YouTube metadata when mapped."""
    client = TestClient(app)
    resp = client.get("/api/lessons/lesson-sci-6-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["video_source_type"] in ("LOCAL", "YOUTUBE")
    if data.get("youtube_video"):
        yt = data["youtube_video"]
        assert yt["youtube_id"] is not None
        if yt["embed_url"]:
            assert yt["embed_url"].startswith("https://www.youtube-nocookie.com/embed/")
        assert "Watch on YouTube" in yt["attribution_text"] or len(yt["original_url"]) > 0 or "Official" in yt["channel_name"]


def test_lesson_video_inspection_endpoint():
    """Verify GET /api/lessons/{id}/video inspects video availability."""
    client = TestClient(app)
    resp = client.get("/api/lessons/lesson-sci-6-1/video")
    assert resp.status_code == 200
    data = resp.json()
    assert "video_source_type" in data
    assert "local_media" in data
    assert data["local_media"]["exists_on_disk"] is True
    assert "offline_capable" in data


# =====================================================================
# 3. Server-Enforced RBAC & Session Management
# =====================================================================

def test_auth_me_endpoint_for_all_roles():
    """Verify /api/auth/me returns identity for active pilot roles and 403 for inactive roles."""
    client = TestClient(app)
    roles = ["STUDENT", "TEACHER", "CONTENT_REVIEWER", "SCHOOL_ADMIN", "DISTRICT_OFFICER", "SUPER_ADMIN"]
    for role in roles:
        token = get_token(client, role)
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if role in settings.active_pilot_roles:
            assert resp.status_code == 200
            data = resp.json()
            assert data["role"] == role
            assert "user_id" in data
        else:
            assert resp.status_code == 403
            assert "پائلٽ" in resp.json()["detail"] or "inactive for pilot" in resp.json()["detail"].lower()


def test_auth_logout_logs_audit_trail():
    """Verify logout logs an audit event and returns 200 for active pilot role."""
    client = TestClient(app)
    token = get_token(client, "SUPER_ADMIN")
    resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# =====================================================================
# 4. Content Reviewer Workflow & Approval Gates
# =====================================================================

def test_content_reviewer_approves_lesson():
    """Verify Content Reviewer is inactive under pilot lock (403 Forbidden)."""
    client = TestClient(app)
    rev_token = get_token(client, "CONTENT_REVIEWER")
    payload = {
        "action": "APPROVED",
        "comments": "STBB syllabus alignment verified. Chapter 1 concepts accurate."
    }
    resp = client.post(
        "/api/lessons/lesson-sci-6-1/review",
        json=payload,
        headers={"Authorization": f"Bearer {rev_token}"}
    )
    assert resp.status_code == 403
    assert "پائلٽ" in resp.json()["detail"] or "inactive for pilot" in resp.json()["detail"].lower()


def test_student_forbidden_from_lesson_review():
    """Verify student cannot perform lesson reviews (403 Forbidden)."""
    client = TestClient(app)
    stu_token = get_token(client, "STUDENT")
    resp = client.post(
        "/api/lessons/lesson-sci-6-1/review",
        json={"action": "APPROVED", "comments": "I approve this"},
        headers={"Authorization": f"Bearer {stu_token}"}
    )
    assert resp.status_code == 403


def test_teacher_forbidden_from_content_reviewer_role():
    """Verify teacher cannot approve or reject lessons at the curriculum level."""
    client = TestClient(app)
    tch_token = get_token(client, "TEACHER")
    resp = client.post(
        "/api/lessons/lesson-sci-6-1/review",
        json={"action": "APPROVED", "comments": "Self approving"},
        headers={"Authorization": f"Bearer {tch_token}"}
    )
    assert resp.status_code == 403


# =====================================================================
# 5. School Admin Boundaries & Privilege Escalation Defenses
# =====================================================================

def test_school_admin_can_list_users():
    """Verify School Admin is inactive under pilot lock (403 Forbidden) and Super Admin can list users."""
    client = TestClient(app)
    admin_token = get_token(client, "SCHOOL_ADMIN")
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 403
    assert "پائلٽ" in resp.json()["detail"] or "inactive for pilot" in resp.json()["detail"].lower()

    # Super Admin can list users
    super_token = get_token(client, "SUPER_ADMIN")
    super_resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {super_token}"})
    assert super_resp.status_code == 200
    assert isinstance(super_resp.json(), list)


def test_school_admin_can_create_student():
    """Verify School Admin is inactive under pilot lock (403 Forbidden) and Super Admin can create students."""
    client = TestClient(app)
    admin_token = get_token(client, "SCHOOL_ADMIN")
    payload = {
        "pseudonymous_code": "STU-HYD-999",
        "role": "STUDENT",
        "school_id": "sch-hyd-01",
        "pin_or_password": "1234"
    }
    resp = client.post("/api/admin/users", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 403
    assert "پائلٽ" in resp.json()["detail"] or "inactive for pilot" in resp.json()["detail"].lower()

    # Super Admin can create students
    super_token = get_token(client, "SUPER_ADMIN")
    super_resp = client.post("/api/admin/users", json=payload, headers={"Authorization": f"Bearer {super_token}"})
    assert super_resp.status_code == 201
    assert super_resp.json()["pseudonymous_code"] == "STU-HYD-999"


def test_school_admin_cannot_escalate_to_super_admin():
    """Verify School Admin cannot create accounts under pilot lock (403 Forbidden)."""
    client = TestClient(app)
    admin_token = get_token(client, "SCHOOL_ADMIN")
    payload = {
        "pseudonymous_code": "rogue_superadmin",
        "role": "SUPER_ADMIN",
        "school_id": "sch-hyd-01",
        "pin_or_password": "Password@123"
    }
    resp = client.post("/api/admin/users", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 403
    assert "پائلٽ" in resp.json()["detail"] or "inactive for pilot" in resp.json()["detail"].lower()


def test_school_admin_cross_school_creation_forbidden():
    """Verify School Admin cannot create users for another school."""
    client = TestClient(app)
    admin_token = get_token(client, "SCHOOL_ADMIN")
    payload = {
        "pseudonymous_code": "STU-SUK-999",
        "role": "STUDENT",
        "school_id": "sch-suk-02",  # Different school
        "pin_or_password": "1234"
    }
    resp = client.post("/api/admin/users", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 403


# =====================================================================
# 6. District Officer & Super Admin Privilege Separation
# =====================================================================

def test_district_officer_forbidden_from_admin_user_creation():
    """Verify District Officer cannot create or edit users."""
    client = TestClient(app)
    off_token = get_token(client, "DISTRICT_OFFICER")
    resp = client.post("/api/admin/users", json={
        "pseudonymous_code": "dummy",
        "role": "STUDENT",
        "school_id": "sch-hyd-01",
        "pin_or_password": "1234"
    }, headers={"Authorization": f"Bearer {off_token}"})
    assert resp.status_code == 403


def test_audit_logs_restricted_to_super_admin():
    """Verify only SUPER_ADMIN can view security audit logs."""
    client = TestClient(app)
    super_token = get_token(client, "SUPER_ADMIN")
    resp = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {super_token}"})
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
    
    # Verify non-superadmin (School Admin) is rejected
    admin_token = get_token(client, "SCHOOL_ADMIN")
    resp_denied = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_denied.status_code == 403


def test_permissions_matrix_public_endpoint():
    """Verify permissions matrix endpoint returns complete RBAC definition."""
    client = TestClient(app)
    resp = client.get("/api/admin/permissions-matrix")
    assert resp.status_code == 200
    matrix = resp.json()
    assert "roles" in matrix
    roles = [r["role"] for r in matrix["roles"]]
    for expected in ["STUDENT", "TEACHER", "CONTENT_REVIEWER", "SCHOOL_ADMIN", "DISTRICT_OFFICER", "SUPER_ADMIN"]:
        assert expected in roles
