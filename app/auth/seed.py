"""研修用初期利用者のシード（起動時に自動実行）。"""
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.password_hasher import PasswordHasher
from app.auth.repository import UserRepository

_SEED_USERS = [
    {"username": "user01", "password": "password", "role": "user"},
    {"username": "admin01", "password": "password", "role": "admin"},
]


def seed_initial_users(db: Session) -> None:
    """user01・admin01 が未登録の場合だけ作成する。既存利用者は変更しない。"""
    repo = UserRepository()
    hasher = PasswordHasher()
    for seed in _SEED_USERS:
        normalized = UserRepository.normalize_username(seed["username"])
        if repo.get_by_username(db, normalized) is not None:
            continue
        user = User(
            username=seed["username"],
            username_normalized=normalized,
            password_hash=hasher.hash(seed["password"]),
            role=seed["role"],
            is_active=True,
        )
        repo.create(db, user)
    db.commit()
