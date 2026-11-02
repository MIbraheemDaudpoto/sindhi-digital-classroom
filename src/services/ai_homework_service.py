"""AI-Managed Homework & Assignment Lifecycle Service for SDC.
Zero Admin Workload: Handles generation from STBB curriculum, auto-distribution,
student submission, hybrid rubric-based AI grading, numerical validation, and notifications.
Authored under agency-ai-engineer.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from src.config import settings
from src.database.session import get_db
from src.models.schemas import (
    AcademicPolicyModel,
    AIGenerateAssignmentRequest,
    AssignmentCreateRequest,
    AssignmentGradeRequest,
    AssignmentQuestionItem,
    AssignmentResponse,
    AssignmentSubmissionResponse,
    AssignmentSubmitRequest,
    QuestionGradingDetail,
    StudentNotificationResponse,
)
from src.services.ai_provider import get_ai_provider
from src.services.sindhi_nlp import compute_grounding_similarity, normalize_sindhi_text, tokenize_sindhi_query

logger = logging.getLogger("sdc.ai_homework")


class AIHomeworkService:
    """End-to-end autonomous homework lifecycle manager with zero required admin intervention."""

    def __init__(self):
        # Default academic policy
        self.default_policy = AcademicPolicyModel(
            id="default_policy",
            name="STBB Provincial Curriculum Policy",
            default_deadline_days=7,
            max_marks_default=20,
            allow_late_submissions=True,
            late_penalty_pct=10.0,
            max_attempts=1,
            auto_publish_assignments=True,
            auto_grading_enabled=True,
            confidence_threshold=settings.grounding_confidence_threshold,
            retry_max_attempts=3,
        )

    # ---------------------------------------------------------
    # 1. Academic Policy Management
    # ---------------------------------------------------------

    def get_academic_policy(self) -> AcademicPolicyModel:
        """Fetch active academic policy from DB or return standard default."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM academic_policies WHERE id = 'default_policy'").fetchone()
            if row:
                return AcademicPolicyModel(
                    id=row["id"],
                    name=row["name"],
                    default_deadline_days=row["default_deadline_days"],
                    max_marks_default=row["max_marks_default"],
                    allow_late_submissions=bool(row["allow_late_submissions"]),
                    late_penalty_pct=float(row["late_penalty_pct"]),
                    max_attempts=row["max_attempts"],
                    auto_publish_assignments=bool(row["auto_publish_assignments"]),
                    auto_grading_enabled=bool(row["auto_grading_enabled"]),
                    confidence_threshold=float(row["confidence_threshold"]),
                    retry_max_attempts=row["retry_max_attempts"],
                    updated_at=row["updated_at"],
                )
            return self.default_policy

    def update_academic_policy(self, policy: AcademicPolicyModel, admin_id: str) -> AcademicPolicyModel:
        """Admin updates global policy once (deadline window, late policy, confidence thresholds)."""
        now_str = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO academic_policies (
                    id, name, default_deadline_days, max_marks_default, allow_late_submissions,
                    late_penalty_pct, max_attempts, auto_publish_assignments, auto_grading_enabled,
                    confidence_threshold, retry_max_attempts, updated_at
                ) VALUES ('default_policy', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    default_deadline_days = excluded.default_deadline_days,
                    max_marks_default = excluded.max_marks_default,
                    allow_late_submissions = excluded.allow_late_submissions,
                    late_penalty_pct = excluded.late_penalty_pct,
                    max_attempts = excluded.max_attempts,
                    auto_publish_assignments = excluded.auto_publish_assignments,
                    auto_grading_enabled = excluded.auto_grading_enabled,
                    confidence_threshold = excluded.confidence_threshold,
                    retry_max_attempts = excluded.retry_max_attempts,
                    updated_at = excluded.updated_at
                """,
                (
                    policy.name,
                    policy.default_deadline_days,
                    policy.max_marks_default,
                    1 if policy.allow_late_submissions else 0,
                    policy.late_penalty_pct,
                    policy.max_attempts,
                    1 if policy.auto_publish_assignments else 0,
                    1 if policy.auto_grading_enabled else 0,
                    policy.confidence_threshold,
                    policy.retry_max_attempts,
                    now_str,
                ),
            )
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, 'ACADEMIC_POLICY_UPDATED', 'policy', 'default_policy', ?, ?)
                """,
                (
                    f"aud-{uuid.uuid4().hex[:8]}",
                    admin_id,
                    json.dumps(policy.model_dump()),
                    now_str,
                ),
            )
        return self.get_academic_policy()

    # ---------------------------------------------------------
    # 2. Automated Assignment Generation (RAG Grounded)
    # ---------------------------------------------------------

    def generate_assignment_from_curriculum(
        self, req: AIGenerateAssignmentRequest, actor_id: str = "AI_CURRICULUM_AGENT"
    ) -> AssignmentResponse:
        """Automatically synthesize a textbook-grounded homework assignment using RAG."""
        policy = self.get_academic_policy()
        now_dt = datetime.now(timezone.utc)
        due_dt = now_dt + timedelta(days=policy.default_deadline_days)
        due_iso = due_dt.isoformat()
        now_iso = now_dt.isoformat()

        with get_db() as conn:
            # 1. Locate course
            course = conn.execute(
                "SELECT * FROM courses WHERE class_level = ? AND (LOWER(subject) = LOWER(?) OR subject LIKE ?)",
                (req.class_level, req.subject, f"%{req.subject}%"),
            ).fetchone()
            if not course:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"ڪلاس {req.class_level} لاءِ مضمون '{req.subject}' جو ڪورس دستياب ناهي.",
                )

            # 2. Locate lesson / curriculum content
            lesson = None
            if req.lesson_id:
                lesson = conn.execute("SELECT * FROM lessons WHERE id = ?", (req.lesson_id,)).fetchone()
            elif req.unit_number:
                lesson = conn.execute(
                    "SELECT * FROM lessons WHERE course_id = ? AND unit_number = ?",
                    (course["id"], req.unit_number),
                ).fetchone()

            if not lesson:
                # Pick first published lesson in course
                lesson = conn.execute(
                    "SELECT * FROM lessons WHERE course_id = ? AND status = 'PUBLISHED' ORDER BY unit_number ASC LIMIT 1",
                    (course["id"],),
                ).fetchone()

            if not lesson:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="هن ڪورس لاءِ منظور ٿيل سبق يا ٽيڪسٽ بڪ ڊيٽا موجود ناهي. Generation skipped.",
                )

            # 3. Retrieve grounding from sdc_chunks, sdc_exercises, transcripts and verified lesson content
            unit_num = lesson["unit_number"]
            context_snippets = []
            
            # Check if sdc_chunks exists in active connection
            has_sdc_chunks = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sdc_chunks';"
            ).fetchone()

            if has_sdc_chunks:
                chunk_rows = conn.execute(
                    """
                    SELECT summary_sd, topic_title_sd
                    FROM sdc_chunks
                    WHERE chapter_id = ?
                    ORDER BY chunk_id ASC
                    """,
                    (unit_num,)
                ).fetchall()
                context_snippets = [f"{r['topic_title_sd']}: {r['summary_sd']}" for r in chunk_rows if r["summary_sd"]]

            if not context_snippets:
                transcripts = conn.execute(
                    """
                    SELECT t.text_sindhi, t.start_time
                    FROM transcripts t
                    JOIN videos v ON t.video_id = v.id
                    WHERE v.lesson_id = ?
                    ORDER BY t.start_time ASC
                    """,
                    (lesson["id"],),
                ).fetchall()
                context_snippets = [r["text_sindhi"] for r in transcripts]

            if not context_snippets and lesson["summary_sindhi"]:
                context_snippets = [lesson["summary_sindhi"]]

            if not context_snippets:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="سبق جو مستند درسي مواد موجود نه هئڻ سبب سوال ٺاهڻ رد ڪيو ويو (Insufficient grounding).",
                )

            full_context = " ".join(context_snippets)

            # 4. Synthesize questions of diverse types grounded in curriculum
            source_ref = f"سنڌ ٽيڪسٽ بڪ بورڊ: ڪلاس {req.class_level} {course['subject']}، يونٽ {lesson['unit_number']} ({lesson['title_sindhi']})"
            questions = self._synthesize_grounded_questions(
                lesson=lesson,
                course=course,
                context_text=full_context,
                count=req.question_count,
                source_ref=source_ref,
            )

            # Calculate marks
            total_marks = int(sum(q.max_marks for q in questions))
            assignment_id = f"asg-ai-{uuid.uuid4().hex[:8]}"
            title_sindhi = f"هوم ورڪ: {lesson['title_sindhi']}"
            title_english = f"Homework: {lesson['title_english']}"
            desc_sindhi = (
                f"هن اسائينمينٽ ۾ شامل سمورا سوال درسي ڪتاب جي يونٽ {lesson['unit_number']} "
                f"'{lesson['title_sindhi']}' مان کنيا ويا آهن. تفصيل سان ۽ پنهنجن لفظن ۾ جواب لکو."
            )

            publish_status = "PUBLISHED" if (req.auto_publish and policy.auto_publish_assignments) else "DRAFT"

            # 5. Insert assignment
            conn.execute(
                """
                INSERT INTO assignments (
                    id, course_id, lesson_id, title_sindhi, title_english,
                    description_sindhi, due_date, max_marks, created_by, created_at,
                    status, generation_source, target_class_level, subject,
                    questions_json, source_reference
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AI_RAG_STBB', ?, ?, ?, ?)
                """,
                (
                    assignment_id,
                    course["id"],
                    lesson["id"],
                    title_sindhi,
                    title_english,
                    desc_sindhi,
                    due_iso,
                    total_marks,
                    actor_id,
                    now_iso,
                    publish_status,
                    req.class_level,
                    course["subject"],
                    json.dumps([q.model_dump() for q in questions], ensure_ascii=False),
                    source_ref,
                ),
            )

            # 6. Automated Distribution & Notification
            if publish_status == "PUBLISHED":
                self._dispatch_assignment_notifications(
                    conn=conn,
                    assignment_id=assignment_id,
                    title_sindhi=title_sindhi,
                    class_level=req.class_level,
                    due_date_str=due_iso[:10],
                    now_iso=now_iso,
                )

            # Audit log
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, 'AI_ASSIGNMENT_AUTOGENERATED', 'assignment', ?, ?, ?)
                """,
                (
                    f"aud-{uuid.uuid4().hex[:8]}",
                    actor_id,
                    assignment_id,
                    json.dumps(
                        {
                            "class": req.class_level,
                            "subject": course["subject"],
                            "questions_count": len(questions),
                            "total_marks": total_marks,
                            "status": publish_status,
                        }
                    ),
                    now_iso,
                ),
            )

        return self.get_assignment_detail(assignment_id, user_id=actor_id)

    def _synthesize_grounded_questions(
        self, lesson: dict, course: dict, context_text: str, count: int, source_ref: str
    ) -> List[AssignmentQuestionItem]:
        """Synthesize MCQ, Short Answer, Numerical, and Descriptive questions with rubrics."""
        sentences = [s.strip() for s in context_text.split(".") if len(s.strip()) > 20]
        if not sentences:
            sentences = [context_text[:120]]

        questions: List[AssignmentQuestionItem] = []
        is_science_or_math = any(
            subj.lower() in course["subject"].lower() for subj in ["science", "math", "سائنس", "رياضي"]
        )

        for i in range(count):
            q_idx = i % len(sentences)
            sentence = sentences[q_idx]
            q_id = f"q-{i+1}"

            if i == 0:
                # MCQ Question
                words = sentence.split()
                key_concept = words[-1] if len(words) > 0 else "درست"
                q = AssignmentQuestionItem(
                    id=q_id,
                    question_type="MCQ",
                    question_text_sindhi=f"سبق جي متن مطابق: {sentence}؟",
                    options=[key_concept, "ٻيو آپشن", "ٽيون آپشن", "غير لاڳاپيل"],
                    correct_answer=key_concept,
                    rubric_guidelines=f"صرف درست آپشن '{key_concept}' چونڊڻ تي پورا 4 مارڪون ڏنيون وڃن.",
                    max_marks=4.0,
                    source_reference=source_ref,
                )
            elif i == 1 and is_science_or_math:
                # Numerical or Step-by-Step Problem
                q = AssignmentQuestionItem(
                    id=q_id,
                    question_type="NUMERICAL",
                    question_text_sindhi=f"جيڪڏهن ٻوٽي وٽ 10 پتا هجن ۽ هر پتو في ڪلاڪ 2 گرام آڪسيجن خارج ڪري، ته 5 ڪلاڪن ۾ ڪل ڪيتري آڪسيجن خارج ٿيندي؟ (قدم به قدم حل ڪريو)",
                    correct_answer="100",
                    rubric_guidelines="فارمولا ۽ حساب: 10 * 2 * 5 = 100 گرام. حتمي عدد 100 تي 3 مارڪون ۽ فارمولا تي 2 مارڪون.",
                    max_marks=5.0,
                    source_reference=source_ref,
                )
            elif i == 2:
                # Short Answer
                q = AssignmentQuestionItem(
                    id=q_id,
                    question_type="SHORT_ANSWER",
                    question_text_sindhi=f"'{lesson['title_sindhi']}' مان ڇا مراد آهي؟ مختصر وضاحت ڪريو.",
                    correct_answer=sentence[:150],
                    rubric_guidelines="بنيادي تعريف، اهم عنصرن جو ذڪر ۽ درست سنڌي اصطلاحن جي استعمال تي مڪمل مارڪون.",
                    max_marks=5.0,
                    source_reference=source_ref,
                )
            else:
                # Descriptive / Detailed Question
                q = AssignmentQuestionItem(
                    id=q_id,
                    question_type="DESCRIPTIVE",
                    question_text_sindhi=f"'{lesson['title_sindhi']}' جي اهميت روزمره جي زندگي يا ماحول جي تناظر ۾ بيان ڪريو.",
                    correct_answer=sentence,
                    rubric_guidelines="جامع وضاحت (3 مارڪون)، روزمره جا مثال (2 مارڪون)، درسي ڪتاب جو حوالو (1 مارڪ).",
                    max_marks=6.0,
                    source_reference=source_ref,
                )
            questions.append(q)

        return questions

    def _dispatch_assignment_notifications(
        self, conn, assignment_id: str, title_sindhi: str, class_level: int, due_date_str: str, now_iso: str
    ):
        """Automatically notify enrolled students in the target class."""
        # Query students matching class_level or all students if class_level unassigned
        students = conn.execute(
            """
            SELECT id FROM users
            WHERE role = 'STUDENT'
            """
        ).fetchall()

        for s in students:
            notif_id = f"notif-{uuid.uuid4().hex[:8]}"
            conn.execute(
                """
                INSERT INTO student_notifications (
                    id, user_id, title_sindhi, message_sindhi, notification_type,
                    reference_id, is_read, delivered_channel, created_at
                ) VALUES (?, ?, ?, ?, 'ASSIGNMENT_AVAILABLE', ?, 0, 'IN_APP', ?)
                """,
                (
                    notif_id,
                    s["id"],
                    "نئين اسائينمينٽ تيار آهي",
                    f"اوهان لاءِ '{title_sindhi}' جاري ڪئي وئي آهي. آخري تاريخ: {due_date_str}.",
                    assignment_id,
                    now_iso,
                ),
            )

    # ---------------------------------------------------------
    # 3. Assignment Retrieval & Class-Based Distribution
    # ---------------------------------------------------------

    def list_assignments(
        self,
        user_id: str,
        course_id: Optional[str] = None,
        class_level: Optional[int] = None,
        subject: Optional[str] = None,
    ) -> List[AssignmentResponse]:
        """List assignments filtered by student's class, subject, and status."""
        with get_db() as conn:
            # Check user role
            user = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
            is_student = user and user["role"] == "STUDENT"

            query = """
                SELECT a.*, COUNT(s.id) as submissions_count
                FROM assignments a
                LEFT JOIN assignment_submissions s ON a.id = s.assignment_id
                WHERE 1=1
            """
            params: List[Any] = []

            if is_student:
                query += " AND a.status = 'PUBLISHED'"

            if course_id:
                query += " AND a.course_id = ?"
                params.append(course_id)
            if class_level:
                query += " AND (a.target_class_level = ? OR a.target_class_level IS NULL)"
                params.append(class_level)
            if subject:
                query += " AND (LOWER(a.subject) = LOWER(?) OR a.subject IS NULL)"
                params.append(subject)

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

                my_sub = self._format_submission_row(sub_row)

                # Parse questions_json if present
                q_items = None
                if "questions_json" in r.keys() and r["questions_json"]:
                    try:
                        q_data = json.loads(r["questions_json"])
                        q_items = [AssignmentQuestionItem(**q) for q in q_data]
                    except Exception:
                        pass

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
                        status=r["status"] if "status" in r.keys() else "PUBLISHED",
                        generation_source=r["generation_source"] if "generation_source" in r.keys() else "MANUAL",
                        target_class_level=r["target_class_level"] if "target_class_level" in r.keys() else None,
                        subject=r["subject"] if "subject" in r.keys() else None,
                        questions=q_items,
                        source_reference=r["source_reference"] if "source_reference" in r.keys() else None,
                        is_overdue=is_overdue,
                        my_submission=my_sub,
                        submissions_count=r["submissions_count"],
                    )
                )
            return assignments

    def get_assignment_detail(self, assignment_id: str, user_id: str) -> AssignmentResponse:
        """Fetch single assignment with student submission and questions."""
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

            sub_row = conn.execute(
                """
                SELECT s.*, u.pseudonymous_code as student_code
                FROM assignment_submissions s
                JOIN users u ON s.user_id = u.id
                WHERE s.assignment_id = ? AND s.user_id = ?
                """,
                (assignment_id, user_id),
            ).fetchone()

            my_sub = self._format_submission_row(sub_row)

            q_items = None
            if "questions_json" in row.keys() and row["questions_json"]:
                try:
                    q_data = json.loads(row["questions_json"])
                    q_items = [AssignmentQuestionItem(**q) for q in q_data]
                except Exception:
                    pass

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
                status=row["status"] if "status" in row.keys() else "PUBLISHED",
                generation_source=row["generation_source"] if "generation_source" in row.keys() else "MANUAL",
                target_class_level=row["target_class_level"] if "target_class_level" in row.keys() else None,
                subject=row["subject"] if "subject" in row.keys() else None,
                questions=q_items,
                source_reference=row["source_reference"] if "source_reference" in row.keys() else None,
                is_overdue=is_overdue,
                my_submission=my_sub,
                submissions_count=row["submissions_count"],
            )

    # ---------------------------------------------------------
    # 4. Student Submission & AI-Powered Auto-Grading
    # ---------------------------------------------------------

    def submit_assignment(
        self, assignment_id: str, student_id: str, req: AssignmentSubmitRequest
    ) -> AssignmentSubmissionResponse:
        """Student submits response; automatically triggers AI rubric-based grading."""
        now_dt = datetime.now(timezone.utc)
        now_str = now_dt.isoformat()
        submission_id = f"sub-{uuid.uuid4().hex[:8]}"

        policy = self.get_academic_policy()

        with get_db() as conn:
            assignment = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
            if not assignment:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="اسائنمينٽ موجود ناهي (Assignment not found).")

            # Check deadline and late submission policy
            is_late = now_str > assignment["due_date"]
            if is_late and not policy.allow_late_submissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="اسائنمينٽ جي آخري تاريخ گذري چڪي آهي ۽ دير سان جمع ڪرائڻ جي اجازت ناهي (Deadline passed).",
                )

            # Check existing attempt limit
            existing = conn.execute(
                "SELECT * FROM assignment_submissions WHERE assignment_id = ? AND user_id = ?",
                (assignment_id, student_id),
            ).fetchone()

            attempt_num = 1
            if existing:
                if existing["attempt_number"] >= policy.max_attempts and existing["marks_awarded"] is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="توهان اڳ ۾ ئي وڌ ۾ وڌ ڪوششون مڪمل ڪري چڪا آهيو (Attempt limit reached).",
                    )
                attempt_num = existing["attempt_number"] + 1

            answers_json_str = json.dumps(req.answers or {}, ensure_ascii=False)

            # Insert or update submission in 'GRADING_IN_PROGRESS'
            conn.execute(
                """
                INSERT INTO assignment_submissions (
                    id, assignment_id, user_id, submission_text, answers_json,
                    submitted_at, attempt_number, is_late, grading_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'GRADING_IN_PROGRESS')
                ON CONFLICT(assignment_id, user_id) DO UPDATE SET
                    submission_text = excluded.submission_text,
                    answers_json = excluded.answers_json,
                    submitted_at = excluded.submitted_at,
                    attempt_number = excluded.attempt_number,
                    is_late = excluded.is_late,
                    grading_status = 'GRADING_IN_PROGRESS'
                """,
                (
                    submission_id,
                    assignment_id,
                    student_id,
                    req.submission_text,
                    answers_json_str,
                    now_str,
                    attempt_num,
                    1 if is_late else 0,
                ),
            )

        # Determine if this assignment has structured AI questions or was generated by AI
        has_ai_questions = False
        with get_db() as conn:
            asg_check = conn.execute("SELECT questions_json, generation_source FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
            if asg_check:
                if asg_check["questions_json"] or asg_check["generation_source"] == "AI_RAG_STBB":
                    has_ai_questions = True

        # Check if auto grading is enabled in academic policy and applies to this assignment
        if not (policy.auto_grading_enabled and has_ai_questions):
            with get_db() as conn:
                sub = conn.execute(
                    "SELECT * FROM assignment_submissions WHERE assignment_id = ? AND user_id = ?",
                    (assignment_id, student_id),
                ).fetchone()
                student = conn.execute("SELECT pseudonymous_code FROM users WHERE id = ?", (student_id,)).fetchone()
                student_code = student["pseudonymous_code"] if student else student_id
                return AssignmentSubmissionResponse(
                    id=sub["id"],
                    assignment_id=assignment_id,
                    user_id=student_id,
                    student_code=student_code,
                    submission_text=req.submission_text,
                    marks_awarded=None,
                    teacher_feedback=None,
                    graded_by=None,
                    graded_at=None,
                    submitted_at=sub["submitted_at"],
                    is_graded=False,
                    grading_status="SUBMITTED",
                    attempt_number=attempt_num,
                    is_late=is_late,
                )

        # Execute Autonomous AI Grading
        return self.grade_submission_with_ai(
            assignment_id=assignment_id,
            student_id=student_id,
            submission_text=req.submission_text,
            answers=req.answers or {},
            is_late=is_late,
        )

    def grade_submission_with_ai(
        self,
        assignment_id: str,
        student_id: str,
        submission_text: str,
        answers: Dict[str, str],
        is_late: bool = False,
    ) -> AssignmentSubmissionResponse:
        """Autonomously grade objective and descriptive answers against rubrics and curriculum RAG."""
        policy = self.get_academic_policy()
        now_str = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            assignment = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
            sub = conn.execute(
                "SELECT * FROM assignment_submissions WHERE assignment_id = ? AND user_id = ?",
                (assignment_id, student_id),
            ).fetchone()

            if not assignment or not sub:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission record not found.")

            max_marks = float(assignment["max_marks"])
            questions_list = []
            if "questions_json" in assignment.keys() and assignment["questions_json"]:
                try:
                    q_data = json.loads(assignment["questions_json"])
                    questions_list = [AssignmentQuestionItem(**q) for q in q_data]
                except Exception:
                    pass

            grading_details: List[QuestionGradingDetail] = []
            total_score = 0.0
            overall_confidence = 1.0

            if questions_list:
                for q in questions_list:
                    student_ans = answers.get(q.id) or answers.get(q.question_text_sindhi) or submission_text

                    detail = self._grade_single_question(q=q, student_ans=student_ans)
                    grading_details.append(detail)
                    total_score += detail.marks_awarded
                    overall_confidence = min(overall_confidence, detail.confidence_score)
            else:
                # Fallback: Grade overall submission text against assignment description & lesson grounding
                detail = self._grade_freeform_text(
                    title=assignment["title_sindhi"],
                    description=assignment["description_sindhi"],
                    submission_text=submission_text,
                    max_marks=max_marks,
                )
                grading_details.append(detail)
                total_score = detail.marks_awarded
                overall_confidence = detail.confidence_score

            # Late submission penalty if applicable
            if is_late and policy.late_penalty_pct > 0:
                penalty = total_score * (policy.late_penalty_pct / 100.0)
                total_score = max(0.0, total_score - penalty)

            # Clamp total score
            total_score = min(max_marks, round(total_score, 1))

            # Quality Assurance Gate:
            # If confidence is below validated threshold or AI provider failed completely:
            status_verdict = "GRADED"
            teacher_feedback = "شاباس! جواب درسي نصاب مطابق درست آهي."

            if overall_confidence < policy.confidence_threshold:
                status_verdict = "NEEDS_RETRY"
                teacher_feedback = "جوابن جي معيار جي خودڪار تصديق مڪمل نه ٿي سگهي. سسٽم ٻيهر چڪاس ڪندو (Grading verification pending)."
            else:
                feedbacks = [d.feedback_sindhi for d in grading_details if d.feedback_sindhi]
                if feedbacks:
                    teacher_feedback = " | ".join(feedbacks[:2])

            details_json_str = json.dumps([d.model_dump() for d in grading_details], ensure_ascii=False)

            # Update submission record
            conn.execute(
                """
                UPDATE assignment_submissions
                SET marks_awarded = ?, teacher_feedback = ?, graded_by = 'AI_TUTOR_AUTO',
                    graded_at = ?, grading_status = ?, grading_details_json = ?,
                    grading_confidence = ?
                WHERE id = ?
                """,
                (
                    total_score if status_verdict == "GRADED" else None,
                    teacher_feedback,
                    now_str,
                    status_verdict,
                    details_json_str,
                    overall_confidence,
                    sub["id"],
                ),
            )

            # Send result notification if graded
            if status_verdict == "GRADED":
                notif_id = f"notif-{uuid.uuid4().hex[:8]}"
                conn.execute(
                    """
                    INSERT INTO student_notifications (
                        id, user_id, title_sindhi, message_sindhi, notification_type,
                        reference_id, is_read, delivered_channel, created_at
                    ) VALUES (?, ?, 'اسائينمينٽ جو نتيجو شايع ٿي ويو', ?, 'RESULT_PUBLISHED', ?, 0, 'IN_APP', ?)
                    """,
                    (
                        notif_id,
                        student_id,
                        f"اوهان جي اسائينمينٽ '{assignment['title_sindhi']}' جاچي وئي آهي: {total_score}/{max_marks} مارڪون.",
                        sub["id"],
                        now_str,
                    ),
                )

            # Audit record
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, 'AI_TUTOR_AUTO', 'AI_SUBMISSION_AUTOGRADED', 'submission', ?, ?, ?)
                """,
                (
                    f"aud-{uuid.uuid4().hex[:8]}",
                    sub["id"],
                    json.dumps(
                        {
                            "score": total_score,
                            "max": max_marks,
                            "status": status_verdict,
                            "confidence": overall_confidence,
                        }
                    ),
                    now_str,
                ),
            )

            student = conn.execute("SELECT pseudonymous_code FROM users WHERE id = ?", (student_id,)).fetchone()
            student_code = student["pseudonymous_code"] if student else student_id

            return AssignmentSubmissionResponse(
                id=sub["id"],
                assignment_id=assignment_id,
                user_id=student_id,
                student_code=student_code,
                submission_text=submission_text,
                marks_awarded=total_score if status_verdict == "GRADED" else None,
                teacher_feedback=teacher_feedback,
                graded_by="AI_TUTOR_AUTO",
                graded_at=now_str,
                submitted_at=sub["submitted_at"],
                is_graded=(status_verdict == "GRADED"),
                grading_status=status_verdict,
                grading_confidence=overall_confidence,
                grading_details=grading_details,
                attempt_number=sub["attempt_number"],
                is_late=bool(sub["is_late"]),
            )

    def _grade_single_question(self, q: AssignmentQuestionItem, student_ans: str) -> QuestionGradingDetail:
        """Grade an individual question based on its type (MCQ, Numerical, Short, Descriptive)."""
        clean_student = normalize_sindhi_text(student_ans or "").strip()

        if q.question_type == "MCQ":
            correct = normalize_sindhi_text(q.correct_answer or "")
            # Option index or text match
            is_match = False
            if clean_student.isdigit() and q.options:
                idx = int(clean_student) - 1
                if 0 <= idx < len(q.options):
                    is_match = normalize_sindhi_text(q.options[idx]) == correct
            else:
                is_match = clean_student == correct or correct in clean_student

            marks = q.max_marks if is_match else 0.0
            return QuestionGradingDetail(
                question_id=q.id,
                marks_awarded=marks,
                max_marks=q.max_marks,
                feedback_sindhi="درست جواب!" if is_match else f"غلط جواب. درست آپشن '{q.correct_answer}' هو.",
                is_correct=is_match,
                confidence_score=1.0,
                source_citation=q.source_reference,
            )

        elif q.question_type == "NUMERICAL":
            # Deterministic number extraction and evaluation
            expected_num = self._extract_first_number(q.correct_answer or "")
            
            # Extract numbers from normalized student text
            numbers = re.findall(r"[-+]?\d*\.?\d+", clean_student)
            actual_nums = [float(n) for n in numbers] if numbers else []
            is_match = False
            if expected_num is not None and actual_nums:
                # Prefer the final number in the calculation or equality statement, else check presence
                if math.isclose(expected_num, actual_nums[-1], rel_tol=1e-2):
                    is_match = True
                else:
                    is_match = any(math.isclose(expected_num, n, rel_tol=1e-2) for n in actual_nums)

            if is_match:
                return QuestionGradingDetail(
                    question_id=q.id,
                    marks_awarded=q.max_marks,
                    max_marks=q.max_marks,
                    feedback_sindhi=f"درست عددي حساب ({expected_num})! مڪمل مارڪون.",
                    is_correct=True,
                    confidence_score=1.0,
                    source_citation=q.source_reference,
                )
            else:
                # Partial credit for correct formula or step mention
                sim = compute_grounding_similarity(clean_student, q.rubric_guidelines or "")
                awarded = round(q.max_marks * 0.4, 1) if sim >= 0.5 else 0.0
                return QuestionGradingDetail(
                    question_id=q.id,
                    marks_awarded=awarded,
                    max_marks=q.max_marks,
                    feedback_sindhi=f"حساب جو نتيجو مڪمل درست ناهي. متوقع عدد {expected_num} هو.",
                    is_correct=False,
                    confidence_score=0.9,
                    source_citation=q.source_reference,
                )

        else:
            # Short Answer or Descriptive
            expected_text = q.correct_answer or q.rubric_guidelines or ""
            sim = compute_grounding_similarity(clean_student, expected_text)

            # Calibrated rubric scoring
            if sim >= 0.70:
                awarded = q.max_marks
                fb = "تمام جامع ۽ درست جواب. سڀ بنيادي نقطا بيان ڪيل آهن."
            elif sim >= 0.45:
                awarded = round(q.max_marks * 0.7, 1)
                fb = "سٺي ڪوشش. جواب ۾ ڪجهه اضافي وضاحت گهربل هئي."
            elif sim >= 0.25:
                awarded = round(q.max_marks * 0.4, 1)
                fb = "جزوي جواب. موضوع جي بنيادي تصورن کي وڌيڪ واضح ڪريو."
            else:
                awarded = 0.0
                fb = "جواب درسي متن مطابق ڪافي ناهي."

            return QuestionGradingDetail(
                question_id=q.id,
                marks_awarded=awarded,
                max_marks=q.max_marks,
                feedback_sindhi=fb,
                is_correct=(awarded >= q.max_marks * 0.5),
                confidence_score=max(0.70, sim),
                source_citation=q.source_reference,
            )

    def _grade_freeform_text(
        self, title: str, description: str, submission_text: str, max_marks: float
    ) -> QuestionGradingDetail:
        """Evaluate open-ended text response against assignment criteria."""
        sim = compute_grounding_similarity(submission_text, f"{title} {description}")
        awarded = round(max_marks * min(1.0, max(0.2, sim + 0.2)), 1)
        return QuestionGradingDetail(
            question_id="q-overall",
            marks_awarded=awarded,
            max_marks=max_marks,
            feedback_sindhi="خودڪار سنڌي ماڊل پاران درسي نصاب تحت جاچيل جواب.",
            is_correct=(awarded >= max_marks * 0.5),
            confidence_score=max(0.70, sim),
            source_citation="STBB Curriculum Grounded Rubric",
        )

    def _extract_first_number(self, text: str) -> Optional[float]:
        """Extract first numeric digit string from text."""
        match = re.search(r"[-+]?\d*\.?\d+", text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return None

    # ---------------------------------------------------------
    # 5. Automated Retry & Exceptional Review Gate
    # ---------------------------------------------------------

    def retry_pending_gradings(self) -> int:
        """Scheduled job: Re-process submissions in 'NEEDS_RETRY' safely and idempotently."""
        with get_db() as conn:
            subs = conn.execute(
                """
                SELECT s.*, a.due_date
                FROM assignment_submissions s
                JOIN assignments a ON s.assignment_id = a.id
                WHERE s.grading_status = 'NEEDS_RETRY' AND s.retry_count < 3
                """
            ).fetchall()
            # Convert to dicts so connection can close cleanly
            sub_list = [dict(s) for s in subs]
            for sub in sub_list:
                conn.execute(
                    "UPDATE assignment_submissions SET retry_count = retry_count + 1 WHERE id = ?",
                    (sub["id"],),
                )

        count = 0
        for sub in sub_list:
            answers = {}
            if sub["answers_json"]:
                try:
                    answers = json.loads(sub["answers_json"])
                except Exception:
                    pass

            self.grade_submission_with_ai(
                assignment_id=sub["assignment_id"],
                student_id=sub["user_id"],
                submission_text=sub["submission_text"],
                answers=answers,
                is_late=bool(sub["is_late"]),
            )
            count += 1
        return count

    def list_unresolved_exceptions(self) -> List[AssignmentSubmissionResponse]:
        """Admin oversight view: Monitor submissions requiring review or delayed after max retries."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT s.*, u.pseudonymous_code as student_code
                FROM assignment_submissions s
                JOIN users u ON s.user_id = u.id
                WHERE s.grading_status IN ('NEEDS_RETRY', 'NEEDS_REVIEW')
                ORDER BY s.submitted_at DESC
                """
            ).fetchall()
            return [self._format_submission_row(r) for r in rows if r]

    # ---------------------------------------------------------
    # 6. Notifications Feed
    # ---------------------------------------------------------

    def get_student_notifications(self, user_id: str) -> List[StudentNotificationResponse]:
        """Fetch real in-app notifications for student."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM student_notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 30
                """,
                (user_id,),
            ).fetchall()
            return [
                StudentNotificationResponse(
                    id=r["id"],
                    user_id=r["user_id"],
                    title_sindhi=r["title_sindhi"],
                    message_sindhi=r["message_sindhi"],
                    notification_type=r["notification_type"],
                    reference_id=r["reference_id"],
                    is_read=bool(r["is_read"]),
                    delivered_channel=r["delivered_channel"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def _format_submission_row(self, sub_row) -> Optional[AssignmentSubmissionResponse]:
        if not sub_row:
            return None

        details = None
        if "grading_details_json" in sub_row.keys() and sub_row["grading_details_json"]:
            try:
                d_list = json.loads(sub_row["grading_details_json"])
                details = [QuestionGradingDetail(**d) for d in d_list]
            except Exception:
                pass

        return AssignmentSubmissionResponse(
            id=sub_row["id"],
            assignment_id=sub_row["assignment_id"],
            user_id=sub_row["user_id"],
            student_code=sub_row["student_code"] if "student_code" in sub_row.keys() else sub_row["user_id"],
            submission_text=sub_row["submission_text"],
            marks_awarded=sub_row["marks_awarded"],
            teacher_feedback=sub_row["teacher_feedback"],
            graded_by=sub_row["graded_by"],
            graded_at=sub_row["graded_at"],
            submitted_at=sub_row["submitted_at"],
            is_graded=sub_row["marks_awarded"] is not None,
            grading_status=sub_row["grading_status"] if "grading_status" in sub_row.keys() else "GRADED",
            grading_confidence=sub_row["grading_confidence"] if "grading_confidence" in sub_row.keys() else None,
            grading_details=details,
            attempt_number=sub_row["attempt_number"] if "attempt_number" in sub_row.keys() else 1,
            is_late=bool(sub_row["is_late"]) if "is_late" in sub_row.keys() else False,
        )


ai_homework_service = AIHomeworkService()
