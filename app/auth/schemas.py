from dataclasses import dataclass
from typing import Literal

Role = Literal["user", "admin"]


@dataclass(frozen=True)
class CurrentUser:
    """後続仕様へ渡す読み取り専用の現在利用者情報。秘密情報を含まない。"""
    id: int
    username: str
    role: Role
