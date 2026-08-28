"""FAQ ドメインモデル（SQLAlchemy ORM）。"""
from sqlalchemy import Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.base_models import BaseEntity


class Faq(BaseEntity):
    """FAQ エンティティ。質問文と回答文を保持する。"""

    __tablename__ = "faq"

    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    embedding: Mapped["FaqEmbedding | None"] = relationship(
        "FaqEmbedding", back_populates="faq", cascade="all, delete-orphan", uselist=False
    )


class FaqEmbedding(BaseEntity):
    """FAQ 質問文の Embedding ベクトルを保持するエンティティ。"""

    __tablename__ = "faq_embedding"

    faq_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("faq.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[bytes] = mapped_column(nullable=False)

    faq: Mapped["Faq"] = relationship("Faq", back_populates="embedding")
