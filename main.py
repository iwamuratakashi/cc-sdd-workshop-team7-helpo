import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.config import Settings
from app.db import DatabaseEngine
from app.logging_conf import configure_logging, log_exception
from app.router_registry import router_registry, include_registered_routers
from app.routers.pages import router as pages_router
from app.faq.router import router as faq_router
from app.faq.router import router as faq_router
from app.faq.dependencies import get_faq_search_index

logger = logging.getLogger(__name__)

# 下位機能ルーターを共有レジストリへ登録（import 順に登録される）
import app.auth  # noqa: F401  — AuthRouter を router_registry へ登録
import app.chat  # noqa: F401  — ChatRouter を router_registry へ登録


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    configure_logging(debug=settings.debug)
    engine = DatabaseEngine()
    engine.init(settings)
    # 研修用初期利用者シード
    from app.auth.seed import seed_initial_users
    db = engine.get_session()
    try:
        seed_initial_users(db)
    finally:
        db.close()
    yield


async def handle_exception(request: Request, exc: Exception):
    log_exception(exc, context={"path": str(request.url.path), "method": request.method})
    if request.url.path.startswith("/api"):
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
    return HTMLResponse("<h1>Internal Server Error</h1>", status_code=500)


def create_app() -> FastAPI:
    app = FastAPI(title="HELPO", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.add_exception_handler(Exception, handle_exception)
    # 共有レジストリをコピーしてから pages_router を追加（重複登録を防ぐ）
    from app.router_registry import RouterRegistry as _RR
    local_registry = _RR()
    for r, prefix, tags in router_registry._routers:
        local_registry.register_router(r, prefix, tags)
    local_registry.register_router(pages_router)
    local_registry.register_router(faq_router, tags=["FAQ"])
    include_registered_routers(app, local_registry)
    return app


app = create_app()
