from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "AutoBan"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://autoban:autoban_dev_password@localhost:5432/autoban"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # OAuth - GitHub
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    github_redirect_uri: str = "http://localhost:3002/auth/callback/github"

    # OAuth - Google
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:3002/auth/callback/google"

    # Agent Pool
    agent_pool_min_size: int = 2
    agent_pool_max_size: int = 10
    agent_heartbeat_interval: int = 30
    agent_workspace_path: str = "/workspaces"

    # AI Providers
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_ai_api_key: Optional[str] = None

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3002",
        "http://localhost:3000",
        "https://autoban.learnai.cz",
        "https://www.autoban.learnai.cz",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
