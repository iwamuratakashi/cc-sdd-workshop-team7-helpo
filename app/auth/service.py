from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.password_hasher import PasswordHasher
from app.auth.repository import (
    UserRepository,
    SessionRepository,
    generate_token,
    digest_token,
)
from app.auth.settings import AuthSettings


class InvalidCredentials(Exception):
    """認証失敗（理由を統合して列挙耐性を確保）。"""


@dataclass(frozen=True)
class IssuedSession:
    token: str
    expires_at: datetime


class AuthService:
    def __init__(self) -> None:
        self._user_repo = UserRepository()
        self._session_repo = SessionRepository()
        self._hasher = PasswordHasher()
        self._settings = AuthSettings()

    def login(self, db: Session, username: str, password: str) -> IssuedSession:
        """資格情報を検証してセッションを発行する。
        不明ユーザー・誤パスワード・無効ユーザーをすべて InvalidCredentials に統一する。
        """
        normalized = UserRepository.normalize_username(username)
        user: User | None = self._user_repo.get_by_username(db, normalized)

        if user is None or not user.is_active or not self._hasher.verify(password, user.password_hash):
            raise InvalidCredentials

        raw_token = generate_token()
        token_digest = digest_token(raw_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._settings.auth_session_ttl_seconds)

        self._session_repo.create(db, user.id, token_digest, expires_at)
        db.commit()
        return IssuedSession(token=raw_token, expires_at=expires_at)

    def logout(self, db: Session, token: str | None) -> None:
        """セッションを失効させる。冪等操作。トークンが不明・失効済みでも成功扱い。"""
        if token is None:
            return
        token_digest = digest_token(token)
        now = datetime.now(timezone.utc)
        self._session_repo.revoke(db, token_digest, now)
        db.commit()
