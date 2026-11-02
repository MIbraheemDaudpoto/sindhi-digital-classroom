"""Tests for FR-28 Teacher Assignments and Student Submissions.
Enforces assignment creation RBAC, student submission, teacher grading, and boundary checks.
Authored under agency-backend-architect and agency-test-automation-engineer.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum


@pytest.fixture(autouse=True)
def setup_test_db():
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "assignments_test.db"
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


def test_teacher_creates_assignment_success():
    """Verify administrator can create an assignment with due date and max marks (FR-28)."""
    client = TestClient(app)
    payload = {
        "course_id": "crs-sci-6",
        "lesson_id": "lesson-sci-6-1",
        "title_sindhi": "فوٽوسنٿيسز جا مرحلا لکو",
        "title_english": "Write stages of photosynthesis",
        "description_sindhi": "ٻوٽن ۾ روشني جي موجودگي ۾ خوراڪ تيار ڪرڻ جو پورو طريقو لکو.",
        "due_date": "2026-11-01T23:59:59Z",
        "max_marks": 10
    }
    resp = client.post("/api/assignments?user_id=usr-super-admin-01", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("asg-")
    assert data["title_sindhi"] == "فوٽوسنٿيسز جا مرحلا لکو"
    assert data["max_marks"] == 10
    assert data["created_by"] == "usr-super-admin-01"


def test_student_forbidden_from_creating_assignment():
    """Verify student role is strictly rejected (403 Forbidden) from creating assignments."""
    client = TestClient(app)
    payload = {
        "course_id": "crs-sci-6",
        "title_sindhi": "غير مجاز اسائنمينٽ",
        "description_sindhi": "هي شاگرد پاران ٺاهيل آهي.",
        "due_date": "2026-11-01T23:59:59Z",
        "max_marks": 10
    }
    resp = client.post("/api/assignments?user_id=usr-stu-101", json=payload)
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"] or "پائلٽ" in resp.json()["detail"] or "صرف" in resp.json()["detail"]


def test_student_submits_assignment_success():
    """Verify student can submit assignment text and retrieve status (FR-28)."""
    client = TestClient(app)

    # 1. Admin creates assignment
    create_payload = {
        "course_id": "crs-sci-6",
        "title_sindhi": "پاڻي ۽ آبي چڪر",
        "description_sindhi": "پاڻي جي بخار بڻجڻ ۽ برسات پوڻ جي مرحلن جي وضاحت ڪريو.",
        "due_date": "2026-12-01T12:00:00Z",
        "max_marks": 10
    }
    asg_resp = client.post("/api/assignments?user_id=usr-super-admin-01", json=create_payload)
    assert asg_resp.status_code == 201
    asg_id = asg_resp.json()["id"]

    # 2. Student submits assignment
    sub_payload = {
        "submission_text": "پاڻي گرمي پد وڌڻ سان بخار بڻجي هوا ۾ وڃي ٿو ۽ ٿڌو ٿي بادل ٺاهي ٿو."
    }
    sub_resp = client.post(f"/api/assignments/{asg_id}/submit?student_id=usr-stu-101", json=sub_payload)
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["assignment_id"] == asg_id
    assert sub_data["user_id"] == "usr-stu-101"
    assert sub_data["is_graded"] is False
    assert sub_data["marks_awarded"] is None

    # 3. Student views assignment detail, verifies their submission is attached
    detail_resp = client.get(f"/api/assignments/{asg_id}?user_id=usr-stu-101")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["my_submission"] is not None
    assert detail_data["my_submission"]["submission_text"] == sub_payload["submission_text"]


def test_teacher_grades_student_submission():
    """Verify admin can review submissions and assign marks and Sindhi feedback (FR-28)."""
    client = TestClient(app)

    # Create assignment
    asg_resp = client.post(
        "/api/assignments?user_id=usr-super-admin-01",
        json={
            "course_id": "crs-sci-6",
            "title_sindhi": "ڪلاس ورڪ ٽيسٽ",
            "description_sindhi": "وضاحت ڪريو",
            "due_date": "2026-12-01T12:00:00Z",
            "max_marks": 10
        }
    )
    asg_id = asg_resp.json()["id"]

    # Student submits
    sub_resp = client.post(
        f"/api/assignments/{asg_id}/submit?student_id=usr-stu-101",
        json={"submission_text": "منهنجو پورو جواب"}
    )
    sub_id = sub_resp.json()["id"]

    # Admin reviews submissions list
    subs_list_resp = client.get(f"/api/assignments/{asg_id}/submissions?user_id=usr-super-admin-01")
    assert subs_list_resp.status_code == 200
    assert len(subs_list_resp.json()) == 1

    # Admin grades submission
    grade_payload = {
        "marks_awarded": 8.5,
        "teacher_feedback": "تمام بهترين ڪوشش! اڳيان به اهڙي طرح محنت جاري رکو."
    }
    grade_resp = client.post(
        f"/api/assignments/{asg_id}/submissions/{sub_id}/grade?user_id=usr-super-admin-01",
        json=grade_payload
    )
    assert grade_resp.status_code == 200
    grade_data = grade_resp.json()
    assert grade_data["is_graded"] is True
    assert grade_data["marks_awarded"] == 8.5
    assert grade_data["graded_by"] == "usr-super-admin-01"
    assert "تمام بهترين" in grade_data["teacher_feedback"]


def test_grade_exceeding_max_marks_rejected():
    """Verify grading exceeding assignment max_marks is rejected with 400 Bad Request."""
    client = TestClient(app)

    asg_resp = client.post(
        "/api/assignments?user_id=usr-super-admin-01",
        json={
            "course_id": "crs-sci-6",
            "title_sindhi": "5 مارڪن وارو سوال",
            "description_sindhi": "مختصر جواب",
            "due_date": "2026-12-01T12:00:00Z",
            "max_marks": 5
        }
    )
    asg_id = asg_resp.json()["id"]

    sub_resp = client.post(
        f"/api/assignments/{asg_id}/submit?student_id=usr-stu-101",
        json={"submission_text": "جواب"}
    )
    sub_id = sub_resp.json()["id"]

    # Awarding 7 marks on 5-mark assignment
    over_resp = client.post(
        f"/api/assignments/{asg_id}/submissions/{sub_id}/grade?user_id=usr-super-admin-01",
        json={"marks_awarded": 7.0, "teacher_feedback": "Invalid"}
    )
    assert over_resp.status_code == 400
    assert "وڌيڪ آهن" in over_resp.json()["detail"]
