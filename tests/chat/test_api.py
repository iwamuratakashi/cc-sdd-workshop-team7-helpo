"""
タスク 5.2: 結合・E2Eテスト。
TestClient(create_app()) を使い POST /api/chat からレスポンスまでの主要フローを検証する。
- ai_answer（モック適合あり質問）と no_match（モック適合なし質問）
- HTTP 422（空入力・文字数超過）
- HTTP 500（FAQ 検索失敗）
- network をブロックした状態でも回答が返ること（外部 AI サービスへの通信なし）
- chat router が pages_router の /chat プレースホルダーより優先されること
- 未認証アクセスの 303 / 401 ふるまい
- 範囲外 route（履歴・共有・export 等）が存在しないこと
"""
import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user_optional, require_authenticated_user
from app.auth.schemas import CurrentUser
from app.chat.dependencies import get_chat_service
from app.chat.faq_mock import FaqMockSearchService
from app.chat.grounding import GroundingPolicy
from app.chat.services import ChatService
from app.chat.settings import ChatSettings
from app.db import DatabaseEngine

# テスト全域で使うスタブ利用者
_STUB_USER = CurrentUser(id=1, username="testuser", role="user")


def _stub_authenticated() -> CurrentUser:
    """require_authenticated_user の代替: 常に _STUB_USER を返す。"""
    return _STUB_USER


def _stub_optional() -> CurrentUser | None:
    """get_current_user_optional の代替: 常に _STUB_USER を返す。"""
    return _STUB_USER


def _stub_anonymous() -> CurrentUser | None:
    """get_current_user_optional の代替: 未認証（None）を返す。"""
    return None


@pytest.fixture(autouse=True)
def reset_db():
    """各テストで DB をリセットしてインメモリ SQLite を使う。"""
    original_db_url = os.environ.get("DATABASE_URL")
    DatabaseEngine.reset()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    from app.config import Settings
    DatabaseEngine().init(Settings())
    yield
    DatabaseEngine.reset()
    if original_db_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original_db_url


def _make_app(*, authenticated: bool = True, broken_faq: bool = False):
    """テスト用アプリを生成する。

    Args:
        authenticated: True なら認証済み利用者をスタブ。False なら未認証をスタブ。
        broken_faq: True なら FAQ 検索が RuntimeError を送出するサービスを注入。
    """
    from main import create_app
    app = create_app()

    if authenticated:
        app.dependency_overrides[require_authenticated_user] = _stub_authenticated
        app.dependency_overrides[get_current_user_optional] = _stub_optional
    else:
        app.dependency_overrides[get_current_user_optional] = _stub_anonymous
        # require_authenticated_user は override しない → 実際の 401/303 を返す

    if broken_faq:
        mock_faq = MagicMock()
        mock_faq.search.side_effect = RuntimeError("DB connection failed")
        broken_service = ChatService(
            faq_search_service=mock_faq,
            grounding_policy=GroundingPolicy(),
            settings=ChatSettings(
                chat_max_question_chars=400,
                chat_contact_guidance="人事・総務窓口へお問い合わせください。",
                chat_server_error_message="サーバーエラーが発生しました。",
            ),
        )
        app.dependency_overrides[get_chat_service] = lambda: broken_service

    return app


@pytest.fixture
def client():
    """認証済みスタブクライアント。"""
    return TestClient(_make_app(authenticated=True), raise_server_exceptions=False)


@pytest.fixture
def anon_client():
    """未認証スタブクライアント。"""
    return TestClient(_make_app(authenticated=False), raise_server_exceptions=False)


@pytest.fixture
def client_with_broken_faq():
    """認証済み + FAQ 検索破損クライアント。"""
    return TestClient(_make_app(authenticated=True, broken_faq=True), raise_server_exceptions=False)


# ===== GET /chat =====

class TestChatPage:
    def test_get_chat_authenticated_returns_200(self, client):
        """GET /chat が認証済みで 200 を返すこと。"""
        r = client.get("/chat")
        assert r.status_code == 200

    def test_get_chat_contains_textarea(self, client):
        """GET /chat のレスポンスに textarea が含まれること。"""
        r = client.get("/chat")
        assert "textarea" in r.text

    def test_get_chat_unauthenticated_redirects_to_login(self, anon_client):
        """GET /chat が未認証で /login へ 303 リダイレクトすること。"""
        r = anon_client.get("/chat", follow_redirects=False)
        assert r.status_code == 303
        assert r.headers.get("location") == "/login"

    def test_get_chat_chat_router_takes_priority_over_placeholder(self, client):
        """chat router が pages_router の /chat プレースホルダーより優先されること。"""
        r = client.get("/chat")
        # placeholder.html は「質問（チャット）」という page_title を持ち textarea がない
        assert "textarea" in r.text


# ===== POST /api/chat — ai_answer =====

class TestChatApiAiAnswer:
    def test_ai_answer_returns_200(self, client):
        """モック適合あり質問で HTTP 200 が返ること。"""
        r = client.post("/api/chat", json={"question": "休暇の申請方法"})
        assert r.status_code == 200

    def test_ai_answer_status_is_ai_answer(self, client):
        """モック適合あり質問で status が ai_answer であること。"""
        r = client.post("/api/chat", json={"question": "休暇の申請方法"})
        assert r.json()["status"] == "ai_answer"

    def test_ai_answer_has_exactly_one_source(self, client):
        """ai_answer の根拠が厳密に1件であること。"""
        r = client.post("/api/chat", json={"question": "休暇の申請方法"})
        assert len(r.json()["sources"]) == 1

    def test_ai_answer_has_stub_suffix(self, client):
        """ai_answer の回答テキストにスタブ文言が含まれること。"""
        r = client.post("/api/chat", json={"question": "休暇の申請方法"})
        assert r.json()["answer"].endswith("（AIによる回答予定）")

    def test_ai_answer_source_fields_present(self, client):
        """ai_answer の根拠に必要なフィールドが含まれること。"""
        r = client.post("/api/chat", json={"question": "経費精算"})
        src = r.json()["sources"][0]
        assert "faq_id" in src
        assert "question" in src
        assert "answer" in src
        assert "confidence" in src


