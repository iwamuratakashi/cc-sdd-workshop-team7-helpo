"""FAQ 固有の FastAPI 依存関数。

SearchIndex と各サービスのアプリケーション生存期間（シングルトン）管理を担う。
"""
from functools import lru_cache
from app.config import Settings
from app.faq.embedding import FaqEmbeddingAdapter
from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
from app.faq.search_index import FaqSearchIndex
from app.faq.markdown_parser import MarkdownParser
from app.faq.services import FaqEmbeddingService, FaqSearchService, FaqAdminService


@lru_cache(maxsize=1)
def get_faq_embedding_adapter() -> FaqEmbeddingAdapter:
    """アプリ生存期間でシングルトンの FaqEmbeddingAdapter を返す。"""
    settings = Settings()
    return FaqEmbeddingAdapter(model_path=settings.local_embedding_path)


@lru_cache(maxsize=1)
def get_faq_search_index() -> FaqSearchIndex:
    """アプリ生存期間でシングルトンの FaqSearchIndex を返す。"""
    return FaqSearchIndex()


def get_faq_admin_service() -> FaqAdminService:
    """FaqAdminService のインスタンスを返す。"""
    adapter = get_faq_embedding_adapter()
    emb_svc = FaqEmbeddingService(
        adapter=adapter,
        repo=FaqEmbeddingRepository(),
        index=get_faq_search_index(),
    )
    return FaqAdminService(
        repo=FaqRepository(),
        parser=MarkdownParser(),
        embedding_service=emb_svc,
    )


def get_faq_search_service() -> FaqSearchService:
    """FaqSearchService のインスタンスを返す。"""
    return FaqSearchService(
        adapter=get_faq_embedding_adapter(),
        index=get_faq_search_index(),
        repo=FaqRepository(),
    )
