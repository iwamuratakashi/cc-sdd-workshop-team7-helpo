"""
タスク 5.1: ChatService と ChatSettings のユニットテスト。
- ai_answer / no_match の状態遷移
- 検索失敗時の例外伝播（ChatStatus に変換しない）
- 通常ログに質問全文・FAQ全文・回答全文が含まれないこと
- ChatSettings のバリデーション境界値
"""
import logging
import pytest
from unittest.mock import MagicMock
from pydantic import ValidationError

from app.chat.faq_mock import FaqMockSearchService
from app.chat.faq_types import FaqCandidate, FaqSearchResult
from app.chat.grounding import GroundingPolicy
from app.chat.schemas import ChatStatus
from app.chat.services import ChatService
from app.chat.settings import ChatSettings


# ===== フィクスチャ =====

@pytest.fixture
def default_settings():
    return ChatSettings(
        chat_max_question_chars=400,
        chat_contact_guidance="人事・総務窓口へお問い合わせください。",
        chat_server_error_message="サーバーエラーが発生しました。",
    )


def _make_service(settings: ChatSettings, faq_service=None) -> ChatService:
    return ChatService(
        faq_search_service=faq_service or FaqMockSearchService(),
        grounding_policy=GroundingPolicy(),
        settings=settings,
    )


# ===== ChatService テスト =====

class TestChatServiceAsk:
    def test_ask_returns_ai_answer_when_match_found(self, default_settings):
        """モック適合ありの質問で ai_answer と根拠1件が返ること。"""
        svc = _make_service(default_settings)
        r = svc.ask(db=None, question="休暇の申請")
        assert r.status == "ai_answer"
        assert len(r.sources) == 1
        assert r.answer.endswith("（AIによる回答予定）")
        assert r.question == "休暇の申請"

    def test_ask_returns_no_match_when_no_match(self, default_settings):
        """モック適合なしの質問で no_match と空根拠が返ること。"""
        svc = _make_service(default_settings)
        r = svc.ask(db=None, question="xyzxyzxyz意味不明クエリ")
        assert r.status == "no_match"
        assert r.sources == []
        assert r.answer == default_settings.contact_guidance

    def test_ask_no_match_answer_uses_contact_guidance(self, default_settings):
        """no_match 時の回答テキストが contact_guidance と一致すること。"""
        svc = _make_service(default_settings)
        r = svc.ask(db=None, question="xyzxyzxyz意味不明クエリ")
        assert r.answer == default_settings.contact_guidance

    def test_ask_propagates_search_exception(self, default_settings):
        """FAQ 検索失敗時に例外が ChatStatus に変換されず伝播すること。"""
        broken_faq = MagicMock()
        broken_faq.search.side_effect = RuntimeError("DB error")
        svc = _make_service(default_settings, faq_service=broken_faq)
        with pytest.raises(RuntimeError, match="DB error"):
            svc.ask(db=None, question="何か質問")

    def test_ask_ai_answer_source_count_is_exactly_one(self, default_settings):
        """ai_answer 時の根拠は厳密に1件であること。"""
        svc = _make_service(default_settings)
        r = svc.ask(db=None, question="経費精算")
        assert r.status == "ai_answer"
        assert len(r.sources) == 1

    def test_ask_source_fields_match_faq_candidate(self, default_settings):
        """根拠の各フィールドが FaqCandidate の内容と一致すること。"""
        svc = _make_service(default_settings)
        r = svc.ask(db=None, question="休暇")
        assert r.status == "ai_answer"
        src = r.sources[0]
        assert isinstance(src.faq_id, int)
        assert isinstance(src.question, str)
        assert isinstance(src.answer, str)
        assert 0.0 <= src.confidence <= 1.0


