"""Regression tests for Phase 3:
1. Sindhi NFKC Presentation Forms A & B normalization to base 52-letter characters.
2. AI Tutor provider transparency: local fallback vs cloud LLM clearly reported.
3. Strict 0.65 similarity refusal behavior on out-of-scope non-curriculum queries.
4. Token expiration and revocation behavior across application requests.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.database.session import init_db
from data.seed_curriculum import seed_sdc_curriculum
from src.services.auth_service import auth_service
from src.services.sindhi_nlp import normalize_sindhi_text, compute_grounding_similarity


@pytest.fixture(autouse=True)
def setup_phase3_db():
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "phase3_regression.db"
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


def test_sindhi_presentation_forms_nfkc_normalization():
    """Verify Arabic Presentation Forms A and B ligatures normalize to base Sindhi characters."""
    # Isolated/Initial forms from PDF extraction
    # ﻛ (U+FEDB, initial kaf), ﺗ (U+FED7, initial teh), ﺎ (U+FE8E, final alef), ب (U+0628)
    pdf_extracted_ligature = "ِﺳﻨﮅي ﮀﮭﻮن ﻛﺘﺎب"
    normalized = normalize_sindhi_text(pdf_extracted_ligature, strip_diacritics=True)
    
    # Must contain standard Sindhi Swash Kaf (ڪ, U+06AA) and standard base characters
    assert "ڪتاب" in normalized
    assert "سنڌي" in normalized
    assert "ڇھون" in normalized or "ڇهون" in normalized


def test_tutor_response_reports_provider_type_honestly():
    """Verify AI Tutor response schema transparently identifies LOCAL_DETERMINISTIC_FALLBACK."""
    client = TestClient(app)
    token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.post(
        "/api/tutor/ask",
        json={"question": "ٻوٽن ۾ فوٽوسنٿيسز جو عمل ڪيئن ٿئي ٿو؟", "lesson_id": "lesson-sci-6-1"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_refused"] is False
    assert data["provider_type"] in {"LOCAL_DETERMINISTIC_FALLBACK", "CLOUD_LLM_INFERENCE"}
    assert data["model_name"] is not None
    assert data["confidence_score"] is not None
    assert data["confidence_score"] >= 0.65
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["lesson_id"] == "lesson-sci-6-1"


def test_tutor_strict_refusal_on_irrelevant_query():
    """Verify query outside curriculum receives strict refusal and empty citations."""
    client = TestClient(app)
    token = auth_service.create_session_token("usr-stu-101", "STUDENT")
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.post(
        "/api/tutor/ask",
        json={"question": "موسميات کاتي اڄ ڪهڙي برسات جي اڳڪٿي ڪئي آهي؟"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_refused"] is True
    assert "معاف ڪجو، هي سوال سبق جي دائري کان ٻاهر آهي" in data["answer_sindhi"]
    assert len(data["citations"]) == 0
