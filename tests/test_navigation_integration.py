"""結合テスト: header-navigation-menu テンプレート描画"""
import pytest
from jinja2 import Environment, FileSystemLoader

from app.auth.schemas import CurrentUser
from app.navigation.policy import NavLinkPolicy


@pytest.fixture(scope="module")
def jinja_env():
    env = Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=True,
    )
    return env


def render(env, template_name: str, **ctx) -> str:
    return env.get_template(template_name).render(**ctx)


# ---------------------------------------------------------------------------
# _header_menu.html
# ---------------------------------------------------------------------------

class TestHeaderMenuTemplate:
    def test_service_title_always_present(self, jinja_env):
        ctx = NavLinkPolicy().build(None)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert "HELPO" in html

    def test_unauthenticated_all_links_disabled(self, jinja_env):
        ctx = NavLinkPolicy().build(None)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert 'aria-disabled="true"' in html
        assert '<a class="hnm-link"' not in html

    def test_unauthenticated_shows_login_link(self, jinja_env):
        ctx = NavLinkPolicy().build(None)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert 'href="/login"' in html
        assert "ログアウト" not in html

    def test_user_role_has_active_links(self, jinja_env):
        user = CurrentUser(id=1, username="user01", role="user")
        ctx = NavLinkPolicy().build(user)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert 'href="/chat"' in html
        assert 'href="/history"' in html

    def test_user_role_faq_inactive(self, jinja_env):
        user = CurrentUser(id=1, username="user01", role="user")
        ctx = NavLinkPolicy().build(user)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert 'href="/faqs/upload"' not in html
        assert "FAQ管理" in html

    def test_admin_role_all_active(self, jinja_env):
        admin = CurrentUser(id=2, username="admin01", role="admin")
        ctx = NavLinkPolicy().build(admin)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert 'href="/faqs/upload"' in html
        assert 'href="/chat"' in html
        assert 'href="/history"' in html

    def test_user_info_shown_when_logged_in(self, jinja_env):
        user = CurrentUser(id=1, username="user01", role="user")
        ctx = NavLinkPolicy().build(user)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert "user01" in html
        assert "一般利用者" in html

    def test_admin_role_label(self, jinja_env):
        admin = CurrentUser(id=2, username="admin01", role="admin")
        ctx = NavLinkPolicy().build(admin)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert "管理者" in html

    def test_logout_button_is_form_post(self, jinja_env):
        user = CurrentUser(id=1, username="user01", role="user")
        ctx = NavLinkPolicy().build(user)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert 'method="post"' in html.lower()
        assert 'action="/logout"' in html

    def test_no_user_info_when_unauthenticated(self, jinja_env):
        ctx = NavLinkPolicy().build(None)
        html = render(jinja_env, "navigation/_header_menu.html", header_menu_context=ctx)
        assert "hnm-user" not in html
        assert "ログアウト" not in html

    def test_not_rendered_without_context(self, jinja_env):
        html = render(jinja_env, "navigation/_header_menu.html")
        assert html.strip() == ""


# ---------------------------------------------------------------------------
# _page_base.html 経由の描画
# ---------------------------------------------------------------------------

class TestPageBaseTemplate:
    def test_page_base_includes_header_menu(self, jinja_env):
        """_page_base.html を継承したテンプレートが header_menu_context を受け取り描画する。"""
        from jinja2 import Template

        jinja_env.get_template("_page_base.html")  # 存在確認
        # ダミーテンプレートで継承テスト
        source = '{% extends "_page_base.html" %}{% block content %}<p>test</p>{% endblock %}'
        tmpl = jinja_env.from_string(source)
        user = CurrentUser(id=1, username="user01", role="user")
        ctx = NavLinkPolicy().build(user)
        html = tmpl.render(header_menu_context=ctx)
        assert "HELPO" in html
        assert "user01" in html
        assert "<p>test</p>" in html
