"""FAQ インメモリ類似度検索索引。

FAQ 件数が少ない MVP 向けに NumPy によるコサイン類似度全探索を実装する。
DB 接続は build() と is_consistent_with_db() のみで使用し、
search() 時は DB に依存しない。
"""
import numpy as np
from sqlalchemy.orm import Session
from app.faq.repositories import FaqEmbeddingRepository


class FaqSearchIndex:
    """インメモリ FAQ ベクトル索引。

    Attributes:
        _vectors: shape (n, dim) の float32 行列。
        _faq_ids: _vectors[i] に対応する faq_id のリスト。
    """

    def __init__(self) -> None:
        self._faq_ids: list[int] = []
        self._vectors: np.ndarray | None = None  # shape (n, dim)
        self._emb_repo = FaqEmbeddingRepository()

    def build(self, db: Session) -> None:
        """DB 内の全 FaqEmbedding を読み込んで索引を再構築する。"""
        embeddings = self._emb_repo.load_all(db)
        if not embeddings:
            self._faq_ids = []
            self._vectors = None
            return

        self._faq_ids = []
        vecs: list[np.ndarray] = []
        for emb in embeddings:
            vec = np.frombuffer(emb.vector, dtype=np.float32).copy()
            # reshape: dimension が保存されている場合はそちらを使う
            vec = vec.reshape(emb.dimension)
            self._faq_ids.append(emb.faq_id)
            vecs.append(vec)
        self._vectors = np.stack(vecs)  # (n, dim)

    def upsert(self, faq_id: int, vector: np.ndarray) -> None:
        """faq_id のベクトルを追加または更新する（DB 接続不要）。"""
        vec = np.asarray(vector, dtype=np.float32)
        if faq_id in self._faq_ids:
            idx = self._faq_ids.index(faq_id)
            self._vectors[idx] = vec
        else:
            self._faq_ids.append(faq_id)
            if self._vectors is None:
                self._vectors = vec.reshape(1, -1)
            else:
                self._vectors = np.vstack([self._vectors, vec.reshape(1, -1)])

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        """コサイン類似度で上位 top_k 件の (faq_id, raw_score) を返す。

        raw_score は -1.0 〜 1.0 の生のコサイン類似度。
        索引が空の場合は空リストを返す。
        """
        if self._vectors is None or len(self._faq_ids) == 0:
            return []

        q = np.asarray(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        # (n,) コサイン類似度ベクトル
        norms = np.linalg.norm(self._vectors, axis=1)
        safe_norms = np.where(norms == 0, 1.0, norms)
        scores = (self._vectors @ q) / (safe_norms * q_norm)

        k = min(top_k, len(self._faq_ids))
        top_indices = np.argsort(scores)[::-1][:k]
        return [(self._faq_ids[i], float(scores[i])) for i in top_indices]

    def is_consistent_with_db(self, db: Session) -> bool:
        """索引エントリ数と DB の faq_embedding 件数が一致するか確認する。

        不一致の場合、呼び出し元は build() で索引を再構築すること。
        """
        db_count = len(self._emb_repo.load_all(db))
        index_count = len(self._faq_ids)
        return db_count == index_count
