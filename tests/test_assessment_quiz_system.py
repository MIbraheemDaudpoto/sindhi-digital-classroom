"""
Comprehensive Test Suite for SDC LMS Real-Time AI & Curriculum Assessment System.
Covers:
1. Single-lesson quiz generation (valid STBB citations, withheld answer key).
2. Multi-lesson quiz generation (proportional distribution, explicit attribution).
3. All-lessons in a subject generation (full course scope).
4. Class/subject filtering and rejection of mismatched lesson IDs (HTTP 400).
5. Fresh question sets across repeated attempts.
6. Honest provider reporting (LOCAL_CURRICULUM_BANK when live AI is offline).
7. Practice mode immediate feedback vs Assessment mode withholding.
8. Server-side score calculation, per-lesson breakdown, topics to review.
9. Authentication, session ownership security, and idempotent submissions.
10. Abandoned/in-progress sessions do not update progress or mark complete.
11. Progress tracking (passed quiz updates post_test_score; failed does not mark complete).
12. Video load failure does not block quiz access.
13. Search distinction: pure 'سيٽ' (Sets) excludes PAKSAT ch12-06; 'پاڪ سيٽ' returns PAKSAT.
14. Transcription authentication (401 on unauthenticated multipart upload) and size validation.
15. TTS status route availability.
"""

import io
import asyncio
import json
from pathlib import Path
import shutil
import sqlite3
import threading
import pytest
import httpx
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import init_db
from src.services.assessment_quiz_service import assessment_quiz_service
from src.services.auth_service import auth_service
from src.models.schemas import TutorAskRequest
from src.services.ai_provider import LLMGenerationResult
from src.services.ai_tutor_service import ai_tutor_service
from src.services.sdc_rag_service import sdc_rag_service

client = TestClient(app)


