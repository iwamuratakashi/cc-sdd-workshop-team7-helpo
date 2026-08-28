from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import LoginAttemptTracker
from app.auth.repository import LoginAttemptRepository
from app.auth.settings import AuthSettings


class LoginAttemptGuard:
    """ブラウザ単位（tracker_token_digest）のログイン試行制限。
    追跡対象はユーザー名・IDではなく匿名の乱数ダイジェストとし、
    第三者による他アカウントへの DoS を防ぐ。
    """

    def __init__(self) -> None:
        self._repo = LoginAttemptRepository()
        self._settings = AuthSettings()

    def is_locked(self, db: Session, tracker_token_digest: str, now: datetime) -> bool:
        tracker = db.execute(
            select(LoginAttemptTracker).where(
                LoginAttemptTracker.tracker_token_digest == tracker_token_digest
            )
        ).scalar_one_or_none()
        if tracker is None:
            return False
        if tracker.locked_until is None:
            return False
        locked_until = tracker.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until > now

    def register_failure(self, db: Session, tracker_token_digest: str, now: datetime) -> None:
        lockout_duration = timedelta(seconds=self._settings.auth_lockout_duration_seconds)
        self._repo.record_failure(
            db,
            tracker_token_digest,
            now,
            self._settings.auth_lockout_threshold,
            lockout_duration,
        )
        db.commit()

    def register_success(self, db: Session, tracker_token_digest: str, now: datetime) -> None:
        self._repo.reset(db, tracker_token_digest, now)
        db.commit()
