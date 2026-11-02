"""Isolated integration checks for invite enrollment and the two active roles."""

import pytest
from fastapi.testclient import TestClient

from data.seed_curriculum import seed_sdc_curriculum
from src.api.app import app
from src.config import settings
from src.database.session import get_db, init_db
from src.services.auth_service import auth_service


@pytest.fixture
def flow(tmp_path):
    db_path = tmp_path / "student_admin_flow.db"
    previous = (settings.database_path, settings.environment, settings.secret_key, settings.cors_allowed_origins, settings.allow_test_query_auth)
    settings.database_path = str(db_path)
    settings.environment = "test"
    settings.secret_key = "isolated-test-secret-do-not-use-in-production-0001"
    settings.cors_allowed_origins = ""
    settings.allow_test_query_auth = False
    init_db(str(db_path))
    seed_sdc_curriculum(str(db_path))
    try:
        with TestClient(app) as client:
            admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")
            student_token = auth_service.create_session_token("usr-stu-101", "STUDENT")
            yield client, db_path, admin_token, student_token
    finally:
        settings.database_path, settings.environment, settings.secret_key, settings.cors_allowed_origins, settings.allow_test_query_auth = previous


def test_invite_enrollment_hashes_and_consumes_code_once(flow):
    client, db_path, admin_token, _ = flow
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    invite_response = client.post("/api/admin/student-invites", headers=admin_headers, json={"expires_in_days": 7})
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()["invite_code"]

    with get_db(str(db_path)) as conn:
        stored = conn.execute("SELECT code_hash, used_by FROM student_invites").fetchone()
        assert stored["code_hash"] != invite
        assert stored["used_by"] is None

    signup = client.post("/api/auth/register", json={
        "invite_code": invite,
        "full_name": "شاگرد آزمائشي",
        "pin": "4321",
        "class_level": 6,
    })
    assert signup.status_code == 201, signup.text
    data = signup.json()
    assert data["role"] == "STUDENT"
    assert data["school_id"] is None
    student_login = client.post("/api/auth/login/student", json={
        "student_code": data["pseudonymous_code"],
        "pin": "4321",
    })
    assert student_login.status_code == 200, student_login.text
    assert student_login.json()["user_id"] == data["user_id"]

    duplicate = client.post("/api/auth/register", json={
        "invite_code": invite,
        "full_name": "ٻيو شاگرد",
        "pin": "1234",
        "class_level": 6,
    })
    assert duplicate.status_code == 400
    with get_db(str(db_path)) as conn:
        invite_row = conn.execute("SELECT used_by FROM student_invites").fetchone()
        student = conn.execute("SELECT role, pin_hash FROM users WHERE id=?", (data["user_id"],)).fetchone()
        assert invite_row["used_by"] == data["user_id"]
        assert student["role"] == "STUDENT"
        assert student["pin_hash"] != "4321"


def test_admin_progress_list_and_dashboard_ownership(flow):
    client, _, admin_token, student_token = flow
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    invite = client.post("/api/admin/student-invites", headers=admin_headers, json={}).json()["invite_code"]
    created = client.post("/api/auth/register", json={"invite_code": invite, "full_name": "شاگرد 2", "pin": "5678", "class_level": 6}).json()

    forbidden = client.get("/api/admin/students/progress", headers=student_headers)
    assert forbidden.status_code == 403
    admin_list = client.get("/api/admin/students/progress?limit=10&offset=0", headers=admin_headers)
    assert admin_list.status_code == 200, admin_list.text
    payload = admin_list.json()
    assert payload["total"] >= 4
    assert payload["summary"]["students"] >= 4
    assert any(row["student_code"] == created["pseudonymous_code"] for row in payload["items"])

    own_dashboard = client.get("/api/dashboards/student", headers=student_headers)
    assert own_dashboard.status_code == 200
    other_student = client.get(f"/api/dashboards/student?user_id={created['user_id']}", headers=student_headers)
    assert other_student.status_code == 403
    admin_dashboard = client.get(
        f"/api/dashboards/student?user_id={created['user_id']}&course_id=crs-math-6",
        headers=admin_headers,
    )
    assert admin_dashboard.status_code == 200, admin_dashboard.text
    assert admin_dashboard.json()["student_code"] == created["pseudonymous_code"]


def test_legacy_staff_account_is_not_active(flow):
    client, _, _, _ = flow
    legacy_token = auth_service.create_session_token("usr-tch-01", "TEACHER")
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy_token}"})
    assert response.status_code == 403


