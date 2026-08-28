from pathlib import Path
from sqlalchemy import Engine, text


class MigrationRunner:
    def __init__(self, engine: Engine, migrations_dir: Path):
        self.engine = engine
        self.migrations_dir = migrations_dir

    def _ensure_meta(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS foundation_meta (
                        schema_version VARCHAR(64) PRIMARY KEY,
                        applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

    def _applied_versions(self) -> set[str]:
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT schema_version FROM foundation_meta"))
            return {row[0] for row in result}

    def apply_migrations(self) -> None:
        self._ensure_meta()
        applied = self._applied_versions()
        if not self.migrations_dir.exists():
            return
        for sql_file in sorted(self.migrations_dir.glob("*.sql")):
            version = sql_file.stem
            if version in applied:
                continue
            sql = sql_file.read_text(encoding="utf-8")
            with self.engine.begin() as conn:
                for statement in sql.split(";"):
                    statement = statement.strip()
                    if not statement:
                        continue
                    conn.execute(text(statement))
                conn.execute(
                    text(
                        "INSERT INTO foundation_meta (schema_version, applied_at) VALUES (:v, CURRENT_TIMESTAMP)"
                    ),
                    {"v": version},
                )
