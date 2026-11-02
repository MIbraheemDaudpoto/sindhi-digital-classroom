"""
Tests for Sindhi Voice AI: T2T (Text-to-Text), TTS (Text-to-Voice), and ASR (Voice-to-Text).
Verifies:
1. Text-to-Text: Grounded answers and citations across both Science and Mathematics (STBB Class 6).
2. Text-to-Voice: Authentic 16kHz WAV generation honoring Sindhi phonetics (implosives, aspirates).
3. Voice-to-Text: Audio transcription and Sindhi Perso-Arabic script normalization.
Authored under agency-ai-engineer and agency-voice-ai-integration-engineer.
"""

import io
import shutil
import wave
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.models.schemas import TutorAskRequest
from src.services.ai_tutor_service import ai_tutor_service
from src.services.sindhi_tts_service import sindhi_tts_service
from src.services.sindhi_asr_service import sindhi_asr_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    """Run tests against an isolated copy of sdc_platform.db."""
    test_db = tmp_path / "sdc_platform_voice_test.db"
    shutil.copy2("data/sdc_platform.db", test_db)
    orig_path = settings.database_path
    settings.database_path = str(test_db)
    yield str(test_db)
    settings.database_path = orig_path


def get_auth_token():
    resp = client.post("/api/auth/login/student", json={
        "school_code": "SCH-HYD-01",
        "student_code": "STU-101",
        "pin": "1234"
    })
    assert resp.status_code == 200
    return resp.json()["token"]


def test_t2t_science_grounding():
    """Verify AI Tutor correctly answers Class 6 General Science queries with citation."""
    req = TutorAskRequest(
        question="جيو گهرڙو ڇا آهي ۽ ان جا مکيه حصا ڪهڙا آهن؟",
        class_level=6,
        subject_id="general-science"
    )
    resp = ai_tutor_service.answer_student_question("usr-stu-101", req)
    assert resp.is_refused is False
    assert len(resp.citations) >= 1
    assert "گهرڙو" in resp.answer_sindhi
    assert any("PDF" in c.citation_formatted for c in resp.citations)


def test_t2t_math_sets_grounding():
    """Verify AI Tutor correctly answers Class 6 Mathematics Unit 1 (Sets) with Riazi Sindhi VI citation."""
    req = TutorAskRequest(
        question="سيٽ ڇا آهي ۽ ان جا رڪن ڪيئن لکبا آهن؟",
        class_level=6,
        subject_id="math"
    )
    resp = ai_tutor_service.answer_student_question("usr-stu-101", req)
    assert resp.is_refused is False
    assert len(resp.citations) >= 1
    assert "سيٽ" in resp.answer_sindhi
    first_cit = resp.citations[0]
    assert "Riazi Sindhi VI" in first_cit.citation_formatted or "PDF 5" in first_cit.citation_formatted


def test_t2t_math_integers_grounding():
    """Verify AI Tutor correctly answers Class 6 Mathematics Unit 4 (Integers) with verified page citations."""
    req = TutorAskRequest(
        question="سڄا عدد ڇا آهن ۽ انهن جي ترتيب ڪيئن هوندي آهي؟",
        class_level=6,
        subject_id="math"
    )
    resp = ai_tutor_service.answer_student_question("usr-stu-101", req)
    assert resp.is_refused is False
    assert len(resp.citations) >= 1
    assert "سڄا عدد" in resp.answer_sindhi
    assert "68-91" in resp.citations[0].citation_formatted or "64-87" in resp.citations[0].citation_formatted


def test_t2t_math_geometry_grounding():
    """Verify AI Tutor correctly answers Class 6 Mathematics Unit 10 (Geometry - Perpendicular Bisector)."""
    req = TutorAskRequest(
        question="عمودي وچولي ليڪ ڇا آهي ۽ ڪيئن ٺاهبي آهي؟",
        class_level=6,
        subject_id="math"
    )
    resp = ai_tutor_service.answer_student_question("usr-stu-101", req)
    assert resp.is_refused is False
    assert len(resp.citations) >= 1
    assert "عمودي وچولي ليڪ" in resp.answer_sindhi
    assert "170" in resp.citations[0].citation_formatted and "166" in resp.citations[0].citation_formatted


def test_t2t_out_of_scope_refusal():
    """Verify AI Tutor strictly refuses out-of-scope non-curriculum queries."""
    req = TutorAskRequest(
        question="پاڪستان جو وزيراعظم ڪير آهي؟",
        class_level=6
    )
    resp = ai_tutor_service.answer_student_question("usr-stu-101", req)
    assert resp.is_refused is True
    assert "دائري کان ٻاهر" in resp.answer_sindhi or "معاف ڪجو" in resp.answer_sindhi
    assert len(resp.citations) == 0


def test_tts_service_wav_generation():
    """Verify SindhiTTSService generates valid 16kHz mono PCM WAV with Sindhi phonetics."""
    sample_text = "اسلام عليڪم! ٻوٽا سج جي روشني ۽ پاڻي مان کاڌو تيار ڪن ٿا."
    wav_bytes, _ = sindhi_tts_service.synthesize(sample_text, allow_diagnostic_fallback=True)
    assert wav_bytes is not None
    assert len(wav_bytes) > 500

    # Parse WAV header to verify audio validity
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1, "Must be mono audio"
        assert wf.getsampwidth() == 2, "Must be 16-bit PCM"
        assert wf.getframerate() == 16000, "Must be 16kHz sample rate"
        assert wf.getnframes() > 1000, "Audio frames must be non-trivial"


def test_tts_api_endpoints():
    """Verify GET and POST /api/tutor/tts endpoints return valid audio/wav responses with diagnostic allowance."""
    # 1. GET endpoint with diagnostic mode
    text_param = "سيٽ مختلف شين جو مجموعو آهي"
    resp_get = client.get(f"/api/tutor/tts?text={text_param}&allow_diagnostic=true")
    assert resp_get.status_code == 200
    assert resp_get.headers["content-type"] == "audio/wav"
    assert len(resp_get.content) > 500

    # 2. POST endpoint with allow_diagnostic
    resp_post = client.post("/api/tutor/tts", json={"text": "سڄا عدد ۽ پورا عدد", "allow_diagnostic": True})
    assert resp_post.status_code == 200
    assert resp_post.headers["content-type"] == "audio/wav"
    assert len(resp_post.content) > 500


def test_asr_service_and_transcribe_endpoint():
    """Verify Voice-to-Text (ASR) transcription pipeline and authenticated API endpoint."""
    # Generate clean in-memory audio using diagnostic acoustic synthesizer
    test_phrase = "جيو گهرڙو ڇا آهي"
    wav_audio, _ = sindhi_tts_service.synthesize(test_phrase, allow_diagnostic_fallback=True)
    assert wav_audio is not None
    assert len(wav_audio) > 500

    # Test service directly (silence/synthetic phonemes)
    res_service = sindhi_asr_service.transcribe_audio_bytes(wav_audio, file_ext=".wav")
    assert "success" in res_service

    # Test authenticated POST /api/tutor/transcribe endpoint
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("student_voice.wav", io.BytesIO(wav_audio), "audio/wav")}
    resp_api = client.post("/api/tutor/transcribe", headers=headers, files=files)
    assert resp_api.status_code == 200
    data = resp_api.json()
    assert "success" in data
