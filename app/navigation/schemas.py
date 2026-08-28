from dataclasses import dataclass
from typing import Literal


NavLinkKey = Literal["question", "history", "faq_admin"]


@dataclass(frozen=True)
class NavLinkState:
    key: NavLinkKey
    href: str
    label: str
    active: bool


@dataclass(frozen=True)
class HeaderMenuContext:
    links: tuple[NavLinkState, NavLinkState, NavLinkState]
    show_user_info: bool
    show_logout: bool
    username: str | None
    role: str | None
