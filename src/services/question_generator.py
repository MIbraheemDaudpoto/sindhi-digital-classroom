"""AI-Assisted Educational Quiz Question Generator for SDC.
Synthesizes draft multiple-choice questions from approved STBB lesson transcripts
and enforces a strict Admin approval gate before questions can reach students.
Authored under agency-ai-engineer.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Dict, List, Optional
import uuid

from src.database.session import get_db
from src.services.ai_provider import get_ai_provider
from src.services.sindhi_nlp import normalize_sindhi_text

logger = logging.getLogger("sdc.quiz_gen")


class QuestionGeneratorService:
    """Service for generating and managing draft educational quiz questions."""

    def generate_draft_questions_for_lesson(
        self,
        lesson_id: str,
        admin_user_id: str,
        question_count: int = 3
    ) -> List[dict]:
        """Synthesize draft quiz questions from lesson transcripts for Admin review."""
        with get_db() as conn:
            lesson = conn.execute("SELECT id, title_sindhi FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
            if not lesson:
                raise ValueError(f"سبق نه مليو (Lesson '{lesson_id}' not found).")

            # Collect transcript text
            transcripts = conn.execute(
                """
                SELECT t.text_sindhi, t.start_time
                FROM transcripts t
                JOIN videos v ON t.video_id = v.id
                WHERE v.lesson_id = ?
                ORDER BY t.start_time ASC
                """,
                (lesson_id,)
            ).fetchall()

            if not transcripts:
                # Fallback to lesson title for synthesis
                context_text = f"سبق {lesson['title_sindhi']}. بنيادي تصور ۽ تعليمي مقصد."
                default_timestamp = 60.0
            else:
                context_text = " ".join([r["text_sindhi"] for r in transcripts])
                default_timestamp = float(transcripts[0]["start_time"])

            ai_provider = get_ai_provider()
            draft_specs = ai_provider.generate_draft_quiz_questions(
                lesson_title=lesson["title_sindhi"],
                context_text=context_text,
                count=question_count
            )

            created_questions = []
            now_iso = datetime.now(timezone.utc).isoformat()

            for i, spec in enumerate(draft_specs):
                q_id = f"q-ai-{uuid.uuid4().hex[:8]}"
                # Stagger timestamps across lesson
                ts = default_timestamp + (i * 45.0)
                options_str = json.dumps(spec["options_json"], ensure_ascii=False)

                conn.execute(
                    """
                    INSERT INTO questions (
                        id, lesson_id, timestamp_seconds, text_sindhi, options_json,
                        correct_answer_index, difficulty, topic, status, approved_by, approved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', NULL, NULL)
                    """,
                    (
                        q_id,
                        lesson_id,
                        ts,
                        spec["text_sindhi"],
                        options_str,
                        spec["correct_answer_index"],
                        spec.get("difficulty", "MEDIUM"),
                        spec.get("topic", lesson["title_sindhi"])
                    )
                )

                created_questions.append({
                    "id": q_id,
                    "lesson_id": lesson_id,
                    "timestamp_seconds": ts,
                    "text_sindhi": spec["text_sindhi"],
                    "options": spec["options_json"],
                    "correct_answer_index": spec["correct_answer_index"],
                    "difficulty": spec.get("difficulty", "MEDIUM"),
                    "status": "PENDING_APPROVAL",
                    "explanation_sindhi": spec.get("explanation_sindhi", "")
                })

            # Record audit event
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, 'AI_QUESTIONS_GENERATED', 'lesson', ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    admin_user_id,
                    lesson_id,
                    json.dumps({"count": len(created_questions), "status": "PENDING_APPROVAL"}),
                    now_iso
                )
            )

            return created_questions


question_generator = QuestionGeneratorService()
