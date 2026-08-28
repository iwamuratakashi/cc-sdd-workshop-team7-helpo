from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.base_models import BaseEntity


class User(BaseEntity):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(128), nullable=False)
    username_normalized: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sessions: Mapped[list["AuthSession"]] = relationship(
        "AuthSession", back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(BaseEntity):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("idx_auth_sessions_user_id", "user_id"),
        Index("idx_auth_sessions_expires_at", "expires_at"),
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class LoginAttemptTracker(BaseEntity):
    __tablename__ = "login_attempt_trackers"

    tracker_token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
