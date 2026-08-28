from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalAISettings(BaseModel):
    """ローカルAIモデルの設定を保持する型。"""

    llm_path: str | None = None
    embedding_path: str | None = None


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

    def get_database_url(self) -> str:
        """データベース接続URLを返す。"""
        return self.database_url

    def get_local_ai_settings(self) -> LocalAISettings | None:
        """ローカルAI設定を返す。どちらのパスも未設定の場合は None を返す。"""
        if self.local_llm_path is None and self.local_embedding_path is None:
            return None
        return LocalAISettings(
            llm_path=self.local_llm_path,
            embedding_path=self.local_embedding_path,
        )
