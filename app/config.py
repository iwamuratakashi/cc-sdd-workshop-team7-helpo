from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./helpo.db"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    debug: bool = False
    local_llm_path: str | None = None
    local_embedding_path: str | None = None
