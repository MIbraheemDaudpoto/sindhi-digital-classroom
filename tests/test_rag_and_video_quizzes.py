"""Comprehensive Unit and Integration Tests for RAG & LLM Interactive Course,
Vector Store Engine, Hybrid Search, and Whisper Video-to-Quiz Pipeline.
Authored under agency-ai-engineer and agency-voice-ai-integration-engineer.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.services.rag_course_service import rag_course_service
from src.services.vector_store_service import VectorStoreEngine, vector_store
from src.services.video_transcription_pipeline import video_transcription_pipeline


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def student_auth_headers():
    return {"Authorization": "Bearer usr-stu-101"}


@pytest.fixture
def teacher_auth_headers():
    from src.services.auth_service import auth_service
    token = auth_service.create_session_token("usr-super-admin-01", "SUPER_ADMIN")
    return {"Authorization": f"Bearer {token}"}


def test_vector_store_embeddings_and_cosine():
    engine = VectorStoreEngine(dimension=64)
    # Cosine similarity between identical text should be ~1.0
    v1 = engine.compute_embedding("ٻوٽن ۾ فوٽوسنٿيسز جو عمل")
    v2 = engine.compute_embedding("ٻوٽن ۾ فوٽوسنٿيسز جو عمل")
    sim = engine.cosine_similarity(v1, v2)
    assert sim >= 0.99


def test_vector_store_hybrid_search_and_rerank():
    engine = VectorStoreEngine(dimension=64)
    engine.add_document("doc-1", "ٻوٽا سج جي روشني ۽ پاڻي مان کاڌو تيار ڪن ٿا جنهن کي فوٽوسنٿيسز چئبو آهي.")
    engine.add_document("doc-2", "سيٽ مختلف شين جو مجموعو هوندو آهي.")

    # Search for photosynthesis
    results = engine.hybrid_search("فوٽوسنٿيسز ڇا آهي؟", top_k=2)
    assert len(results) > 0
    assert results[0]["id"] == "doc-1"
    assert results[0]["hybrid_score"] > 0.0

    # Reranking
    reranked = engine.rerank_candidates("فوٽوسنٿيسز", results, top_k=1)
    assert len(reranked) == 1
    assert reranked[0]["id"] == "doc-1"


def test_rag_course_syllabus_modules_completeness():
    modules = rag_course_service.get_course_modules()
    assert len(modules) == 6
    # Verify all 6 syllabus objectives match user prompt
    objectives = [m["objective"] for m in modules]
    assert any("hallucination and knowledge-cutoff" in obj for obj in objectives)
    assert any("embeddings and store them in a vector database" in obj for obj in objectives)
    assert any("LangChain" in obj for obj in objectives)
    assert any("re-ranking, hybrid search, and metadata filtering" in obj for obj in objectives)
    assert any("relevance, faithfulness, and correctness" in obj for obj in objectives)
    assert any("real-world RAG assistant" in obj for obj in objectives)


def test_rag_course_api_modules(test_client):
    res = test_client.get("/api/rag-course/modules")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["modules"]) == 6


def test_rag_course_api_sandbox_grounded(test_client, student_auth_headers):
    res = test_client.post(
        "/api/rag-course/query-sandbox",
        json={"query": "ٻوٽن ۾ فوٽوسنٿيسز جو عمل", "use_reranker": True},
        headers=student_auth_headers
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["evaluation_metrics"]["decision"] == "GROUNDED_ANSWER_GENERATED"
    assert data["evaluation_metrics"]["context_relevance"] > 0.0
    assert len(data["re_ranked_top_chunks"]) > 0


def test_rag_course_api_sandbox_out_of_scope_refusal(test_client, student_auth_headers):
    res = test_client.post(
        "/api/rag-course/query-sandbox",
        json={"query": "آمريڪا جو صدر ڪير آهي؟", "use_reranker": True},
        headers=student_auth_headers
    )
    assert res.status_code == 200
    data = res.json()["data"]
    # Refusal gate triggered
    assert data["evaluation_metrics"]["decision"] == "REFUSED_OUT_OF_SCOPE"
    assert "معاف ڪجو" in data["generated_answer"]


def test_rag_course_quiz_submission(test_client, student_auth_headers):
    modules = rag_course_service.get_course_modules()
    first_mod = modules[0]
    correct_idx = first_mod["quiz"]["correct_answer_index"]

    res = test_client.post(
        "/api/rag-course/module-quiz/submit",
        json={"module_id": first_mod["id"], "selected_option_index": correct_idx},
        headers=student_auth_headers
    )
    assert res.status_code == 200
    assert res.json()["is_correct"] is True


def test_whisper_video_quiz_pipeline():
    result = video_transcription_pipeline.process_and_save_video_quizzes(
        lesson_id="lesson-sci-6-1",
        lesson_title="Photosynthesis in Plants"
    )
    assert result["lesson_id"] == "lesson-sci-6-1"
    assert result["generated_quizzes_count"] >= 3
    for q in result["quizzes"]:
        assert q["status"] == "PENDING_APPROVAL"
        assert len(q["options"]) == 4


def test_generate_video_quiz_endpoint(test_client, teacher_auth_headers):
    res = test_client.post(
        "/api/rag-course/generate-video-quiz",
        json={"lesson_id": "lesson-sci-6-1", "lesson_title": "Photosynthesis in Plants"},
        headers=teacher_auth_headers
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["data"]["generated_quizzes_count"] >= 3
