"""
chat feature-local FastAPI 依存。
get_chat_service が ChatService に FaqMockSearchService・GroundingPolicy・ChatSettings を注入する。
"""
from app.chat.faq_mock import FaqMockSearchService
from app.chat.grounding import GroundingPolicy
from app.chat.services import ChatService
from app.chat.settings import ChatSettings


def get_chat_service() -> ChatService:
    """ChatService のインスタンスを生成して返す FastAPI 依存関数。

    検索サービスは現時点で FaqMockSearchService を注入する。
    faq-management-and-search 実装後は差し替えるだけでよい。
    """
    return ChatService(
        faq_search_service=FaqMockSearchService(),
        grounding_policy=GroundingPolicy(),
        settings=ChatSettings(),
    )
