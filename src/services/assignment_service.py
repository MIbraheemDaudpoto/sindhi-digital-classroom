"""Teacher Assignments and Student Submissions Service for SDC (FR-28).
Enforces deadline validation, manual teacher grading, feedback, and role isolation.
Authored under agency-backend-architect and agency-application-security-engineer.
"""

from datetime import datetime, timezone
import json
from typing import List, Optional
import uuid

from fastapi import HTTPException, status
from src.database.session import get_db
from src.models.schemas import (
    AssignmentCreateRequest,
    AssignmentGradeRequest,
    AssignmentResponse,
    AssignmentSubmissionResponse,
    AssignmentSubmitRequest,
)


class AssignmentService:
    """Business logic for FR-28 Teacher Assignments."""

    def create_assignment(self, teacher_id: str, req: AssignmentCreateRequest) -> AssignmentResponse:
        """Create a new course assignment with due date and max marks."""
        now_str = datetime.now(timezone.utc).isoformat()
        assignment_id = f"asg-{uuid.uuid4().hex[:8]}"

        with get_db() as conn:
            # Check course exists
            course = conn.execute("SELECT id FROM courses WHERE id = ?", (req.course_id,)).fetchone()
            if not course:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ڪورس نه مليو (Course not found).")

            conn.execute(
                """
                INSERT INTO assignments (
                    id, course_id, lesson_id, title_sindhi, title_english,
                    description_sindhi, due_date, max_marks, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assignment_id,
                    req.course_id,
                    req.lesson_id,
                    req.title_sindhi,
                    req.title_english,
                    req.description_sindhi,
                    req.due_date,
                    req.max_marks,
                    teacher_id,
                    now_str,
                ),
            )

            # Audit log
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, 'ASSIGNMENT_CREATED', 'assignment', ?, ?, ?)
                """,
                (
                    f"aud-{uuid.uuid4().hex[:8]}",
                    teacher_id,
                    assignment_id,
                    json.dumps({"title": req.title_sindhi, "due_date": req.due_date}),
                    now_str,
                ),
            )

        return self.get_assignment_detail(assignment_id, user_id=teacher_id)

    def get_assignment_detail(self, assignment_id: str, user_id: str) -> AssignmentResponse:
        """Fetch details of an assignment with submission context."""
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT a.*, COUNT(s.id) as submissions_count
                FROM assignments a
                LEFT JOIN assignment_submissions s ON a.id = s.assignment_id
                WHERE a.id = ?
                GROUP BY a.id
                """,
                (assignment_id,),
            ).fetchone()

            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="اسائنمينٽ نه ملي (Assignment not found).")

            now_iso = datetime.now(timezone.utc).isoformat()
            is_overdue = now_iso > row["due_date"]

            # Check if current user has a submission
            sub_row = conn.execute(
                """
                SELECT s.*, u.pseudonymous_code as student_code
                FROM assignment_submissions s
                JOIN users u ON s.user_id = u.id
                WHERE s.assignment_id = ? AND s.user_id = ?
                """,
                (assignment_id, user_id),
            ).fetchone()

            my_sub = None
            if sub_row:
                my_sub = AssignmentSubmissionResponse(
                    id=sub_row["id"],
                    assignment_id=sub_row["assignment_id"],
                    user_id=sub_row["user_id"],
                    student_code=sub_row["student_code"],
                    submission_text=sub_row["submission_text"],
                    marks_awarded=sub_row["marks_awarded"],
                    teacher_feedback=sub_row["teacher_feedback"],
                    graded_by=sub_row["graded_by"],
                    graded_at=sub_row["graded_at"],
                    submitted_at=sub_row["submitted_at"],
                    is_graded=sub_row["marks_awarded"] is not None,
                )

            return AssignmentResponse(
                id=row["id"],
                course_id=row["course_id"],
                lesson_id=row["lesson_id"],
                title_sindhi=row["title_sindhi"],
                title_english=row["title_english"],
                description_sindhi=row["description_sindhi"],
                due_date=row["due_date"],
                max_marks=row["max_marks"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                is_overdue=is_overdue,
                my_submission=my_sub,
                submissions_count=row["submissions_count"],
            )

    def list_assignments(self, user_id: str, course_id: Optional[str] = None) -> List[AssignmentResponse]:
        """List assignments for a course or all courses."""
        with get_db() as conn:
            query = """
                SELECT a.*, COUNT(s.id) as submissions_count
                FROM assignments a
                LEFT JOIN assignment_submissions s ON a.id = s.assignment_id
            """
            params = []
            if course_id:
                query += " WHERE a.course_id = ?"
                params.append(course_id)
            query += " GROUP BY a.id ORDER BY a.due_date ASC"

            rows = conn.execute(query, params).fetchall()

            assignments = []
            now_iso = datetime.now(timezone.utc).isoformat()
            for r in rows:
                is_overdue = now_iso > r["due_date"]

                sub_row = conn.execute(
                    """
                    SELECT s.*, u.pseudonymous_code as student_code
                    FROM assignment_submissions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.assignment_id = ? AND s.user_id = ?
                    """,
                    (r["id"], user_id),
                ).fetchone()

                my_sub = None
                if sub_row:
                    my_sub = AssignmentSubmissionResponse(
                        id=sub_row["id"],
                        assignment_id=sub_row["assignment_id"],
                        user_id=sub_row["user_id"],
                        student_code=sub_row["student_code"],
                        submission_text=sub_row["submission_text"],
                        marks_awarded=sub_row["marks_awarded"],
                        teacher_feedback=sub_row["teacher_feedback"],
                        graded_by=sub_row["graded_by"],
                        graded_at=sub_row["graded_at"],
                        submitted_at=sub_row["submitted_at"],
                        is_graded=sub_row["marks_awarded"] is not None,
                    )

                assignments.append(
                    AssignmentResponse(
                        id=r["id"],
                        course_id=r["course_id"],
                        lesson_id=r["lesson_id"],
                        title_sindhi=r["title_sindhi"],
                        title_english=r["title_english"],
                        description_sindhi=r["description_sindhi"],
                        due_date=r["due_date"],
                        max_marks=r["max_marks"],
                        created_by=r["created_by"],
                        created_at=r["created_at"],
                        is_overdue=is_overdue,
                        my_submission=my_sub,
                        submissions_count=r["submissions_count"],
                    )
                )

            return assignments

    def submit_assignment(
        self, assignment_id: str, student_id: str, req: AssignmentSubmitRequest
    ) -> AssignmentSubmissionResponse:
        """Submit student response to an assignment, auto-evaluated by AI homework service."""
        from src.services.ai_homework_service import ai_homework_service
        return ai_homework_service.submit_assignment(assignment_id=assignment_id, student_id=student_id, req=req)

    def grade_submission(
        self, assignment_id: str, submission_id: str, teacher_id: str, req: AssignmentGradeRequest
    ) -> AssignmentSubmissionResponse:
        """Teacher/Admin manual grade override for exceptional cases (FR-28)."""
        now_str = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            assignment = conn.execute("SELECT max_marks FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
            if not assignment:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="اسائنمينٽ نه ملي (Assignment not found).")

            if req.marks_awarded > assignment["max_marks"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ڏنل مارڪون وڌ ۾ وڌ مارڪن ({assignment['max_marks']}) کان وڌيڪ آهن (Marks exceed max allowed).",
                )

            sub = conn.execute(
                "SELECT * FROM assignment_submissions WHERE id = ? AND assignment_id = ?",
                (submission_id, assignment_id),
            ).fetchone()
            if not sub:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="جوابي رڪارڊ نه مليو (Submission not found).")

            conn.execute(
                """
                UPDATE assignment_submissions
                SET marks_awarded = ?, teacher_feedback = ?, graded_by = ?, graded_at = ?, grading_status = 'GRADED'
                WHERE id = ?
                """,
                (req.marks_awarded, req.teacher_feedback, teacher_id, now_str, submission_id),
            )

            # Audit log
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, 'SUBMISSION_MANUAL_GRADED', 'assignment_submission', ?, ?, ?)
                """,
                (
                    f"aud-{uuid.uuid4().hex[:8]}",
                    teacher_id,
                    submission_id,
                    json.dumps({"marks": req.marks_awarded, "assignment_id": assignment_id}),
                    now_str,
                ),
            )

            student = conn.execute("SELECT pseudonymous_code FROM users WHERE id = ?", (sub["user_id"],)).fetchone()

            return AssignmentSubmissionResponse(
                id=sub["id"],
                assignment_id=sub["assignment_id"],
                user_id=sub["user_id"],
                student_code=student["pseudonymous_code"] if student else sub["user_id"],
                submission_text=sub["submission_text"],
                marks_awarded=req.marks_awarded,
                teacher_feedback=req.teacher_feedback,
                graded_by=teacher_id,
                graded_at=now_str,
                submitted_at=sub["submitted_at"],
                is_graded=True,
                grading_status="GRADED",
            )

    def list_submissions(self, assignment_id: str) -> List[AssignmentSubmissionResponse]:
        """List all submissions for an assignment."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT s.*, u.pseudonymous_code as student_code
                FROM assignment_submissions s
                JOIN users u ON s.user_id = u.id
                WHERE s.assignment_id = ?
                ORDER BY s.submitted_at DESC
                """,
                (assignment_id,),
            ).fetchall()

            from src.services.ai_homework_service import ai_homework_service
            return [ai_homework_service._format_submission_row(r) for r in rows if r]


assignment_service = AssignmentService()

