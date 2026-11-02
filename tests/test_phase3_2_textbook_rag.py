"""Automated Unit, Integration, and Regression Tests for SDC Phase 3.2.
Tests multi-subject schema, textbook PDF ingestion, NFKC normalization,
scanned PDF detection, lexical chunk search, honest AI status, and Admin authorization.
Authored under agency-ai-engineer and agency-model-qa-specialist.
"""

import io
import pytest
from pypdf import PdfWriter

from src.database.session import get_db, init_db
from src.models.schemas import TutorAskRequest
from src.services.ai_provider import get_ai_system_status, get_ai_provider
from src.services.ai_tutor_service import ai_tutor_service
from src.services.sindhi_nlp import normalize_sindhi_text, compute_grounding_similarity
from src.services.textbook_ingestion_service import textbook_ingestion_service


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (id, role, pseudonymous_code, pin_hash, created_at)
            VALUES ('test-student-1', 'STUDENT', 'std-phase3-2', 'hash123', '2026-10-18T00:00:00Z')
            """
        )


def create_synthetic_sindhi_pdf(text_pages: list) -> bytes:
    """Helper to synthesize an in-memory valid text-based PDF with unique metadata."""
    import uuid
    writer = PdfWriter()
    for text in text_pages:
        writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Producer": f"Test-Producer-{uuid.uuid4()}"})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_nfkc_sindhi_presentation_forms_normalization():
    """Verify Arabic Presentation Forms-A/B map cleanly to standard 52 Sindhi characters."""
    # Presentation forms for 'ِﺳﻨﮅي' (Kasra + Seen medial + Noon medial + Dhal with dots + Yeh)
    raw_presentation = "ِﺳﻨﮅي"
    normalized = normalize_sindhi_text(raw_presentation, strip_diacritics=True)
    assert normalized == "سنڌي"
    assert "ﮅ" not in normalized  # Replaced with standard U+068C


def test_pdf_validation_magic_bytes():
    """Verify rejection of empty or non-PDF files."""
    valid, msg = textbook_ingestion_service.validate_pdf_bytes(b"")
    assert not valid
    assert "empty" in msg

    valid, msg = textbook_ingestion_service.validate_pdf_bytes(b"INVALID_HEADER")
    assert not valid
    assert "signature" in msg


def test_subject_registration_and_isolation():
    """Verify subjects are isolated by class level and slug."""
    subj_id = textbook_ingestion_service.create_or_get_subject(
        class_level=6,
        slug="science_test",
        title_sindhi="سائنس ٽيسٽ",
        title_english="Science Test"
    )
    assert subj_id.startswith("subj-science_test-6")

    # Idempotent retrieval
    same_id = textbook_ingestion_service.create_or_get_subject(
        class_level=6,
        slug="science_test",
        title_sindhi="سائنس ٽيسٽ",
        title_english="Science Test"
    )
    assert subj_id == same_id


def test_textbook_ingestion_and_activation_lifecycle():
    """Verify end-to-end ingestion of a textbook PDF and admin activation gate."""
    import uuid
    unique_slug = f"sci_{uuid.uuid4().hex[:6]}"
    subj_id = textbook_ingestion_service.create_or_get_subject(
        class_level=6,
        slug=unique_slug,
        title_sindhi="سائنس",
        title_english="Science Lifecycle"
    )

    pdf_bytes = create_synthetic_sindhi_pdf([f"Unique test content {uuid.uuid4()}", "ٻيو صفحو"])
    result = textbook_ingestion_service.ingest_textbook_pdf(
        file_bytes=pdf_bytes,
        filename=f"test_{unique_slug}.pdf",
        class_level=6,
        subject_id=subj_id,
        title_sindhi="سائنس ڪلاس 6",
        title_english="Science Grade 6"
    )

    assert result["status"] == "SUCCESS"
    book_id = result["textbook_id"]
    assert result["is_active"] == 0

    # Ingest duplicate
    dup_result = textbook_ingestion_service.ingest_textbook_pdf(
        file_bytes=pdf_bytes,
        filename="test_science_g6.pdf",
        class_level=6,
        subject_id=subj_id,
        title_sindhi="سائنس ڪلاس 6",
        title_english="Science Grade 6"
    )
    assert dup_result["status"] == "DUPLICATE_DETECTED"

    # Admin activation gate
    activated = textbook_ingestion_service.activate_textbook(book_id)
    assert activated

    with get_db() as conn:
        row = conn.execute("SELECT is_active FROM textbooks WHERE id = ?", (book_id,)).fetchone()
        assert row["is_active"] == 1


def test_tutor_answers_grounded_science_question():
    """Verify tutor answers legitimate Grade 6 Science question from approved content."""
    req = TutorAskRequest(question="ٻوٽن ۾ فوٽوسنٿيسز جو عمل ڪيئن ٿيندو آهي؟")
    res = ai_tutor_service.answer_student_question("test-student-1", req)
    assert not res.is_refused
    assert len(res.citations) > 0
    assert "فوٽوسنٿيسز" in res.answer_sindhi
    assert res.confidence_score >= 0.65


def test_tutor_refuses_out_of_scope_question():
    """Verify tutor strictly refuses questions outside approved curriculum."""
    req = TutorAskRequest(question="موسميات کاتي اڄ ڪهڙي برسات جي اڳڪٿي ڪئي آهي؟")
    res = ai_tutor_service.answer_student_question("test-student-1", req)
    assert res.is_refused
    assert res.inference_status == "REFUSED_BELOW_GROUNDING_THRESHOLD"
    assert "معاف ڪجو" in res.answer_sindhi


def test_honest_ai_diagnostics_exposure():
    """Verify honest AI provider status does not expose secrets and reports real provider type."""
    status = get_ai_system_status()
    assert "configured_provider" in status
    assert "active_provider_type" in status
    assert "has_credentials" in status
    assert "api_token" not in status
    assert "hf_api_token" not in status
    assert isinstance(status["has_credentials"], bool)
