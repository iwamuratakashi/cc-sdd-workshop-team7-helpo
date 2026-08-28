"""
GroundingPolicy: FAQ根拠の選択とスタブAI回答生成を担う。

タスク 2.1: select() — is_match=True の候補だけを confidence DESC, faq_id ASC で安定ソート。
タスク 2.2: stub_answer() — 先頭候補の answer 末尾に「（AIによる回答予定）」を付加し、
            その1件だけを根拠として返す。
"""
from app.chat.faq_types import FaqCandidate, FaqSearchResult

_STUB_SUFFIX = "（AIによる回答予定）"


class GroundingPolicy:
    """FAQ根拠の選択と回答生成ポリシーを実装するドメインサービス。"""

    def select(self, result: FaqSearchResult) -> list[FaqCandidate]:
        """has_match=True かつ is_match=True の候補を confidence DESC, faq_id ASC で安定ソートして返す。

        - is_match=False の候補は選択結果に含めない。
        - has_match=False の場合は空リストを返す。
        - 外部文書・会話履歴は一切含めない（FaqSearchResult 型のみを入力とする）。
        """
        if not result.has_match:
            return []
        matched = [c for c in result.candidates if c.is_match]
        return sorted(matched, key=lambda c: (-c.confidence, c.faq_id))

    def stub_answer(self, selected: list[FaqCandidate]) -> tuple[str, list[FaqCandidate]]:
        """スタブAI回答を生成する。

        適合候補の先頭1件の answer 末尾に「（AIによる回答予定）」を付加した
        テキストを回答として返し、その1件だけを根拠として返す。

        Returns:
            (answer_text, sources) — sources は根拠として使用した候補1件のみのリスト。
        """
        if not selected:
            raise ValueError("stub_answer には少なくとも1件の適合候補が必要です")
        top = selected[0]
        answer = top.answer + _STUB_SUFFIX
        return answer, [top]
