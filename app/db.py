from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import Settings
from app.migrations import MigrationRunner


class DatabaseEngine:
    _instance: "DatabaseEngine | None" = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self, settings: Settings | None = None) -> None:
        if self._initialized:
            return
        self.settings = settings or Settings()
        self.engine = create_engine(
            self.settings.database_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        migrations_dir = Path(__file__).parent.parent / "migrations"
        MigrationRunner(self.engine, migrations_dir).apply_migrations()
        self._initialized = True

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._initialized = False

    def get_session(self):
        return self.SessionLocal()


def get_db_engine() -> DatabaseEngine:
    return DatabaseEngine()