class TestChatServiceLogging:
    def test_log_does_not_contain_question_text(self, default_settings, caplog):
        """通常ログに質問全文が含まれないこと。"""
        svc = _make_service(default_settings)
        question = "秘密の質問内容テスト12345"
        with caplog.at_level(logging.INFO, logger="app.chat.services"):
            svc.ask(db=None, question=question)
        for record in caplog.records:
            assert question not in record.getMessage()

    def test_log_does_not_contain_answer_text(self, default_settings, caplog):
        """通常ログに回答全文が含まれないこと。"""
        svc = _make_service(default_settings)
        with caplog.at_level(logging.INFO, logger="app.chat.services"):
            r = svc.ask(db=None, question="休暇の申請")
        for record in caplog.records:
            assert r.answer not in record.getMessage()

    def test_log_contains_status_and_duration(self, default_settings, caplog):
        """通常ログに status と duration_ms が含まれること。"""
        svc = _make_service(default_settings)
        with caplog.at_level(logging.INFO, logger="app.chat.services"):
            svc.ask(db=None, question="休暇の申請")
        messages = " ".join(r.getMessage() for r in caplog.records)
        assert "status=" in messages
        assert "duration_ms=" in messages


# ===== ChatSettings バリデーションテスト =====

class TestChatSettings:
    def test_default_settings_are_valid(self):
        """デフォルト値で設定が正常に読み込まれること。"""
        s = ChatSettings(
            chat_max_question_chars=400,
            chat_contact_guidance="人事部へお問い合わせください。",
            chat_server_error_message="エラーが発生しました。",
        )
        assert s.max_question_chars == 400

    def test_max_question_chars_must_be_positive(self):
        """max_question_chars が 0 以下の場合バリデーションエラーになること（fail-closed）。"""
        with pytest.raises(ValidationError):
            ChatSettings(
                chat_max_question_chars=0,
                chat_contact_guidance="案内文",
                chat_server_error_message="エラー",
            )

    def test_max_question_chars_negative_rejected(self):
        """max_question_chars が負の場合バリデーションエラーになること。"""
        with pytest.raises(ValidationError):
            ChatSettings(
                chat_max_question_chars=-1,
                chat_contact_guidance="案内文",
                chat_server_error_message="エラー",
            )

    def test_contact_guidance_empty_string_rejected(self):
        """contact_guidance が空文字列の場合バリデーションエラーになること。"""
        with pytest.raises(ValidationError):
            ChatSettings(
                chat_max_question_chars=400,
                chat_contact_guidance="",
                chat_server_error_message="エラー",
            )

    def test_contact_guidance_whitespace_only_rejected(self):
        """contact_guidance がスペースのみの場合バリデーションエラーになること（trim後0文字）。"""
        with pytest.raises(ValidationError):
            ChatSettings(
                chat_max_question_chars=400,
                chat_contact_guidance="   ",
                chat_server_error_message="エラー",
            )

    def test_contact_guidance_over_1000_chars_rejected(self):
        """contact_guidance が1000文字超の場合バリデーションエラーになること。"""
        with pytest.raises(ValidationError):
            ChatSettings(
                chat_max_question_chars=400,
                chat_contact_guidance="あ" * 1001,
                chat_server_error_message="エラー",
            )

    def test_contact_guidance_exactly_1000_chars_accepted(self):
        """contact_guidance がちょうど1000文字の場合有効であること。"""
        s = ChatSettings(
            chat_max_question_chars=400,
            chat_contact_guidance="あ" * 1000,
            chat_server_error_message="エラー",
        )
        assert len(s.contact_guidance) == 1000

    def test_contact_guidance_control_char_rejected(self):
        """contact_guidance に制御文字（タブ・改行以外）が含まれる場合バリデーションエラーになること。"""
        with pytest.raises(ValidationError):
            ChatSettings(
                chat_max_question_chars=400,
                chat_contact_guidance="案内\x01文",
                chat_server_error_message="エラー",
            )

    def test_contact_guidance_newline_accepted(self):
        """contact_guidance に改行が含まれていても有効であること（制御文字除外対象外）。"""
        s = ChatSettings(
            chat_max_question_chars=400,
            chat_contact_guidance="案内文\n詳細",
            chat_server_error_message="エラー",
        )
        assert "\n" in s.contact_guidance
