"""Tests for Grounded Sindhi AI Tutor, RAG Citations, and Strict Refusal (FR-23 to FR-26).
Authored under agency-ai-engineer and agency-test-automation-engineer.
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
    orig_db = settings.database_path
    orig_auth = settings.allow_test_query_auth
    test_dir = Path("./.pytest_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_db = test_dir / "tutor_test.db"
    if test_db.exists():
        test_db.unlink(missing_ok=True)
    settings.database_path = str(test_db)
    settings.allow_test_query_auth = True
    from src.services.sdc_rag_db import ensure_sdc_data_seeded, get_db_connection
    init_db(str(test_db))
    seed_sdc_curriculum(str(test_db))
    test_conn = get_db_connection(str(test_db))
    ensure_sdc_data_seeded(test_conn)
    test_conn.close()
    yield str(test_db)
    settings.database_path = orig_db
    settings.allow_test_query_auth = orig_auth
    if test_db.exists():
        test_db.unlink(missing_ok=True)


def test_tutor_grounded_answer_with_citation():
    """Verify in-scope curriculum query returns grounded answer and STBB citation (FR-23, FR-25)."""
    client = TestClient(app)
    payload = {
        "question": "ٻوٽن ۾ فوٽوسنٿيسز جو عمل ڇا هوندو آهي؟ (What is photosynthesis?)",
        "lesson_id": "lesson-sci-6-1"
    }
    res = client.post("/api/tutor/ask?user_id=usr-stu-101", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_refused"] is False
    assert "ڪلوروفل" in data["answer_sindhi"]
    # Check citation
    assert len(data["citations"]) >= 1
    citation = data["citations"][0]
    assert citation["lesson_id"] == "lesson-sci-6-1"
    assert citation["timestamp_seconds"] > 0


def test_tutor_out_of_scope_strict_refusal():
    """Verify out-of-scope question is refused with fixed Sindhi message (FR-24)."""
    client = TestClient(app)
    payload = {
        "question": "پاڪستان ڪرڪيٽ ميچ ڪير کٽيو؟ (Who won the cricket match?)",
        "lesson_id": "lesson-sci-6-1"
    }
    res = client.post("/api/tutor/ask?user_id=usr-stu-101", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_refused"] is True
    assert "معاف ڪجو، هي سوال سبق جي دائري کان ٻاهر آهي" in data["answer_sindhi"]
    assert len(data["citations"]) == 0


def test_tutor_report_wrong_answer():
    """Verify student can flag tutor response for teacher review (FR-26)."""
    client = TestClient(app)
    # 1. Ask question to generate chat report ID
    ask_res = client.post("/api/tutor/ask?user_id=usr-stu-101", json={"question": "ٻوٽا ڪهڙي گئس ٺاهين ٿا؟"})
    report_id = ask_res.json()["report_id"]
    assert report_id is not None

    # 2. Report answer
    rep_res = client.post(
        "/api/tutor/report?user_id=usr-stu-101",
        json={"report_id": report_id, "reason": "جواب مڪمل نه هو"}
    )
    assert rep_res.status_code == 200
    assert rep_res.json()["status"] == "ok"