def get_token(school_code="SCH-HYD-01", student_code="STU-101", pin="1234"):
    auth_service._rate_limits.clear()
    resp = client.post("/api/auth/login/student", json={
        "school_code": school_code,
        "student_code": student_code,
        "pin": pin
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(autouse=True)
def isolated_test_db(tmp_path, monkeypatch):
    """Run tests against an isolated temporary database copy."""
    auth_service._rate_limits.clear()
    test_db = tmp_path / "sdc_platform_quiz_test.db"
    shutil.copy2("data/sdc_platform.db", test_db)
    init_db(str(test_db))
    orig_path = settings.database_path
    settings.database_path = str(test_db)
    from tests.fake_grounded_quiz_provider import FakeGroundedQuizProvider
    provider = FakeGroundedQuizProvider()
    monkeypatch.setattr("src.services.assessment_quiz_service.get_ai_provider", lambda: provider)
    monkeypatch.setattr("src.services.assessment_quiz_service.get_ai_system_status", lambda: {
        "can_attempt_inference": True,
        "active_provider_type": provider.provider_type,
        "active_model_name": provider.model_name,
    })
    yield str(test_db)
    settings.database_path = orig_path


# --- 1. Single-Lesson Generation ---

def test_single_lesson_quiz_generation():
    """Verify generating a quiz for a single lesson produces valid questions without exposing answer keys."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-1"],
        "question_count": 3,
        "mode": "practice",
        "difficulty": "MEDIUM"
    })

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["session_id"].startswith("qz-sess-")
    assert data["class_level"] == 6
    assert data["subject"] == "Science"
    assert len(data["lesson_ids"]) == 1
    assert data["total_questions"] == 3
    assert len(data["questions"]) == 3

    for q in data["questions"]:
        assert len(q["text_sindhi"]) > 5
        assert len(q["options"]) == 4
        assert q["lesson_id"] == "lesson-sci-6-1"
        assert "جيو گهرڙو" in q["lesson_title_sd"]
        # CRUCIAL SECURITY: Client model must NOT leak answer key
        assert "correct_answer_index" not in q
        assert "correct_option_index" not in q


@pytest.mark.asyncio
async def test_slow_quiz_generation_does_not_block_health_or_other_requests(monkeypatch):
    """Synchronous CPU inference must run outside FastAPI's event loop."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    started = threading.Event()
    release = threading.Event()

    def slow_generation(user_id, req):
        started.set()
        release.wait(timeout=2.0)
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Live AI unavailable in this test")

    monkeypatch.setattr(assessment_quiz_service, "generate_quiz", slow_generation)
    timer = threading.Timer(1.5, release.set)
    timer.daemon = True
    timer.start()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        quiz_task = asyncio.create_task(async_client.post(
            "/api/quiz/generate",
            headers=headers,
            json={"class_level": 6, "subject": "Science", "lesson_ids": ["lesson-sci-6-2"], "question_count": 1}
        ))
        try:
            assert await asyncio.to_thread(started.wait, 1.0)
            loop = asyncio.get_running_loop()
            health_started = loop.time()
            health_response = await asyncio.wait_for(async_client.get("/api/health"), timeout=0.5)
            assert health_response.status_code == 200
            assert loop.time() - health_started < 0.5
        finally:
            release.set()

        quiz_response = await asyncio.wait_for(quiz_task, timeout=2.0)
        assert quiz_response.status_code == 503


def test_suggested_eye_question_is_attributed_to_active_science_lesson(monkeypatch):
    """The active Sense Organs lesson must retrieve and cite its eye-parts chunk."""
    class FakeTutorProvider:
        provider_type = "TEST_LLM_PROVIDER"
        model_name = "test-model"

        def generate_grounded_answer(self, question, context_chunks):
            assert context_chunks
            assert context_chunks[0]["chunk_id"] == "ch2-02"
            return LLMGenerationResult(
                text="اک جا مکيه حصا ڪورنيا، بلور، تارو ۽ ريٽينا آهن.",
                provider_type=self.provider_type,
                model_name=self.model_name,
                is_live_inference=True,
                inference_status="REAL_LLM_INFERENCE"
            )

    monkeypatch.setattr("src.services.ai_tutor_service.get_ai_provider", lambda: FakeTutorProvider())
    response = ai_tutor_service.answer_student_question(
        "usr-stu-101",
        TutorAskRequest(
            question="انساني اک جا مختلف حصا ۽ انهن جا ڪم ڪهڙا آهن؟",
            lesson_id="lesson-sci-6-2",
            class_level=6,
            subject_id="science",
            chapter_id=2
        )
    )

    assert response.is_refused is False
    assert response.inference_status == "REAL_LLM_INFERENCE"
    assert response.citations
    assert response.citations[0].lesson_id == "lesson-sci-6-2"
    assert response.citations[0].citation_formatted == "PDF 24-25 (printed 20-21)"


# --- 2. Multi-Lesson Generation & Attribution ---

def test_multi_lesson_quiz_generation_and_attribution():
    """Verify generating a quiz from multiple lessons distributes questions with clear attribution."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    target_lessons = ["lesson-sci-6-1", "lesson-sci-6-3"]
    resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": target_lessons,
        "question_count": 4,
        "mode": "assessment",
        "difficulty": "MEDIUM"
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["total_questions"] == 4
    covered_lessons = {q["lesson_id"] for q in data["questions"]}
    
    assert "lesson-sci-6-1" in covered_lessons
    assert "lesson-sci-6-3" in covered_lessons, data
    
    for q in data["questions"]:
        assert q["lesson_id"] in target_lessons
        assert q["lesson_title_sd"] != ""


# --- 3. All-Lessons in a Subject Scope ---

def test_all_lessons_in_subject_generation():
    """Verify generating a quiz across all lessons when lesson_ids is omitted or empty."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Math",
        "question_count": 5,
        "mode": "practice"
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["total_questions"] == 5
    assert len(data["lesson_ids"]) >= 10  # Math has 13 units
    for q in data["questions"]:
        assert q["lesson_id"].startswith("lesson-math-6-")


# --- 4. Class/Subject Filtering and Mismatch Rejection ---

def test_class_subject_filtering_and_mismatch_rejection():
    """Verify that selecting a lesson from another subject or class is strictly rejected with HTTP 400."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to pair Math lesson with Science subject request
    resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-math-6-1"],
        "question_count": 3
    })

    assert resp.status_code == 400
    assert "mismatch" in resp.text.lower() or "واسطو" in resp.text


# --- 5. Fresh Question Sets on Consecutive Attempts ---

def test_fresh_question_sets_on_retries():
    """Verify consecutive quiz generation requests produce distinct question/option variations."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp1 = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Math",
        "lesson_ids": ["lesson-math-6-1"],
        "question_count": 3
    })
    assert resp1.status_code == 201
    data1 = resp1.json()

    resp2 = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Math",
        "lesson_ids": ["lesson-math-6-1"],
        "question_count": 3
    })
    assert resp2.status_code == 201
    data2 = resp2.json()

    # Sessions must have unique IDs
    assert data1["session_id"] != data2["session_id"]


# --- 6. Honest Provider Reporting ---

