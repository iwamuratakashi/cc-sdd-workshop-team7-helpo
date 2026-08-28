from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """認証機能専用設定。foundation の Settings と共存し app/config.py を直接変更しない。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # セッション Cookie
    auth_session_cookie_name: str = "helpo_session"
    auth_session_ttl_seconds: int = 8 * 3600  # 8 時間
    auth_cookie_secure: bool = False  # ローカル HTTP 向けデフォルト

    # ログイン試行制限（ブルートフォース対策）
    auth_attempt_cookie_name: str = "helpo_login_attempt"
    auth_lockout_threshold: int = 5       # 連続失敗しきい値
    auth_lockout_duration_seconds: int = 900  # ロック期間 15 分
