from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # PostgreSQL
    DATABASE_URL: str  # asyncpg DSN  e.g. postgresql+asyncpg://user:pass@localhost/rce
    SYNC_DATABASE_URL: str  # psycopg2 DSN e.g. postgresql+psycopg2://user:pass@localhost/rce

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_RESULT_URL: str = "redis://localhost:6379/1"

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL_SECONDS: int = 86_400

    # Server-to-server auth (Next.js -> FastAPI)
    S2S_JWT_SECRET: str
    S2S_JWT_ALGORITHM: str = "HS256"
    S2S_JWT_ISSUER: str = "nextjs-auth"
    S2S_JWT_AUDIENCE: str = "fastapi-social"

    # Frontend/CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Email verification
    VERIFICATION_TOKEN_TTL_SECONDS: int = 86_400
    VERIFY_EMAIL_BASE_URL: str = "http://localhost:3000/verify-email"
    RESEND_API_KEY: str | None = None
    RESEND_FROM_EMAIL: str | None = None

    # Sandbox
    SANDBOX_BASE_DIR: str = "/sandbox/jobs"

    # WebSocket
    WS_TIMEOUT_SEC: int = 90
    PING_INTERVAL_SEC: int = 20

    # Rate Limit
    TOKEN_BUCKET_CAPACITY: float = 1.0
    TOKEN_BUCKET_REFILL_RATE: float = 0.5  # tokens per second
    SLIDING_WINDOW_MAX: int = 10
    SLIDING_WINDOW_SEC: int = 60

    # Output caps (bytes)
    STDOUT_CAP_BYTES: int = 102_400   # 100 KB
    STDERR_CAP_BYTES: int = 4_096    # 4 KB
    COMPILE_ERR_CAP_BYTES: int = 4_096


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_allowed_origins() -> list[str]:
    return [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
