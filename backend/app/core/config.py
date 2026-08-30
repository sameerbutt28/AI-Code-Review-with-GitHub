"""
=============================================================================
CONFIGURATION
FILE: app/core/config.py

PURPOSE: Loads settings from the .env file.
All secret keys and limits are stored here (not hardcoded in code).
=============================================================================
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Runtime
    app_env: str = "development"  # development | demo | production
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    app_reload: bool = True

    # Secrets / model
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    github_webhook_secret: str = ""

    # CORS — include common local frontend ports for demos
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,http://localhost:3000"

    # Scan limits
    temp_clone_dir: str = "./temp_repos"
    max_files_to_scan: int = 50
    max_file_size_kb: int = 100
    chunk_max_chars: int = 14000
    chunk_max_files: int = 8

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_demo_or_production(self) -> bool:
        return self.app_env.lower() in {"demo", "production", "prod"}

    @property
    def should_reload(self) -> bool:
        if self.is_demo_or_production:
            return False
        return self.app_reload


settings = Settings()
