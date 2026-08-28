from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_optional, require_authenticated_user
from app.auth.lockout import LoginAttemptGuard
from app.auth.repository import generate_token, digest_token
from app.auth.schemas import CurrentUser
from app.auth.service import AuthService, InvalidCredentials
from app.auth.settings import AuthSettings
from app.dependencies import get_db
from app.navigation.policy import NavLinkPolicy

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")
_settings = AuthSettings()
_guard = LoginAttemptGuard()
_service = AuthService()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_settings.auth_session_cookie_name,
        value=token,
        max_age=_settings.auth_session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=_settings.auth_cookie_secure,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_settings.auth_session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_settings.auth_cookie_secure,
    )


def _get_or_issue_attempt_cookie(request: Request, response: Response) -> str:
    """試行追跡 Cookie（匿名乱数トークン）を取得または新規発行する。DB にはダイジェストのみ保存。"""
    raw = request.cookies.get(_settings.auth_attempt_cookie_name)
    if not raw:
        raw = generate_token()
        response.set_cookie(
            key=_settings.auth_attempt_cookie_name,
            value=raw,
            max_age=_settings.auth_lockout_duration_seconds * 10,
            httponly=True,
            samesite="lax",
            secure=_settings.auth_cookie_secure,
            path="/",
        )
    return raw


# ---------------------------------------------------------------------------
# GET /login
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current: CurrentUser | None = Depends(get_current_user_optional),
):
    if current is not None:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    ctx = NavLinkPolicy().build(current)
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"error": None, "header_menu_context": ctx, "hide_login_link": True},
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    response = Response()
    attempt_raw = _get_or_issue_attempt_cookie(request, response)
    attempt_digest = digest_token(attempt_raw)
    now = datetime.now(timezone.utc)
    _nav_ctx = NavLinkPolicy().build(None)

    # ロック中チェック
    if _guard.is_locked(db, attempt_digest, now):
        html = templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "error": "too_many_attempts",
                "header_menu_context": _nav_ctx,
                "hide_login_link": True,
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        html.set_cookie(
            key=_settings.auth_attempt_cookie_name,
            value=attempt_raw,
            max_age=_settings.auth_lockout_duration_seconds * 10,
            httponly=True,
            samesite="lax",
            secure=_settings.auth_cookie_secure,
            path="/",
        )
        return html

    # 認証
    try:
        issued = _service.login(db, username, password)
    except InvalidCredentials:
        _guard.register_failure(db, attempt_digest, now)
        html = templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "error": "invalid_credentials",
                "header_menu_context": _nav_ctx,
                "hide_login_link": True,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
        html.set_cookie(
            key=_settings.auth_attempt_cookie_name,
            value=attempt_raw,
            max_age=_settings.auth_lockout_duration_seconds * 10,
            httponly=True,
            samesite="lax",
            secure=_settings.auth_cookie_secure,
            path="/",
        )
        return html

    # 認証成功
    _guard.register_success(db, attempt_digest, now)
    redirect = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(redirect, issued.token)
    return redirect


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@router.post("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(_settings.auth_session_cookie_name)
    _service.logout(db, token)
    redirect = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    _clear_session_cookie(redirect)
    return redirect


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@router.get("/api/auth/me")
async def me(current: CurrentUser = Depends(require_authenticated_user)):
    return JSONResponse({"id": current.id, "username": current.username, "role": current.role})
