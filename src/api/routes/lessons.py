"""Curriculum & Lesson routes for SDC.
Authored under agency-api-platform-engineer.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from src.api.deps import get_current_user, require_roles
from src.database.session import get_db
from src.models.schemas import CourseResponse, LessonDetailResponse, LessonResponse, LessonReviewRequest, LessonUploadRequest, ProgressUpdateRequest, UserRole, YouTubeVideoResponse
from src.services.lesson_service import lesson_service

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".m3u8"}
ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
    "application/x-mpegurl",
    "application/vnd.apple.mpegurl",
}
MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024  # 50MB pilot limit


@router.post("/upload", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def upload_lesson(
    req: LessonUploadRequest,
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN))
):
    """Teacher uploads video lesson metadata and sets up unit (FR-09)."""
    return lesson_service.create_lesson(current_user["id"], req)


@router.post("/{lesson_id}/video-file", status_code=status.HTTP_200_OK)
async def upload_lesson_video_file(
    lesson_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN))
):
    """Upload and validate video media binary file for a lesson (MIME & extension enforcement)."""
    # 1. Validate lesson existence
    with get_db() as conn:
        lesson = conn.execute("SELECT id FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="سبق نه مليو (Lesson not found).")

    # 2. Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"غير منظور ٿيل وڊيو فارميٽ '{ext}'. رڳو mp4, webm, mov, mkv, m3u8 منظور آهن (Invalid extension)."
        )

    # 3. Validate MIME type
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_VIDEO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"غير منظور ٿيل وڊيو قسم '{content_type}' (Unsupported video MIME type)."
        )

    # 4. Read contents and validate size bounds
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="خالي فائل قبول ناهي (Empty file).")
    if len(content) > MAX_VIDEO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="وڊيو فائل تمام وڏي آهي (File exceeds 50MB pilot limit)."
        )

    # 5. Deep File Content (Magic Bytes) Verification
    # Check for executable and script signatures to prevent polyglots / webshells
    prefix_100 = content[:100].lower()
    if content[:2] == b"MZ" or content[:4] == b"\x7fELF" or b"<?php" in prefix_100 or b"<script" in prefix_100 or b"eval(" in prefix_100:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="سيڪيورٽي خطرو: غير منظور ٿيل ايگزيڪيوٽيبل يا اسڪرپٽ مواد (Executable/script content rejected)."
        )

    # Verify actual container signatures
    is_valid_media = False
    if ext in {".mp4", ".mov"}:
        is_valid_media = b"ftyp" in content[:32] or b"moov" in content[:32] or b"mdat" in content[:32]
    elif ext in {".webm", ".mkv"}:
        is_valid_media = content[:4] == b"\x1a\x45\xdf\xa3"
    elif ext in {".m3u8"}:
        is_valid_media = content.startswith(b"#EXTM3U")

    if not is_valid_media:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="فائل جو مواد معتبر وڊيو فارميٽ سان مطابقت نٿو رکي (File header does not match valid video container signatures)."
        )

    # 6. Safe Filename & Atomic Write with Interrupted Upload Protection
    import re
    safe_lesson_id = re.sub(r"[^a-zA-Z0-9_\-]", "", lesson_id)
    dest_dir = (Path(__file__).resolve().parent.parent.parent.parent / "static" / "media").resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    clean_filename = f"{safe_lesson_id}{ext}"
    dest_path = (dest_dir / clean_filename).resolve()

    # Verify path containment to strictly block directory traversal
    if not str(dest_path).startswith(str(dest_dir)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="غلط فائل رستو (Invalid file path).")

    # Atomic write via temporary file
    import uuid
    tmp_path = dest_dir / f"{clean_filename}.tmp.{uuid.uuid4().hex[:6]}"
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)
        tmp_path.replace(dest_path)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="اسٽوريج ايرر (Storage write failure).")

    # 7. Update video record in DB
    relative_url = f"/static/media/{clean_filename}"
    with get_db() as conn:
        conn.execute(
            """
            UPDATE videos
            SET fallback_url = ?, file_size_bytes = ?
            WHERE lesson_id = ?
            """,
            (relative_url, len(content), safe_lesson_id)
        )

    return {

        "status": "ok",
        "lesson_id": lesson_id,
        "video_url": relative_url,
        "size_bytes": len(content),
        "message": "وڊيو ڪاميابيءَ سان اپلوڊ ٿي وئي (Video uploaded successfully)."
    }



@router.get("", response_model=List[CourseResponse])
async def list_curriculum(
    class_level: Optional[int] = Query(None, ge=6, le=6, description="Currently supported class: 6"),
    subject: Optional[str] = Query(None, description="Currently supported subjects: Math or Science")
):
    """Browse lessons organized by class, subject, and unit (FR-05)."""
    return lesson_service.list_courses(class_level=class_level, subject=subject)


@router.get("/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve lesson detail with video, transcripts, and approved questions (FR-06, FR-08, FR-13)."""
    detail = lesson_service.get_lesson_detail(lesson_id, user_id=current_user["id"])
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    return detail


