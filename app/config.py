from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # NOTE: This backend performs NO AI generation. The frontend dashboards own
    # all AI agents; the backend only stores/serves their results.
    database_url: str = "sqlite:///./skillflow.db"
    cors_origins: str = "*"

    # Auth
    jwt_secret: str = "dev-insecure-secret-change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 720

    # Report payload guardrail (chars of serialized JSON)
    max_report_payload_chars: int = 200000

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
