import logging
import sys
from typing import Any


def configure_logging(debug: bool = False) -> None:
    """アプリケーション全体のロギングを設定する。

    - INFO レベル以上を標準出力へ出力する。
    - debug=True の場合は DEBUG レベルを有効にする。
    - パスワード・セッション識別子などの秘密情報はログに含めない。
    """
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # 重複ハンドラを防ぐ
    if not root_logger.handlers:
        root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """名前付きロガーを返す。"""
    return logging.getLogger(name)


def log_exception(exc: Exception, context: dict[str, Any] | None = None) -> None:
    """例外の詳細をサーバーログへ記録する。

    機密情報（パスワード・セッションID・質問全文・回答全文・FAQ全文・履歴全文）は
    ここに含めないこと。
    """
    logger = get_logger("helpo.error")
    extra = f" | context={context}" if context else ""
    logger.exception("Unhandled exception%s: %s", extra, exc)
