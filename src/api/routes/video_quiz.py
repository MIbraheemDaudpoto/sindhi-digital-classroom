"""Smart Video Quiz routes for SDC.
Enforces the Teacher Approval Gate (FR-13) and randomized question delivery (FR-16).
Authored under agency-api-platform-engineer and agency-backend-architect.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.api.deps import get_current_user, require_roles
from src.models.schemas import (
    AttemptResponse,
    AttemptSubmitRequest,
    QuestionApprovalRequest,
    QuestionResponse,
    QuizAnswerFeedbackResponse,
    QuizAnswerSubmitRequest,
    QuizGenerateRequest,
    QuizSessionResponse,
    QuizSubmitResponse,
    UserRole,
)
from src.services.assessment_quiz_service import assessment_quiz_service
from src.services.video_quiz_service import video_quiz_service

router = APIRouter(prefix="/api/quiz", tags=["Curriculum & AI Quiz Assessments"])


# --- Real-Time Curriculum & AI Quiz Assessment Endpoints ---

@router.post("/generate", response_model=QuizSessionResponse, status_code=status.HTTP_201_CREATED)
def generate_assessment_quiz(
    req: QuizGenerateRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT))
):
    """Generate a curriculum-grounded quiz in FastAPI's worker pool.

    The local Transformers provider is synchronous and CPU-bound. Keeping this
    handler synchronous prevents model generation from blocking the ASGI event
    loop (including health checks and other student requests).
    """
    return assessment_quiz_service.generate_quiz(user_id=current_user["id"], req=req)


@router.post("/{session_id}/answer", response_model=QuizAnswerFeedbackResponse)
async def submit_quiz_answer(
    session_id: str,
    req: QuizAnswerSubmitRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT))
):
    """Submit answer for one question: immediate feedback in practice mode, withheld in assessment mode."""
    return assessment_quiz_service.submit_single_answer(
        user_id=current_user["id"],
        session_id=session_id,
        req=req
    )


@router.post("/{session_id}/submit", response_model=QuizSubmitResponse)
async def submit_complete_quiz(
    session_id: str,
    current_user: dict = Depends(require_roles(UserRole.STUDENT))
):
    """Finalize quiz, compute score server-side, record progress, and return detailed review."""
    return assessment_quiz_service.submit_final_quiz(
        user_id=current_user["id"],
        session_id=session_id
    )


@router.get("/student/history")
async def get_student_quiz_history(
    current_user: dict = Depends(require_roles(UserRole.STUDENT))
):
    """Retrieve history of past quiz assessments for student."""
    return assessment_quiz_service.list_student_history(user_id=current_user["id"])


@router.get("/session/{session_id}")
async def get_quiz_session_details(
    session_id: str,
    current_user: dict = Depends(require_roles(UserRole.STUDENT))
):
    """Retrieve active or completed quiz session (withholds answer keys if in progress)."""
    return assessment_quiz_service.get_quiz_session(user_id=current_user["id"], session_id=session_id)



@router.get("/pending", response_model=List[QuestionResponse])
async def list_pending_questions_for_teacher(
    school_id: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN))
):
    """Teacher approval portal: List questions pending approval before release (FR-13 Gate)."""
    target_school = school_id or current_user.get("school_id")
    return video_quiz_service.get_pending_questions_for_teacher(school_id=target_school)


@router.post("/{question_id}/review", status_code=status.HTTP_200_OK)
async def review_question(
    question_id: str,
    req: QuestionApprovalRequest,
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN))
):
    """Teacher action: Approve, edit, or reject a draft question (FR-13 Gate)."""
    success = video_quiz_service.review_question(question_id, current_user["id"], req)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    return {"status": "ok", "message": f"Question {req.status.value} successfully."}


@router.get("/{lesson_id}/questions", response_model=List[QuestionResponse])
async def get_student_quiz_bank(
    lesson_id: str,
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN))
):
    """Retrieve randomized bank of APPROVED questions for student video playback (FR-13, FR-16)."""
    return video_quiz_service.get_lesson_quiz_bank_for_student(lesson_id, current_user["id"])


@router.post("/attempt", response_model=AttemptResponse)
async def submit_quiz_attempt(
    req: AttemptSubmitRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT))
):
    """Submit answer during interactive video pop-up pause and receive instant Sindhi feedback (FR-14, FR-27)."""
    res = video_quiz_service.submit_attempt(current_user["id"], req)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    return res
