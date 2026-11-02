"""Role-Based Dashboards and CSV Export routes for SDC.
Authored under agency-analytics-reporter.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from src.api.deps import get_current_user, require_roles
from src.database.session import get_db
from src.models.schemas import OfficerDistrictReport, StudentDashboardResponse, TeacherDashboardResponse, UserRole
from src.services.dashboard_service import dashboard_service
from src.services.sync_service import sync_service

router = APIRouter(prefix="/api/dashboards", tags=["Dashboards"])


@router.get("/student", response_model=StudentDashboardResponse)
async def get_student_dashboard(
    user_id: Optional[str] = Query(None),
    course_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Personalized student dashboard: learning progress, quiz scores, next unit (FR-29)."""
    target_user_id = user_id or current_user["id"]

    if current_user["role"] == UserRole.STUDENT.value and target_user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="توهان ٻين شاگردن جا نتيجا نٿا ڏسي سگهو (Forbidden: Cannot access other students' dashboards)."
        )

    with get_db() as conn:
        target_student = conn.execute("SELECT role FROM users WHERE id = ?", (target_user_id,)).fetchone()
        if not target_student or target_student["role"] != "STUDENT":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
        if course_id:
            course = conn.execute(
                "SELECT 1 FROM courses WHERE id = ? AND class_level = 6 AND subject IN ('Math','Science')",
                (course_id,)
            ).fetchone()
            if not course:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supported course not found.")

    return dashboard_service.get_student_dashboard(target_user_id, course_id=course_id)


@router.get("/teacher", response_model=TeacherDashboardResponse)
async def get_teacher_dashboard(
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN))
):
    """Teacher dashboard: class results, weak topics, Cohen's d gain, approval queues (FR-30)."""
    return dashboard_service.get_teacher_dashboard(current_user["id"])


@router.get("/officer", response_model=List[OfficerDistrictReport])
async def get_officer_dashboard(
    current_user: dict = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN))
):
    """Education department officer dashboard: district summaries and school totals (FR-31)."""
    return dashboard_service.get_officer_dashboard()


@router.get("/export-anonymized")
async def export_anonymized_data(
    current_user: dict = Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN, UserRole.TEACHER))
):
    """Export pilot evaluation data with ZERO student PII as CSV (FR-36)."""
    csv_data = sync_service.export_anonymized_pilot_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sdc_anonymized_pilot_data.csv"}
    )
