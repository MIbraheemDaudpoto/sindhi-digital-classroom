"""Curriculum and Lesson Management Service for SDC.
Handles Class 6-10 Sindh Textbook Board curriculum browsing and lesson progress.
Authored under agency-backend-architect.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.database.session import get_db
from src.models.schemas import CourseResponse, LessonDetailResponse, LessonResponse, LessonUploadRequest, QuestionResponse, QuestionStatus, TranscriptLine, YouTubeVideoResponse


class LessonService:
    """Service for courses, lessons, and progress tracking."""

    def list_courses(self, class_level: Optional[int] = None, subject: Optional[str] = None) -> List[CourseResponse]:
        """List only published Class 6 Math and Science courses with usable lessons."""
        if class_level not in (None, 6):
            return []
        if subject:
            normalized = subject.strip().lower()
            if normalized not in ("math", "mathematics", "رياضي", "science", "general science", "سائنس", "عام سائنس"):
                return []
        with get_db() as conn:
            query = """
                SELECT c.* FROM courses c
                WHERE c.class_level = 6 AND c.subject IN ('Math', 'Science')
                  AND EXISTS (SELECT 1 FROM lessons l WHERE l.course_id=c.id AND l.status IN ('PUBLISHED','APPROVED'))
            """
            params = []
            if subject:
                if normalized in ("math", "mathematics", "رياضي"):
                    query += " AND c.subject = 'Math'"
                else:
                    query += " AND c.subject = 'Science'"
            query += " ORDER BY class_level ASC, subject ASC"

            course_rows = conn.execute(query, params).fetchall()
            if not course_rows:
                return []

            # Single batch query to avoid N+1 query bottleneck
            course_ids = [c["id"] for c in course_rows]
            placeholders = ",".join(["?"] * len(course_ids))
            all_lesson_rows = conn.execute(
                f"SELECT * FROM lessons WHERE course_id IN ({placeholders}) AND status IN ('PUBLISHED', 'APPROVED') ORDER BY unit_number ASC",
                course_ids
            ).fetchall()

            lessons_by_course = {}
            for l in all_lesson_rows:
                cid = l["course_id"]
                if cid not in lessons_by_course:
                    lessons_by_course[cid] = []
                lessons_by_course[cid].append(
                    LessonResponse(
                        id=l["id"],
                        course_id=l["course_id"],
                        unit_number=l["unit_number"],
                        title_sindhi=l["title_sindhi"],
                        title_english=l["title_english"],
                        duration_seconds=l["duration_seconds"],
                        status=l["status"],
                        summary_sindhi=l["summary_sindhi"]
                    )
                )

            results = []
            for c in course_rows:
                results.append(
                    CourseResponse(
                        id=c["id"],
                        class_level=c["class_level"],
                        subject=c["subject"],
                        title_sindhi=c["title_sindhi"],
                        title_english=c["title_english"],
                        lessons=lessons_by_course.get(c["id"], [])
                    )
                )

            return results

    def get_lesson_detail(self, lesson_id: str, user_id: Optional[str] = None) -> Optional[LessonDetailResponse]:
        """Retrieve complete lesson detail with HLS video urls, transcripts, and approved questions."""
        with get_db() as conn:
            l_row = conn.execute(
                """SELECT l.* FROM lessons l JOIN courses c ON c.id=l.course_id
                   WHERE l.id=? AND l.status IN ('PUBLISHED','APPROVED')
                     AND c.class_level=6 AND c.subject IN ('Math','Science')""",
                (lesson_id,)
            ).fetchone()
            if not l_row:
                return None

            v_row = conn.execute("SELECT * FROM videos WHERE lesson_id = ?", (lesson_id,)).fetchone()
            video_hls = v_row["hls_url"] if v_row else f"/static/media/{lesson_id}.m3u8"
            video_fallback = v_row["fallback_url"] if v_row else f"/static/media/{lesson_id}.mp4"
            audio_only = v_row["audio_only_url"] if v_row else f"/static/media/{lesson_id}.mp3"

            # Transcripts
            t_rows = conn.execute(
                "SELECT * FROM transcripts WHERE video_id = ? ORDER BY line_number ASC",
                (v_row["id"] if v_row else "none",)
            ).fetchall()
            transcripts = [
                TranscriptLine(
                    line_number=t["line_number"],
                    start_time=t["start_time"],
                    end_time=t["end_time"],
                    text_sindhi=t["text_sindhi"],
                    confidence=t["confidence"],
                    is_flagged=bool(t["is_flagged"])
                )
                for t in t_rows
            ]

            # Approved Questions ONLY for student playback (FR-13 Gate)
            q_rows = conn.execute(
                "SELECT * FROM questions WHERE lesson_id = ? AND status = 'APPROVED' ORDER BY timestamp_seconds ASC",
                (lesson_id,)
            ).fetchall()
            approved_questions = [
                QuestionResponse(
                    id=q["id"],
                    lesson_id=q["lesson_id"],
                    timestamp_seconds=q["timestamp_seconds"],
                    text_sindhi=q["text_sindhi"],
                    options=json.loads(q["options_json"]),
                    correct_answer_index=q["correct_answer_index"],
                    difficulty=q["difficulty"],
                    topic=q["topic"],
                    status=QuestionStatus(q["status"])
                )
                for q in q_rows
            ]

            # Progress check (FR-08 Resume)
            last_pos = 0.0
            is_comp = False
            if user_id:
                p_row = conn.execute(
                    "SELECT last_position_seconds, is_completed FROM progress WHERE user_id = ? AND lesson_id = ?",
                    (user_id, lesson_id)
                ).fetchone()
                if p_row:
                    last_pos = p_row["last_position_seconds"]
                    is_comp = bool(p_row["is_completed"])

            # YouTube educational video metadata
            yt_row = conn.execute(
                "SELECT * FROM youtube_videos WHERE lesson_id = ?",
                (lesson_id,)
            ).fetchone()
            youtube_video = None
            video_source_type = "LOCAL"
            if yt_row:
                youtube_video = YouTubeVideoResponse(
                    id=yt_row["id"],
                    lesson_id=yt_row["lesson_id"],
                    youtube_id=yt_row["youtube_id"],
                    title=yt_row["title"],
                    channel_name=yt_row["channel_name"],
                    original_url=yt_row["original_url"],
                    embed_url=yt_row["embed_url"],
                    class_level=yt_row["class_level"],
                    subject=yt_row["subject"],
                    language=yt_row["language"],
                    topic=yt_row["topic"],
                    duration_seconds=yt_row["duration_seconds"],
                    curriculum_status=yt_row["curriculum_status"],
                    attribution_text=yt_row["attribution_text"],
                    is_embeddable=bool(yt_row["is_embeddable"]),
                    is_offline_available=False
                )
                video_source_type = "YOUTUBE"

            return LessonDetailResponse(
                id=l_row["id"],
                course_id=l_row["course_id"],
                unit_number=l_row["unit_number"],
                title_sindhi=l_row["title_sindhi"],
                title_english=l_row["title_english"],
                duration_seconds=l_row["duration_seconds"],
                status=l_row["status"],
                summary_sindhi=l_row["summary_sindhi"],
                is_completed=is_comp,
                last_position_seconds=last_pos,
                video_hls_url=video_hls,
                video_fallback_url=video_fallback,
                audio_only_url=audio_only,
                video_source_type=video_source_type,
                youtube_video=youtube_video,
                transcripts=transcripts,
                approved_questions=approved_questions
            )

    def review_lesson(self, reviewer_id: str, lesson_id: str, action: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Content reviewer reviews lesson draft/curriculum mapping (Phase 5 RBAC)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        rev_id = f"rev-{uuid.uuid4().hex[:8]}"

        status_mapping = {
            "APPROVED": "PUBLISHED",
            "REJECTED": "REJECTED",
            "REVISION_REQUESTED": "DRAFT"
        }
        new_status = status_mapping.get(action.upper(), "DRAFT")

        with get_db() as conn:
            lesson = conn.execute("SELECT id FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
            if not lesson:
                raise ValueError("Lesson not found.")

            conn.execute(
                """
                INSERT INTO lesson_reviews (id, lesson_id, reviewer_id, action, comments, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (rev_id, lesson_id, reviewer_id, action.upper(), comments, now_iso)
            )

            conn.execute(
                "UPDATE lessons SET status = ? WHERE id = ?",
                (new_status, lesson_id)
            )

            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, 'LESSON_REVIEWED', 'lesson', ?, ?, ?)
                """,
                (str(uuid.uuid4()), reviewer_id, lesson_id, json.dumps({"action": action.upper(), "comments": comments}), now_iso)
            )

        return {
            "id": rev_id,
            "lesson_id": lesson_id,
            "reviewer_id": reviewer_id,
            "action": action.upper(),
            "new_lesson_status": new_status,
            "comments": comments,
            "created_at": now_iso
        }

    def list_youtube_videos(self, class_level: Optional[int] = None) -> List[YouTubeVideoResponse]:
        """List catalog of approved or mapped educational YouTube videos."""
        with get_db() as conn:
            query = "SELECT * FROM youtube_videos WHERE 1=1"
            params = []
            if class_level is not None:
                query += " AND class_level = ?"
                params.append(class_level)
            query += " ORDER BY class_level ASC, created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [
                YouTubeVideoResponse(
                    id=r["id"],
                    lesson_id=r["lesson_id"],
                    youtube_id=r["youtube_id"],
                    title=r["title"],
                    channel_name=r["channel_name"],
                    original_url=r["original_url"],
                    embed_url=r["embed_url"],
                    class_level=r["class_level"],
                    subject=r["subject"],
                    language=r["language"],
                    topic=r["topic"],
                    duration_seconds=r["duration_seconds"],
                    curriculum_status=r["curriculum_status"],
                    attribution_text=r["attribution_text"],
                    is_embeddable=bool(r["is_embeddable"]),
                    is_offline_available=False
                )
                for r in rows
            ]

    def create_lesson(self, teacher_id: str, req: "LessonUploadRequest") -> LessonResponse:
        """Teacher uploads/creates a lesson with metadata and video URLs (FR-09)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        lesson_id = f"lesson-{uuid.uuid4().hex[:8]}"
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO lessons (id, course_id, unit_number, title_sindhi, title_english, duration_seconds, status, summary_sindhi, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'PUBLISHED', ?, ?)
                """,
                (lesson_id, req.course_id, req.unit_number, req.title_sindhi, req.title_english, req.duration_seconds, req.summary_sindhi, now_iso)
            )
            video_url = req.video_url or f"/static/media/{lesson_id}.mp4"
            conn.execute(
                """
                INSERT INTO videos (id, lesson_id, hls_url, fallback_url, audio_only_url, resolution_240p, resolution_360p)
                VALUES (?, ?, ?, ?, ?, '240p', '360p')
                """,
                (f"vid-{lesson_id}", lesson_id, f"/static/media/{lesson_id}.m3u8", video_url, f"/static/media/{lesson_id}.mp3")
            )
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, 'LESSON_UPLOADED', 'lesson', ?, ?, ?)
                """,
                (str(uuid.uuid4()), teacher_id, lesson_id, json.dumps({"title_sindhi": req.title_sindhi}), now_iso)
            )
            return LessonResponse(
                id=lesson_id,
                course_id=req.course_id,
                unit_number=req.unit_number,
                title_sindhi=req.title_sindhi,
                title_english=req.title_english,
                duration_seconds=req.duration_seconds,
                status="PUBLISHED",
                summary_sindhi=req.summary_sindhi
            )

    def update_progress(self, user_id: str, lesson_id: str, position_seconds: float, is_completed: bool = False) -> None:
        """Update or insert student lesson progress checkpoint with meaningful completion threshold enforcement."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            row = conn.execute(
                """SELECT l.duration_seconds FROM lessons l JOIN courses c ON c.id=l.course_id
                   WHERE l.id=? AND l.status IN ('PUBLISHED','APPROVED') AND c.class_level=6
                     AND c.subject IN ('Math','Science','English','Sindhi')""",
                (lesson_id,)
            ).fetchone()
            if not row:
                raise ValueError("Lesson is not available in the current Class 6 curriculum.")
            expected_duration = float(row["duration_seconds"]) if row["duration_seconds"] else 600.0
            safe_position = max(0.0, min(float(position_seconds), expected_duration))

            # Check if student attempted in-video checkpoints for this lesson
            checkpoint_count = conn.execute(
                "SELECT COUNT(*) FROM questions WHERE lesson_id = ? AND status = 'APPROVED'",
                (lesson_id,)
            ).fetchone()[0]

            attempts_count = conn.execute(
                """SELECT COUNT(DISTINCT a.question_id) FROM attempts a
                   JOIN questions q ON q.id = a.question_id
                   WHERE a.user_id = ? AND q.lesson_id = ?""",
                (user_id, lesson_id)
            ).fetchone()[0]

            has_completed_all_checkpoints = (checkpoint_count > 0 and attempts_count >= checkpoint_count)

            # Completion threshold: at least 80% of expected duration must be reached, OR all in-video checkpoints completed
            completion_threshold = max(60.0, expected_duration * 0.8)
            effective_completed = (
                (is_completed and safe_position >= completion_threshold) or
                (is_completed and has_completed_all_checkpoints)
            )

            conn.execute(
                """
                INSERT INTO progress (id, user_id, lesson_id, last_position_seconds, is_completed, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                    last_position_seconds = excluded.last_position_seconds,
                    is_completed = CASE WHEN excluded.is_completed = 1 THEN 1 ELSE is_completed END,
                    updated_at = excluded.updated_at
                """,
                (str(uuid.uuid4()), user_id, lesson_id, safe_position, 1 if effective_completed else 0, now_iso)
            )


lesson_service = LessonService()
