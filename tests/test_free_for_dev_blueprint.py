"""Tests for Free-for-Dev Infrastructure Blueprint & Ollama Integration.
Authored under agency-ai-engineer, agency-platform-engineer, and agency-api-platform-engineer.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import settings
from src.services.ai_provider import (
    OpenAICompatibleProvider,
    LocalTransformersAIProvider,
    get_ai_provider,
    get_ai_system_status
)


@pytest.fixture
def client():
    return TestClient(app)


class TestFreeForDevBlueprint:

    def test_ollama_provider_configuration(self):
        """Proof that ai_provider='ollama' correctly selects OpenAICompatibleProvider pointing to local Ollama."""
        with patch.object(settings, "ai_provider", "ollama"):
            provider = get_ai_provider()
            assert isinstance(provider, OpenAICompatibleProvider)
            assert provider.provider_type == "OPENAI_COMPATIBLE_LLM"
            assert "11434" in provider.endpoint_url
            assert provider.endpoint_url.endswith("/v1")

    def test_auto_provider_selection_ollama_probe(self):
        """Proof that ai_provider='auto' probes and selects Ollama when service responds."""
        fake_tags = json.dumps({"models": [{"name": "llama3.2:1b"}]}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = fake_tags
        mock_resp.__enter__.return_value = mock_resp

        with patch.object(settings, "ai_provider", "auto"), \
             patch("urllib.request.urlopen", return_value=mock_resp):
            provider = get_ai_provider()
            assert isinstance(provider, OpenAICompatibleProvider)
            assert provider.provider_type == "OPENAI_COMPATIBLE_LLM"
            assert provider.model_name == "llama3.2:1b"

    def test_comprehensive_status_endpoint(self, client):
        """Proof that /api/status returns valid system telemetry and Free-for-Dev readiness matrix."""
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "system_resources" in data
        assert "ram_total_gb" in data["system_resources"]
        assert "ram_available_gb" in data["system_resources"]
        assert "ai_engine" in data
        assert "free_for_dev_blueprint" in data
        
        blueprint = data["free_for_dev_blueprint"]
        assert "compute_tier" in blueprint
        assert "media_cdn" in blueprint
        assert "edge_database" in blueprint
        assert "tunneling" in blueprint
        assert "monitoring" in blueprint

    def test_media_cdn_fallback_redirect(self, client):
        """Proof that missing local media redirects to configured Cloudflare/B2 CDN URL with 307."""
        with patch.object(settings, "media_cdn_url", "https://media.sindhiclassroom.org"):
            resp = client.get("/static/media/missing_video_123.mp4", follow_redirects=False)
            assert resp.status_code == 307
            assert resp.headers["location"] == "https://media.sindhiclassroom.org/missing_video_123.mp4"

    def test_openai_compatible_grounded_inference(self):
        """Proof that OpenAICompatibleProvider executes grounded inference and parses choices."""
        provider = OpenAICompatibleProvider(
            endpoint_url="http://127.0.0.1:11434/v1",
            model_name="llama3.2:1b"
        )

        mock_reply = {
            "choices": [
                {
                    "message": {
                        "content": "خالي سيٽ اهو سيٽ آهي جنهن ۾ ڪوبه رڪن نه هوندو آهي۔"
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_reply).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = provider.generate_grounded_answer(
                "خالي سيٽ ڇا آهي؟",
                [{"topic_title_sd": "سيٽ", "summary_sd": "سيٽ رڪنن جو مجموعو آهي۔", "citation": "STBB VI"}]
            )
            assert res.is_live_inference is True
            assert res.inference_status == "REAL_LLM_INFERENCE"
            assert "خالي سيٽ" in res.text
            assert res.provider_type == "OPENAI_COMPATIBLE_LLM"