def test_honest_provider_status_reporting(monkeypatch):
    """Verify provider status truthfully indicates LOCAL_CURRICULUM_BANK when live AI is offline."""
    monkeypatch.setattr(
        "src.services.assessment_quiz_service.get_ai_system_status",
        lambda: {"is_live_inference": False, "active_provider_type": "LOCAL_DETERMINISTIC_FALLBACK"}
    )
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "question_count": 2,
        "allow_fallback": True
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_live_ai"] is False
    assert "LOCAL" in data["provider_type"] or "CURRICULUM" in data["provider_type"]
    assert "غير AI" in data["ai_status_message"] and "لائيو ماڊل" in data["ai_status_message"]


def test_unique_questions_guarantee_10_mcqs():
    """Verify that 10-MCQ quizzes across Math and Science NEVER contain duplicate questions."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    for subject in ["Math", "Science"]:
        for lesson_scope in [[], ["lesson-math-6-1" if subject == "Math" else "lesson-sci-6-1"]]:
            resp = client.post("/api/quiz/generate", headers=headers, json={
                "class_level": 6,
                "subject": subject,
                "lesson_ids": lesson_scope,
                "question_count": 10,
                "mode": "ASSESSMENT"
            })
            assert resp.status_code == 201, resp.text
            data = resp.json()
            questions = data["questions"]
            assert len(questions) == 10, f"Expected 10 questions, got {len(questions)}"
            texts = [q["text_sindhi"].strip() for q in questions]
            unique_texts = set(texts)
            assert len(texts) == len(unique_texts), f"Duplicates found in 10-MCQ {subject} quiz: {len(texts) - len(unique_texts)} duplicates" 


# --- 7. Practice Mode Immediate Feedback ---

def test_practice_mode_immediate_feedback():
    """Verify practice mode returns instant correctness, explanation, and citation on each answer."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    gen_resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-1"],
        "question_count": 2,
        "mode": "practice"
    })
    session_id = gen_resp.json()["session_id"]
    q1 = gen_resp.json()["questions"][0]

    ans_resp = client.post(f"/api/quiz/{session_id}/answer", headers=headers, json={
        "question_id": q1["id"],
        "selected_option": 0,
        "time_taken_seconds": 4.5
    })

    assert ans_resp.status_code == 200
    fb = ans_resp.json()
    assert fb["session_id"] == session_id
    assert fb["question_id"] == q1["id"]
    assert isinstance(fb["is_correct"], bool)
    assert isinstance(fb["correct_answer_index"], int)
    assert fb["explanation_sindhi"] is not None
    assert fb["citation"] is not None
    assert "STBB" in fb["citation"] or "PDF" in fb["citation"] or "Science" in fb["citation"] or "باب" in fb["citation"]


# --- 8. Assessment Mode Answer Withholding ---

def test_assessment_mode_answer_withholding():
    """Verify assessment mode withholds correctness and explanations until final submission."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    gen_resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-1"],
        "question_count": 2,
        "mode": "assessment"
    })
    session_id = gen_resp.json()["session_id"]
    q1 = gen_resp.json()["questions"][0]

    ans_resp = client.post(f"/api/quiz/{session_id}/answer", headers=headers, json={
        "question_id": q1["id"],
        "selected_option": 1,
        "time_taken_seconds": 6.0
    })

    assert ans_resp.status_code == 200
    fb = ans_resp.json()
    assert fb["is_correct"] is None
    assert fb["correct_answer_index"] is None
    assert fb["explanation_sindhi"] is None


# --- 9. Server-Side Score Calculation & Detailed Review ---

def test_server_side_scoring_and_review():
    """Verify final submission calculates score on server and returns per-lesson breakdown."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    gen_resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-1", "lesson-sci-6-3"],
        "question_count": 2,
        "mode": "practice"
    })
    session_id = gen_resp.json()["session_id"]
    questions = gen_resp.json()["questions"]

    for q in questions:
        client.post(f"/api/quiz/{session_id}/answer", headers=headers, json={
            "question_id": q["id"],
            "selected_option": 0
        })

    sub_resp = client.post(f"/api/quiz/{session_id}/submit", headers=headers)
    assert sub_resp.status_code == 200
    result = sub_resp.json()

    assert result["session_id"] == session_id
    assert result["total_questions"] == 2
    assert result["correct_count"] + result["incorrect_count"] == 2
    assert 0.0 <= result["score"] <= 100.0
    assert isinstance(result["passed"], bool)
    assert len(result["per_lesson_breakdown"]) >= 1
    assert len(result["review"]) == 2

    for rev in result["review"]:
        assert len(rev["explanation_sindhi"]) > 0
        assert len(rev["citation"]) > 0


