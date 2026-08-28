from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.repository import SessionRepository, UserRepository, digest_token
from app.auth.schemas import CurrentUser
from app.dependencies import get_db


def get_current_user_optional(
    request_cookie: str | None = Cookie(default=None, alias="helpo_session"),
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    """セッション Cookie から現在利用者を解決する。未ログイン・失効時は None を返す。"""
    if request_cookie is None:
        return None
    token_digest = digest_token(request_cookie)
    now = datetime.now(timezone.utc)
    session = SessionRepository().get_active(db, token_digest, now)
    if session is None:
        return None
    user = UserRepository().get_by_id(db, session.user_id)
    if user is None or not user.is_active:
        return None
    return CurrentUser(id=user.id, username=user.username, role=user.role)  # type: ignore[arg-type]


def require_authenticated_user(
    current: CurrentUser | None = Depends(get_current_user_optional),
) -> CurrentUser:
    """認証済み利用者を要求する。未認証なら 401 を返す。"""
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current


def require_admin(
    current: CurrentUser = Depends(require_authenticated_user),
) -> CurrentUser:
    """管理者ロールを要求する。ロール不足なら 403 を返す。"""
    if current.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return current


def require_owner(current: CurrentUser, owner_user_id: int) -> None:
    """本人所有を確認する。不一致なら 403 を raise する。admin バイパスなし。"""
    if current.id != owner_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
