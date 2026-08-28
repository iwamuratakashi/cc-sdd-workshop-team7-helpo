"""
ChatRouter: GET /chat (HTML) と POST /api/chat (JSON) を提供する。
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_optional, require_authenticated_user
from app.auth.schemas import CurrentUser
from app.chat.dependencies import get_chat_service
from app.chat.schemas import ChatAnswerResponse, ChatQuestionRequest
from app.chat.services import ChatService
from app.chat.settings import ChatSettings
from app.dependencies import get_db
from app.navigation.policy import NavLinkPolicy

router = APIRouter(tags=["chat"])
templates = Jinja2Templates(directory="app/templates")
_settings = ChatSettings()


def _nav_ctx(current: CurrentUser | None) -> dict:
    return {"header_menu_context": NavLinkPolicy().build(current)}


@router.get("/chat")
def chat_page(
    request: Request,
    current: CurrentUser | None = Depends(get_current_user_optional),
):
    """チャット画面を返す。未認証時は /login へ 303 リダイレクト。"""
    if current is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request,
        "chat/index.html",
        {
            "current_user": current,
            "max_question_chars": _settings.max_question_chars,
            "server_error_message": _settings.server_error_message,
            **_nav_ctx(current),
        },
    )


@router.post("/api/chat", response_model=ChatAnswerResponse)
def chat_ask(
    body: ChatQuestionRequest,
    db: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
    current: CurrentUser = Depends(require_authenticated_user),
):
    """質問を受け取り AI 回答を返す。

    - 認証必須（未認証は 401）
    - question は trim 後 1〜max_question_chars 文字（超過は 422）
    - 成功は HTTP 200 (ai_answer / no_match)
    - FAQ 検索失敗・予期しないエラーは HTTP 500
    """
    question = body.question.strip()
    if len(question) > _settings.max_question_chars:
        return JSONResponse(
            {"detail": f"質問は{_settings.max_question_chars}文字以内で入力してください"},
            status_code=422,
        )

    result = chat_service.ask(db=db, question=question)
    return result
