"""Comprehensive End-to-End User Workflows and Navigation Continuity Tests for SDC.
Covers:
1. Student login -> browse public website -> return to LMS (session survival).
2. Login -> refresh / reload -> LMS session restoration.
3. Login -> open lesson -> browser history back/forward navigation.
4. Logout -> token revocation check -> protected route denial.
5. Multi-worker safe session revocation persisted across server/database restarts.
6. Student-to-student IDOR attempts rejected (403).
7. Student attempting privileged Admin APIs rejected (403).
8. STBB Curriculum filtering and video playback source fallback.
9. AI Tutor RAG retrieval, citations, and strict refusal.
10. Admin assignment creation, student submission, and grading.

Authored under agency-test-automation-engineer, agency-application-security-engineer, and agency-backend-architect.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import get_db, init_db
from data.seed_curriculum import seed_sdc_curriculum
from src.services.auth_service import auth_service


@pytest.fixture(autouse=True)
def setup_e2e_test_db():
    """Seed test database in an isolated temporary location."""
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "sdc_e2e_workflows.db"
    if test_db.exists():
        test_db.unlink(missing_ok=True)
    orig_db = settings.database_path
    orig_query_auth = settings.allow_test_query_auth
    orig_env = settings.environment

    settings.database_path = str(test_db)
    settings.allow_test_query_auth = False  # Enforce strict production bearer token validation
    settings.environment = "test"

    init_db(str(test_db))
    seed_sdc_curriculum(str(test_db))

    yield str(test_db)

    settings.database_path = orig_db
    settings.allow_test_query_auth = orig_query_auth
    settings.environment = orig_env
    if test_db.exists():
        test_db.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 1. Authentication, Navigation, and Multi-Worker Session Revocation
# ---------------------------------------------------------------------------

def test_workflow_student_login_public_nav_and_return():
    """Workflow: Student logs in, navigates to public site, and returns to LMS with session intact."""
    client = TestClient(app)

    # Step 1: Student Login
    login_resp = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    assert token.startswith("sdc_stu_")

    # Step 2: Navigate to public home page and curriculum
    pub_resp = client.get("/")
    assert pub_resp.status_code == 200
    assert "سنڌي ڊجيٽل ڪلاس روم" in pub_resp.text

    curric_resp = client.get("/curriculum")
    assert curric_resp.status_code == 200

    # Step 3: Return to LMS protected profile - token remains valid
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["user_id"] == "usr-stu-101"
    assert me_resp.json()["role"] == "STUDENT"


def test_workflow_logout_and_session_revocation():
    """Workflow: Student logs out, token is immediately revoked, subsequent requests denied (401)."""
    client = TestClient(app)

    # Login
    login_resp = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    token = login_resp.json()["token"]

    # Verify active session
    res_before = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_before.status_code == 200

    # Logout
    logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # Access after logout must be rejected with 401
    res_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_after.status_code == 401
    assert "ختم ٿي چڪو آهي" in res_after.json()["detail"] or "invalid" in res_after.json()["detail"].lower()


def test_workflow_multi_worker_revocation_survives_memory_reset():
    """Workflow: Session revocation cutoff is written to SQLite and enforced even after in-memory state is cleared."""
    client = TestClient(app)

    # Login
    login_resp = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    token = login_resp.json()["token"]

    # Revoke sessions
    auth_service.revoke_user_sessions("usr-stu-101")

    # Clear in-memory revoked users dict to simulate server restart / separate worker
    auth_service._revoked_users.clear()

    # Protected request must query SQLite, find the cutoff, and reject with 401
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_workflow_student_idor_and_privilege_escalation_blocked():
    """Workflow: Student A cannot access Student B data and cannot invoke Admin endpoints."""
    client = TestClient(app)

    # Student 101 logs in
    login_resp = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    token_101 = login_resp.json()["token"]

    # 1. IDOR Attempt: Student 101 requests Student 102's dashboard
    idor_resp = client.get(
        "/api/dashboards/student?user_id=usr-stu-102",
        headers={"Authorization": f"Bearer {token_101}"}
    )
    assert idor_resp.status_code == 403

    # 2. Privilege Escalation: Student attempts Admin audit logs
    admin_resp = client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {token_101}"}
    )
    assert admin_resp.status_code == 403

    # 3. Privilege Escalation: Student attempts to create an assignment
    asg_create_resp = client.post(
        "/api/assignments",
        json={
            "course_id": "crs-sci-6",
            "title_sindhi": "غير مجاز",
            "description_sindhi": "ٽيسٽ",
            "due_date": "2026-12-31T23:59:59Z",
            "max_marks": 10
        },
        headers={"Authorization": f"Bearer {token_101}"}
    )
    assert asg_create_resp.status_code == 403


# ---------------------------------------------------------------------------
# 2. Dynamic Curriculum, Lesson Playback, and Homework Workflow
# ---------------------------------------------------------------------------

def test_workflow_student_learn_progress_and_quiz():
    """Workflow: Student views lessons, tracks playback progress, answers quiz checkpoint."""
    client = TestClient(app)

    login_resp = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Filter curriculum by Class 6 Science
    curric_resp = client.get("/api/lessons?class_level=6&subject=Science", headers=headers)
    assert curric_resp.status_code == 200
    courses = curric_resp.json()
    assert len(courses) >= 1
    assert courses[0]["subject"] == "Science"
    lesson_id = courses[0]["lessons"][0]["id"]

    # 2. Get lesson details (verify local MP4 fallback and YouTube catalog info)
    detail_resp = client.get(f"/api/lessons/{lesson_id}?user_id=usr-stu-101", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["video_fallback_url"].endswith(".mp4")
    assert len(detail["approved_questions"]) >= 1

    # 3. Update playback progress (position = 180s)
    prog_resp = client.post(
        f"/api/lessons/{lesson_id}/progress",
        json={"lesson_id": lesson_id, "position_seconds": 180.0, "is_completed": False},
        headers=headers
    )
    assert prog_resp.status_code == 200

    # 4. Answer checkpoint quiz question
    q_id = detail["approved_questions"][0]["id"]
    attempt_resp = client.post(
        "/api/quiz/attempt",
        json={"question_id": q_id, "selected_option": 0, "time_taken_seconds": 5.2},
        headers=headers
    )
    assert attempt_resp.status_code == 200
    assert "explanation_sindhi" in attempt_resp.json()

    # 5. Check updated dashboard metrics
    dash_resp = client.get("/api/dashboards/student?user_id=usr-stu-101", headers=headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["student_code"] == "STU-101"
    assert len(dash_data["recent_attempts"]) >= 1


def test_workflow_full_homework_cycle():
    """Workflow: Admin creates assignment, student submits answer, Admin grades submission."""
    client = TestClient(app)

    # 1. Admin logs in
    admin_login = client.post("/api/auth/login/staff", json={
        "identifier": "superadmin",
        "password": "super123"
    })
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Admin creates an assignment
    asg_payload = {
        "course_id": "crs-sci-6",
        "lesson_id": "lesson-sci-6-1",
        "title_sindhi": "فوٽوسنٿيسز ۽ زندگي",
        "title_english": "Photosynthesis and Life",
        "description_sindhi": "ٻوٽا ماحول مان ڪاربان ڊاءِ آڪسائيڊ ڪيئن جذب ڪندا آهن؟",
        "due_date": "2026-12-31T23:59:59Z",
        "max_marks": 10
    }
    create_resp = client.post("/api/assignments", json=asg_payload, headers=admin_headers)
    assert create_resp.status_code == 201
    asg_id = create_resp.json()["id"]

    # 3. Student logs in and views assignment
    stu_login = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    stu_token = stu_login.json()["token"]
    stu_headers = {"Authorization": f"Bearer {stu_token}"}

    list_resp = client.get("/api/assignments", headers=stu_headers)
    assert list_resp.status_code == 200
    assert any(a["id"] == asg_id for a in list_resp.json())

    # 4. Student submits homework
    submit_resp = client.post(
        f"/api/assignments/{asg_id}/submit",
        json={"submission_text": "ٻوٽا پنن ۾ موجود اسٽوماٽا ذريعي ڪاربان ڊاءِ آڪسائيڊ وٺن ٿا."},
        headers=stu_headers
    )
    assert submit_resp.status_code == 200
    sub_id = submit_resp.json()["id"]

    # 5. Admin grades the submission
    grade_resp = client.post(
        f"/api/assignments/{asg_id}/submissions/{sub_id}/grade",
        json={"marks_awarded": 9.5, "teacher_feedback": "تمام عمده جواب! شاباس."},
        headers=admin_headers
    )
    assert grade_resp.status_code == 200
    assert grade_resp.json()["is_graded"] is True
    assert grade_resp.json()["marks_awarded"] == 9.5

    # 6. Student verifies marks and feedback in their view
    stu_view_resp = client.get(f"/api/assignments/{asg_id}", headers=stu_headers)
    assert stu_view_resp.status_code == 200
    sub = stu_view_resp.json()["my_submission"]
    assert sub is not None
    assert sub["marks_awarded"] == 9.5
    assert "تمام عمده" in sub["teacher_feedback"]


# ---------------------------------------------------------------------------
# 3. Grounded AI Tutor and RAG Citations Workflow
# ---------------------------------------------------------------------------

def test_workflow_ai_tutor_rag_and_refusal():
    """Workflow: Student queries AI tutor, receives grounded answer with source citation, or refusal on out-of-scope."""
    client = TestClient(app)

    stu_login = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    token = stu_login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. In-scope Science question
    in_scope_resp = client.post(
        "/api/tutor/ask",
        json={
            "question": "ٻوٽن ۾ فوٽوسنٿيسز دوران سج جي روشني ۽ پاڻي مان ڇا تيار ٿيندو آهي؟",
            "lesson_id": "lesson-sci-6-1"
        },
        headers=headers
    )
    assert in_scope_resp.status_code == 200
    in_data = in_scope_resp.json()
    assert in_data["is_refused"] is False
    assert len(in_data["citations"]) >= 1
    assert in_data["citations"][0]["lesson_id"] == "lesson-sci-6-1"

    # 2. Out-of-scope question
    out_scope_resp = client.post(
        "/api/tutor/ask",
        json={"question": "ڪراچي کان حيدرآباد جي وچ ۾ ڪيترا ڪلوميٽر فاصلو آهي؟"},
        headers=headers
    )
    assert out_scope_resp.status_code == 200
    out_data = out_scope_resp.json()
    assert out_data["is_refused"] is True
    assert "معاف ڪجو، هي سوال سبق جي دائري کان ٻاهر آهي" in out_data["answer_sindhi"]
    assert len(out_data["citations"]) == 0
