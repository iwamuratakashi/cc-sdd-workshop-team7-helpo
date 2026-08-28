import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User, AuthSession, LoginAttemptTracker


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------

class UserRepository:
    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    def get_by_username(self, db: Session, normalized_username: str) -> User | None:
        stmt = select(User).where(User.username_normalized == normalized_username)
        return db.execute(stmt).scalar_one_or_none()

    def create(self, db: Session, user: User) -> User:
        db.add(user)
        db.flush()
        db.refresh(user)
        return user

    @staticmethod
    def normalize_username(username: str) -> str:
        return username.strip().casefold()


# ---------------------------------------------------------------------------
# SessionRepository
# ---------------------------------------------------------------------------

class SessionRepository:
    def create(
        self,
        db: Session,
        user_id: int,
        token_digest: str,
        expires_at: datetime,
    ) -> AuthSession:
        session = AuthSession(
            user_id=user_id,
            token_digest=token_digest,
            expires_at=expires_at,
        )
        db.add(session)
        db.flush()
        db.refresh(session)
        return session

    def get_active(
        self, db: Session, token_digest: str, now: datetime
    ) -> AuthSession | None:
        stmt = (
            select(AuthSession)
            .where(AuthSession.token_digest == token_digest)
            .where(AuthSession.expires_at > now)
            .where(AuthSession.revoked_at.is_(None))
        )
        return db.execute(stmt).scalar_one_or_none()

    def revoke(self, db: Session, token_digest: str, now: datetime) -> bool:
        session = db.execute(
            select(AuthSession).where(AuthSession.token_digest == token_digest)
        ).scalar_one_or_none()
        if session is None:
            return False
        session.revoked_at = now
        db.flush()
        return True


# ---------------------------------------------------------------------------
# LoginAttemptRepository
# ---------------------------------------------------------------------------

class LoginAttemptRepository:
    def get_or_create(
        self, db: Session, tracker_token_digest: str, now: datetime
    ) -> LoginAttemptTracker:
        tracker = db.execute(
            select(LoginAttemptTracker).where(
                LoginAttemptTracker.tracker_token_digest == tracker_token_digest
            )
        ).scalar_one_or_none()
        if tracker is None:
            tracker = LoginAttemptTracker(
                tracker_token_digest=tracker_token_digest,
                failed_count=0,
                last_attempt_at=now,
            )
            db.add(tracker)
            db.flush()
            db.refresh(tracker)
        return tracker

    def record_failure(
        self,
        db: Session,
        tracker_token_digest: str,
        now: datetime,
        threshold: int,
        lockout_duration: timedelta,
    ) -> LoginAttemptTracker:
        tracker = self.get_or_create(db, tracker_token_digest, now)
        tracker.failed_count += 1
        tracker.last_attempt_at = now
        if tracker.failed_count >= threshold:
            tracker.locked_until = now + lockout_duration
        db.flush()
        return tracker

    def reset(self, db: Session, tracker_token_digest: str, now: datetime) -> None:
        tracker = db.execute(
            select(LoginAttemptTracker).where(
                LoginAttemptTracker.tracker_token_digest == tracker_token_digest
            )
        ).scalar_one_or_none()
        if tracker is not None:
            tracker.failed_count = 0
            tracker.locked_until = None
            tracker.last_attempt_at = now
            db.flush()


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def generate_token() -> str:
    """暗号学的に安全な乱数トークンを生成する。"""
    return secrets.token_urlsafe(32)


def digest_token(token: str) -> str:
    """トークンの SHA-256 ダイジェスト（16 進数文字列）を返す。DB 保存用。"""
    return hashlib.sha256(token.encode()).hexdigest()