# ===== POST /api/chat — no_match =====

class TestChatApiNoMatch:
    def test_no_match_returns_200(self, client):
        """モック適合なし質問で HTTP 200 が返ること。"""
        r = client.post("/api/chat", json={"question": "xyzxyzxyz意味不明クエリ"})
        assert r.status_code == 200

    def test_no_match_status_is_no_match(self, client):
        """モック適合なし質問で status が no_match であること。"""
        r = client.post("/api/chat", json={"question": "xyzxyzxyz意味不明クエリ"})
        assert r.json()["status"] == "no_match"

    def test_no_match_sources_is_empty(self, client):
        """no_match の sources が空であること。"""
        r = client.post("/api/chat", json={"question": "xyzxyzxyz意味不明クエリ"})
        assert r.json()["sources"] == []


# ===== POST /api/chat — 未認証 =====

class TestChatApiUnauthenticated:
    def test_unauthenticated_returns_401(self, anon_client):
        """未認証で POST /api/chat すると 401 が返ること。"""
        r = anon_client.post("/api/chat", json={"question": "休暇の申請方法"})
        assert r.status_code == 401


# ===== POST /api/chat — バリデーションエラー =====

class TestChatApiValidation:
    def test_empty_question_returns_422(self, client):
        """空の question で 422 が返ること。"""
        r = client.post("/api/chat", json={"question": ""})
        assert r.status_code == 422

    def test_whitespace_only_question_returns_422(self, client):
        """スペースのみの question で 422 が返ること（trim後0文字）。"""
        r = client.post("/api/chat", json={"question": "   "})
        assert r.status_code == 422

    def test_over_limit_question_returns_422(self, client):
        """401文字以上の question で 422 が返ること。"""
        r = client.post("/api/chat", json={"question": "あ" * 401})
        assert r.status_code == 422

    def test_exactly_max_chars_question_returns_200(self, client):
        """ちょうど max_chars 文字の question で 200 が返ること。"""
        r = client.post("/api/chat", json={"question": "あ" * 400})
        assert r.status_code == 200

    def test_missing_question_field_returns_422(self, client):
        """question フィールドがない場合 422 が返ること。"""
        r = client.post("/api/chat", json={})
        assert r.status_code == 422


# ===== POST /api/chat — HTTP 500（FAQ 検索失敗） =====

class TestChatApiFaqSearchFailure:
    def test_faq_search_failure_returns_500(self, client_with_broken_faq):
        """FAQ 検索失敗時に HTTP 500 が返ること（ChatStatus に変換しない）。"""
        r = client_with_broken_faq.post("/api/chat", json={"question": "休暇の申請"})
        assert r.status_code == 500

    def test_faq_search_failure_response_is_json(self, client_with_broken_faq):
        """FAQ 検索失敗時のレスポンスが JSON であること。"""
        r = client_with_broken_faq.post("/api/chat", json={"question": "休暇の申請"})
        assert "detail" in r.json()

    def test_faq_search_failure_does_not_expose_internal_details(self, client_with_broken_faq):
        """FAQ 検索失敗時に内部エラー詳細が公開されないこと。"""
        r = client_with_broken_faq.post("/api/chat", json={"question": "休暇の申請"})
        assert "DB connection failed" not in r.text
        assert "RuntimeError" not in r.text


# ===== ネットワーク遮断テスト =====

class TestChatApiNoNetwork:
    def test_answer_without_network_access(self, reset_db):
        """外部ネットワーク接続なしでも回答が返ること（外部AI通信なし）。

        FaqMockSearchService は外部ネットワーク通信を行わない。
        ChatService が外部接続なしで ai_answer / no_match へ収束することを直接検証する。
        """
        svc = ChatService(
            faq_search_service=FaqMockSearchService(),
            grounding_policy=GroundingPolicy(),
            settings=ChatSettings(
                chat_max_question_chars=400,
                chat_contact_guidance="人事・総務窓口へお問い合わせください。",
                chat_server_error_message="サーバーエラーが発生しました。",
            ),
        )
        assert svc.ask(db=None, question="休暇の申請方法").status == "ai_answer"
        assert svc.ask(db=None, question="xyzxyzxyz意味不明クエリ").status == "no_match"


# ===== 範囲外 route の不存在テスト =====

class TestChatApiOutOfScope:
    def test_chat_history_route_does_not_exist(self, client):
        """/api/chat/history が存在しないこと（chat-history は別スペック）。"""
        r = client.get("/api/chat/history")
        assert r.status_code == 404

    def test_chat_export_route_does_not_exist(self, client):
        """/api/chat/export が存在しないこと。"""
        r = client.get("/api/chat/export")
        assert r.status_code == 404

    def test_chat_share_route_does_not_exist(self, client):
        """/api/chat/share が存在しないこと。"""
        r = client.post("/api/chat/share", json={})
        assert r.status_code == 404
