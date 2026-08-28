"""FAQ ドメインサービス群。

- FaqEmbeddingService: FAQ 登録時の Embedding 生成・保存・索引更新
- FaqSearchService: 類似検索・適合判定
- FaqAdminService: Markdown アップロードから FAQ 一括登録
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.faq.models import Faq, FaqEmbedding
from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
from app.faq.embedding import FaqEmbeddingAdapter, FaqEmbeddingError
from app.faq.search_index import FaqSearchIndex
from app.faq.markdown_parser import MarkdownParser, MarkdownParseError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 固定適合基準（実装所有の定数。MVPの実用検証後にコード変更として調整する）
# ---------------------------------------------------------------------------
_RELEVANCE_THRESHOLD = 0.75


# ---------------------------------------------------------------------------
# FaqEmbeddingService
# ---------------------------------------------------------------------------

class FaqEmbeddingService:
    """FAQ 登録時に Embedding を生成・保存・索引更新する。"""

    def __init__(
        self,
        adapter: FaqEmbeddingAdapter,
        repo: FaqEmbeddingRepository,
        index: FaqSearchIndex,
    ) -> None:
        self._adapter = adapter
        self._repo = repo
        self._index = index

    def generate_and_store(self, db: Session, faq: Faq) -> FaqEmbedding | None:
        """FAQ 質問文から Embedding を生成し、Repository と SearchIndex に upsert する。

        adapter.is_ready() が False の場合は何もせず None を返す。
        トランザクション境界は呼び出し元が管理する。
        """
        if not self._adapter.is_ready():
            logger.info(
                "FaqEmbeddingService: Embedding adapter not ready, skipping faq_id=%s", faq.id
            )
            return None

        vector = self._adapter.encode(faq.question)
        dimension = vector.shape[0]
        embedding = self._repo.upsert(db, faq.id, dimension, vector.tobytes())
        self._index.upsert(faq.id, vector)
        logger.info("FaqEmbeddingService: stored embedding for faq_id=%s dim=%s", faq.id, dimension)
        return embedding


# ---------------------------------------------------------------------------
# FaqSearchService
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FaqCandidate:
    """検索候補 1 件の DTO。"""
    faq_id: int
    question: str
    answer: str
    confidence: float   # 0.0〜1.0 に正規化・クランプした類似度
    is_match: bool      # confidence >= _RELEVANCE_THRESHOLD


@dataclass(frozen=True)
class FaqSearchResult:
    """類似検索結果 DTO。"""
    query: str
    candidates: list[FaqCandidate]
    has_match: bool     # candidates に is_match=True が 1 件以上あるか


class FaqSearchService:
    """類似検索と適合判定を行うサービス。"""

    def __init__(
        self,
        adapter: FaqEmbeddingAdapter,
        index: FaqSearchIndex,
        repo: FaqRepository,
    ) -> None:
        self._adapter = adapter
        self._index = index
        self._repo = repo

    def search(self, db: Session, query: str, top_k: int = 5) -> FaqSearchResult:
        """query に類似する FAQ を top_k 件返す。

        Raises:
            FaqEmbeddingError: adapter が未準備の場合（HTTP 503 にマップ）。
        """
        if not self._adapter.is_ready():
            raise FaqEmbeddingError(
                "Embedding モデルが準備できていません。FAQ 検索を利用できません。"
            )

        query_vector = self._adapter.encode(query)
        raw_results = self._index.search(query_vector, top_k)

        candidates: list[FaqCandidate] = []
        for faq_id, raw_score in raw_results:
            faq = self._repo.get_by_id(db, faq_id)
            if faq is None:
                continue
            confidence = max(0.0, min(1.0, (raw_score + 1.0) / 2.0))
            is_match = confidence >= _RELEVANCE_THRESHOLD
            candidates.append(FaqCandidate(
                faq_id=faq_id,
                question=faq.question,
                answer=faq.answer,
                confidence=confidence,
                is_match=is_match,
            ))

        has_match = any(c.is_match for c in candidates)
        logger.info(
            "FaqSearchService: query=%r top_k=%d hits=%d has_match=%s",
            query, top_k, len(candidates), has_match,
        )
        return FaqSearchResult(query=query, candidates=candidates, has_match=has_match)


# ---------------------------------------------------------------------------
# FaqAdminService
# ---------------------------------------------------------------------------

class FaqAdminService:
    """管理者向け FAQ 一括登録サービス。"""

    def __init__(
        self,
        repo: FaqRepository,
        parser: MarkdownParser,
        embedding_service: FaqEmbeddingService,
    ) -> None:
        self._repo = repo
        self._parser = parser
        self._embedding_service = embedding_service

    def import_faqs(self, db: Session, content: str) -> list[Faq]:
        """Markdown コンテンツを解析し、FAQ と Embedding を一括登録する。

        パースエラー、重複質問文、保存 0 件の場合はトランザクションを
        ロールバックして例外を送出する。

        Raises:
            MarkdownParseError: Markdown 形式エラー。
            ValueError: 重複質問文またはその他登録エラー。
        """
        pairs = self._parser.parse(content)  # MarkdownParseError は上位へ

        saved: list[Faq] = []
        existing_questions = {faq.question for faq in self._repo.list_all(db)}

        for question, answer in pairs:
            if question in existing_questions:
                db.rollback()
                raise ValueError(f"質問文「{question}」はすでに登録されています。")
            faq = self._repo.create(db, question=question, answer=answer)
            db.flush()
            self._embedding_service.generate_and_store(db, faq)
            saved.append(faq)
            existing_questions.add(question)

        if not saved:
            db.rollback()
            raise ValueError("保存できた FAQ が 0 件でした。")

        logger.info("FaqAdminService: imported %d FAQs", len(saved))
        return saved
