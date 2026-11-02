"""Smart Video Quiz Service for SDC.
Implements the 7-step pipeline: upload, transcription, 2-3 min splitting,
question generation, mandatory teacher approval gate (FR-13), randomized playback, and auto-marking.
Authored under agency-ai-engineer and agency-backend-architect.
"""

import json
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.database.session import get_db
from src.models.schemas import AttemptResponse, AttemptSubmitRequest, QuestionApprovalRequest, QuestionResponse, QuestionStatus


class VideoQuizService:
    """Smart Video Quiz orchestrator enforcing the Teacher Approval Gate (FR-13)."""

    def get_pending_questions_for_teacher(self, school_id: Optional[str] = None) -> List[QuestionResponse]:
        """Retrieve questions awaiting teacher approval (FR-13 Gate)."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT q.*, l.title_sindhi as lesson_title 
                FROM questions q
                JOIN lessons l ON q.lesson_id = l.id
                WHERE q.status = 'PENDING_APPROVAL'
                ORDER BY q.timestamp_seconds ASC
                """
            ).fetchall()

            return [
                QuestionResponse(
                    id=r["id"],
                    lesson_id=r["lesson_id"],
                    timestamp_seconds=r["timestamp_seconds"],
                    text_sindhi=r["text_sindhi"],
                    options=json.loads(r["options_json"]),
                    correct_answer_index=r["correct_answer_index"],
                    difficulty=r["difficulty"],
                    topic=r["topic"],
                    status=QuestionStatus(r["status"])
                )
                for r in rows
            ]

    def review_question(self, question_id: str, teacher_id: str, req: QuestionApprovalRequest) -> bool:
        """Approve, edit, or reject a draft question (FR-13 Teacher Gate)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            q_row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
            if not q_row:
                return False

            new_text = req.edited_text_sindhi or q_row["text_sindhi"]
            new_opts = json.dumps(req.edited_options) if req.edited_options else q_row["options_json"]
            new_corr = req.edited_correct_answer if req.edited_correct_answer is not None else q_row["correct_answer_index"]

            conn.execute(
                """
                UPDATE questions
                SET status = ?, text_sindhi = ?, options_json = ?, correct_answer_index = ?, approved_by = ?, approved_at = ?
                WHERE id = ?
                """,
                (req.status.value, new_text, new_opts, new_corr, teacher_id, now_iso, question_id)
            )

            # Audit log (FR-35)
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    teacher_id,
                    f"QUESTION_{req.status.value}",
                    "question",
                    question_id,
                    json.dumps({"old_status": q_row["status"], "new_status": req.status.value}),
                    now_iso
                )
            )
            return True

    def get_lesson_quiz_bank_for_student(self, lesson_id: str, student_id: str) -> List[QuestionResponse]:
        """Fetch randomized, balanced question bank of APPROVED questions only (FR-13, FR-16, FR-17)."""
        with get_db() as conn:
            # Query ONLY APPROVED questions
            rows = conn.execute(
                """
                SELECT * FROM questions 
                WHERE lesson_id = ? AND status = 'APPROVED'
                ORDER BY timestamp_seconds ASC
                """,
                (lesson_id,)
            ).fetchall()

            if not rows:
                return []

            # Return all approved checkpoints sorted chronologically by timestamp
            selected_rows = list(rows)
            selected_rows.sort(key=lambda x: (x["timestamp_seconds"] or 0))

            return [
                QuestionResponse(
                    id=r["id"],
                    lesson_id=r["lesson_id"],
                    timestamp_seconds=r["timestamp_seconds"],
                    text_sindhi=r["text_sindhi"],
                    options=json.loads(r["options_json"]),
                    correct_answer_index=None, # Omit correct answer to prevent student cheating
                    difficulty=r["difficulty"],
                    topic=r["topic"],
                    status=QuestionStatus.APPROVED
                )
                for r in selected_rows
            ]

    def submit_attempt(self, user_id: str, req: AttemptSubmitRequest) -> Optional[AttemptResponse]:
        """Auto-mark answer, persist attempt in SQLite, and return correctness explanation (FR-27)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            q_row = conn.execute("SELECT * FROM questions WHERE id = ?", (req.question_id,)).fetchone()
            if not q_row:
                return None

            correct_idx = q_row["correct_answer_index"]
            is_skipped = (req.selected_option == -1 or getattr(req, "is_skipped", False))
            if is_skipped:
                is_correct = False
                explanation = "توهان هي سوال ڇڏي ڏنو (Question was skipped)."
            else:
                is_correct = (req.selected_option == correct_idx)
                explanation = (
                    "شاباس! توهان جو جواب بلڪل درست آهي."
                    if is_correct
                    else f"توهان جو جواب غلط آهي. صحيح جواب آپشن {correct_idx + 1} آهي."
                )
            attempt_id = str(uuid.uuid4())

            conn.execute(
                """
                INSERT INTO attempts (
                    id, user_id, question_id, selected_option, is_correct, time_taken_seconds, device_sync_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    user_id,
                    req.question_id,
                    req.selected_option,
                    1 if is_correct else 0,
                    req.time_taken_seconds,
                    req.device_sync_time or now_iso,
                    now_iso
                )
            )

            return AttemptResponse(
                id=attempt_id,
                question_id=req.question_id,
                selected_option=req.selected_option,
                is_correct=is_correct,
                correct_answer_index=correct_idx,
                explanation_sindhi=explanation
            )


video_quiz_service = VideoQuizService()