def test_production_settings_require_secret_and_reject_wildcard_cors():
    previous = (settings.environment, settings.secret_key, settings.cors_allowed_origins)
    try:
        settings.environment = "production"
        settings.secret_key = "sdc-dev-secret-key-2026"
        settings.cors_allowed_origins = "https://school.example"
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            settings.validate_production_settings()
        settings.secret_key = "production-test-secret-that-is-long-enough-0001"
        settings.cors_allowed_origins = "*"
        with pytest.raises(RuntimeError, match="wildcard"):
            settings.validate_production_settings()
    finally:
        settings.environment, settings.secret_key, settings.cors_allowed_origins = previous


def test_quiz_runs_selected_provider_and_persists_inference_provenance(flow, monkeypatch):
    """Exercise the real quiz orchestration without loading a multi-GB model in tests."""
    import re
    from src.services import assessment_quiz_service as quiz_module

    client, db_path, _, student_token = flow

    class FakeInferenceProvider:
        provider_type = "TEST_OPENAI_COMPATIBLE_LLM"
        model_name = "test-grounded-model"
        last_quiz_inference = False
        last_quiz_request_id = None

        def generate_draft_quiz_questions(self, lesson_title, context_text, count=3):
            self.last_quiz_inference = False
            self.last_quiz_request_id = None
            lesson_id = re.search(r"LESSON_ID=([^ |]+)", context_text).group(1)
            citation = re.search(r"CITATION=(.*?) \| TOPIC=", context_text).group(1)
            self.last_quiz_inference = True
            self.last_quiz_request_id = "test-inference-request-1"
            return [{
                "text_sindhi": f"هي نصابي سوال نمبر {i} ڪهڙي سبق سان لاڳاپيل آهي؟",
                "options": [f"جواب الف {i}", f"جواب ب {i}", f"جواب ج {i}", f"جواب د {i}"],
                "correct_answer_index": 0,
                "explanation_sindhi": "چونڊيل درسي متن مطابق.",
                "topic": lesson_title,
                "lesson_id": lesson_id,
                "citation": citation,
            } for i in range(1, count + 1)]

    provider = FakeInferenceProvider()
    monkeypatch.setattr(quiz_module, "get_ai_system_status", lambda: {
        "can_attempt_inference": True,
        "active_provider_type": provider.provider_type,
        "active_model_name": provider.model_name,
    })
    monkeypatch.setattr(quiz_module, "get_ai_provider", lambda: provider)

    response = client.post(
        "/api/quiz/generate",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"class_level": 6, "subject": "Science", "lesson_ids": ["lesson-sci-6-1"], "question_count": 2},
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["provider_type"] == "TEST_OPENAI_COMPATIBLE_LLM"
    assert result["model_name"] == "test-grounded-model"
    assert result["inference_status"] == "LIVE_INFERENCE_SUCCEEDED"
    assert result["inference_request_id"] == "test-inference-request-1"
    assert result["is_live_ai"] is True
    assert all(q["lesson_id"] == "lesson-sci-6-1" for q in result["questions"])
    assert all("correct_answer_index" not in q for q in result["questions"])

    with get_db(str(db_path)) as conn:
        saved = conn.execute("SELECT provider_used, model_used, inference_request_id, inference_status, is_live_ai FROM quiz_sessions WHERE id=?", (result["session_id"],)).fetchone()
        assert tuple(saved) == ("TEST_OPENAI_COMPATIBLE_LLM", "test-grounded-model", "test-inference-request-1", "LIVE_INFERENCE_SUCCEEDED", 1)


def test_quiz_returns_unavailable_without_claiming_ai_when_provider_cannot_run(flow, monkeypatch):
    from fastapi import HTTPException
    from src.services import assessment_quiz_service as quiz_module

    client, db_path, _, student_token = flow

    class OfflineProvider:
        provider_type = "LOCAL_TRANSFORMERS_NEURAL_ENGINE"
        model_name = "configured-but-not-running"
        last_quiz_inference = False
        last_quiz_request_id = None

        def generate_draft_quiz_questions(self, **kwargs):
            return []

    provider = OfflineProvider()
    monkeypatch.setattr(quiz_module, "get_ai_system_status", lambda: {"can_attempt_inference": False})
    monkeypatch.setattr(quiz_module, "get_ai_provider", lambda: provider)
    response = client.post(
        "/api/quiz/generate",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"class_level": 6, "subject": "Science", "lesson_ids": ["lesson-sci-6-1"], "question_count": 1},
    )
    assert response.status_code == 503, response.text
    with get_db(str(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM quiz_sessions").fetchone()[0] == 0
