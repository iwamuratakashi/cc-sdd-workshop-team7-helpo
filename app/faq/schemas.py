"""FAQ API の Pydantic スキーマ定義。"""
from datetime import datetime
from pydantic import BaseModel, Field


class FaqRead(BaseModel):
    """FAQ 読み取り用スキーマ。"""
    id: int
    question: str
    answer: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FaqSearchQuery(BaseModel):
    """FAQ 検索リクエストスキーマ。"""
    query: str = Field(..., min_length=1, description="検索クエリ")
    top_k: int = Field(default=5, ge=1, le=20, description="取得件数")


class FaqCandidateSchema(BaseModel):
    """検索候補 1 件のレスポンススキーマ。"""
    faq_id: int
    question: str
    answer: str
    confidence: float
    is_match: bool


class FaqSearchResultSchema(BaseModel):
    """FAQ 検索結果のレスポンススキーマ。"""
    query: str
    candidates: list[FaqCandidateSchema]
    has_match: bool
