"""Real-Time Curriculum-Grounded AI Quiz Assessment Service for SDC.
Supports single-lesson, multi-lesson, and class/subject wide quiz generation.
Truthfully reports provider status (live neural vs local curriculum question bank).
Enforces practice mode (immediate feedback) vs assessment mode (withheld correctness).
Performs server-side scoring, immutable snapshot persistence, and authentic progress tracking.
Authored under agency-ai-engineer and agency-backend-architect.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import random
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from fastapi import HTTPException, status
from src.config import settings
from src.database.session import get_db
from src.models.schemas import (
    LessonScoreBreakdown,
    QuestionReviewItem,
    QuizAnswerFeedbackResponse,
    QuizAnswerSubmitRequest,
    QuizGenerateRequest,
    QuizQuestionClientItem,
    QuizSessionResponse,
    QuizSubmitResponse,
)
from src.services.ai_provider import get_ai_provider, get_ai_system_status
from src.services.sindhi_nlp import normalize_sindhi_text

logger = logging.getLogger("sdc.assessment_quiz")


class AssessmentQuizService:
    """Orchestrates dynamic, curriculum-grounded assessment quizzes for students."""

    def __init__(self):
        self._math_complete_data: Optional[Dict[str, Any]] = None

    def _get_math_data(self) -> Dict[str, Any]:
        """Lazy load verified STBB Math 6 dataset."""
        if self._math_complete_data is None:
            p = Path("data/stbb_math_6_complete.json")
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        self._math_complete_data = json.load(f)
                except Exception as e:
                    logger.warning("Failed to load stbb_math_6_complete.json: %s", e)
                    self._math_complete_data = {}
            else:
                self._math_complete_data = {}
        return self._math_complete_data

    # -------------------------------------------------------------------------
    # 1. QUIZ GENERATION
    # -------------------------------------------------------------------------

    def generate_quiz(self, user_id: str, req: QuizGenerateRequest) -> QuizSessionResponse:
        """Generate a fresh assessment quiz grounded in verified STBB curriculum."""
        now_iso = datetime.now(timezone.utc).isoformat()
        
        with get_db() as conn:
            # 1. Verify Course exists for class_level and subject (with subject normalization)
            s_clean = (req.subject or "").strip().lower()
            if s_clean in ("math", "mathematics", "رياضي"):
                subj_sql = "(LOWER(subject) = 'math' OR LOWER(subject) = 'mathematics')"
                subj_params = []
            elif s_clean in ("science", "general science", "عام سائنس", "سائنس"):
                subj_sql = "(LOWER(subject) = 'science' OR LOWER(subject) LIKE '%sci%')"
                subj_params = []
            else:
                raise HTTPException(status_code=400, detail="هن وقت رڳو ڪلاس 6 جا رياضي ۽ سائنس جا ڪوئيز موجود آهن (Only Class 6 Math and Science are available).")
            if req.class_level != 6:
                raise HTTPException(status_code=400, detail="هن وقت رڳو ڪلاس 6 موجود آهي (Only Class 6 is available).")

            course = conn.execute(
                f"""
                SELECT id, class_level, subject, title_sindhi, title_english
                FROM courses
                WHERE class_level = ? AND {subj_sql}
                LIMIT 1
                """,
                [req.class_level] + subj_params
            ).fetchone()

            if not course:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"ڪلاس {req.class_level} لاءِ مضمون '{req.subject}' دستياب ناهي (Course not found)."
                )

            course_id = course["id"]

            # 2. Retrieve & Validate Lessons
            all_course_lessons = conn.execute(
                """
                SELECT id, course_id, unit_number, title_sindhi, title_english, summary_sindhi
                FROM lessons
                WHERE course_id = ? AND status IN ('PUBLISHED', 'APPROVED')
                ORDER BY unit_number ASC
                """,
                (course_id,)
            ).fetchall()

            if not all_course_lessons:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"مضمون '{req.subject}' جا ڪي به فعال سبق نه مليا (No published lessons found)."
                )

            course_lesson_map = {l["id"]: dict(l) for l in all_course_lessons}

            # If student specified lesson_ids, validate all belong to this course
            target_lesson_ids: List[str] = []
            if req.lesson_ids and len(req.lesson_ids) > 0:
                for lid in req.lesson_ids:
                    if lid not in course_lesson_map:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"سبق '{lid}' هن ڪلاس {req.class_level} ۽ مضمون {req.subject} سان واسطو نٿو رکي (Lesson mismatch)."
                        )
                    target_lesson_ids.append(lid)
            else:
                target_lesson_ids = [l["id"] for l in all_course_lessons]

            lessons_meta = [course_lesson_map[lid] for lid in target_lesson_ids]

            # 3. Check Student's Prior Learning Performance on Target Lessons
            weak_lesson_ids: Set[str] = set()
            try:
                if target_lesson_ids:
                    plh = ",".join(["?"] * len(target_lesson_ids))
                    prog_rows = conn.execute(
                        f"SELECT lesson_id, post_test_score, is_completed FROM progress WHERE user_id = ? AND lesson_id IN ({plh})",
                        [user_id] + target_lesson_ids
                    ).fetchall()
                    for pr in prog_rows:
                        if pr["post_test_score"] is not None and pr["post_test_score"] < 70.0:
                            weak_lesson_ids.add(pr["lesson_id"])
                        elif not pr["is_completed"]:
                            weak_lesson_ids.add(pr["lesson_id"])
            except Exception as e:
                logger.debug("Could not inspect student learning history: %s", e)

            # 4. Check Live AI Provider Status
            ai_status = get_ai_system_status()
            ai_provider = get_ai_provider()
            provider_available = bool(ai_status.get("can_attempt_inference", False))
            provider_type = getattr(ai_provider, "provider_type", ai_status.get("active_provider_type", "LOCAL_DETERMINISTIC_FALLBACK"))
            model_name = getattr(ai_provider, "model_name", ai_status.get("active_model_name"))
            inference_request_id = None
            inference_status = "NOT_RUN"
            is_live_ai = False

            # 5. Generate Question Set
            raw_questions: List[Dict[str, Any]] = []

            # Attempt live model inference if genuinely active
            if provider_available:
                try:
                    raw_questions = self._generate_with_live_ai(
                        conn=conn,
                        user_id=user_id,
                        course=course,
                        lessons=lessons_meta,
                        count=req.question_count,
                        difficulty=req.difficulty
                    )
                    is_live_ai = bool(getattr(ai_provider, "last_quiz_inference", False))
                    inference_request_id = getattr(ai_provider, "last_quiz_request_id", None)
                    if is_live_ai and raw_questions:
                        inference_status = "LIVE_INFERENCE_SUCCEEDED"
                    else:
                        raw_questions = []
                        inference_status = "LIVE_INFERENCE_FAILED_OR_EMPTY"
                except Exception as e:
                    logger.warning("Live AI quiz generation failed: %s", type(e).__name__)
                    raw_questions = []
                    inference_status = "LIVE_INFERENCE_FAILED"

            # If live AI is offline or produced insufficient valid questions, use curriculum bank
            if not raw_questions:
                if not req.allow_fallback:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="AI ماڊل هن وقت دستياب ناهي يا سوال تيار نه ڪري سگهيو (Live AI unavailable).",
                    )
                provider_type = "LOCAL_CURRICULUM_BANK"
                model_name = None
                is_live_ai = False
                if weak_lesson_ids:
                    ai_status_message = "غير AI سوال بئنڪ: سوال محفوظ نصابي سوالن مان چونڊيا ويا آهن؛ لائيو ماڊل سوال تيار نه ڪيا آهن."
                else:
                    ai_status_message = "غير AI سوال بئنڪ: سوال محفوظ نصابي سوالن مان چونڊيا ويا آهن؛ اهي لائيو AI ذريعي ٺاهيل ناهن."
                raw_questions = self._generate_from_curriculum_bank(
                    conn=conn,
                    user_id=user_id,
                    course=course,
                    lessons=lessons_meta,
                    count=req.question_count,
                    difficulty=req.difficulty,
                    weak_lesson_ids=weak_lesson_ids
                )
            else:
                ai_status_message = "سوال لائيو AI ماڊل ذريعي درسي نصاب مان تيار ڪيا ويا آهن."

            if not raw_questions:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="هن چونڊ لاءِ سوال تيار نه ٿي سگهيا. مهرباني ڪري ٻيو سبق يا مضمون چونڊيو."
                )

            # 5. Strict Global Deduplication & Final Backfill Guard
            # Guarantees that in 10-MCQ quizzes, zero duplicate questions ever appear
            final_unique_questions: List[Dict[str, Any]] = []
            seen_final_texts: Set[str] = set()
            for q in raw_questions:
                norm_q = re.sub(r"\s+", " ", q.get("text_sindhi", "")).strip()
                if norm_q and norm_q not in seen_final_texts:
                    seen_final_texts.add(norm_q)
                    final_unique_questions.append(q)

            if len(final_unique_questions) < req.question_count:
                if not req.allow_fallback:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="AI ماڊل ڪافي نوان ۽ تصديق ٿيل سوال تيار نه ڪري سگهيو (Not enough fresh valid AI questions were generated)."
                    )
                more_needed = req.question_count - len(final_unique_questions)
                extra_fill = self._generate_from_curriculum_bank(
                    conn=conn,
                    user_id=user_id,
                    course=course,
                    lessons=lessons_meta,
                    count=more_needed * 2,
                    difficulty=req.difficulty,
                    weak_lesson_ids=weak_lesson_ids
                )
                for eq in extra_fill:
                    norm_eq = re.sub(r"\s+", " ", eq.get("text_sindhi", "")).strip()
                    if norm_eq and norm_eq not in seen_final_texts:
                        seen_final_texts.add(norm_eq)
                        final_unique_questions.append(eq)
                    if len(final_unique_questions) >= req.question_count:
                        break

            raw_questions = final_unique_questions[:req.question_count]

            # 6. Build Immutable Snapshot & Client View
            session_id = f"qz-sess-{uuid.uuid4().hex[:12]}"
            snapshot_questions: List[Dict[str, Any]] = []
            client_questions: List[QuizQuestionClientItem] = []

            for idx, q in enumerate(raw_questions):
                q_id = f"q-{session_id}-{idx + 1}"
                
                # Shuffle options and track correct answer to guarantee variation on retries
                original_options = list(q["options"])
                correct_val = original_options[q["correct_answer_index"]]
                
                # Shuffle options randomly
                shuffled_opts = list(original_options)
                random.shuffle(shuffled_opts)
                new_corr_idx = shuffled_opts.index(correct_val)

                lesson_info = course_lesson_map.get(q["lesson_id"], {})

                # Snapshot item contains correct answer & citations
                snapshot_item = {
                    "id": q_id,
                    "index": idx,
                    "text_sindhi": q["text_sindhi"],
                    "options": shuffled_opts,
                    "correct_answer_index": new_corr_idx,
                    "explanation_sindhi": q.get("explanation_sindhi", "درست جواب نصاب مطابق ڏنو ويو آهي."),
                    "citation": q.get("citation", f"STBB {req.subject} Class {req.class_level}"),
                    "difficulty": q.get("difficulty", "MEDIUM"),
                    "lesson_id": q["lesson_id"],
                    "lesson_title_sd": lesson_info.get("title_sindhi", ""),
                    "lesson_title_en": lesson_info.get("title_english", ""),
                    "topic": q.get("topic", lesson_info.get("title_sindhi", ""))
                }
                snapshot_questions.append(snapshot_item)

                # Client item WITHHOLDS correct_answer_index to prevent cheating
                client_item = QuizQuestionClientItem(
                    id=q_id,
                    index=idx,
                    text_sindhi=q["text_sindhi"],
                    options=shuffled_opts,
                    difficulty=q.get("difficulty", "MEDIUM"),
                    lesson_id=q["lesson_id"],
                    lesson_title_sd=lesson_info.get("title_sindhi", ""),
                    lesson_title_en=lesson_info.get("title_english", ""),
                    topic=q.get("topic", lesson_info.get("title_sindhi", ""))
                )
                client_questions.append(client_item)

            # 6. Save Session in Database
            conn.execute(
                """
                INSERT INTO quiz_sessions (
                    id, user_id, class_level, subject, lesson_ids_json, mode,
                    difficulty, total_questions, questions_snapshot_json,
                    provider_used, model_used, inference_request_id, inference_status,
                    is_live_ai, status, answers_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'IN_PROGRESS', '{}', ?)
                """,
                (
                    session_id,
                    user_id,
                    req.class_level,
                    req.subject,
                    json.dumps(target_lesson_ids),
                    req.mode,
                    req.difficulty,
                    len(snapshot_questions),
                    json.dumps(snapshot_questions, ensure_ascii=False),
                    provider_type,
                    model_name,
                    inference_request_id,
                    inference_status,
                    1 if is_live_ai else 0,
                    now_iso
                )
            )

            return QuizSessionResponse(
                session_id=session_id,
                class_level=req.class_level,
                subject=req.subject,
                lesson_ids=target_lesson_ids,
                lessons_meta=[
                    {
                        "id": l["id"],
                        "unit_number": l["unit_number"],
                        "title_sindhi": l["title_sindhi"],
                        "title_english": l["title_english"]
                    }
                    for l in lessons_meta
                ],
                total_questions=len(snapshot_questions),
                mode=req.mode,
                difficulty=req.difficulty,
                provider_type=provider_type,
                model_name=model_name,
                inference_request_id=inference_request_id,
                inference_status=inference_status,
                is_live_ai=is_live_ai,
                ai_status_message=ai_status_message,
                status="IN_PROGRESS",
                questions=client_questions
            )

    # -------------------------------------------------------------------------
    # 2. SUBMIT SINGLE ANSWER (Practice immediate feedback vs Assessment withholding)
    # -------------------------------------------------------------------------

    def submit_single_answer(
        self,
        user_id: str,
        session_id: str,
        req: QuizAnswerSubmitRequest
    ) -> QuizAnswerFeedbackResponse:
        """Process answer for one question, providing immediate feedback in practice mode."""
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            row = conn.execute("SELECT * FROM quiz_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ڪوئز سيشن نه مليو (Quiz session not found).")

            # Ownership check
            if row["user_id"] != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="توهان کي هن سيشن تائين رسائي ناهي (Access denied).")

            if row["status"] != "IN_PROGRESS":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="هي ڪوئز اڳ ۾ ئي جمع ٿي چڪو آهي (Quiz already submitted).")

            snapshots: List[Dict[str, Any]] = json.loads(row["questions_snapshot_json"])
            target_q = next((q for q in snapshots if q["id"] == req.question_id), None)
            if not target_q:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سوال نه مليو (Question ID not in session).")

            correct_idx = target_q["correct_answer_index"]
            is_correct = (req.selected_option == correct_idx) if req.selected_option >= 0 else False

            # Update recorded answers dictionary
            answers_dict: Dict[str, Any] = json.loads(row["answers_json"] or "{}")
            answers_dict[req.question_id] = {
                "selected_option": req.selected_option,
                "is_correct": is_correct,
                "time_taken_seconds": req.time_taken_seconds,
                "answered_at": now_iso
            }

            conn.execute(
                "UPDATE quiz_sessions SET answers_json = ? WHERE id = ?",
                (json.dumps(answers_dict, ensure_ascii=False), session_id)
            )

            # In practice mode: immediate feedback with explanation & citation
            if (row["mode"] or "").strip().lower() == "practice":
                msg = "شاباس! جواب بلڪل درست آهي." if is_correct else "غلط جواب. صحيح جواب تي غور ڪريو."
                return QuizAnswerFeedbackResponse(
                    session_id=session_id,
                    question_id=req.question_id,
                    selected_option=req.selected_option,
                    is_correct=is_correct,
                    correct_answer_index=correct_idx,
                    explanation_sindhi=target_q.get("explanation_sindhi"),
                    citation=target_q.get("citation"),
                    lesson_id=target_q.get("lesson_id"),
                    lesson_title_sd=target_q.get("lesson_title_sd"),
                    topic=target_q.get("topic"),
                    message=msg
                )
            else:
                # In assessment mode: withhold correctness until final submission
                return QuizAnswerFeedbackResponse(
                    session_id=session_id,
                    question_id=req.question_id,
                    selected_option=req.selected_option,
                    is_correct=None,
                    correct_answer_index=None,
                    explanation_sindhi=None,
                    citation=None,
                    lesson_id=target_q.get("lesson_id"),
                    lesson_title_sd=target_q.get("lesson_title_sd"),
                    topic=target_q.get("topic"),
                    message="جواب ڪاميابي سان محفوظ ٿي ويو (Answer saved)."
                )

    # -------------------------------------------------------------------------
    # 3. SUBMIT FINAL QUIZ & SERVER-SIDE SCORING
    # -------------------------------------------------------------------------

    def submit_final_quiz(self, user_id: str, session_id: str) -> QuizSubmitResponse:
        """Calculate final score server-side, mark complete, and update student progress."""
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            row = conn.execute("SELECT * FROM quiz_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ڪوئز سيشن نه مليو.")

            if row["user_id"] != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

            snapshots: List[Dict[str, Any]] = json.loads(row["questions_snapshot_json"])
            answers_dict: Dict[str, Any] = json.loads(row["answers_json"] or "{}")

            correct_count = 0
            incorrect_count = 0
            review_items: List[QuestionReviewItem] = []
            lesson_stats: Dict[str, Dict[str, Any]] = {}
            topics_to_review: List[str] = []

            for q in snapshots:
                qid = q["id"]
                lid = q["lesson_id"]
                corr_idx = q["correct_answer_index"]

                if lid not in lesson_stats:
                    lesson_stats[lid] = {
                        "lesson_id": lid,
                        "lesson_title_sd": q.get("lesson_title_sd", ""),
                        "total": 0,
                        "correct": 0
                    }
                lesson_stats[lid]["total"] += 1

                ans = answers_dict.get(qid)
                sel_opt = ans["selected_option"] if ans else -1
                is_corr = (sel_opt == corr_idx)

                if is_corr:
                    correct_count += 1
                    lesson_stats[lid]["correct"] += 1
                else:
                    incorrect_count += 1
                    t = q.get("topic")
                    if t and t not in topics_to_review:
                        topics_to_review.append(t)

                review_items.append(
                    QuestionReviewItem(
                        question_id=qid,
                        index=q["index"],
                        text_sindhi=q["text_sindhi"],
                        options=q["options"],
                        selected_option=sel_opt,
                        correct_answer_index=corr_idx,
                        is_correct=is_corr,
                        explanation_sindhi=q.get("explanation_sindhi", ""),
                        citation=q.get("citation", ""),
                        lesson_id=lid,
                        lesson_title_sd=q.get("lesson_title_sd", ""),
                        topic=q.get("topic", "")
                    )
                )

            total_q = len(snapshots)
            score_pct = round((correct_count / total_q) * 100.0, 1) if total_q > 0 else 0.0
            passed = (score_pct >= 50.0)

            # Build per-lesson breakdown
            breakdown: Dict[str, LessonScoreBreakdown] = {}
            for lid, st in lesson_stats.items():
                pct = round((st["correct"] / st["total"]) * 100.0, 1) if st["total"] > 0 else 0.0
                breakdown[lid] = LessonScoreBreakdown(
                    lesson_id=lid,
                    lesson_title_sd=st["lesson_title_sd"],
                    total_questions=st["total"],
                    correct_questions=st["correct"],
                    percentage=pct
                )

            # Idempotent status update: do not overwrite an already completed quiz
            if row["status"] != "COMPLETED":
                conn.execute(
                    """
                    UPDATE quiz_sessions
                    SET status = 'COMPLETED', score = ?, max_score = 100.0, percentage = ?, submitted_at = ?
                    WHERE id = ?
                    """,
                    (score_pct, score_pct, now_iso, session_id)
                )

                # Update real student progress if passed
                if passed:
                    for lid, b in breakdown.items():
                        is_comp = 1 if b.percentage >= 50.0 else 0
                        # Update post_test_score and is_completed in progress table
                        conn.execute(
                            """
                            INSERT INTO progress (id, user_id, lesson_id, last_position_seconds, is_completed, pre_test_score, post_test_score, updated_at)
                            VALUES (?, ?, ?, 0.0, ?, 0.0, ?, ?)
                            ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                                post_test_score = MAX(COALESCE(post_test_score, 0), excluded.post_test_score),
                                is_completed = CASE WHEN excluded.is_completed = 1 OR excluded.post_test_score >= 50.0 THEN 1 ELSE progress.is_completed END,
                                updated_at = excluded.updated_at
                            """,
                            (str(uuid.uuid4()), user_id, lid, is_comp, b.percentage, now_iso)
                        )

            return QuizSubmitResponse(
                session_id=session_id,
                user_id=user_id,
                class_level=row["class_level"],
                subject=row["subject"],
                total_questions=total_q,
                correct_count=correct_count,
                incorrect_count=incorrect_count,
                score=score_pct,
                percentage=score_pct,
                passed=passed,
                per_lesson_breakdown=breakdown,
                topics_to_review=topics_to_review,
                review=review_items,
                provider_used=row["provider_used"],
                is_live_ai=bool(row["is_live_ai"]),
                submitted_at=row["submitted_at"] or now_iso
            )

    # -------------------------------------------------------------------------
    # 4. GET SESSION & STUDENT HISTORY
    # -------------------------------------------------------------------------

    def get_quiz_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Fetch session data, withholding answers if in-progress."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM quiz_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سيشن نه مليو.")

            if row["user_id"] != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

            res = dict(row)
            res["session_id"] = res["id"]
            snapshots = json.loads(res["questions_snapshot_json"])
            try:
                answers = json.loads(res.get("answers_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                answers = {}

            if res["status"] != "COMPLETED":
                # Withhold correct answer keys
                safe_q = []
                for q in snapshots:
                    safe_q.append({
                        "id": q["id"],
                        "index": q["index"],
                        "text_sindhi": q["text_sindhi"],
                        "options": q["options"],
                        "difficulty": q["difficulty"],
                        "lesson_id": q["lesson_id"],
                        "lesson_title_sd": q["lesson_title_sd"],
                        "topic": q["topic"]
                    })
                res["questions"] = safe_q
                # Never leak correctness flags through stored answers in assessment mode.
                if (res.get("mode") or "").lower() == "assessment":
                    answers = {
                        qid: {key: value for key, value in answer.items() if key != "is_correct"}
                        for qid, answer in answers.items() if isinstance(answer, dict)
                    }
            else:
                res["questions"] = snapshots

            del res["questions_snapshot_json"]
            del res["answers_json"]
            res["answers"] = answers
            return res

    def list_student_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List past quiz attempts and scores for student dashboard."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT id, class_level, subject, lesson_ids_json, mode,
                       difficulty, total_questions, provider_used, is_live_ai,
                       status, score, percentage, created_at, submitted_at
                FROM quiz_sessions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            ).fetchall()

            history = []
            for r in rows:
                item = dict(r)
                item["session_id"] = item["id"]
                item["lesson_ids"] = json.loads(item["lesson_ids_json"])
                del item["lesson_ids_json"]
                history.append(item)
            return history

    # -------------------------------------------------------------------------
    # 5. GENERATION ENGINES (Curriculum Question Bank & Live AI)
    # -------------------------------------------------------------------------

    def _generate_from_curriculum_bank(
        self,
        conn,
        course,
        lessons: List[Dict[str, Any]],
        count: int,
        difficulty: str,
        weak_lesson_ids: Optional[Set[str]] = None,
        user_id: Optional[str] = "usr-stu-101"
    ) -> List[Dict[str, Any]]:
        """Synthesize fresh, balanced, diverse MCQs from verified STBB curriculum."""
        subject_name = course["subject"]
        is_math = (subject_name.lower() == "math")
        selected_questions: List[Dict[str, Any]] = []
        seen_texts: Set[str] = set()

        # Prioritize lessons where student had weak performance (<70% or incomplete)
        target_lessons = list(lessons)
        if weak_lesson_ids:
            target_lessons.sort(key=lambda l: 0 if l["id"] in weak_lesson_ids else 1)

        # Target questions per lesson for fair distribution across multi-lesson selections
        num_lessons = len(target_lessons)
        per_lesson_target = max(1, count // num_lessons)
        subj_filter = "math-6" if is_math else "science-6"

        # Pre-fetch subject terms and chunks to create rich, authentic distractors
        all_subj_gloss: List[Dict[str, Any]] = []
        all_subj_chunks: List[Dict[str, Any]] = []

        if not is_math:
            try:
                gloss_cols = [c[1] for c in conn.execute("PRAGMA table_info(sdc_glossary)").fetchall()]
                if "subject_id" in gloss_cols:
                    all_subj_gloss = [dict(g) for g in conn.execute(
                        "SELECT * FROM sdc_glossary WHERE subject_id = ?",
                        (subj_filter,)
                    ).fetchall()]
                else:
                    all_subj_gloss = [dict(g) for g in conn.execute(
                        "SELECT * FROM sdc_glossary"
                    ).fetchall()]
            except Exception:
                all_subj_gloss = []

            try:
                chunk_cols = [c[1] for c in conn.execute("PRAGMA table_info(sdc_chunks)").fetchall()]
                if "subject_id" in chunk_cols:
                    all_subj_chunks = [dict(c) for c in conn.execute(
                        "SELECT * FROM sdc_chunks WHERE subject_id = ?",
                        (subj_filter,)
                    ).fetchall()]
                else:
                    all_subj_chunks = [dict(c) for c in conn.execute(
                        "SELECT * FROM sdc_chunks"
                    ).fetchall()]
            except Exception:
                all_subj_chunks = []

        all_unselected_pool: List[Dict[str, Any]] = []

        for lesson in lessons:
            lid = lesson["id"]
            unit_num = lesson["unit_number"]
            lesson_pool: List[Dict[str, Any]] = []

            def _add_to_pool(candidate: Dict[str, Any]):
                q_text = candidate.get("text_sindhi", "")
                q_text_clean = re.sub(r"\[[^\]]*?\]:?\s*", "", q_text)
                norm_key = re.sub(r"\s+", " ", q_text_clean).strip()
                if not norm_key or norm_key in seen_texts:
                    return
                candidate["text_sindhi"] = norm_key
                seen_texts.add(norm_key)
                lesson_pool.append(candidate)

            # A. Math specific verified exercises from stbb_math_6_complete.json
            if is_math:
                math_data = self._get_math_data()
                exercises = math_data.get("exercises", [])
                for ex in exercises:
                    if ex.get("chapter_id") == unit_num:
                        corr_val = ex["correct_answer"]
                        if corr_val in ex["options"]:
                            corr_idx = ex["options"].index(corr_val)
                            _add_to_pool({
                                "text_sindhi": ex["question_sd"],
                                "options": list(ex["options"]),
                                "correct_answer_index": corr_idx,
                                "explanation_sindhi": ex.get("solution_steps_sd", "نصاب مطابق حل."),
                                "citation": f"Riazi Sindhi VI (2024-25), Unit {unit_num}",
                                "difficulty": "MEDIUM",
                                "topic": lesson["title_sindhi"],
                                "lesson_id": lid
                            })

            # B. Check approved questions table (deduplicating against verified bank)
            app_rows = conn.execute(
                """
                SELECT * FROM questions
                WHERE lesson_id = ? AND status = 'APPROVED'
                  AND text_sindhi NOT LIKE '%اسلام جو ڪهڙو ڪردار%'
                  AND options_json NOT LIKE '%غير ضروري معلومات%'
                  AND options_json NOT LIKE '%ٻيو آپشن%'
                """,
                (lid,)
            ).fetchall()
            for ar in app_rows:
                opts = json.loads(ar["options_json"])
                _add_to_pool({
                    "text_sindhi": ar["text_sindhi"],
                    "options": opts,
                    "correct_answer_index": ar["correct_answer_index"],
                    "explanation_sindhi": f"درسي ڪتاب جي موضوع '{ar['topic']}' مان ورتل.",
                    "citation": f"STBB {subject_name} VI, Unit {unit_num}",
                    "difficulty": ar["difficulty"],
                    "topic": ar["topic"],
                    "lesson_id": lid
                })

            # C. Check sdc_glossary terms for this unit to build conceptual items with authentic distractors
            gloss_rows = [g for g in all_subj_gloss if g.get("chapter_id") == unit_num]
            other_gloss = [g for g in all_subj_gloss if g.get("chapter_id") != unit_num]

            for gr in gloss_rows:
                t_sd = gr["term_sd"]
                t_en = gr.get("term_en", "")
                defn = gr.get("definition_sd", "")
                if defn and len(defn) > 10:
                    candidate_distractors = [g["term_sd"] for g in other_gloss + [x for x in gloss_rows if x["id"] != gr["id"]]]
                    if len(candidate_distractors) >= 3:
                        distractors = random.sample(candidate_distractors, 3)
                        q_opts = [t_sd] + distractors
                        _add_to_pool({
                            "text_sindhi": f"'{defn}' هي وصف هيٺين مان ڪنهن جي آهي؟",
                            "options": q_opts,
                            "correct_answer_index": 0,
                            "explanation_sindhi": f"{t_sd} ({t_en}): {defn}",
                            "citation": gr.get("citation_formatted") or f"STBB {subject_name} VI, Unit {unit_num}",
                            "difficulty": "EASY",
                            "topic": t_sd,
                            "lesson_id": lid
                        })

            # D. Check sdc_chunks for reading comprehension questions with real curriculum statements as distractors
            chunk_rows = [c for c in all_subj_chunks if c.get("chapter_id") == unit_num]
            other_chunks = [c for c in all_subj_chunks if c.get("chapter_id") != unit_num]

            for cr in chunk_rows:
                topic_sd = cr["topic_title_sd"]
                summary = cr["summary_sd"]
                citation = cr.get("citation_formatted") or f"STBB {subject_name} VI, Unit {unit_num}"
                
                # Extract first sentence
                sentences = [s.strip() for s in re.split(r"[۔\.\n]+", summary) if len(s.strip()) > 15]
                if sentences:
                    first_sent = sentences[0]
                    # Sample 3 genuine distractors from other curriculum chunks
                    distractor_sents = []
                    if len(other_chunks) >= 3:
                        sampled_other = random.sample(other_chunks, 3)
                        for sc in sampled_other:
                            sc_sents = [s.strip() for s in re.split(r"[۔\.\n]+", sc.get("summary_sd", "")) if len(s.strip()) > 15]
                            if sc_sents:
                                distractor_sents.append(sc_sents[0])
                    
                    if len(distractor_sents) >= 3:
                        _add_to_pool({
                            "text_sindhi": f"موضوع '{topic_sd}' بابت درسي ڪتاب مطابق ڪهڙو بيان درست آهي؟",
                            "options": [first_sent] + distractor_sents[:3],
                            "correct_answer_index": 0,
                            "explanation_sindhi": f"نصابي خلاصو: {first_sent}",
                            "citation": citation,
                            "difficulty": "HARD",
                            "topic": topic_sd,
                            "lesson_id": lid
                        })

            # Filter by difficulty if requested and available
            if difficulty in ("EASY", "MEDIUM", "HARD"):
                diff_matches = [q for q in lesson_pool if q.get("difficulty") == difficulty]
                if len(diff_matches) >= per_lesson_target:
                    # Keep non-matching in unselected pool
                    for q in lesson_pool:
                        if q not in diff_matches:
                            all_unselected_pool.append(q)
                    lesson_pool = diff_matches

            # Shuffle and sample questions for this lesson
            random.shuffle(lesson_pool)
            sampled = lesson_pool[:per_lesson_target]
            selected_questions.extend(sampled)
            # Add any remaining to fallback pool
            all_unselected_pool.extend(lesson_pool[per_lesson_target:])

        # If we need more questions to reach count, pull from remaining unselected pool without duplicating
        if len(selected_questions) < count and all_unselected_pool:
            random.shuffle(all_unselected_pool)
            for extra_q in all_unselected_pool:
                if len(selected_questions) >= count:
                    break
                norm_k = re.sub(r"\s+", " ", extra_q.get("text_sindhi", "")).strip()
                if not norm_k or norm_k in seen_texts:
                    continue
                seen_texts.add(norm_k)
                selected_questions.append(extra_q)

        # If still short, pull from other units of the same course
        if len(selected_questions) < count:
            remaining_needed = count - len(selected_questions)
            fallback_rows = conn.execute(
                """
                SELECT * FROM questions
                WHERE lesson_id LIKE ? AND status = 'APPROVED'
                  AND text_sindhi NOT LIKE '%اسلام جو ڪهڙو ڪردار%'
                  AND options_json NOT LIKE '%غير ضروري معلومات%'
                ORDER BY RANDOM() LIMIT ?
                """,
                (f"%{subj_filter}%", remaining_needed * 3)
            ).fetchall()
            for fr in fallback_rows:
                if len(selected_questions) >= count:
                    break
                norm_k = re.sub(r"\s+", " ", fr["text_sindhi"]).strip()
                if norm_k in seen_texts:
                    continue
                seen_texts.add(norm_k)
                opts = json.loads(fr["options_json"])
                selected_questions.append({
                    "text_sindhi": fr["text_sindhi"],
                    "options": opts,
                    "correct_answer_index": fr["correct_answer_index"],
                    "explanation_sindhi": f"درسي ڪتاب جي موضوع '{fr['topic']}' مان ورتل.",
                    "citation": f"STBB {subject_name} VI",
                    "difficulty": fr["difficulty"],
                    "topic": fr["topic"],
                    "lesson_id": fr["lesson_id"]
                })

        # If still short, dynamically synthesize distinct conceptual questions from all subject glossary terms
        if len(selected_questions) < count and all_subj_gloss:
            for gr in all_subj_gloss:
                if len(selected_questions) >= count:
                    break
                t_sd = gr["term_sd"]
                defn = gr.get("definition_sd", "")
                q_text = f"سنڌ ٽيڪسٽ بڪ مطابق اصطلاح '{t_sd}' مان ڇا مراد آهي؟"
                norm_k = re.sub(r"\s+", " ", q_text).strip()
                if not defn or len(defn) < 10 or norm_k in seen_texts:
                    continue
                other_defs = [
                    g["definition_sd"] for g in all_subj_gloss 
                    if g["id"] != gr["id"] and g.get("definition_sd") and len(g.get("definition_sd", "")) > 10
                ]
                if len(other_defs) < 3:
                    continue
                distractors = random.sample(other_defs, 3)
                seen_texts.add(norm_k)
                selected_questions.append({
                    "text_sindhi": q_text,
                    "options": [defn] + distractors,
                    "correct_answer_index": 0,
                    "explanation_sindhi": f"{t_sd}: {defn}",
                    "citation": gr.get("citation_formatted") or f"STBB {subject_name} VI",
                    "difficulty": "MEDIUM",
                    "topic": t_sd,
                    "lesson_id": lessons[0]["id"]
                })

        # Truncate to exact requested count and shuffle question order
        random.shuffle(selected_questions)
        return selected_questions[:count]

    def _generate_with_live_ai(
        self,
        conn,
        user_id: str,
        course,
        lessons: List[Dict[str, Any]],
        count: int,
        difficulty: str
    ) -> List[Dict[str, Any]]:
        """Synthesize structured questions using live model inference."""
        # Live generation prompts the active AI provider with textbook chunks
        ai_provider = get_ai_provider()
        chunks_by_lesson: Dict[str, List[Dict[str, Any]]] = {}
        is_math = (course["subject"].lower() == "math")

        for lesson in lessons:
            unit_num = lesson["unit_number"]
            if is_math:
                # The Math RAG dataset is the STBB JSON package, not the Science-only
                # sdc_chunks table. Keep the source and citation from that package.
                math_chunks = self._get_math_data().get("chunks", [])
                c_rows = [
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "chapter_id": chunk.get("chapter_id"),
                        "topic_title_sd": chunk.get("topic_title_sd", ""),
                        "summary_sd": chunk.get("summary_sd", ""),
                        "citation_formatted": (
                            f"Riazi Sindhi VI, {chunk.get('citation_formatted')}"
                            if chunk.get("citation_formatted") else ""
                        ),
                    }
                    for chunk in math_chunks
                    if int(chunk.get("chapter_id", -1)) == int(unit_num)
                ]
            else:
                # sdc_chunks is the Science curriculum table; it has chapter_id but
                # deliberately has no subject_id column. Its canonical chunk IDs
                # identify the science chapters (ch1-01 ... ch12-06).
                c_rows = conn.execute(
                    "SELECT * FROM sdc_chunks WHERE chapter_id = ? AND chunk_id LIKE ? LIMIT 6",
                    (unit_num, f"ch{unit_num}-%")
                ).fetchall()
                c_rows = [dict(r) for r in c_rows]
            chunks_by_lesson[lesson["id"]] = c_rows

        if not chunks_by_lesson or any(not chunks_by_lesson.get(lesson["id"]) for lesson in lessons):
            return []

        citation_map: Dict[str, set[str]] = {}
        context_parts = []
        for lesson in lessons:
            citation_map[lesson["id"]] = set()
            for chunk in chunks_by_lesson[lesson["id"]]:
                citation = (chunk.get("citation_formatted") or "").strip()
                if not citation:
                    continue
                citation_map[lesson["id"]].add(citation)
                context_parts.append(
                    f"[LESSON_ID={lesson['id']} | UNIT={lesson['unit_number']} | LESSON_TITLE={lesson['title_sindhi']} | CITATION={citation} | TOPIC={chunk.get('topic_title_sd','')}]: {chunk.get('summary_sd','')}"
                )
        if any(not citation_map[lesson["id"]] for lesson in lessons):
            return []
        selected_ids = {lesson["id"] for lesson in lessons}
        prior_questions: set[str] = set()
        prior_sessions = conn.execute(
            "SELECT lesson_ids_json, questions_snapshot_json FROM quiz_sessions WHERE user_id=? AND class_level=6 AND subject=? ORDER BY created_at DESC LIMIT 100",
            (user_id, course["subject"])
        ).fetchall()
        for prior in prior_sessions:
            try:
                prior_scope = set(json.loads(prior["lesson_ids_json"] or "[]"))
                if not prior_scope.intersection(selected_ids):
                    continue
                for old_question in json.loads(prior["questions_snapshot_json"] or "[]"):
                    if isinstance(old_question, dict):
                        old_text = re.sub(r"\s+", " ", old_question.get("text_sindhi", "")).strip()
                        if old_text:
                            prior_questions.add(old_text.casefold())
            except (TypeError, json.JSONDecodeError):
                continue
        if prior_questions:
            context_parts.append("[QUESTIONS_TO_AVOID; do not repeat or lightly paraphrase]: " + " | ".join(sorted(prior_questions)))
        context_text = "\n".join(context_parts)
        
        drafts = ai_provider.generate_draft_quiz_questions(
            lesson_title=lessons[0]["title_sindhi"],
            context_text=context_text,
            count=count
        )

        valid_items: List[Dict[str, Any]] = []
        seen_ai_texts: Set[str] = set()

        def _is_valid_quiz_option(opt: Any) -> bool:
            if not opt or not isinstance(opt, str):
                return False
            o = opt.strip()
            if len(o) < 2:
                return False
            bad_phrases = ["ٻيو آپشن", "ٽيون آپشن", "چوٿون آپشن", "پھريون آپشن", "آپشن", "option", "dummy", "placeholder"]
            if any(bp in o.lower() for bp in bad_phrases):
                return False
            if o in ["آهي.", "آهي", "ناهي.", "ناهي"]:
                return False
            return True

        def _clean_question_text(txt: str) -> str:
            cleaned = re.sub(r"\[[^\]]*?\(PDF[^\)]*?\)[^\]]*?\]:?\s*", "", txt)
            cleaned = re.sub(r"\[[^\]]*?\]:?\s*", "", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return cleaned

        for d in drafts:
            opts = d.get("options_json") or d.get("options", [])
            corr = d.get("correct_answer_index")
            txt = d.get("text_sindhi") or d.get("question_text_sindhi") or ""
            lesson_id = d.get("lesson_id")
            citation = (d.get("citation") or "").strip()
            clean_txt = _clean_question_text(txt)
            norm_key = re.sub(r"\s+", " ", clean_txt).strip()
            if norm_key.casefold() in prior_questions:
                continue
            if lesson_id not in citation_map or citation not in citation_map.get(lesson_id, set()):
                continue
            if not norm_key or norm_key in seen_ai_texts or len(clean_txt) < 10:
                continue
            if not isinstance(opts, list) or len(opts) != 4 or not isinstance(corr, int) or not (0 <= corr < 4):
                continue
            opts_clean = [o.strip() for o in opts if isinstance(o, str)]
            if len(opts_clean) != 4 or len(set(opts_clean)) != 4:
                continue
            if not all(_is_valid_quiz_option(o) for o in opts_clean):
                continue

            target_les = next((lesson for lesson in lessons if lesson["id"] == lesson_id), None)
            if not target_les:
                continue
            seen_ai_texts.add(norm_key)
            valid_items.append({
                "text_sindhi": clean_txt,
                "options": opts_clean,
                "correct_answer_index": corr,
                "explanation_sindhi": d.get("explanation_sindhi", "نصاب مطابق."),
                "citation": citation,
                "difficulty": difficulty,
                "topic": d.get("topic") or target_les.get("title_sindhi", lessons[0]["title_sindhi"]),
                "lesson_id": target_les["id"]
            })

        return valid_items[:count]


assessment_quiz_service = AssessmentQuizService()
