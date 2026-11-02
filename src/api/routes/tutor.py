"""Grounded Sindhi AI Tutor routes for SDC.
Authored under agency-ai-engineer.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import BaseModel
from typing import Optional
from src.api.deps import get_current_user, require_roles
from src.models.schemas import TutorAskRequest, TutorAskResponse, UserRole
from src.services.ai_tutor_service import ai_tutor_service
from src.services.sindhi_asr_service import sindhi_asr_service
from src.services.sindhi_tts_service import sindhi_tts_service

router = APIRouter(prefix="/api/tutor", tags=["AI Tutor"])


class ReportWrongAnswerRequest(BaseModel):
    report_id: str
    reason: str = "Incorrect answer"


class TTSRequest(BaseModel):
    text: str
    allow_diagnostic: bool = False


@router.get("/tts/status")
async def get_tts_status():
    """Return operational availability and diagnostic info for Sindhi speech synthesis."""
    return sindhi_tts_service.get_status()


@router.get("/tts")
async def synthesize_text_to_speech_get(
    text: str = Query(..., min_length=1, max_length=2000, description="Sindhi text to synthesize into spoken audio"),
    allow_diagnostic: bool = Query(False, description="Explicitly allow diagnostic formant oscillator tones")
):
    """Text-to-Speech (TTS) GET endpoint returning 16kHz WAV audio."""
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text cannot be empty.")
    try:
        wav_bytes, is_neural = sindhi_tts_service.synthesize(text, allow_diagnostic_fallback=allow_diagnostic)
        if wav_bytes is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="سنڌي آواز وارو ماڊل هن وقت دستياب ناهي (Neural Sindhi TTS model unavailable offline)."
            )
        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=sindhi_speech.wav",
                "Cache-Control": "public, max-age=86400",
                "X-SDC-TTS-Model": "neural" if is_neural else "diagnostic_formants"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"TTS synthesis failed: {str(e)}")


@router.post("/tts")
async def synthesize_text_to_speech_post(req: TTSRequest):
    """Text-to-Speech (TTS) POST endpoint returning 16kHz WAV audio."""
    if not req.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text cannot be empty.")
    try:
        wav_bytes, is_neural = sindhi_tts_service.synthesize(req.text, allow_diagnostic_fallback=req.allow_diagnostic)
        if wav_bytes is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="سنڌي آواز وارو ماڊل هن وقت دستياب ناهي (Neural Sindhi TTS model unavailable offline)."
            )
        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "inline; filename=sindhi_speech.wav",
                "Cache-Control": "public, max-age=86400",
                "X-SDC-TTS-Model": "neural" if is_neural else "diagnostic_formants"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"TTS synthesis failed: {str(e)}")


@router.post("/ask", response_model=TutorAskResponse)
def ask_ai_tutor(
    req: TutorAskRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN))
):
    """Query Grounded Sindhi AI Tutor. Returns grounded answer or strict Sindhi refusal (FR-23, FR-24, FR-25)."""
    return ai_tutor_service.answer_student_question(current_user["id"], req)


@router.post("/report", status_code=status.HTTP_200_OK)
async def report_wrong_answer(
    req: ReportWrongAnswerRequest,
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN))
):
    """Flag inaccurate AI answer for teacher review (FR-26)."""
    success = ai_tutor_service.report_wrong_answer(req.report_id, current_user["id"], req.reason)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat log report ID not found.")
    return {"status": "ok", "message": "Report submitted to teacher for review."}


MAX_AUDIO_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB limit
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".ogg", ".mp3", ".m4a", ".aac"}
ALLOWED_AUDIO_MIMES = {
    "audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/aac", "application/octet-stream"
}


@router.post("/transcribe")
async def transcribe_audio_input(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles(UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN))
):
    """Voice-to-Text (ASR) endpoint. Transcribes speech audio to normalized Sindhi text."""
    import os
    # Validate extension and MIME type
    ext = ".webm"
    if file.filename:
        _, ext_candidate = os.path.splitext(file.filename)
        if ext_candidate:
            ext = ext_candidate.lower()

    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if ext not in ALLOWED_AUDIO_EXTENSIONS and content_type not in ALLOWED_AUDIO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"غير معاونت ٿيل آڊيو فارميٽ (Unsupported audio format: {ext or content_type})."
        )

    # Stream-read up to MAX_AUDIO_UPLOAD_SIZE without unconstrained memory exhaustion
    audio_buffer = bytearray()
    chunk_size = 65536
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        audio_buffer.extend(chunk)
        if len(audio_buffer) > MAX_AUDIO_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="آڊيو فائل 10 ايم بي جي حد کان وڌيڪ آهي (Audio file exceeds 10MB limit)."
            )

    if len(audio_buffer) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="آڊيو ڊيٽا خالي آهي (Empty audio file).")

    if len(audio_buffer) < 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="آڊيو فائل ناقص آهي (Malformed audio file).")

    try:
        result = sindhi_asr_service.transcribe_audio_bytes(bytes(audio_buffer), file_ext=ext)
        if not result.get("success") and "دستياب ناهي" in str(result.get("error", "")):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Transcription error: {str(e)}")




