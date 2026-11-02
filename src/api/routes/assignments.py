"""API routes for Teacher Assignments and Student Submissions (FR-28).
Enforces RBAC: only Teachers/Admins can create/grade; Students can view/submit.
Authored under agency-backend-architect and agency-api-platform-engineer.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.api.deps import get_current_user, require_roles
from src.models.schemas import (
    AcademicPolicyModel,
    AIGenerateAssignmentRequest,
    AssignmentCreateRequest,
    AssignmentGradeRequest,
    AssignmentResponse,
    AssignmentSubmissionResponse,
    AssignmentSubmitRequest,
    StudentNotificationResponse,
    UserRole,
)
from src.database.session import get_db
from src.services.ai_homework_service import ai_homework_service
from src.services.assignment_service import assignment_service

router = APIRouter(prefix="/api/assignments", tags=["Assignments & AI Homework"])


@router.post("/ai/generate", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_assignment(
    req: AIGenerateAssignmentRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN)),
):
    """Generate and automatically publish an assignment grounded in STBB curriculum."""
    actor_id = current_user["id"]
    if current_user.get("role") == UserRole.STUDENT.value:
        # Default assignment creator to teacher or admin in DB to satisfy foreign key
        with get_db() as conn:
            tch = conn.execute("SELECT id FROM users WHERE role IN ('TEACHER', 'ADMIN') LIMIT 1;").fetchone()
            if tch:
                actor_id = tch["id"]

    return ai_homework_service.generate_assignment_from_curriculum(
        req=req, actor_id=actor_id
    )


@router.get("/policy", response_model=AcademicPolicyModel)
async def get_academic_policy(
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN, UserRole.OFFICER)),
):
    """Retrieve active academic policy (deadline window, grading rubrics, retry rules)."""
    return ai_homework_service.get_academic_policy()


@router.put("/policy", response_model=AcademicPolicyModel)
async def update_academic_policy(
    policy: AcademicPolicyModel,
    current_user: dict = Depends(require_roles(UserRole.ADMIN)),
):
    """Admin configures the global academic policy once."""
    return ai_homework_service.update_academic_policy(policy=policy, admin_id=current_user["id"])


@router.get("/exceptions", response_model=List[AssignmentSubmissionResponse])
async def list_unresolved_exceptions(
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Admin exception monitoring dashboard: submissions flagged for review or delayed."""
    return ai_homework_service.list_unresolved_exceptions()


@router.post("/jobs/retry-gradings", status_code=status.HTTP_200_OK)
async def trigger_retry_gradings(
    current_user: dict = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Scheduled job to re-evaluate submissions marked as NEEDS_RETRY."""
    count = ai_homework_service.retry_pending_gradings()
    return {"status": "ok", "retried_count": count}


@router.get("/notifications", response_model=List[StudentNotificationResponse])
async def get_my_notifications(
    current_user: dict = Depends(require_roles(UserRole.STUDENT)),
):
    """Get student assignment alerts and grading notifications."""
    return ai_homework_service.get_student_notifications(user_id=current_user["id"])


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    req: AssignmentCreateRequest,
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
):
    """Teacher/Admin manually creates an assignment with deadline and maximum marks (FR-28)."""
    return assignment_service.create_assignment(teacher_id=current_user["id"], req=req)


@router.get("", response_model=List[AssignmentResponse])
async def list_assignments(
    course_id: Optional[str] = Query(None, description="Optional filter by course ID"),
    class_level: Optional[int] = Query(None, description="Optional filter by class level"),
    subject: Optional[str] = Query(None, description="Optional filter by subject"),
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN, UserRole.OFFICER)),
):
    """List assignments filtered by class, subject, or student."""
    return ai_homework_service.list_assignments(
        user_id=current_user["id"], course_id=course_id, class_level=class_level, subject=subject
    )


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment_detail(
    assignment_id: str,
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN, UserRole.OFFICER)),
):
    """Get single assignment details with student submission state."""
    return ai_homework_service.get_assignment_detail(assignment_id=assignment_id, user_id=current_user["id"])


@router.post("/{assignment_id}/submit", response_model=AssignmentSubmissionResponse, status_code=status.HTTP_200_OK)
async def submit_assignment(
    assignment_id: str,
    req: AssignmentSubmitRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT)),
):
    """Student submits response to an assignment; automatically graded by AI."""
    return assignment_service.submit_assignment(
        assignment_id=assignment_id, student_id=current_user["id"], req=req
    )


@router.get("/{assignment_id}/submissions", response_model=List[AssignmentSubmissionResponse])
async def list_assignment_submissions(
    assignment_id: str,
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
):
    """Teacher/Admin reviews all student submissions for an assignment."""
    return assignment_service.list_submissions(assignment_id=assignment_id)


@router.post(
    "/{assignment_id}/submissions/{submission_id}/grade",
    response_model=AssignmentSubmissionResponse,
    status_code=status.HTTP_200_OK,
)
async def grade_submission(
    assignment_id: str,
    submission_id: str,
    req: AssignmentGradeRequest,
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN)),
):
    """Teacher/Admin grades student submission or overrides AI grade (FR-28)."""
    return assignment_service.grade_submission(
        assignment_id=assignment_id,
        submission_id=submission_id,
        teacher_id=current_user["id"],
        req=req,
    )

