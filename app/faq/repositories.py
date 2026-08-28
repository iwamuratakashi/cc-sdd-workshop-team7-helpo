"""FAQ リポジトリ群。トランザクション境界は呼び出し元が管理する。"""
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.base_repository import BaseRepository
from app.faq.models import Faq, FaqEmbedding


class FaqRepository(BaseRepository[Faq]):
    """FAQ の永続化を担うリポジトリ。"""

    def __init__(self) -> None:
        super().__init__(Faq)

    def create(self, db: Session, question: str, answer: str) -> Faq:
        """FAQ を作成して返す。コミットは呼び出し元が行う。"""
        faq = Faq(question=question, answer=answer)
        return super().create(db, faq)

    def list_all(self, db: Session) -> list[Faq]:
        """全 FAQ を返す。"""
        return super().list(db)

    def get_by_id(self, db: Session, faq_id: int) -> Faq | None:
        """指定 ID の FAQ を返す。存在しない場合は None。"""
        return super().get(db, faq_id)


class FaqEmbeddingRepository(BaseRepository[FaqEmbedding]):
    """FaqEmbedding の永続化を担うリポジトリ。"""

    def __init__(self) -> None:
        super().__init__(FaqEmbedding)

    def upsert(self, db: Session, faq_id: int, dimension: int, vector: bytes) -> FaqEmbedding:
        """faq_id の Embedding をアップサート（存在すれば更新、なければ作成）する。"""
        stmt = select(FaqEmbedding).where(FaqEmbedding.faq_id == faq_id)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            existing.dimension = dimension
            existing.vector = vector
            db.flush()
            db.refresh(existing)
            return existing
        embedding = FaqEmbedding(faq_id=faq_id, dimension=dimension, vector=vector)
        return super().create(db, embedding)

    def load_all(self, db: Session) -> list[FaqEmbedding]:
        """全 FaqEmbedding を返す。"""
        return super().list(db)
