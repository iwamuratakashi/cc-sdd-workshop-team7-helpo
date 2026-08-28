"""単体テスト: header-navigation-menu NavLinkPolicy"""
import pytest
from app.auth.schemas import CurrentUser
from app.navigation.policy import NavLinkPolicy
from app.navigation.schemas import HeaderMenuContext


class TestNavLinkPolicy:
    def setup_method(self):
        self.policy = NavLinkPolicy()

    # --- リンク件数・固定順序 ---

    def test_always_returns_3_links(self):
        for user in [None, CurrentUser(id=1, username="u", role="user"), CurrentUser(id=2, username="a", role="admin")]:
            ctx = self.policy.build(user)
            assert len(ctx.links) == 3

    def test_link_order_is_fixed(self):
        ctx = self.policy.build(None)
        assert ctx.links[0].key == "question"
        assert ctx.links[1].key == "history"
        assert ctx.links[2].key == "faq_admin"

    # --- 未ログイン ---

    def test_none_all_links_inactive(self):
        ctx = self.policy.build(None)
        assert all(not link.active for link in ctx.links)

    def test_none_no_user_info(self):
        ctx = self.policy.build(None)
        assert ctx.show_user_info is False
        assert ctx.show_logout is False
        assert ctx.username is None
        assert ctx.role is None

    # --- 一般利用者 ---

    def test_user_question_and_history_active(self):
        user = CurrentUser(id=1, username="user01", role="user")
        ctx = self.policy.build(user)
        link_map = {l.key: l.active for l in ctx.links}
        assert link_map["question"] is True
        assert link_map["history"] is True

    def test_user_faq_admin_inactive(self):
        user = CurrentUser(id=1, username="user01", role="user")
        ctx = self.policy.build(user)
        link_map = {l.key: l.active for l in ctx.links}
        assert link_map["faq_admin"] is False

    def test_user_shows_user_info(self):
        user = CurrentUser(id=1, username="user01", role="user")
        ctx = self.policy.build(user)
        assert ctx.show_user_info is True
        assert ctx.show_logout is True
        assert ctx.username == "user01"
        assert ctx.role == "user"

    # --- 管理者 ---

    def test_admin_all_links_active(self):
        admin = CurrentUser(id=2, username="admin01", role="admin")
        ctx = self.policy.build(admin)
        assert all(link.active for link in ctx.links)

    def test_admin_shows_user_info(self):
        admin = CurrentUser(id=2, username="admin01", role="admin")
        ctx = self.policy.build(admin)
        assert ctx.show_user_info is True
        assert ctx.username == "admin01"
        assert ctx.role == "admin"

    # --- href と label の存在確認 ---

    def test_links_have_href_and_label(self):
        ctx = self.policy.build(None)
        for link in ctx.links:
            assert link.href.startswith("/")
            assert len(link.label) > 0
