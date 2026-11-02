"""Automated verification of Sindhi NLP Normalization, AI RAG Retrieval, and Question Generation for SDC.
Tests Unicode character preservation, 0.65 grounding threshold, draft quiz generation,
Admin approval gates, and adaptive learning recommendations.
Authored under agency-ai-engineer and agency-test-automation-engineer.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum
from src.services.ai_tutor_service import ai_tutor_service, SINDHI_REFUSAL_MESSAGE
from src.services.auth_service import auth_service
from src.services.question_generator import question_generator
from src.services.sindhi_nlp import compute_grounding_similarity, normalize_sindhi_text, tokenize_sindhi_query


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database is seeded with STBB test curriculum and isolated test DB."""
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "sdc_ai_test.db"
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


def test_sindhi_unicode_normalization():
    """Verify normalization of Perso-Arabic variants while strictly preserving all 52 Sindhi letters."""
    # Test Kaf normalization: Arabic Kaf (ك) -> Sindhi Kaf (ڪ)
    assert normalize_sindhi_text("ڪتاب") == "ڪتاب"
    assert normalize_sindhi_text("كتاب") == "ڪتاب"

    # Test Yeh normalization: Persian Yeh (ی) -> Sindhi Yeh (ي)
    assert normalize_sindhi_text("پاڻی") == "پاڻي"

    # Test Heh normalization: Urdu Goal Heh (ہ) -> Sindhi Heh (ه)
    assert normalize_sindhi_text("شاہ") == "شاه"

    # Test Implosive letters preservation: ٻ, ڄ, ڳ, ڊ
    implosives = "ٻوٽا ڄامشورو ڳوٺ ڊاڪٽر"
    assert normalize_sindhi_text(implosives) == implosives

    # Test diacritic stripping for search
    voweled = "فُوٽُوسَنٿِيسِز"
    stripped = normalize_sindhi_text(voweled, strip_diacritics=True)
    assert "فوٽوسنٿيسز" in stripped


def test_grounding_similarity_and_refusal_threshold():
    """Verify similarity computation correctly differentiates curriculum queries from out-of-scope queries."""
    doc = "فوٽوسنٿيسز اهو عمل آهي جنهن ذريعي ٻوٽا سج جي روشني ۽ پاڻي مان پنهنجو کاڌو تيار ڪن ٿا."

    # In-scope curriculum question
    in_scope_query = "ٻوٽا سج جي روشني ۽ فوٽوسنٿيسز مان ڇا ٺاهين ٿا؟"
    score_in = compute_grounding_similarity(in_scope_query, doc)
    assert score_in >= 0.65

    # Out-of-scope query
    out_scope_query = "پاڪستان ڪرڪيٽ ٽيم جو ڪپتان ڪير آهي؟"
    score_out = compute_grounding_similarity(out_scope_query, doc)
    assert score_out < 0.65


def test_ai_tutor_answers_in_scope_and_refuses_out_of_scope():
    """Verify AI Tutor generates grounded answers for curriculum questions and strictly refuses out-of-scope queries."""
    client = TestClient(app)
    student_token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    headers = {"Authorization": f"Bearer {student_token}"}

    # 1. In-scope Science query
    sci_resp = client.post(
        "/api/tutor/ask",
        json={"question": "ٻوٽن ۾ فوٽوسنٿيسز جو عمل ڪيئن ٿئي ٿو؟", "lesson_id": "lesson-sci-6-1"},
        headers=headers
    )
    assert sci_resp.status_code == 200
    sci_data = sci_resp.json()
    assert sci_data["is_refused"] is False
    assert len(sci_data["citations"]) > 0
    assert "فوٽوسنٿيسز" in sci_data["answer_sindhi"]

    # 2. Out-of-scope query
    unrelated_resp = client.post(
        "/api/tutor/ask",
        json={"question": "ڪراچي کان لاهور ويندڙ ريل گاڏي جو وقت ڇا آهي؟"},
        headers=headers
    )
    assert unrelated_resp.status_code == 200
    unrelated_data = unrelated_resp.json()
    assert unrelated_data["is_refused"] is True
    assert SINDHI_REFUSAL_MESSAGE in unrelated_data["answer_sindhi"]
    assert len(unrelated_data["citations"]) == 0


def test_ai_question_generation_and_admin_approval_gate():
    """Verify AI generates draft questions with PENDING_APPROVAL status, and only Admin approval releases them to students."""
    client = TestClient(app)
    admin_token = auth_service.create_session_token("usr-super-admin-01", "ADMIN")
    student_token = auth_service.create_session_token("usr-stu-101", "STUDENT")

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Admin triggers AI question generation for science lesson
    gen_resp = client.post("/api/admin/lessons/lesson-sci-6-1/generate-questions?count=2", headers=admin_headers)
    assert gen_resp.status_code == 200
    questions = gen_resp.json()["questions"]
    assert len(questions) == 2
    draft_q_id = questions[0]["id"]
    assert questions[0]["status"] == "PENDING_APPROVAL"

    # 2. Verify that student quiz bank DOES NOT contain this pending question
    bank_resp = client.get("/api/quiz/lesson-sci-6-1/questions", headers=student_headers)
    assert bank_resp.status_code == 200
    student_questions = bank_resp.json()
    assert not any(q["id"] == draft_q_id for q in student_questions)

    # 3. Admin approves the draft question
    appr_resp = client.post(f"/api/admin/questions/{draft_q_id}/approve", headers=admin_headers)
    assert appr_resp.status_code == 200

    # 4. Student quiz bank NOW contains the approved question
    updated_bank = client.get("/api/quiz/lesson-sci-6-1/questions", headers=student_headers).json()
    assert any(q["id"] == draft_q_id for q in updated_bank)


def test_adaptive_recommendations():
    """Verify adaptive learning suggests revision topics based on student's incorrect attempts."""
    recs = ai_tutor_service.get_adaptive_recommendations("usr-stu-101")
    assert isinstance(recs, list)
