from typing import Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.base_models import BaseEntity

T = TypeVar("T", bound=BaseEntity)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T]):
        self._model = model

    def get(self, db: Session, id: int) -> T | None:
        return db.get(self._model, id)

    def list(self, db: Session) -> list[T]:
        return db.execute(select(self._model)).scalars().all()

    def create(self, db: Session, obj: T) -> T:
        db.add(obj)
        db.flush()
        db.refresh(obj)
        return obj

    def update(self, db: Session, obj: T) -> T:
        merged = db.merge(obj)
        db.flush()
        db.refresh(merged)
        return merged

    def delete(self, db: Session, obj: T) -> None:
        db.delete(obj)
        db.flush()
