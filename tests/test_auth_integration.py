"""結合テスト: local-user-authentication HTTP フロー"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import DatabaseEngine
from app.migrations import MigrationRunner
from app.router_registry import RouterRegistry
import app.auth  # noqa: F401

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


@pytest.fixture(scope="function")
def app_client():
    """インメモリ SQLite でテスト用 FastAPI アプリを構築する。StaticPool で全接続を同一 DB に統一する。"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    MigrationRunner(engine, MIGRATIONS_DIR).apply_migrations()

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # DatabaseEngine シングルトンをリセットして差し替え
    DatabaseEngine.reset()
    db_engine = DatabaseEngine()
    db_engine.engine = engine
    db_engine.SessionLocal = TestSessionLocal
    db_engine._initialized = True

    # テスト用 app を生成（共有 router_registry を利用）
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates
    from app.router_registry import router_registry, include_registered_routers
    from app.routers.pages import router as pages_router
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(application):
        db = db_engine.get_session()
        try:
            from app.auth.seed import seed_initial_users
            seed_initial_users(db)
        finally:
            db.close()
        yield

    # router_registry に pages_router が重複登録されないようにコピーを使う
    from app.router_registry import RouterRegistry as _RR
    local_registry = _RR()
    for r, prefix, tags in router_registry._routers:
        local_registry.register_router(r, prefix, tags)
    local_registry.register_router(pages_router)

    test_app = FastAPI(lifespan=lifespan)
    from fastapi.staticfiles import StaticFiles
    test_app.mount("/static", StaticFiles(directory="app/static"), name="static")
    include_registered_routers(test_app, local_registry)

    from app.dependencies import get_db
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app, raise_server_exceptions=True) as client:
        yield client

    DatabaseEngine.reset()


# ---------------------------------------------------------------------------
# ログイン/ログアウト フロー
# ---------------------------------------------------------------------------

class TestAuthFlow:
    def test_login_success_redirects(self, app_client):
        r = app_client.post("/login", data={"username": "user01", "password": "password"}, follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/chat"
        assert "helpo_session" in r.cookies

    def test_login_wrong_password_400(self, app_client):
        r = app_client.post("/login", data={"username": "user01", "password": "wrong"}, follow_redirects=False)
        assert r.status_code == 400

    def test_login_unknown_user_400(self, app_client):
        r = app_client.post("/login", data={"username": "nobody", "password": "x"}, follow_redirects=False)
        assert r.status_code == 400

    def test_me_unauthenticated_401(self, app_client):
        r = app_client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_authenticated(self, app_client):
        app_client.post("/login", data={"username": "user01", "password": "password"})
        r = app_client.get("/api/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "user01"
        assert r.json()["role"] == "user"

    def test_logout_clears_session(self, app_client):
        app_client.post("/login", data={"username": "user01", "password": "password"})
        r = app_client.post("/logout", follow_redirects=False)
        assert r.status_code == 303
        r2 = app_client.get("/api/auth/me")
        assert r2.status_code == 401

    def test_admin_login(self, app_client):
        app_client.post("/login", data={"username": "admin01", "password": "password"})
        r = app_client.get("/api/auth/me")
        assert r.json()["role"] == "admin"

    def test_login_page_redirects_if_already_logged_in(self, app_client):
        app_client.post("/login", data={"username": "user01", "password": "password"})
        r = app_client.get("/login", follow_redirects=False)
        assert r.status_code == 303


# ---------------------------------------------------------------------------
# ブルートフォース対策
# ---------------------------------------------------------------------------

class TestBruteForce:
    def test_lockout_after_5_failures(self, app_client):
        for _ in range(5):
            app_client.post("/login", data={"username": "user01", "password": "wrong"})
        r = app_client.post("/login", data={"username": "user01", "password": "wrong"})
        assert r.status_code == 429

    def test_success_resets_counter(self, app_client):
        for _ in range(4):
            app_client.post("/login", data={"username": "user01", "password": "wrong"})
        # 正しいパスワードで成功
        app_client.post("/login", data={"username": "user01", "password": "password"})
        app_client.post("/logout")
        # カウントリセット済みなので次の失敗は 400（429 ではない）
        r = app_client.post("/login", data={"username": "user01", "password": "wrong"})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# シードユーザー
# ---------------------------------------------------------------------------

class TestSeedUsers:
    def test_user01_exists(self, app_client):
        r = app_client.post("/login", data={"username": "user01", "password": "password"}, follow_redirects=False)
        assert r.status_code == 303

    def test_admin01_exists(self, app_client):
        r = app_client.post("/login", data={"username": "admin01", "password": "password"}, follow_redirects=False)
        assert r.status_code == 303
