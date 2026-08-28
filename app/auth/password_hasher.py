from argon2 import PasswordHasher as _Argon2PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError


class PasswordHasher:
    """Argon2id によるパスワードのハッシュ化と照合。"""

    def __init__(self) -> None:
        self._hasher = _Argon2PasswordHasher()

    def hash(self, password: str) -> str:
        """平文パスワードから Argon2id ハッシュを生成する。"""
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """パスワードがハッシュと一致するか検証する。
        照合失敗・不正ハッシュはいずれも False を返す（例外を外に漏らさない）。
        入力値・ハッシュをログへ渡さない。
        """
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
        except Exception:
            return False
