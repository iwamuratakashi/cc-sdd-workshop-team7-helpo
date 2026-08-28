from app.auth.schemas import CurrentUser
from app.navigation.schemas import HeaderMenuContext, NavLinkState

_NAV_LINKS = [
    {"key": "question",  "href": "/chat",        "label": "質問"},
    {"key": "history",   "href": "/history",     "label": "履歴"},
    {"key": "faq_admin", "href": "/faqs/upload", "label": "FAQ管理"},
]


class NavLinkPolicy:
    """現在利用者の状態だけからナビリンクの活性・非活性を決定する純粋関数クラス。
    DB アクセス・副作用なし。
    """

    def build(self, current_user: CurrentUser | None) -> HeaderMenuContext:
        is_logged_in = current_user is not None
        is_admin = is_logged_in and current_user.role == "admin"  # type: ignore[union-attr]

        def _active(key: str) -> bool:
            if not is_logged_in:
                return False
            if key == "faq_admin":
                return is_admin
            return True

        links = tuple(
            NavLinkState(
                key=cfg["key"],  # type: ignore[arg-type]
                href=cfg["href"],
                label=cfg["label"],
                active=_active(cfg["key"]),
            )
            for cfg in _NAV_LINKS
        )
        return HeaderMenuContext(
            links=links,  # type: ignore[arg-type]
            show_user_info=is_logged_in,
            show_logout=is_logged_in,
            username=current_user.username if current_user else None,
            role=current_user.role if current_user else None,
        )
