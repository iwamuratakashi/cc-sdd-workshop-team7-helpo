from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from app.config import Settings
from app.db import DatabaseEngine
from app.router_registry import RouterRegistry, include_registered_routers
from app.routers.pages import router as pages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    DatabaseEngine().init(Settings())
    yield


def handle_exception(request: Request, exc: Exception):
    if request.url.path.startswith("/api"):
        return JSONResponse({"detail": "Internal server error"}, status_code=500)
    return HTMLResponse("<h1>Internal Server Error</h1>", status_code=500)


def create_app() -> FastAPI:
    app = FastAPI(title="HELPO", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.add_exception_handler(Exception, handle_exception)
    registry = RouterRegistry()
    registry.register_router(pages_router)
    include_registered_routers(app, registry)
    return app


app = create_app()
