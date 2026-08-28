import re
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _validate_guidance_text(value: str, field_name: str) -> str:
    """trim後1〜1000文字、NULおよびタブ・改行以外の制御文字を禁止する。"""
    stripped = value.strip()
    if len(stripped) < 1:
        raise ValueError(f"{field_name} は空にできません（trim後1文字以上が必要です）")
    if len(stripped) > 1000:
        raise ValueError(f"{field_name} は1000文字以内である必要があります（trim後）")
    if _CONTROL_CHAR_RE.search(stripped):
        raise ValueError(f"{field_name} に制御文字を含めることはできません")
    return stripped


class ChatSettings(BaseSettings):
    """チャット機能のローカル設定。.env から読み込む。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    chat_max_question_chars: int = 400
    chat_contact_guidance: str = "ご不明な点は人事・総務窓口へお問い合わせください。"
    chat_server_error_message: str = "サーバーエラーが発生しました。しばらく時間をおいて再度お試しください。"

    @field_validator("chat_max_question_chars")
    @classmethod
    def validate_max_question_chars(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("CHAT_MAX_QUESTION_CHARS は正整数である必要があります")
        return v

    @field_validator("chat_contact_guidance")
    @classmethod
    def validate_contact_guidance(cls, v: str) -> str:
        return _validate_guidance_text(v, "CHAT_CONTACT_GUIDANCE")

    @field_validator("chat_server_error_message")
    @classmethod
    def validate_server_error_message(cls, v: str) -> str:
        return _validate_guidance_text(v, "CHAT_SERVER_ERROR_MESSAGE")

    @property
    def max_question_chars(self) -> int:
        return self.chat_max_question_chars

    @property
    def contact_guidance(self) -> str:
        return self.chat_contact_guidance

    @property
    def server_error_message(self) -> str:
        return self.chat_server_error_message
