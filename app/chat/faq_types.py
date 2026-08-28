from dataclasses import dataclass


@dataclass(frozen=True)
class FaqCandidate:
    """FAQ検索の1件の候補。上流 faq-management-and-search との型契約。"""

    faq_id: int
    question: str
    answer: str
    confidence: float
    is_match: bool


@dataclass(frozen=True)
class FaqSearchResult:
    """FAQ検索の結果。上流 faq-management-and-search との型契約。"""

    query: str
    candidates: tuple[FaqCandidate, ...]
    has_match: bool