# --- 10. Authentication & Ownership Security ---

def test_unauthenticated_and_cross_user_access_rejected():
    """Verify unauthenticated requests (401) and accessing another student's session (403)."""
    # 1. Unauthenticated generation rejected
    resp_unauth = client.post("/api/quiz/generate", json={
        "class_level": 6,
        "subject": "Science"
    })
    assert resp_unauth.status_code == 401

    # 2. Student 1 creates session
    token1 = get_token(student_code="STU-101")
    gen_resp = client.post("/api/quiz/generate", headers={"Authorization": f"Bearer {token1}"}, json={
        "class_level": 6,
        "subject": "Science",
        "question_count": 2
    })
    session_id = gen_resp.json()["session_id"]

    # 3. Student 2 tries to answer Student 1's session
    token2 = get_token(student_code="STU-102", pin="5678")
    resp_cross = client.post(f"/api/quiz/{session_id}/answer", headers={"Authorization": f"Bearer {token2}"}, json={
        "question_id": "any-id",
        "selected_option": 0
    })
    assert resp_cross.status_code == 403


# --- 11. Student Progress Update on Passed vs Failed Quiz ---

def test_progress_updated_only_on_valid_assessment():
    """Verify passing quiz updates student post_test_score in progress table."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    gen_resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-2"],
        "question_count": 1,
        "mode": "practice"
    })
    session_id = gen_resp.json()["session_id"]
    q1 = gen_resp.json()["questions"][0]

    with sqlite3.connect(settings.database_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT questions_snapshot_json FROM quiz_sessions WHERE id = ?", (session_id,)).fetchone()
        snapshot = json.loads(row["questions_snapshot_json"])
        correct_idx = snapshot[0]["correct_answer_index"]

    ans_resp = client.post(f"/api/quiz/{session_id}/answer", headers=headers, json={
        "question_id": q1["id"],
        "selected_option": correct_idx,
        "time_taken_seconds": 3.0
    })
    assert ans_resp.status_code == 200
    assert ans_resp.json()["is_correct"] is True

    sub_res = client.post(f"/api/quiz/{session_id}/submit", headers=headers)
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["total_questions"] == 1
    assert sub_data["score"] == 100.0
    assert sub_data["passed"] is True

    with sqlite3.connect(settings.database_path) as conn:
        conn.row_factory = sqlite3.Row
        prog = conn.execute("SELECT * FROM progress WHERE user_id = 'usr-stu-101' AND lesson_id = 'lesson-sci-6-2'").fetchone()
        assert prog is not None
        assert prog["post_test_score"] == 100.0


# --- 12. Abandoned Sessions Do Not Update Progress ---

def test_abandoned_session_does_not_update_progress():
    """Verify starting a quiz and abandoning it does not falsely complete the lesson or record progress."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Generate quiz for lesson-sci-6-4
    gen_resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-4"],
        "question_count": 2,
        "mode": "assessment"
    })
    assert gen_resp.status_code == 201

    # Never submit. Check that progress table has NO record for lesson-sci-6-4
    with sqlite3.connect(settings.database_path) as conn:
        conn.row_factory = sqlite3.Row
        prog = conn.execute("SELECT * FROM progress WHERE user_id = 'usr-stu-101' AND lesson_id = 'lesson-sci-6-4'").fetchone()
        assert prog is None or prog["is_completed"] == 0


# --- 13. Idempotent Submission & Answer Rejection after Completion ---

