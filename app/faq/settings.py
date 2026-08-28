"""FAQ 機能固有の設定。"""
from pydantic import BaseModel


class FaqSettings(BaseModel):
    """FAQ 管理・検索機能固有の設定。

    foundation の Settings に既に `local_embedding_path` があるため、
    Embedding モデルパスはそちらを使用する。本クラスはモデル選定後に
    モデル固有の設定項目を追加するための拡張ポイントとして用意する。

    適合基準（RELEVANCE_THRESHOLD）は運用者設定ではなく、実装が所有する
    固定定数とする。MVP 検証後にコード変更として調整する。
    """

    # アップロード可能な最大ファイルサイズ (バイト)
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10MB

    # 検索時に返す上位件数のデフォルト値
    default_top_k: int = 5
