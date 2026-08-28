from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import get_current_user_optional
from app.auth.schemas import CurrentUser
from app.navigation.policy import NavLinkPolicy

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _nav_ctx(current: CurrentUser | None) -> dict:
    return {"header_menu_context": NavLinkPolicy().build(current)}


@router.get("/")
def index(
    request: Request,
    current: CurrentUser | None = Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        request, "index.html", _nav_ctx(current)
    )


@router.get("/history")
def history(request: Request):
    return templates.TemplateResponse(
        request,
        "history.html",
        {},
    )


# --- 下流機能が未実装の間の仮ルート ---
@router.get("/chat")
def chat_placeholder(
    request: Request,
    current: CurrentUser | None = Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        request, "placeholder.html", {"page_title": "質問（チャット）", **_nav_ctx(current)}
    )


@router.get("/faqs/upload")
def faq_upload_placeholder(
    request: Request,
    current: CurrentUser | None = Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        request, "placeholder.html", {"page_title": "FAQ管理", **_nav_ctx(current)}
    )
