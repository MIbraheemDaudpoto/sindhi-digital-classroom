"""Application configuration for Sindhi Digital Classroom (SDC).
Authored under agency-backend-architect.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sindhi Digital Classroom (SDC)"
    environment: str = "development"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8001
    secret_key: str = "sdc-dev-secret-key-2026"
    cors_allowed_origins: str = ""

    # Database
    database_path: str = "data/sdc_platform.db"

    # Storage & Uploads
    media_root: str = "media"
    offline_packs_root: str = "media/offline_packs"

    # Smart Video Quiz rules
    min_quiz_popup_interval_seconds: int = 120
    max_quiz_popup_interval_seconds: int = 180

    # Security & Tokens
    session_expiry_seconds: int = 86400  # 24 hours
    password_reset_token_expiry_seconds: int = 600  # 10 minutes
    allow_test_query_auth: bool = False  # Strictly False: no query parameter bypass
    active_pilot_roles: list[str] = ["STUDENT", "SUPER_ADMIN"]  # Only STUDENT and SUPER_ADMIN active for pilot
    admin_username: str = "superadmin"
    admin_password: str = ""

    # SMS Gateway Configuration (Pakistan OTP)
    sms_provider: str = "mock"  # "mock", "twilio", "pakistan_http"
    sms_api_key: str = ""
    sms_api_secret: str = ""
    sms_sender_id: str = "SDC-Alert"
    sms_endpoint_url: str = ""
    otp_expiry_seconds: int = 300  # 5 minutes
    otp_max_attempts: int = 3
    otp_resend_cooldown_seconds: int = 60

    # AI Tutor & LLM Configuration
    ai_provider: str = "auto"  # "auto" (Ollama -> safe fast local fallback), "neural", "ollama", "local"
    ai_model_name: str = "sdc-sindhillm-1b-science"
    local_model_dir: str = "models/sdc-sindhillm-1b-science"
    gguf_model_path: str = "models/sdc-sindhillm-1b-science-q4_k_m.gguf"
    hf_api_token: str = ""
    ai_api_key: str = ""
    ai_endpoint_url: str = ""
    ai_inference_timeout_seconds: float = 30.0
    grounding_confidence_threshold: float = 0.65
    ollama_endpoint_url: str = "http://127.0.0.1:11434/v1"
    ollama_default_model: str = "llama3.2:1b"

    # Free-for-Dev Infrastructure & Cloudflare CDN
    media_cdn_url: str = ""  # e.g., "https://media.sindhiclassroom.org" or Backblaze B2 via Cloudflare
    database_url: str = ""   # e.g., for Turso "libsql://..." or PostgreSQL "postgresql://..."
    sentry_dsn: str = ""     # e.g., for Sentry error monitoring
    better_stack_heartbeat_url: str = ""  # e.g., for Better Stack uptime monitoring

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_otp_per_minute: int = 5
    rate_limit_login_per_minute: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_db_path(self) -> Path:
        p = Path(self.database_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def get_cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    def validate_production_settings(self) -> None:
        if self.environment.lower() != "production":
            return
        if len(self.secret_key) < 32 or self.secret_key == "sdc-dev-secret-key-2026":
            raise RuntimeError("Production requires a unique SECRET_KEY of at least 32 characters.")
        origins = self.get_cors_origins()
        if "*" in origins:
            raise RuntimeError("Production CORS must list explicit origins; wildcard origins are not allowed.")


settings = Settings()
