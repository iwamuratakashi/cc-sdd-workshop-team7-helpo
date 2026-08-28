import os
import pytest
from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column
from fastapi.testclient import TestClient
from app.base_models import Base, BaseEntity
from app.base_repository import BaseRepository
from app.config import Settings
from app.db import DatabaseEngine
from main import create_app


class SampleItem(BaseEntity):
    __tablename__ = "sample_items"
    name: Mapped[str] = mapped_column(String(64))


@pytest.fixture
def db_session():
    DatabaseEngine.reset()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    DatabaseEngine().init(Settings())
    Base.metadata.create_all(DatabaseEngine().engine)
    session = DatabaseEngine().SessionLocal()
    yield session
    session.close()
    DatabaseEngine.reset()


def test_config_defaults():
    settings = Settings()
    assert settings.database_url == "sqlite:///./helpo.db"
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 8000
    assert settings.debug is False


def test_baseline_migration_creates_meta():
    DatabaseEngine.reset()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    DatabaseEngine().init(Settings())
    with DatabaseEngine().engine.connect() as conn:
        result = conn.execute(text("SELECT schema_version FROM foundation_meta"))
        versions = {row[0] for row in result}
    assert "001_baseline" in versions


def test_base_repository_crud(db_session):
    repo = BaseRepository(SampleItem)
    item = SampleItem(name="hello")
    created = repo.create(db_session, item)
    db_session.commit()

    assert created.id is not None
    fetched = repo.get(db_session, created.id)
    assert fetched is not None
    assert fetched.name == "hello"

    listed = repo.list(db_session)
    assert len(listed) == 1

    created.name = "updated"
    updated = repo.update(db_session, created)
    db_session.commit()
    assert updated.name == "updated"

    repo.delete(db_session, updated)
    db_session.commit()
    assert repo.get(db_session, created.id) is None


def test_root_page():
    DatabaseEngine.reset()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "HELPO" in response.text


def test_unhandled_api_exception_returns_500_json():
    DatabaseEngine.reset()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app()

    @app.get("/api/error")
    def error():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/error")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def test_unhandled_html_exception_returns_500_html():
    DatabaseEngine.reset()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app()

    @app.get("/error")
    def error():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/error")
    assert response.status_code == 500
    assert "Internal Server Error" in response.text