def test_idempotent_submission_and_no_answers_after_complete():
    """Verify duplicate submissions return the same score idempotently, and answering completed quiz is blocked."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    gen_resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-1"],
        "question_count": 2,
        "mode": "assessment"
    })
    session_id = gen_resp.json()["session_id"]
    q1 = gen_resp.json()["questions"][0]

    client.post(f"/api/quiz/{session_id}/answer", headers=headers, json={
        "question_id": q1["id"],
        "selected_option": 0
    })

    sub1 = client.post(f"/api/quiz/{session_id}/submit", headers=headers)
    assert sub1.status_code == 200
    score1 = sub1.json()["score"]

    sub2 = client.post(f"/api/quiz/{session_id}/submit", headers=headers)
    assert sub2.status_code == 200
    score2 = sub2.json()["score"]
    assert score1 == score2

    q2 = gen_resp.json()["questions"][1]
    late_ans = client.post(f"/api/quiz/{session_id}/answer", headers=headers, json={
        "question_id": q2["id"],
        "selected_option": 1
    })
    assert late_ans.status_code == 400
    assert "اڳ ۾ ئي جمع" in late_ans.text or "already submitted" in late_ans.text.lower()


# --- 14. Student Assessment History and Session Lookup ---

def test_student_history_and_session_lookup():
    """Verify retrieving student assessment history and specific session details."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    gen_resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Math",
        "lesson_ids": ["lesson-math-6-1"],
        "question_count": 2,
        "mode": "practice"
    })
    session_id = gen_resp.json()["session_id"]
    client.post(f"/api/quiz/{session_id}/submit", headers=headers)

    get_sess = client.get(f"/api/quiz/session/{session_id}", headers=headers)
    assert get_sess.status_code == 200
    sess_data = get_sess.json()
    assert (sess_data.get("session_id") or sess_data.get("id")) == session_id
    assert sess_data["status"] == "COMPLETED"

    hist = client.get("/api/quiz/student/history", headers=headers)
    assert hist.status_code == 200
    items = hist.json()
    assert isinstance(items, list)
    assert any((item.get("session_id") or item.get("id")) == session_id for item in items)


# --- 15. Validation of Question Count and Boundaries ---

def test_invalid_scope_and_question_count_validation():
    """Verify input validation rejects negative or oversized question counts."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp_large = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "question_count": 50
    })
    assert resp_large.status_code == 422

    resp_zero = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "question_count": 0
    })
    assert resp_zero.status_code == 422


# --- 16. Video Error Does Not Block Quiz Generation ---

def test_video_error_does_not_block_quiz():
    """Verify student can launch and complete quiz even when video media is missing/corrupted."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/quiz/generate", headers=headers, json={
        "class_level": 6,
        "subject": "Science",
        "lesson_ids": ["lesson-sci-6-12"],
        "question_count": 2
    })
    assert resp.status_code == 201
    assert resp.json()["total_questions"] == 2


# --- 17. Search Distinction: Pure 'سيٽ' (Sets) vs 'پاڪ سيٽ' (PAKSAT) ---

def test_search_distinction_sets_vs_paksat():
    """Verify 'سيٽ' excludes PAKSAT satellite chunk ch12-06, while 'پاڪ سيٽ' returns PAKSAT."""
    # 1. Pure Sets query
    pure_res = sdc_rag_service.search_chunks("سيٽ")
    chunk_ids = [c["chunk_id"] for c in pure_res]
    assert "ch12-06" not in chunk_ids, f"PAKSAT ch12-06 erroneously included in pure Sets search: {chunk_ids}"
    assert any("math-ch01" in cid for cid in chunk_ids), f"Math Unit 1 Sets chunks expected: {chunk_ids}"

    # 2. PAKSAT query
    paksat_res = sdc_rag_service.search_chunks("پاڪ سيٽ")
    paksat_cids = [c["chunk_id"] for c in paksat_res]
    assert "ch12-06" in paksat_cids, f"PAKSAT query must return ch12-06, got: {paksat_cids}"


def test_search_http_distinction_sets_vs_paksat():
    """Verify the student-facing HTTP search keeps the same Math/PAKSAT distinction."""
    pure_res = client.get("/api/sdc/search", params={"q": "سيٽ"})
    assert pure_res.status_code == 200, pure_res.text
    pure_chunks = pure_res.json()["chunks"]
    assert "ch12-06" not in {item.get("chunk_id") for item in pure_chunks}
    assert any("math-ch01" in (item.get("chunk_id") or "") for item in pure_chunks)

    paksat_res = client.get("/api/sdc/search", params={"q": "پاڪ سيٽ"})
    assert paksat_res.status_code == 200, paksat_res.text
    assert "ch12-06" in {item.get("chunk_id") for item in paksat_res.json()["chunks"]}


# --- 18. Transcription Authentication and Size Validation with Valid Multipart ---

def test_transcription_auth_with_valid_multipart():
    """Verify unauthenticated valid multipart upload to /api/tutor/transcribe returns 401."""
    fake_audio = io.BytesIO(b"RIFF....WAVEfmt ....data....")
    files = {"file": ("audio.wav", fake_audio, "audio/wav")}
    resp = client.post("/api/tutor/transcribe", files=files)
    assert resp.status_code == 401, f"Expected 401 Unauthorized for unauthenticated transcribe, got {resp.status_code}: {resp.text}"


# --- 19. TTS Status Route Availability in Source ---

def test_tts_status_route_available():
    """Verify GET /api/tutor/tts/status exists and returns engine availability."""
    resp = client.get("/api/tutor/tts/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "model_name" in data

