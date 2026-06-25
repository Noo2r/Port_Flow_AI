import secrets
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings

_DEV_SECRET = "changeme-in-production-use-a-64char-random-string"


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "PortFlow AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://portflow:portflow@db:5432/portflow"

    # ── Security / JWT ────────────────────────────────────────────────────────
    SECRET_KEY: str = _DEV_SECRET
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24          # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30                  # 30 days
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15              # 15 minutes

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins. Defaults to the local Vite dev
    # server — never "*", since the API is called with credentialed requests
    # (allow_credentials=True below) and browsers forbid combining a wildcard
    # origin with credentials in any case that matters (the server would be
    # reflecting any origin back, which is what made this exploitable before).
    # Example: CORS_ORIGINS=https://app.portflow.ai,https://admin.portflow.ai
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Email (SMTP) ──────────────────────────────────────────────────────────
    SMTP_HOST: str = ""                                  # empty = dev mode (console log)
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    SMTP_FROM_EMAIL: str = "noreply@portflow.ai"

    # ── Frontend (for reset links) ────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Storage / S3 ─────────────────────────────────────────────────────────
    S3_BACKUP_BUCKET: str = ""                           # empty = local only

    # ── AI Chatbot ───────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""                         # empty = rule-based fallback
    CHAT_MODEL: str = "claude-haiku-4-5-20251001"      # model used for chat responses

    # ── Log retention ─────────────────────────────────────────────────────────
    LOG_RETENTION_MONTHS: int = 12                       # SRS Privacy 9.3

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        if v == _DEV_SECRET:
            import os
            if not os.getenv("DEBUG", "false").lower() in ("1", "true"):
                raise ValueError(
                    "SECRET_KEY must be changed from the default in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """
        Parse CORS_ORIGINS into a list for use in CORSMiddleware.

        "*" is rejected here, not just discouraged in a comment — this app
        always sends credentialed requests (allow_credentials=True in
        main.py), and FastAPI's CORSMiddleware will reflect back whatever
        Origin header it receives when allow_origins=["*"] is combined with
        allow_credentials=True, which is exactly the misconfiguration that
        made every origin (including an attacker's) get a valid CORS grant
        in a live security audit of this project. Fail loudly instead of
        silently re-introducing it.
        """
        if self.CORS_ORIGINS.strip() == "*":
            raise ValueError(
                "CORS_ORIGINS=\"*\" is not allowed because this app sends "
                "credentialed requests — combined with allow_credentials=True, "
                "a wildcard origin gets reflected back to ANY caller, including "
                "a malicious one. Set CORS_ORIGINS to an explicit comma-separated "
                "list of origins instead, e.g. http://localhost:5173"
            )
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
