"""FAQ Embedding アダプター。

ローカル CPU で動作する Embedding モデルへの接続口。
実際のモデル・ライブラリはライセンス確認後に差し替える（再検証ゲート）。
未確認のモデルを自動ダウンロード・外部送信しない。
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


class FaqEmbeddingError(RuntimeError):
    """Embedding モデル未準備または encode 失敗を表す例外。HTTP 503 にマップする。"""


class FaqEmbeddingAdapter:
    """ローカル Embedding モデルのラッパー。

    Args:
        model_path: モデルファイルまたはディレクトリのパス。
                    None の場合はモデルをロードせず is_ready() == False となる。

    Notes:
        実際のモデルライブラリはライセンス・Windows CPU 動作確認後に
        このクラスの _load_model / encode 内部実装へ差し替える。
        現在はモックモデルの注入（_model 属性の上書き）でテスト可能。
    """

    def __init__(self, model_path: str | None) -> None:
        self._model_path = model_path
        self._model = None
        if model_path:
            self._load_model(model_path)

    def _load_model(self, model_path: str) -> None:
        """モデルをロードする。ライセンス確認後に実装を差し替えること。

        現在は未実装（再検証ゲート）。モデルライブラリが選定されたら
        sentence-transformers や onnxruntime を使ってここに実装する。
        """
        logger.warning(
            "FaqEmbeddingAdapter: model_path=%s が指定されていますが、"
            "Embedding ライブラリはまだ選定中（ライセンス確認待ち）です。"
            "実際のモデルはロードされません。",
            model_path,
        )
        # TODO: ライセンス・Windows CPU 動作確認後にモデルロードを実装する
        # 例: from sentence_transformers import SentenceTransformer
        #     self._model = SentenceTransformer(model_path, device="cpu")

    def is_ready(self) -> bool:
        """モデルがロード済みで使用可能かどうかを返す。"""
        return self._model is not None

    def encode(self, text: str) -> np.ndarray:
        """テキストを float32 ベクトルに変換して返す。

        Args:
            text: Embedding するテキスト。

        Returns:
            numpy.ndarray (float32) のベクトル。

        Raises:
            FaqEmbeddingError: モデル未ロード時。
        """
        if not self.is_ready():
            raise FaqEmbeddingError(
                "Embedding モデルが準備できていません。"
                "LOCAL_EMBEDDING_PATH を設定し、ライセンス確認済みのモデルを配置してください。"
            )
        # _model.encode の戻り値を float32 ndarray に正規化する
        raw = self._model.encode(text)
        vec = np.asarray(raw, dtype=np.float32)
        return vec
