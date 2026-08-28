"""FAQ ルーター。

エンドポイント:
  POST /api/faqs/upload  — FAQ Markdown アップロード API（require_admin）
  POST /api/faqs/search  — FAQ 類似検索 API（require_authenticated_user）
  GET  /faqs/upload      — アップロード画面
  POST /faqs/upload      — アップロード処理（管理者のみ）
"""
import logging
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import require_admin, require_authenticated_user
from app.auth.schemas import CurrentUser
from app.faq.dependencies import get_faq_admin_service, get_faq_search_service
from app.faq.embedding import FaqEmbeddingError
from app.faq.markdown_parser import MarkdownParseError
from app.faq.schemas import FaqRead, FaqSearchQuery, FaqSearchResultSchema, FaqCandidateSchema
from app.faq.services import FaqAdminService, FaqSearchService
from app.faq.settings import FaqSettings

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

_FAQ_SETTINGS = FaqSettings()

# 受け入れる MIME タイプ
_ALLOWED_CONTENT_TYPES = {"text/markdown", "text/x-markdown", "application/octet-stream"}


def _validate_upload(file: UploadFile) -> bytes:
    """アップロードファイルの形式・サイズを検証して内容を返す。

    Raises:
        HTTPException: 415 (形式エラー)、413 (サイズ超過)
    """
    # 拡張子チェック
    if file.filename and not file.filename.lower().endswith(".md"):
        raise HTTPException(
            status_code=415,
            detail="Markdown ファイル（.md）のみアップロード可能です。",
        )
    content = file.file.read()
    if len(content) > _FAQ_SETTINGS.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"ファイルサイズは {_FAQ_SETTINGS.max_upload_size_bytes // 1024 // 1024}MB 以下にしてください。",
        )
    return content


# ---------------------------------------------------------------------------
# API エンドポイント
# ---------------------------------------------------------------------------

@router.post("/api/faqs/upload", response_model=list[FaqRead], status_code=201)
async def api_upload_faqs(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
    admin_service: FaqAdminService = Depends(get_faq_admin_service),
):
    """Markdown ファイルをアップロードして FAQ を一括登録する（管理者専用）。"""
    content_bytes = _validate_upload(file)
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="ファイルの文字エンコーディングが UTF-8 ではありません。",
        )

    try:
        saved_faqs = admin_service.import_faqs(db, content)
        db.commit()
    except MarkdownParseError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    logger.info("api_upload_faqs: user=%s uploaded %d FAQs, size=%d", current_user.username, len(saved_faqs), len(content_bytes))
    return [FaqRead.model_validate(f) for f in saved_faqs]


@router.post("/api/faqs/search", response_model=FaqSearchResultSchema)
async def api_search_faqs(
    query: FaqSearchQuery,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
    search_service: FaqSearchService = Depends(get_faq_search_service),
):
    """問い合わせテキストに類似する FAQ を検索する（認証済みユーザー専用）。"""
    try:
        result = search_service.search(db, query.query, top_k=query.top_k)
    except FaqEmbeddingError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return FaqSearchResultSchema(
        query=result.query,
        candidates=[
            FaqCandidateSchema(
                faq_id=c.faq_id,
                question=c.question,
                answer=c.answer,
                confidence=c.confidence,
                is_match=c.is_match,
            )
            for c in result.candidates
        ],
        has_match=result.has_match,
    )


# ---------------------------------------------------------------------------
# Web UI エンドポイント
# ---------------------------------------------------------------------------

@router.get("/faqs/upload", response_class=HTMLResponse)
async def get_faq_upload(
    request: Request,
    current_user: CurrentUser = Depends(require_admin),
):
    """FAQ アップロード画面を表示する（管理者専用）。"""
    return templates.TemplateResponse(request, "faq/upload.html", {})


@router.post("/faqs/upload", response_class=HTMLResponse)
async def post_faq_upload(
    request: Request,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
    admin_service: FaqAdminService = Depends(get_faq_admin_service),
):
    """FAQ Markdown ファイルをアップロードして登録する（管理者専用）。"""
    try:
        content_bytes = _validate_upload(file)
        content = content_bytes.decode("utf-8")
        saved_faqs = admin_service.import_faqs(db, content)
        db.commit()
        return templates.TemplateResponse(
            request, "faq/upload.html", {"success": len(saved_faqs)}
        )
    except HTTPException as e:
        db.rollback()
        return templates.TemplateResponse(
            request, "faq/upload.html", {"error": e.detail}, status_code=e.status_code
        )
    except (MarkdownParseError, ValueError) as e:
        db.rollback()
        return templates.TemplateResponse(
            request, "faq/upload.html", {"error": str(e)}, status_code=422
        )