@router.post("/{lesson_id}/progress", status_code=status.HTTP_200_OK)
async def update_lesson_progress(
    lesson_id: str,
    req: ProgressUpdateRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT))
):
    """Update student playback position and completion status (FR-08)."""
    try:
        lesson_service.update_progress(
            user_id=current_user["id"],
            lesson_id=lesson_id,
            position_seconds=req.position_seconds,
            is_completed=req.is_completed
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"status": "ok", "message": "Progress recorded."}


@router.get("/youtube/catalog", response_model=List[YouTubeVideoResponse])
async def list_youtube_catalog(
    class_level: Optional[int] = Query(None, ge=6, le=10, description="Filter by class level 6-10")
):
    """Retrieve official educational YouTube video catalog for STBB curriculum (Phase 4)."""
    return lesson_service.list_youtube_videos(class_level=class_level)


@router.get("/{lesson_id}/video", status_code=status.HTTP_200_OK)
async def get_lesson_video_info(lesson_id: str):
    """Inspect video source, format compatibility, byte-range capability, and YouTube mapping."""
    detail = lesson_service.get_lesson_detail(lesson_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    clean_id = lesson_id.replace("..", "").replace("/", "").replace("\\", "").strip()
    local_path = (Path(__file__).resolve().parent.parent.parent.parent / "static" / "media" / f"{clean_id}.mp4").resolve()
    local_exists = local_path.exists()
    file_size = local_path.stat().st_size if local_exists else 0

    return {
        "lesson_id": lesson_id,
        "video_source_type": detail.video_source_type,
        "local_media": {
            "url": detail.video_fallback_url,
            "exists_on_disk": local_exists,
            "file_size_bytes": file_size,
            "supports_byte_ranges": True,
            "mime_type": "video/mp4"
        },
        "youtube_media": detail.youtube_video,
        "hls_url": detail.video_hls_url,
        "audio_only_url": detail.audio_only_url,
        "offline_capable": local_exists,
        "legal_notice": "Channel attribution and promotion do not independently authorize copyright reuse. Local playback requires authorized distribution."
    }


@router.post("/{lesson_id}/review", status_code=status.HTTP_200_OK)
async def review_lesson_status(
    lesson_id: str,
    req: LessonReviewRequest,
    current_user: dict = Depends(require_roles(UserRole.CONTENT_REVIEWER, UserRole.SUPER_ADMIN, UserRole.ADMIN))
):
    """Content reviewer approves or rejects lesson for curriculum publication (Phase 5 RBAC)."""
    caller_role = current_user.get("legacy_role") or current_user.get("role")
    if caller_role in {"TEACHER", "STUDENT", "DISTRICT_OFFICER", "SCHOOL_ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="استادن يا عام اسڪول اسٽاف کي نصاب منظور ڪرڻ جو اختيار ناهي (Teachers not authorized for lesson review)."
        )
    try:
        result = lesson_service.review_lesson(
            reviewer_id=current_user["id"],
            lesson_id=lesson_id,
            action=req.action,
            comments=req.comments
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

