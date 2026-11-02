"""RAG & LLM Interactive Course Routes for SDC.
Exposes endpoints for exploring the 6 core modules of RAG, testing interactive vector retrieval,
executing hybrid search & re-ranking pipelines, evaluating faithfulness, and auto-generating video quizzes with Whisper.
Authored under agency-ai-engineer, agency-voice-ai-integration-engineer, and agency-api-platform-engineer.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, require_roles
from src.models.schemas import UserRole
from src.services.rag_course_service import rag_course_service
from src.services.vector_store_service import vector_store
from src.services.video_transcription_pipeline import video_transcription_pipeline

router = APIRouter(prefix="/api/rag-course", tags=["RAG & LLM Interactive Course"])


class RAGSandboxQueryRequest(BaseModel):
    query: str = Field(..., description="Student or researcher query in Sindhi or English")
    subject_filter: Optional[str] = Field(None, description="Optional subject filter (e.g. Science, Math, Sindhi)")
    use_reranker: bool = Field(True, description="Whether to apply cross-encoder style re-ranking")


class RAGQuizAnswerRequest(BaseModel):
    module_id: str
    selected_option_index: int


class VideoAutoQuizRequest(BaseModel):
    lesson_id: str
    lesson_title: str
    video_path: Optional[str] = None


@router.get("/modules")
async def get_rag_course_modules():
    """Retrieve full curriculum modules covering RAG, Embeddings, LangChain, Hybrid Search, and Evaluation."""
    return {
        "status": "success",
        "modules": rag_course_service.get_course_modules()
    }


@router.post("/query-sandbox")
async def execute_rag_sandbox(
    req: RAGSandboxQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute live query against the vector database, applying Hybrid Search (Dense + BM25) and Re-ranking.
    Requires authenticated user (Student, Teacher, Admin).
    """
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty.")
    if len(clean_query) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query exceeds maximum allowed length of 500 characters.")
    
    result = rag_course_service.execute_rag_pipeline_sandbox(
        query=clean_query,
        subject_filter=req.subject_filter,
        use_reranker=req.use_reranker
    )
    return {
        "status": "success",
        "data": result
    }


@router.post("/module-quiz/submit")
async def submit_module_quiz(
    req: RAGQuizAnswerRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit answer to a module checkpoint quiz and receive instant evaluation and explanation.
    Requires authenticated session.
    """
    modules = rag_course_service.get_course_modules()
    target_mod = next((m for m in modules if m["id"] == req.module_id), None)
    if not target_mod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    quiz = target_mod["quiz"]
    is_correct = (req.selected_option_index == quiz["correct_answer_index"])

    return {
        "status": "success",
        "module_id": req.module_id,
        "is_correct": is_correct,
        "selected_option": req.selected_option_index,
        "correct_answer_index": quiz["correct_answer_index"],
        "explanation": quiz["explanation"]
    }


@router.post("/generate-video-quiz")
async def generate_video_quiz_from_transcription(
    req: VideoAutoQuizRequest,
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Run Whisper transcription & voice pipeline to generate checkpoint quizzes at 2-3 min intervals for teacher review.
    Enforces lesson existence check and server-side RBAC.
    """
    from src.database.session import get_db
    with get_db() as conn:
        lesson = conn.execute("SELECT id, title_sindhi FROM lessons WHERE id = ?", (req.lesson_id,)).fetchone()
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson '{req.lesson_id}' not found.")
        actual_title = lesson["title_sindhi"]

    result = video_transcription_pipeline.process_and_save_video_quizzes(
        lesson_id=req.lesson_id,
        lesson_title=actual_title,
        file_path=req.video_path
    )
    return {
        "status": "success",
        "message": f"Successfully generated {result['generated_quizzes_count']} draft checkpoint questions.",
        "data": result
    }
