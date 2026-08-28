"""
FaqMockSearchService: faq-management-and-search が未実装の間使用するモック実装。
上流実装が完成したら ChatService の依存注入で差し替える。
"""
from app.chat.faq_types import FaqCandidate, FaqSearchResult

_MOCK_FAQS: list[FaqCandidate] = [
    FaqCandidate(
        faq_id=1,
        question="年次有給休暇の申請方法を教えてください",
        answer="社内ポータルの「休暇申請」メニューから申請できます。申請は取得希望日の3営業日前までに行ってください。",
        confidence=0.95,
        is_match=True,
    ),
    FaqCandidate(
        faq_id=2,
        question="経費精算の締め日はいつですか",
        answer="経費精算の締め日は毎月末日です。翌月5日までに経理部へ提出してください。",
        confidence=0.92,
        is_match=True,
    ),
    FaqCandidate(
        faq_id=3,
        question="慶弔見舞金の支給条件を教えてください",
        answer="慶弔見舞金は就業規則第20条に基づき支給されます。結婚・出産・忌引きの場合は人事部へ申請してください。",
        confidence=0.88,
        is_match=True,
    ),
    FaqCandidate(
        faq_id=4,
        question="健康診断はいつ受ければよいですか",
        answer="定期健康診断は毎年4〜6月に実施されます。日程は総務部から案内メールが届きます。",
        confidence=0.85,
        is_match=True,
    ),
    FaqCandidate(
        faq_id=5,
        question="リモートワーク申請の手続きを教えてください",
        answer="リモートワーク申請は上長の承認後、社内ポータルの「勤怠管理」から登録してください。",
        confidence=0.82,
        is_match=True,
    ),
]


class FaqMockSearchService:
    """固定FAQデータを返すモック検索サービス。

    ChatService は型（FaqSearchResult / FaqCandidate）にのみ依存するため、
    このクラスを本物の FaqSearchService に差し替えるだけで動作する。
    """

    def search(self, db: object, query: str, top_k: int = 5) -> FaqSearchResult:
        """query 文字列に部分一致する候補を返す。一致がなければ has_match=False。"""
        matched = [
            faq for faq in _MOCK_FAQS
            if any(word in faq.question or word in faq.answer for word in query.split())
        ]
        if not matched:
            return FaqSearchResult(query=query, candidates=tuple(_MOCK_FAQS[:top_k]), has_match=False)
        return FaqSearchResult(
            query=query,
            candidates=tuple(matched[:top_k]),
            has_match=True,
        )
