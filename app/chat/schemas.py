from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator

ChatStatus = Literal["ai_answer", "no_match"]


class ChatQuestionRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 1:
            raise ValueError("質問を入力してください")
        return stripped


class ChatSourceResponse(BaseModel):
    faq_id: int
    question: str
    answer: str
    confidence: float


class ChatAnswerResponse(BaseModel):
    question: str
    answer: str
    status: ChatStatus
    answered_at: datetime
    sources: list[ChatSourceResponse]
