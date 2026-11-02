"""Tests for AI-Managed Homework & Assignments Lifecycle (Zero Admin Workload).
Verifies:
1. Automatic assignment generation grounded in STBB curriculum with RAG and citations.
2. Question diversity: MCQs, Short Answers, Numerical/Step-by-step, and Descriptive questions with rubrics.
3. Class-based automated distribution and notifications.
4. Autonomous AI grading: objective keys, mathematical calculations, and rubric-based text evaluation.
5. Quality assurance gates: Low-confidence/ambiguity -> NEEDS_RETRY.
6. Automated retry job execution.
7. IDOR isolation and deadline enforcement.
8. Zero Admin Workload: complete cycle functions without human intervention.
Authored under agency-ai-engineer and agency-test-automation-engineer.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum
from src.services.auth_service import auth_service


@pytest.fixture(autouse=True)
def setup_ai_homework_test_db():
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "ai_homework_test.db"
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


def test_ai_autonomous_assignment_generation_from_stbb_curriculum():
    """Verify AI generates homework directly from STBB lessons with question rubrics and source references."""
    client = TestClient(app)
    admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")

    req_payload = {
        "class_level": 6,
        "subject": "Science",
        "question_count": 3,
        "auto_publish": True
    }
    resp = client.post(
        "/api/assignments/ai/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=req_payload
    )
    assert resp.status_code == 201
    asg = resp.json()
    assert asg["id"].startswith("asg-ai-")
    assert asg["target_class_level"] == 6
    assert asg["status"] == "PUBLISHED"
    assert asg["generation_source"] == "AI_RAG_STBB"
    assert "سنڌ ٽيڪسٽ بڪ بورڊ" in asg["source_reference"]

    # Verify structured questions and rubrics
    assert len(asg["questions"]) >= 3
    q_types = [q["question_type"] for q in asg["questions"]]
    assert "MCQ" in q_types
    assert "NUMERICAL" in q_types or "SHORT_ANSWER" in q_types

    # Verify each question has rubrics and citations
    for q in asg["questions"]:
        assert q["max_marks"] > 0
        assert q["rubric_guidelines"] is not None
        assert q["source_reference"] is not None


def test_ai_assignment_distribution_and_student_notifications():
    """Verify published assignments automatically notify students and appear in their feeds."""
    client = TestClient(app)
    admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")
    stu_token = auth_service.create_session_token("usr-stu-101", "STUDENT")

    # Generate assignment
    gen_resp = client.post(
        "/api/assignments/ai/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"class_level": 6, "subject": "Science", "question_count": 2, "auto_publish": True}
    )
    asg_id = gen_resp.json()["id"]

    # Student checks assignment list
    list_resp = client.get(
        "/api/assignments?class_level=6&subject=Science",
        headers={"Authorization": f"Bearer {stu_token}"}
    )
    assert list_resp.status_code == 200
    assignments = list_resp.json()
    matched = [a for a in assignments if a["id"] == asg_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "PUBLISHED"

    # Student checks in-app notifications
    notif_resp = client.get(
        "/api/assignments/notifications",
        headers={"Authorization": f"Bearer {stu_token}"}
    )
    assert notif_resp.status_code == 200
    notifs = notif_resp.json()
    assert len(notifs) >= 1
    asg_notif = next((n for n in notifs if n["reference_id"] == asg_id), None)
    assert asg_notif is not None
    assert asg_notif["notification_type"] == "ASSIGNMENT_AVAILABLE"


def test_ai_autonomous_grading_objective_and_numerical():
    """Verify AI grades MCQs and mathematical numericals deterministically without teacher intervention."""
    client = TestClient(app)
    admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")
    stu_token = auth_service.create_session_token("usr-stu-101", "STUDENT")

    # 1. Generate assignment with MCQ and Numerical questions
    gen_resp = client.post(
        "/api/assignments/ai/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"class_level": 6, "subject": "Science", "question_count": 2, "auto_publish": True}
    )
    asg = gen_resp.json()
    asg_id = asg["id"]
    q1 = asg["questions"][0] # MCQ
    q2 = asg["questions"][1] # Numerical

    # 2. Student submits answers
    submit_payload = {
        "submission_text": "منهنجا سمورا جواب هيٺ ڏنل آهن.",
        "answers": {
            q1["id"]: q1["correct_answer"], # Exact correct option
            q2["id"]: "حساب جو فارمولا: 10 * 2 * 5 = 100 گرام." # Contains exact numerical answer 100
        }
    }
    sub_resp = client.post(
        f"/api/assignments/{asg_id}/submit",
        headers={"Authorization": f"Bearer {stu_token}"},
        json=submit_payload
    )
    assert sub_resp.status_code == 200
    result = sub_resp.json()

    # Zero Admin Workload: Result is immediately graded autonomously
    assert result["is_graded"] is True
    assert result["graded_by"] == "AI_TUTOR_AUTO"
    assert result["grading_status"] == "GRADED"
    assert result["marks_awarded"] > 0
    assert len(result["grading_details"]) == 2

    # Verify MCQ evaluation
    q1_result = result["grading_details"][0]
    assert q1_result["is_correct"] is True
    assert q1_result["marks_awarded"] == q1["max_marks"]

    # Verify Numerical evaluation
    q2_result = result["grading_details"][1]
    assert q2_result["is_correct"] is True
    assert q2_result["marks_awarded"] == q2["max_marks"]
    assert "100" in q2_result["feedback_sindhi"]


def test_ai_autonomous_grading_descriptive_and_partial_credit():
    """Verify AI grades descriptive text against curriculum rubrics with calibrated partial credit."""
    client = TestClient(app)
    admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")
    stu_token = auth_service.create_session_token("usr-stu-101", "STUDENT")

    # Generate 4-question assignment (includes descriptive)
    gen_resp = client.post(
        "/api/assignments/ai/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"class_level": 6, "subject": "Science", "question_count": 4, "auto_publish": True}
    )
    asg = gen_resp.json()
    asg_id = asg["id"]
    q_desc = asg["questions"][2] # Short/descriptive

    # Student submits partial answer with relevant keywords
    sub_payload = {
        "submission_text": "ٻوٽن ۾ فوٽوسنٿيسز سج جي روشني ۽ پاڻي ذريعي کاڌو تيار ڪرڻ جو عمل آهي جنهن ۾ آڪسيجن خارج ٿئي ٿي.",
        "answers": {
            q_desc["id"]: "ٻوٽن ۾ فوٽوسنٿيسز سج جي روشني ۽ پاڻي ذريعي کاڌو تيار ڪرڻ جو عمل آهي."
        }
    }
    sub_resp = client.post(
        f"/api/assignments/{asg_id}/submit",
        headers={"Authorization": f"Bearer {stu_token}"},
        json=sub_payload
    )
    assert sub_resp.status_code == 200
    res = sub_resp.json()
    assert res["is_graded"] is True
    assert res["marks_awarded"] > 0
    assert "شاباس" in res["teacher_feedback"] or "درست" in res["teacher_feedback"] or "ڪوشش" in res["teacher_feedback"]


def test_ai_quality_assurance_gate_and_retry_job():
    """Verify low-confidence or ambiguous submissions are gated into NEEDS_RETRY and resolved by background retry job."""
    client = TestClient(app)
    admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")
    stu_token = auth_service.create_session_token("usr-stu-101", "STUDENT")

    # Update policy to set strict confidence threshold
    policy_resp = client.get("/api/assignments/policy", headers={"Authorization": f"Bearer {admin_token}"})
    policy_data = policy_resp.json()
    policy_data["confidence_threshold"] = 0.99 # Very high threshold to test quality gate
    client.put("/api/assignments/policy", headers={"Authorization": f"Bearer {admin_token}"}, json=policy_data)

    # Generate assignment
    gen_resp = client.post(
        "/api/assignments/ai/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"class_level": 6, "subject": "Science", "question_count": 2, "auto_publish": True}
    )
    asg_id = gen_resp.json()["id"]

    # Student submits brief ambiguous answer
    sub_resp = client.post(
        f"/api/assignments/{asg_id}/submit",
        headers={"Authorization": f"Bearer {stu_token}"},
        json={"submission_text": "جواب"}
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()

    # Should be held in NEEDS_RETRY rather than fabricating marks
    assert sub_data["grading_status"] == "NEEDS_RETRY"
    assert sub_data["marks_awarded"] is None

    # Check exceptions dashboard
    ex_resp = client.get("/api/assignments/exceptions", headers={"Authorization": f"Bearer {admin_token}"})
    assert ex_resp.status_code == 200
    ex_list = ex_resp.json()
    assert any(e["id"] == sub_data["id"] for e in ex_list)

    # Restore realistic threshold and run automated retry job
    policy_data["confidence_threshold"] = 0.65
    client.put("/api/assignments/policy", headers={"Authorization": f"Bearer {admin_token}"}, json=policy_data)

    retry_resp = client.post("/api/assignments/jobs/retry-gradings", headers={"Authorization": f"Bearer {admin_token}"})
    assert retry_resp.status_code == 200
    assert retry_resp.json()["retried_count"] >= 1

    # Verify submission is now graded
    detail_resp = client.get(f"/api/assignments/{asg_id}", headers={"Authorization": f"Bearer {stu_token}"})
    assert detail_resp.status_code == 200
    my_sub = detail_resp.json()["my_submission"]
    assert my_sub["grading_status"] == "GRADED"


def test_assignment_deadline_enforcement_and_idor_protection():
    """Verify deadline enforcement and cross-student IDOR security."""
    client = TestClient(app)
    admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")
    stu1_token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    stu2_token = auth_service.create_session_token("usr-stu-102", "STUDENT")

    # Create expired assignment with late submissions disabled
    policy = client.get("/api/assignments/policy", headers={"Authorization": f"Bearer {admin_token}"}).json()
    policy["allow_late_submissions"] = False
    client.put("/api/assignments/policy", headers={"Authorization": f"Bearer {admin_token}"}, json=policy)

    asg_resp = client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "course_id": "crs-sci-6",
            "title_sindhi": "مدو گذريل اسائينمينٽ",
            "description_sindhi": "هي پڙهو",
            "due_date": "2020-01-01T00:00:00Z", # Past date
            "max_marks": 10
        }
    )
    asg_id = asg_resp.json()["id"]

    # Student 1 attempts to submit expired assignment -> Rejected
    expired_resp = client.post(
        f"/api/assignments/{asg_id}/submit",
        headers={"Authorization": f"Bearer {stu1_token}"},
        json={"submission_text": "منهنجو جواب"}
    )
    assert expired_resp.status_code == 400
    assert "گذري چڪي آهي" in expired_resp.json()["detail"]

    # Restore policy
    policy["allow_late_submissions"] = True
    client.put("/api/assignments/policy", headers={"Authorization": f"Bearer {admin_token}"}, json=policy)

    # Student 1 submits valid assignment
    asg2 = client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "course_id": "crs-sci-6",
            "title_sindhi": "فعال اسائينمينٽ",
            "description_sindhi": "تفصيل",
            "due_date": "2030-01-01T00:00:00Z",
            "max_marks": 10
        }
    ).json()

    client.post(
        f"/api/assignments/{asg2['id']}/submit",
        headers={"Authorization": f"Bearer {stu1_token}"},
        json={"submission_text": "شاگرد 1 جو ڳجهو جواب"}
    )

    # Student 2 views assignment detail -> Student 2 must NOT see Student 1's submission
    stu2_view = client.get(
        f"/api/assignments/{asg2['id']}",
        headers={"Authorization": f"Bearer {stu2_token}"}
    )
    assert stu2_view.status_code == 200
    assert stu2_view.json()["my_submission"] is None # Clean state for Student 2
