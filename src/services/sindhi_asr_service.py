"""
Sindhi Automatic Speech Recognition (ASR / Voice-to-Text) Service for SDC.
Integrates local faster-whisper with cached multilingual base model targeting Sindhi (language='sd').
Converts incoming browser audio (WebM, OGG, WAV, MP4) via ffmpeg into 16kHz mono PCM,
transcribes speech, and normalizes into canonical 52-letter Sindhi script.

Authored under agency-ai-engineer and agency-voice-ai-integration-engineer.
"""

from __future__ import annotations
import logging
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Dict, Any, Optional

from src.services.sindhi_nlp import normalize_sindhi_text

logger = logging.getLogger("sdc.asr")

# Default cached model path on the system
DEFAULT_WHISPER_SNAPSHOT = Path(os.path.expanduser("~/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"))


class SindhiASRService:
    """Offline-capable Sindhi Automatic Speech Recognition Service."""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path) if model_path else DEFAULT_WHISPER_SNAPSHOT
        self._model = None
        self._initialized = False

    def _get_model(self):
        if self._initialized:
            return self._model
        self._initialized = True
        try:
            from faster_whisper import WhisperModel
            if self.model_path.exists():
                logger.info("Loading local faster-whisper model from %s...", self.model_path)
                self._model = WhisperModel(str(self.model_path), device="cpu", compute_type="int8")
                logger.info("faster-whisper Sindhi ASR initialized successfully.")
            else:
                logger.warning("Local faster-whisper snapshot not found at %s. Implicit download disabled.", self.model_path)
                self._model = None
        except Exception as e:
            logger.error("Failed to initialize faster-whisper ASR: %s", e)
            self._model = None
        return self._model

    def get_status(self) -> Dict[str, Any]:
        """Return observable status of the ASR engine without leaking secrets."""
        return {
            "engine": "faster-whisper",
            "model_path_exists": self.model_path.exists(),
            "model_loaded": self._model is not None,
            "target_language": "sd",
            "compute_type": "int8"
        }

    def convert_audio_to_wav16k(self, input_bytes: bytes, suffix: str = ".webm") -> Optional[Path]:
        """Convert any browser audio stream to 16kHz mono WAV using system ffmpeg."""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as in_file:
            in_file.write(input_bytes)
            in_path = Path(in_file.name)

        out_path = in_path.parent / f"proc_{in_path.stem}.wav"
        try:
            cmd = [
                "ffmpeg", "-y", "-i", str(in_path),
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                str(out_path)
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 44:
                return out_path
        except Exception as e:
            logger.warning("ffmpeg conversion failed: %s", e)
        finally:
            try:
                if in_path.exists():
                    in_path.unlink()
            except Exception:
                pass

        # Return original if ffmpeg failed but file exists
        return out_path if out_path.exists() else None

    def transcribe_audio_bytes(self, audio_bytes: bytes, file_ext: str = ".webm") -> Dict[str, Any]:
        """Transcribe speech audio bytes into normalized Sindhi text."""
        if not audio_bytes or len(audio_bytes) < 100:
            return {
                "success": False,
                "text_sindhi": "",
                "confidence": 0.0,
                "error": "آڊيو ڊيٽا ناڪافي آهي (Empty or too short audio)."
            }

        wav_path = self.convert_audio_to_wav16k(audio_bytes, suffix=file_ext)
        if not wav_path or not wav_path.exists():
            return {
                "success": False,
                "text_sindhi": "",
                "confidence": 0.0,
                "error": "آڊيو فارميٽ تبديل ڪرڻ ۾ ڏکيائي آئي (Audio conversion failed)."
            }

        try:
            model = self._get_model()
            if not model:
                return {
                    "success": False,
                    "text_sindhi": "",
                    "confidence": 0.0,
                    "error": "آواز جي سڃاڻپ وارو ماڊل دستياب ناهي (ASR model unavailable)."
                }

            segments, info = model.transcribe(
                str(wav_path),
                language="sd",
                task="transcribe",
                beam_size=2,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )

            text_parts = []
            for seg in segments:
                text_parts.append(seg.text.strip())

            raw_text = " ".join(text_parts).strip()
            # If Sindhi language model transcribed, normalize preserving Sindhi script
            clean_sindhi = normalize_sindhi_text(raw_text, strip_diacritics=False)

            if not clean_sindhi:
                return {
                    "success": False,
                    "text_sindhi": "",
                    "confidence": 0.0,
                    "error": "ڪو به آواز يا سنڌي لفظ سڃاڻپ نه ٿي سگهيو (No speech or intelligible words recognized)."
                }

            return {
                "success": True,
                "text_sindhi": clean_sindhi,
                "detected_language": info.language,
                "language_probability": round(float(info.language_probability), 3),
                "duration_seconds": round(float(info.duration), 2)
            }
        except Exception as e:
            logger.error("Transcription error: %s", e)
            return {
                "success": False,
                "text_sindhi": "",
                "confidence": 0.0,
                "error": f"ٽرانسڪرپشن دوران غلطي آئي: {str(e)}"
            }
        finally:
            try:
                if wav_path and wav_path.exists():
                    wav_path.unlink()
            except Exception:
                pass


sindhi_asr_service = SindhiASRService()
