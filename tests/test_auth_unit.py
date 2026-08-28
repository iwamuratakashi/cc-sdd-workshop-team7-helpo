"""単体テスト: local-user-authentication コンポーネント"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.auth.password_hasher import PasswordHasher
from app.auth.schemas import CurrentUser
from app.auth.repository import (
    UserRepository,
    SessionRepository,
    LoginAttemptRepository,
    generate_token,
    digest_token,
)
from app.auth.lockout import LoginAttemptGuard
from app.auth.dependencies import require_authenticated_user, require_admin, require_owner


# ---------------------------------------------------------------------------
# PasswordHasher
# ---------------------------------------------------------------------------

class TestPasswordHasher:
    def setup_method(self):
        self.hasher = PasswordHasher()

    def test_same_password_verifies(self):
        h = self.hasher.hash("secret")
        assert self.hasher.verify("secret", h) is True

    def test_wrong_password_fails(self):
        h = self.hasher.hash("secret")
        assert self.hasher.verify("wrong", h) is False

    def test_hash_does_not_store_plaintext(self):
        h = self.hasher.hash("secret")
        assert "secret" not in h

    def test_invalid_hash_returns_false(self):
        assert self.hasher.verify("any", "not-a-valid-hash") is False


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------

class TestUserRepository:
    def test_normalize_username_strips_and_caseolds(self):
        assert UserRepository.normalize_username("  Alice  ") == "alice"
        assert UserRepository.normalize_username("USER01") == "user01"


# ---------------------------------------------------------------------------
# digest_token
# ---------------------------------------------------------------------------

class TestDigestToken:
    def test_same_input_same_digest(self):
        t = generate_token()
        assert digest_token(t) == digest_token(t)

    def test_different_tokens_different_digests(self):
        assert digest_token(generate_token()) != digest_token(generate_token())

    def test_digest_is_64_chars(self):
        assert len(digest_token("x")) == 64


# ---------------------------------------------------------------------------
# LoginAttemptGuard (DB をモック)
# ---------------------------------------------------------------------------

class TestLoginAttemptGuard:
    def _make_db(self):
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = None
        return db

    def test_no_tracker_not_locked(self):
        guard = LoginAttemptGuard()
        db = self._make_db()
        now = datetime.now(timezone.utc)
        assert guard.is_locked(db, "digest", now) is False

    def test_locked_until_future_is_locked(self):
        guard = LoginAttemptGuard()
        from app.auth.models import LoginAttemptTracker
        tracker = MagicMock(spec=LoginAttemptTracker)
        tracker.locked_until = datetime.now(timezone.utc) + timedelta(minutes=5)
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = tracker
        now = datetime.now(timezone.utc)
        assert guard.is_locked(db, "digest", now) is True

    def test_locked_until_past_is_not_locked(self):
        guard = LoginAttemptGuard()
        from app.auth.models import LoginAttemptTracker
        tracker = MagicMock(spec=LoginAttemptTracker)
        tracker.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = tracker
        now = datetime.now(timezone.utc)
        assert guard.is_locked(db, "digest", now) is False


# ---------------------------------------------------------------------------
# AuthorizationPolicy (FastAPI HTTPException を確認)
# ---------------------------------------------------------------------------

class TestAuthorizationPolicy:
    def test_require_authenticated_user_raises_if_none(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            require_authenticated_user(None)
        assert exc_info.value.status_code == 401

    def test_require_authenticated_user_passes_current(self):
        user = CurrentUser(id=1, username="u", role="user")
        assert require_authenticated_user(user) == user

    def test_require_admin_raises_for_user_role(self):
        from fastapi import HTTPException
        user = CurrentUser(id=1, username="u", role="user")
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        assert exc_info.value.status_code == 403

    def test_require_admin_passes_for_admin_role(self):
        admin = CurrentUser(id=2, username="a", role="admin")
        assert require_admin(admin) == admin

    def test_require_owner_raises_if_different(self):
        from fastapi import HTTPException
        user = CurrentUser(id=1, username="u", role="user")
        with pytest.raises(HTTPException) as exc_info:
            require_owner(user, 99)
        assert exc_info.value.status_code == 403

    def test_require_owner_passes_if_same(self):
        user = CurrentUser(id=1, username="u", role="user")
        require_owner(user, 1)  # raises なし
