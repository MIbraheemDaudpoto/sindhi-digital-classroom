"""
Comprehensive Verification Test Suite for SDC LMS Repairs.
Tests:
1. Unified Science & Mathematics Retrieval and Citation Accuracy.
2. Cross-domain Disambiguation (Query 'سيٽ' matches Math Sets, not Science PAKSAT).
3. Authenticated vs Unauthenticated access to /api/tutor/transcribe.
4. Input validation on /transcribe (empty, oversized, unsupported format, malformed).
5. Truthful ASR failure behavior (never returns canned fake student words).
6. Truthful TTS behavior and status (503 when neural model unavailable, diagnostic mode).
7. Video completion semantics (10s placeholder cannot complete 10-minute lesson).
8. Database idempotency and unique question constraints.
"""

import io
import os
from pathlib import Path
import shutil
import sqlite3
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.models.schemas import TutorAskRequest
from src.services.ai_tutor_service import ai_tutor_service
from src.services.lesson_service import lesson_service
from src.services.sdc_rag_service import sdc_rag_service
from src.services.sindhi_asr_service import sindhi_asr_service
from src.services.sindhi_tts_service import sindhi_tts_service

client = TestClient(app)

# Helper to obtain a valid authenticated student token
def get_student_auth_token():
    resp = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    """Run tests against an isolated copy of sdc_platform.db to protect production data."""
    test_db = tmp_path / "sdc_platform_isolated.db"
    shutil.copy2("data/sdc_platform.db", test_db)
    orig_path = settings.database_path
    settings.database_path = str(test_db)
    yield str(test_db)
    settings.database_path = orig_path


# --- 1. Unified Retrieval & Disambiguation ---

def test_unified_retrieval_math_sets_vs_science_paksat():
    """Verify query 'سيٽ' returns Math Unit 1 Sets and eliminates Science PAKSAT false match."""
    # 1. Pure query for "سيٽ" without subject filter
    chunks = sdc_rag_service.search_chunks("سيٽ", limit=5)
    assert len(chunks) > 0
    top_c = chunks[0]
    assert top_c["subject_id"] == "math-6", f"Expected math-6 top result, got: {top_c['subject_id']}"
    assert top_c["chapter_id"] == 1, "Expected Unit 1 (Sets)"
    assert "سيٽ" in top_c["topic_title_sd"]
    
    # Confirm PAKSAT chunk (ch12-06) is not in the set results
    chunk_ids = [c["chunk_id"] for c in chunks]
    assert "ch12-06" not in chunk_ids, "Cross-domain PAKSAT satellite chunk must not match pure 'سيٽ' query!"

    # 2. Pure query for "پاڪ سيٽ" (PAKSAT) returns Science Chapter 12
    paksat_chunks = sdc_rag_service.search_chunks("پاڪ سيٽ", limit=3)
    assert len(paksat_chunks) > 0
    assert paksat_chunks[0]["chunk_id"] == "ch12-06"
    assert paksat_chunks[0]["subject_id"] == "science-6"


def test_unified_retrieval_subject_filtering():
    """Verify explicit subject filter restricts search to Math or Science."""
    math_results = sdc_rag_service.search_chunks("عدد", subject_id="math-6", limit=5)
    for c in math_results:
        assert c["subject_id"] == "math-6"

    sci_results = sdc_rag_service.search_chunks("توانائي", subject_id="science-6", limit=5)
    for c in sci_results:
        assert c["subject_id"] == "science-6"


def test_tutor_ask_in_lesson_context():
    """Verify AI Tutor answers within lesson context and formats verified STBB citations."""
    token = get_student_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Ask Math Question within lesson-math-6-1
    resp = client.post("/api/tutor/ask", headers=headers, json={
        "question": "سيٽ ڇا آهي ۽ ان جا رڪن ڪيئن لکبا آهن؟",
        "lesson_id": "lesson-math-6-1",
        "class_level": 6,
        "subject_id": "math"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refused"] is False
    assert len(data["citations"]) >= 1
    assert "Riazi Sindhi VI" in data["citations"][0]["citation_formatted"] or "PDF" in data["citations"][0]["citation_formatted"]
    assert data["provider_type"] == "LOCAL_DETERMINISTIC_FALLBACK"


def test_tutor_out_of_curriculum_refusal():
    """Verify AI Tutor strictly refuses out-of-curriculum queries."""
    token = get_student_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/tutor/ask", headers=headers, json={
        "question": "ڪرڪيٽ ورلڊ ڪپ ڪنهن کٽيو؟",
        "class_level": 6
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refused"] is True
    assert "دائري کان ٻاهر" in data["answer_sindhi"] or "معاف ڪجو" in data["answer_sindhi"]


# --- 2. Secure Speech Transcription & Upload Limits ---

def test_transcribe_unauthenticated_rejected():
    """Verify unauthenticated requests to /api/tutor/transcribe receive HTTP 401."""
    fake_wav = b"RIFF" + b"\x00" * 100
    files = {"file": ("test.wav", io.BytesIO(fake_wav), "audio/wav")}
    resp = client.post("/api/tutor/transcribe", files=files)
    assert resp.status_code == 401, f"Expected 401 Unauthorized, got: {resp.status_code}"


def test_transcribe_authenticated_empty_file_rejected():
    """Verify empty audio uploads receive HTTP 400."""
    token = get_student_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("empty.wav", io.BytesIO(b""), "audio/wav")}
    resp = client.post("/api/tutor/transcribe", headers=headers, files=files)
    assert resp.status_code == 400


def test_transcribe_authenticated_malformed_file_rejected():
    """Verify malformed audio (< 32 bytes) receives HTTP 400."""
    token = get_student_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("tiny.wav", io.BytesIO(b"RIFFshort"), "audio/wav")}
    resp = client.post("/api/tutor/transcribe", headers=headers, files=files)
    assert resp.status_code == 400


