"""
タスク 5.1: GroundingPolicy のユニットテスト。
- 安定根拠選択（confidence DESC, faq_id ASC）
- is_match=False 候補の排除
- スタブ文言付加
- 使用根拠の絞り込み（先頭1件のみ）
"""
import pytest
from app.chat.faq_types import FaqCandidate, FaqSearchResult
from app.chat.grounding import GroundingPolicy


def _make_candidate(faq_id: int, confidence: float, is_match: bool = True) -> FaqCandidate:
    return FaqCandidate(
        faq_id=faq_id,
        question=f"質問{faq_id}",
        answer=f"回答{faq_id}",
        confidence=confidence,
        is_match=is_match,
    )


def _make_result(candidates: list[FaqCandidate], has_match: bool) -> FaqSearchResult:
    return FaqSearchResult(
        query="test",
        candidates=tuple(candidates),
        has_match=has_match,
    )


@pytest.fixture
def policy():
    return GroundingPolicy()


# ===== select() テスト =====

class TestGroundingPolicySelect:
    def test_select_returns_only_is_match_true(self, policy):
        """is_match=False の候補が選択結果に含まれないこと。"""
        candidates = [
            _make_candidate(1, 0.9, is_match=True),
            _make_candidate(2, 0.8, is_match=False),
            _make_candidate(3, 0.7, is_match=True),
        ]
        result = _make_result(candidates, has_match=True)
        selected = policy.select(result)
        ids = [c.faq_id for c in selected]
        assert 2 not in ids
        assert set(ids) == {1, 3}

    def test_select_stable_sort_confidence_desc_faq_id_asc(self, policy):
        """confidence 降順・faq_id 昇順で安定ソートされること。"""
        candidates = [
            _make_candidate(4, 0.7),
            _make_candidate(2, 0.9),
            _make_candidate(1, 0.9),
            _make_candidate(3, 0.7),
        ]
        result = _make_result(candidates, has_match=True)
        selected = policy.select(result)
        ids = [c.faq_id for c in selected]
        assert ids == [1, 2, 3, 4]  # confidence 0.9: [1,2], confidence 0.7: [3,4]

    def test_select_returns_empty_when_has_match_false(self, policy):
        """has_match=False のとき空リストを返すこと。"""
        candidates = [_make_candidate(1, 0.9)]
        result = _make_result(candidates, has_match=False)
        assert policy.select(result) == []

    def test_select_returns_empty_when_no_is_match_true(self, policy):
        """has_match=True でも is_match=True の候補がなければ空リストを返すこと。"""
        candidates = [
            _make_candidate(1, 0.9, is_match=False),
            _make_candidate(2, 0.8, is_match=False),
        ]
        result = _make_result(candidates, has_match=True)
        assert policy.select(result) == []

    def test_select_same_result_is_deterministic(self, policy):
        """同じ検索結果から常に同じ適合候補順が得られること。"""
        candidates = [
            _make_candidate(3, 0.85),
            _make_candidate(1, 0.9),
            _make_candidate(2, 0.85),
        ]
        result = _make_result(candidates, has_match=True)
        selected1 = [c.faq_id for c in policy.select(result)]
        selected2 = [c.faq_id for c in policy.select(result)]
        assert selected1 == selected2 == [1, 2, 3]


# ===== stub_answer() テスト =====

class TestGroundingPolicyStubAnswer:
    def test_stub_answer_appends_suffix(self, policy):
        """先頭候補の answer 末尾にスタブ文言が付加されること。"""
        candidates = [
            _make_candidate(1, 0.9),
            _make_candidate(2, 0.8),
        ]
        result = _make_result(candidates, has_match=True)
        selected = policy.select(result)
        answer, sources = policy.stub_answer(selected)
        assert answer.endswith("（AIによる回答予定）")
        assert answer.startswith("回答1")

    def test_stub_answer_returns_only_top_candidate_as_source(self, policy):
        """根拠として返されるのは先頭1件だけであること。"""
        candidates = [
            _make_candidate(1, 0.9),
            _make_candidate(2, 0.8),
            _make_candidate(3, 0.7),
        ]
        result = _make_result(candidates, has_match=True)
        selected = policy.select(result)
        _, sources = policy.stub_answer(selected)
        assert len(sources) == 1
        assert sources[0].faq_id == 1

    def test_stub_answer_raises_on_empty_selected(self, policy):
        """selected が空のとき ValueError が発生すること。"""
        with pytest.raises(ValueError):
            policy.stub_answer([])

    def test_stub_answer_does_not_include_other_candidates_in_sources(self, policy):
        """残りの適合候補が根拠に含まれないこと。"""
        candidates = [_make_candidate(i, 1.0 - i * 0.1) for i in range(1, 6)]
        result = _make_result(candidates, has_match=True)
        selected = policy.select(result)
        _, sources = policy.stub_answer(selected)
        assert len(sources) == 1
