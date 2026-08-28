from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {},
    )


@router.get("/history")
def history(request: Request):
    return templates.TemplateResponse(
        request,
        "history.html",
        {},
    )


# --- 下流機能が未実装の間の仮ルート ---
# local-user-authentication spec が実装されたら RouterRegistry 経由で上書きされる

@router.get("/login")
def login_placeholder(request: Request):
    return templates.TemplateResponse(
        request,
        "placeholder.html",
        {"page_title": "ログイン"},
    )


@router.get("/chat")
def chat_placeholder(request: Request):
    return templates.TemplateResponse(
        request,
        "placeholder.html",
        {"page_title": "質問（チャット）"},
    )


@router.get("/faqs/upload")
def faq_upload_placeholder(request: Request):
    return templates.TemplateResponse(
        request,
        "placeholder.html",
        {"page_title": "FAQ管理"},
    )