def test_transcribe_unsupported_format_rejected():
    """Verify unsupported file extensions/MIMEs receive HTTP 415."""
    token = get_student_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("script.py", io.BytesIO(b"print('hello')\n" * 10), "text/x-python")}
    resp = client.post("/api/tutor/transcribe", headers=headers, files=files)
    assert resp.status_code == 415


def test_transcribe_oversized_file_rejected():
    """Verify uploads exceeding 10MB receive HTTP 413."""
    token = get_student_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Simulate 10.5 MB file
    big_buffer = io.BytesIO(b"RIFF" + b"\x00" * (10 * 1024 * 1024 + 1024))
    files = {"file": ("big.wav", big_buffer, "audio/wav")}
    resp = client.post("/api/tutor/transcribe", headers=headers, files=files)
    assert resp.status_code == 413


# --- 3. Truthful ASR and No Canned Fallbacks ---

def test_asr_empty_recognition_returns_failure_not_canned_answer():
    """Verify ASR on pure silence/noise returns success=False, NEVER canned student question."""
    # Generate 1 second of silent 16kHz PCM WAV
    import struct
    silent_pcm = struct.pack(f"<{16000}h", *([0] * 16000))
    wav_buf = io.BytesIO()
    import wave
    with wave.open(wav_buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(silent_pcm)
    silent_wav = wav_buf.getvalue()

    result = sindhi_asr_service.transcribe_audio_bytes(silent_wav, file_ext=".wav")
    assert result["success"] is False
    assert result["text_sindhi"] == ""
    # Crucial assertion: Must not return the old deceptive canned question!
    assert "جيو گهرڙو ڇا آهي" not in result.get("text_sindhi", "")


def test_asr_status_observable():
    """Verify ASR model availability is observable without leaking secrets."""
    status = sindhi_asr_service.get_status()
    assert "engine" in status
    assert "model_loaded" in status
    assert "compute_type" in status
    assert status["engine"] == "faster-whisper"


# --- 4. Truthful TTS Behavior ---

def test_tts_status_and_honest_unavailable_response():
    """Verify TTS truthfully returns 503 when neural model is not cached, preserving text answer."""
    status = sindhi_tts_service.get_status()
    assert "neural_model_loaded" in status
    assert "speech_usable" in status

    # Without neural model, GET /api/tutor/tts must return 503 Service Unavailable
    resp = client.get("/api/tutor/tts?text=سلام")
    if not status["neural_model_loaded"]:
        assert resp.status_code == 503
        assert "دستياب ناهي" in resp.json()["detail"]

    # When allow_diagnostic=true is passed, diagnostic formant audio is returned
    resp_diag = client.get("/api/tutor/tts?text=سلام&allow_diagnostic=true")
    assert resp_diag.status_code == 200
    assert resp_diag.headers["content-type"] == "audio/wav"
    assert resp_diag.headers["X-SDC-TTS-Model"] == "diagnostic_formants"


def test_tts_empty_input_rejected():
    """Verify empty text to TTS returns 400 Bad Request."""
    resp = client.get("/api/tutor/tts?text=   ")
    assert resp.status_code == 400 or resp.status_code == 422


# --- 5. Video Progress and Completion Semantics ---

def test_short_placeholder_video_cannot_complete_lesson():
    """Verify playing a 10s demo video cannot mark a 600s lesson completed."""
    user_id = "usr-stu-101"
    lesson_id = "lesson-sci-6-2"

    # Student reaches 10.0 seconds on a 600-second lesson
    lesson_service.update_progress(
        user_id=user_id,
        lesson_id=lesson_id,
        position_seconds=10.0,
        is_completed=True  # Client claims completed
    )

    with sqlite3.connect(settings.database_path) as conn:
        conn.row_factory = sqlite3.Row
        prog = conn.execute("SELECT * FROM progress WHERE user_id = ? AND lesson_id = ?", (user_id, lesson_id)).fetchone()
        assert prog is not None
        assert prog["last_position_seconds"] == 10.0
        # Completion MUST be rejected because 10s < 80% of 600s
        assert prog["is_completed"] == 0, "10-second clip must NOT mark a 600-second lesson as complete!"


def test_full_watch_marks_lesson_complete():
    """Verify watching past the 80% threshold genuinely marks lesson completed."""
    user_id = "usr-stu-101"
    lesson_id = "lesson-sci-6-2"

    lesson_service.update_progress(
        user_id=user_id,
        lesson_id=lesson_id,
        position_seconds=500.0,  # 500s / 600s = 83.3%
        is_completed=True
    )

    with sqlite3.connect(settings.database_path) as conn:
        conn.row_factory = sqlite3.Row
        prog = conn.execute("SELECT * FROM progress WHERE user_id = ? AND lesson_id = ?", (user_id, lesson_id)).fetchone()
        assert prog["is_completed"] == 1


# --- 6. Database Idempotency & Unique Question Constraint ---

def test_database_question_uniqueness_enforced():
    """Verify questions table enforces uniqueness on (lesson_id, timestamp_seconds, text_sindhi)."""
    with sqlite3.connect(settings.database_path) as conn:
        # Inserting exact duplicate row must be rejected by unique index
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO questions (
                    id, lesson_id, timestamp_seconds, text_sindhi, options_json,
                    correct_answer_index, difficulty, topic, status
                ) VALUES ('duplicate-test-id-123', 'lesson-sci-6-1', 125.0, 'فوٽوسنٿيسز عمل دوران ٻوٽا ڇا ٺاهيندا آهن؟', '[]', 0, 'MEDIUM', 'Science', 'APPROVED')
            """)
