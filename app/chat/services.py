"""
ChatService: FAQ検索からスタブAI回答・該当FAQなしへの状態遷移を統合する。
"""
import logging
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.chat.faq_types import FaqSearchResult
from app.chat.grounding import GroundingPolicy
from app.chat.schemas import ChatAnswerResponse, ChatSourceResponse, ChatStatus
from app.chat.settings import ChatSettings

logger = logging.getLogger(__name__)


class ChatService:
    """FAQ検索→根拠選択→スタブAI回答の状態遷移を統合するドメインサービス。"""

    def __init__(self, faq_search_service: object, grounding_policy: GroundingPolicy, settings: ChatSettings) -> None:
        self._faq_search = faq_search_service
        self._grounding = grounding_policy
        self._settings = settings

    def ask(self, db: Session, question: str) -> ChatAnswerResponse:
        """質問を受け取り、FAQ検索→根拠選択→回答生成を行い ChatAnswerResponse を返す。

        - 適合候補あり → ai_answer + 根拠1件
        - 適合候補なし → no_match + sources=[]
        - FAQ検索失敗・予期しない例外 → そのまま上位へ伝播（HTTP 500 委譲）
        - 通常ログに status・duration のみ記録し、質問全文・FAQ全文・回答全文は出力しない。
        """
        start = time.monotonic()

        # FAQ 検索（失敗時は例外をそのまま伝播）
        search_result: FaqSearchResult = self._faq_search.search(db, question, top_k=5)

        # 根拠選択
        selected = self._grounding.select(search_result)

        if selected:
            # 適合候補あり → スタブAI回答
            answer_text, sources = self._grounding.stub_answer(selected)
            status: ChatStatus = "ai_answer"
            source_responses = [
                ChatSourceResponse(
                    faq_id=s.faq_id,
                    question=s.question,
                    answer=s.answer,
                    confidence=s.confidence,
                )
                for s in sources
            ]
        else:
            # 適合候補なし → no_match
            answer_text = self._settings.contact_guidance
            status = "no_match"
            source_responses = []

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info("chat.ask status=%s duration_ms=%d", status, duration_ms)

        return ChatAnswerResponse(
            question=question,
            answer=answer_text,
            status=status,
            answered_at=datetime.now(timezone.utc),
            sources=source_responses,
        )
