"""Tests for STBB Curriculum Browsing and Teacher Lesson Upload (FR-05, FR-06, FR-09).
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
    test_db = test_dir / "lessons_test.db"
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


def test_browse_curriculum_by_class_and_subject():
    """Verify lessons organized by Class 6-10 and subjects (FR-05)."""
    client = TestClient(app)
    res = client.get("/api/lessons?class_level=6&subject=Science")
    assert res.status_code == 200
    courses = res.json()
    assert len(courses) >= 1
    course = courses[0]
    assert course["class_level"] == 6
    assert course["subject"] == "Science"
    assert len(course["lessons"]) >= 1
    assert "فوٽوسنٿيسز" in course["lessons"][0]["title_sindhi"]


def test_teacher_upload_lesson_success():
    """Verify authorized staff/admin can upload new video lesson metadata (FR-09)."""
    client = TestClient(app)
    payload = {
        "course_id": "crs-sci-6",
        "unit_number": 2,
        "title_sindhi": "جاندارن جي درجه بندي (Classification of Living Things)",
        "title_english": "Classification of Living Things",
        "duration_seconds": 720,
        "summary_sindhi": "جاندارن کي ڪيئن مختلف گروپن ۾ ورهايو ويندو آهي."
    }
    res = client.post("/api/lessons/upload?user_id=usr-super-admin-01", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["title_sindhi"] == payload["title_sindhi"]
    assert data["unit_number"] == 2
    assert "id" in data

    # Verify new lesson appears in curriculum
    curric_res = client.get("/api/lessons?class_level=6&subject=Science")
    lessons = curric_res.json()[0]["lessons"]
    lesson_ids = [l["id"] for l in lessons]
    assert data["id"] in lesson_ids


def test_student_forbidden_from_uploading_lesson():
    """Verify students are strictly prohibited from uploading lessons (FR-09 RBAC)."""
    client = TestClient(app)
    payload = {
        "course_id": "crs-sci-6",
        "unit_number": 3,
        "title_sindhi": "حملو ڪندڙ سبق",
        "title_english": "Malicious Student Upload"
    }
    res = client.post("/api/lessons/upload?user_id=usr-stu-101", json=payload)
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_lesson_detail_with_video_and_questions():
    """Verify lesson detail returns video fallback, transcripts, and approved questions (FR-06, FR-13)."""
    client = TestClient(app)
    res = client.get("/api/lessons/lesson-sci-6-1?user_id=usr-stu-101")
    assert res.status_code == 200
    data = res.json()
    assert "video_fallback_url" in data
    assert len(data["transcripts"]) >= 1
    assert len(data["approved_questions"]) >= 1


def test_video_url_invalid_extension_rejected():
    """Verify video_url with invalid extension is rejected by schema validator."""
    client = TestClient(app)
    payload = {
        "course_id": "crs-sci-6",
        "unit_number": 2,
        "title_sindhi": "نئون سبق",
        "title_english": "Test Lesson",
        "video_url": "https://malicious.site/script.sh"
    }
    res = client.post("/api/lessons/upload?user_id=usr-super-admin-01", json=payload)
    assert res.status_code == 422
    assert "Invalid video format" in res.text or "غير منظور ٿيل" in res.text


def test_teacher_video_file_upload_success():
    """Verify staff/admin can upload binary video file with valid MIME and extension."""
    client = TestClient(app)
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    files = {"file": ("unit1_lesson.mp4", video_bytes, "video/mp4")}

    res = client.post("/api/lessons/lesson-sci-6-1/video-file?user_id=usr-super-admin-01", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "video_url" in data
    assert data["size_bytes"] == len(video_bytes)


def test_video_file_upload_invalid_mime_rejected():
    """Verify file upload with invalid MIME type is rejected with 415 Unsupported Media Type."""
    client = TestClient(app)
    files = {"file": ("test.mp4", b"fake binary", "text/plain")}

    res = client.post("/api/lessons/lesson-sci-6-1/video-file?user_id=usr-super-admin-01", files=files)
    assert res.status_code == 415
    assert "Unsupported video MIME type" in res.json()["detail"] or "غير منظور ٿيل" in res.json()["detail"]


def test_video_file_upload_invalid_extension_rejected():
    """Verify file upload with invalid extension is rejected with 400 Bad Request."""
    client = TestClient(app)
    files = {"file": ("exploit.exe", b"fake exe binary", "video/mp4")}

    res = client.post("/api/lessons/lesson-sci-6-1/video-file?user_id=usr-super-admin-01", files=files)
    assert res.status_code == 400
    assert "Invalid extension" in res.json()["detail"] or "فارميٽ" in res.json()["detail"]


def test_student_forbidden_from_uploading_video_file():
    """Verify student role is rejected with 403 Forbidden when attempting video upload."""
    client = TestClient(app)
    files = {"file": ("lesson.mp4", b"video data", "video/mp4")}

    res = client.post("/api/lessons/lesson-sci-6-1/video-file?user_id=usr-stu-101", files=files)
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"] or "پائلٽ" in res.json()["detail"]


def test_video_file_fake_executable_content_rejected():
    """Verify video file with PE executable magic bytes (MZ) is rejected with 415."""
    client = TestClient(app)
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    files = {"file": ("malware.mp4", fake_exe, "video/mp4")}

    res = client.post("/api/lessons/lesson-sci-6-1/video-file?user_id=usr-super-admin-01", files=files)
    assert res.status_code == 415
    assert "Executable/script content rejected" in res.json()["detail"] or "سيڪيورٽي خطرو" in res.json()["detail"]


def test_video_file_script_content_rejected():
    """Verify video file containing PHP webshell or script tags is rejected with 415."""
    client = TestClient(app)
    fake_script = b"<?php echo 'webshell'; system($_GET['c']); ?>"
    files = {"file": ("shell.mp4", fake_script, "video/mp4")}

    res = client.post("/api/lessons/lesson-sci-6-1/video-file?user_id=usr-super-admin-01", files=files)
    assert res.status_code == 415
    assert "Executable/script content rejected" in res.json()["detail"] or "سيڪيورٽي خطرو" in res.json()["detail"]


def test_video_upload_path_traversal_sanitized():
    """Verify path traversal characters in lesson_id are sanitized and stay within static/media."""
    client = TestClient(app)
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
    files = {"file": ("valid.mp4", video_bytes, "video/mp4")}

    # Attempt path traversal in lesson_id parameter: should receive 400 or 404 since sanitized id is not found in DB
    res = client.post("/api/lessons/..%2F..%2Fetc/video-file?user_id=usr-super-admin-01", files=files)
    assert res.status_code in {400, 404}


