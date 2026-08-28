"""
faq-management-and-search 結合テスト
"""
import os
import pytest
import numpy as np
from sqlalchemy import text
from fastapi.testclient import TestClient

from app.db import DatabaseEngine
from app.config import Settings


# ---------------------------------------------------------------------------
# 共通フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_db_engine():
    """各テスト前後に DatabaseEngine をリセットし、DATABASE_URL を元に戻す。"""
    _orig = os.environ.get("DATABASE_URL")
    DatabaseEngine.reset()
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    yield
    DatabaseEngine.reset()
    if _orig is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = _orig


@pytest.fixture
def db_session():
    DatabaseEngine().init(Settings())
    session = DatabaseEngine().get_session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Task 1.1: マイグレーション
# ---------------------------------------------------------------------------

def test_faq_migration_creates_faq_table(db_session):
    """003マイグレーションでfaqテーブルが作成される。"""
    with DatabaseEngine().engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='faq'"
        ))
        assert result.fetchone() is not None, "faq テーブルが存在しない"


def test_faq_migration_creates_faq_embedding_table(db_session):
    """003マイグレーションでfaq_embeddingテーブルが作成される。"""
    with DatabaseEngine().engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='faq_embedding'"
        ))
        assert result.fetchone() is not None, "faq_embedding テーブルが存在しない"


# ---------------------------------------------------------------------------
# Task 1.2: FaqSettings
# ---------------------------------------------------------------------------

def test_faq_settings_defaults():
    """FaqSettings のデフォルト値が仕様通りであること。"""
    from app.faq.settings import FaqSettings
    s = FaqSettings()
    assert s.max_upload_size_bytes == 10 * 1024 * 1024
    assert s.default_top_k == 5


def test_faq_settings_can_be_overridden():
    """FaqSettings はフィールドを上書きできること。"""
    from app.faq.settings import FaqSettings
    s = FaqSettings(max_upload_size_bytes=1024, default_top_k=3)
    assert s.max_upload_size_bytes == 1024
    assert s.default_top_k == 3


# ---------------------------------------------------------------------------
# Task 2.1: FaqRepository
# ---------------------------------------------------------------------------

def test_faq_repository_create(db_session):
    """FaqRepository.create で FAQ が保存されること。"""
    from app.faq.repositories import FaqRepository
    repo = FaqRepository()
    faq = repo.create(db_session, question="有給休暇の申請方法は？", answer="3営業日前までに申請してください。")
    db_session.commit()
    assert faq.id is not None
    assert faq.question == "有給休暇の申請方法は？"
    assert faq.answer == "3営業日前までに申請してください。"


def test_faq_repository_list_all(db_session):
    """FaqRepository.list_all で全FAQ一覧を取得できること。"""
    from app.faq.repositories import FaqRepository
    repo = FaqRepository()
    repo.create(db_session, question="Q1", answer="A1")
    repo.create(db_session, question="Q2", answer="A2")
    db_session.commit()
    faqs = repo.list_all(db_session)
    assert len(faqs) == 2


def test_faq_repository_get_by_id(db_session):
    """FaqRepository.get_by_id で指定IDのFAQを取得できること。"""
    from app.faq.repositories import FaqRepository
    repo = FaqRepository()
    faq = repo.create(db_session, question="Q?", answer="A.")
    db_session.commit()
    found = repo.get_by_id(db_session, faq.id)
    assert found is not None
    assert found.id == faq.id


def test_faq_repository_get_by_id_not_found(db_session):
    """存在しないIDは None を返すこと。"""
    from app.faq.repositories import FaqRepository
    repo = FaqRepository()
    assert repo.get_by_id(db_session, 9999) is None


def test_faq_repository_transaction_rollback(db_session):
    """コミット前にロールバックするとFAQが保存されないこと。"""
    from app.faq.repositories import FaqRepository
    repo = FaqRepository()
    repo.create(db_session, question="Q?", answer="A.")
    db_session.rollback()
    assert len(repo.list_all(db_session)) == 0


# ---------------------------------------------------------------------------
# Task 2.2: MarkdownParser
# ---------------------------------------------------------------------------

VALID_MD = """## 有給休暇の申請方法は？

3営業日前までに申請システムから申請してください。

## 交通費精算の期限はいつですか？

当月末までに精算システムに入力してください。
"""

def test_markdown_parser_valid():
    """正しいMarkdownからQ&Aリストを返すこと。"""
    from app.faq.markdown_parser import MarkdownParser
    pairs = MarkdownParser().parse(VALID_MD)
    assert len(pairs) == 2
    assert pairs[0][0] == "有給休暇の申請方法は？"
    assert "3営業日前" in pairs[0][1]


def test_markdown_parser_multi_paragraph_answer():
    """複数段落の回答を連結すること。"""
    from app.faq.markdown_parser import MarkdownParser
    md = "## Q?\n\n段落1\n\n段落2\n"
    pairs = MarkdownParser().parse(md)
    assert len(pairs) == 1
    assert "段落1" in pairs[0][1]
    assert "段落2" in pairs[0][1]


def test_markdown_parser_empty_question_raises():
    """空の質問文はエラーを返すこと。"""
    from app.faq.markdown_parser import MarkdownParser, MarkdownParseError
    with pytest.raises(MarkdownParseError):
        MarkdownParser().parse("## \n\n回答\n")


def test_markdown_parser_empty_answer_raises():
    """回答がないセクションはエラーを返すこと。"""
    from app.faq.markdown_parser import MarkdownParser, MarkdownParseError
    with pytest.raises(MarkdownParseError):
        MarkdownParser().parse("## Q?\n\n## Q2?\n\n回答\n")


def test_markdown_parser_duplicate_question_raises():
    """ファイル内の重複質問文はエラーを返すこと。"""
    from app.faq.markdown_parser import MarkdownParser, MarkdownParseError
    md = "## Q?\n\n回答1\n\n## Q?\n\n回答2\n"
    with pytest.raises(MarkdownParseError):
        MarkdownParser().parse(md)


def test_markdown_parser_no_sections_raises():
    """有効なQ&Aセクションがゼロ件はエラーを返すこと。"""
    from app.faq.markdown_parser import MarkdownParser, MarkdownParseError
    with pytest.raises(MarkdownParseError):
        MarkdownParser().parse("これはMarkdownだが見出しがない\n")


def test_markdown_parser_h3_not_treated_as_question():
    """H3見出し（###）は質問文として扱わないこと。"""
    from app.faq.markdown_parser import MarkdownParser
    md = "## Q?\n\n### サブタイトル\n\n回答\n"
    pairs = MarkdownParser().parse(md)
    assert len(pairs) == 1
    assert pairs[0][0] == "Q?"


# ---------------------------------------------------------------------------
# Task 2.3: FaqEmbeddingAdapter
# ---------------------------------------------------------------------------

def test_embedding_adapter_not_ready_when_no_path():
    """モデルパスなしの場合は is_ready() が False。"""
    from app.faq.embedding import FaqEmbeddingAdapter
    adapter = FaqEmbeddingAdapter(model_path=None)
    assert adapter.is_ready() is False


def test_embedding_adapter_encode_raises_when_not_ready():
    """is_ready() が False の状態で encode を呼ぶと RuntimeError。"""
    from app.faq.embedding import FaqEmbeddingAdapter
    adapter = FaqEmbeddingAdapter(model_path=None)
    with pytest.raises(RuntimeError):
        adapter.encode("テスト")


def test_embedding_adapter_with_mock_returns_float32(monkeypatch):
    """モックモデルを差し込んだ場合、encode は float32 ndarray を返す。"""
    import numpy as np
    from app.faq.embedding import FaqEmbeddingAdapter

    class FakeModel:
        def encode(self, text: str):
            return np.ones(384, dtype=np.float32)

    adapter = FaqEmbeddingAdapter(model_path=None)
    adapter._model = FakeModel()  # 内部モデルをモックに差し替え

    vec = adapter.encode("テスト")
    assert isinstance(vec, np.ndarray)
    assert vec.dtype == np.float32


# ---------------------------------------------------------------------------
# Task 2.4: FaqEmbeddingRepository
# ---------------------------------------------------------------------------

def _make_vector(dim: int = 4) -> tuple[bytes, int]:
    vec = np.ones(dim, dtype=np.float32)
    return vec.tobytes(), dim


def test_embedding_repo_upsert_creates(db_session):
    """FaqEmbeddingRepository.upsert で Embedding を作成できること。"""
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    faq = FaqRepository().create(db_session, question="Q?", answer="A.")
    db_session.flush()
    vec_bytes, dim = _make_vector()
    emb = FaqEmbeddingRepository().upsert(db_session, faq.id, dim, vec_bytes)
    db_session.commit()
    assert emb.id is not None
    assert emb.faq_id == faq.id
    assert emb.dimension == dim
    assert emb.vector == vec_bytes


def test_embedding_repo_upsert_updates(db_session):
    """同じ faq_id で upsert すると更新されること。"""
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    faq = FaqRepository().create(db_session, question="Q?", answer="A.")
    db_session.flush()
    repo = FaqEmbeddingRepository()
    vec1, dim = _make_vector(4)
    repo.upsert(db_session, faq.id, dim, vec1)
    vec2 = (np.zeros(4, dtype=np.float32)).tobytes()
    updated = repo.upsert(db_session, faq.id, dim, vec2)
    db_session.commit()
    assert updated.vector == vec2


def test_embedding_repo_load_all(db_session):
    """FaqEmbeddingRepository.load_all で全件取得できること。"""
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    faq_repo = FaqRepository()
    emb_repo = FaqEmbeddingRepository()
    for i in range(3):
        faq = faq_repo.create(db_session, question=f"Q{i}?", answer=f"A{i}.")
        db_session.flush()
        vec, dim = _make_vector()
        emb_repo.upsert(db_session, faq.id, dim, vec)
    db_session.commit()
    all_embs = emb_repo.load_all(db_session)
    assert len(all_embs) == 3


def test_embedding_repo_faq_id_unique_constraint(db_session):
    """同じ faq_id に対する直接 INSERT は UNIQUE 制約でエラーになること。"""
    from sqlalchemy.exc import IntegrityError
    from app.faq.repositories import FaqRepository
    from app.faq.models import FaqEmbedding
    faq = FaqRepository().create(db_session, question="Q?", answer="A.")
    db_session.flush()
    vec, dim = _make_vector()
    e1 = FaqEmbedding(faq_id=faq.id, dimension=dim, vector=vec)
    e2 = FaqEmbedding(faq_id=faq.id, dimension=dim, vector=vec)
    db_session.add(e1)
    db_session.add(e2)
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---------------------------------------------------------------------------
# Task 2.5: FaqSearchIndex
# ---------------------------------------------------------------------------

def _make_index_with_faqs(db_session):
    """テスト用に FaqSearchIndex にベクトルを3件 upsert して返す。"""
    from app.faq.search_index import FaqSearchIndex
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository

    faq_repo = FaqRepository()
    emb_repo = FaqEmbeddingRepository()
    index = FaqSearchIndex()

    vecs = [
        np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32),
        np.array([0.7, 0.7, 0.0, 0.0], dtype=np.float32),
    ]
    faq_ids = []
    for i, vec in enumerate(vecs):
        faq = faq_repo.create(db_session, question=f"Q{i}?", answer=f"A{i}.")
        db_session.flush()
        emb_repo.upsert(db_session, faq.id, 4, vec.tobytes())
        index.upsert(faq.id, vec)
        faq_ids.append(faq.id)
    db_session.commit()
    return index, faq_ids, vecs


def test_search_index_upsert_and_search(db_session):
    """upsert 後の search がコサイン類似度の高い順を返すこと。"""
    from app.faq.search_index import FaqSearchIndex
    index, faq_ids, vecs = _make_index_with_faqs(db_session)
    query = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    results = index.search(query, top_k=3)
    # 最上位は faq_ids[0]（完全一致）
    assert results[0][0] == faq_ids[0]
    assert results[0][1] > results[1][1]  # スコアは降順


def test_search_index_build_from_db(db_session):
    """build() でDBから全ベクトルを読み込んで索引を再構築できること。"""
    from app.faq.search_index import FaqSearchIndex
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository

    faq_repo = FaqRepository()
    emb_repo = FaqEmbeddingRepository()
    faq = faq_repo.create(db_session, question="Q?", answer="A.")
    db_session.flush()
    vec = np.array([1.0, 0.0], dtype=np.float32)
    emb_repo.upsert(db_session, faq.id, 2, vec.tobytes())
    db_session.commit()

    index = FaqSearchIndex()
    index.build(db_session)
    results = index.search(vec, top_k=1)
    assert len(results) == 1
    assert results[0][0] == faq.id


def test_search_index_is_consistent_with_db_true(db_session):
    """DB件数と索引件数が一致する場合 is_consistent_with_db() が True。"""
    index, _, _ = _make_index_with_faqs(db_session)
    assert index.is_consistent_with_db(db_session) is True


def test_search_index_is_consistent_with_db_false(db_session):
    """DBに追加した後に索引を更新しない場合 False になること。"""
    from app.faq.search_index import FaqSearchIndex
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    index, _, _ = _make_index_with_faqs(db_session)
    # 索引を更新せずDBにだけ追加
    faq_repo = FaqRepository()
    emb_repo = FaqEmbeddingRepository()
    faq = faq_repo.create(db_session, question="新しいQ?", answer="A.")
    db_session.flush()
    vec = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)
    emb_repo.upsert(db_session, faq.id, 4, vec.tobytes())
    db_session.commit()
    assert index.is_consistent_with_db(db_session) is False


def test_search_index_empty_returns_empty():
    """索引が空の場合 search は空リストを返すこと。"""
    from app.faq.search_index import FaqSearchIndex
    index = FaqSearchIndex()
    results = index.search(np.array([1.0, 0.0], dtype=np.float32), top_k=5)
    assert results == []


# ---------------------------------------------------------------------------
# Task 3.1: FaqEmbeddingService
# ---------------------------------------------------------------------------

def _make_mock_adapter(dim: int = 4):
    """テスト用モックアダプターを返す。"""
    import numpy as np
    from app.faq.embedding import FaqEmbeddingAdapter

    class FakeModel:
        def encode(self, text: str):
            return np.ones(dim, dtype=np.float32)

    adapter = FaqEmbeddingAdapter(model_path=None)
    adapter._model = FakeModel()
    return adapter


def test_embedding_service_generate_and_store(db_session):
    """generate_and_store で faq_embedding が保存され、索引に追加されること。"""
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    from app.faq.search_index import FaqSearchIndex
    from app.faq.services import FaqEmbeddingService

    faq_repo = FaqRepository()
    faq = faq_repo.create(db_session, question="Q?", answer="A.")
    db_session.flush()

    adapter = _make_mock_adapter()
    emb_repo = FaqEmbeddingRepository()
    index = FaqSearchIndex()
    svc = FaqEmbeddingService(adapter=adapter, repo=emb_repo, index=index)

    result = svc.generate_and_store(db_session, faq)
    db_session.commit()

    assert result is not None
    assert result.faq_id == faq.id
    # 索引にも追加されていること
    query = np.ones(4, dtype=np.float32)
    hits = index.search(query, top_k=1)
    assert len(hits) == 1 and hits[0][0] == faq.id


def test_embedding_service_skips_when_adapter_not_ready(db_session):
    """adapter.is_ready() が False の場合、何も書き込まずに None を返すこと。"""
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    from app.faq.search_index import FaqSearchIndex
    from app.faq.services import FaqEmbeddingService
    from app.faq.embedding import FaqEmbeddingAdapter

    faq = FaqRepository().create(db_session, question="Q?", answer="A.")
    db_session.flush()

    adapter = FaqEmbeddingAdapter(model_path=None)  # is_ready() == False
    svc = FaqEmbeddingService(adapter=adapter, repo=FaqEmbeddingRepository(), index=FaqSearchIndex())
    result = svc.generate_and_store(db_session, faq)
    db_session.commit()

    assert result is None
    assert len(FaqEmbeddingRepository().load_all(db_session)) == 0


# ---------------------------------------------------------------------------
# Task 3.2: FaqSearchService
# ---------------------------------------------------------------------------

def _setup_search_service(db_session, questions_answers=None):
    """モックアダプター付きの FaqSearchService を作成してFAQを登録する。"""
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    from app.faq.search_index import FaqSearchIndex
    from app.faq.services import FaqEmbeddingService, FaqSearchService

    adapter = _make_mock_adapter(dim=4)  # 常に ones(4) を返す
    faq_repo = FaqRepository()
    emb_repo = FaqEmbeddingRepository()
    index = FaqSearchIndex()
    emb_svc = FaqEmbeddingService(adapter=adapter, repo=emb_repo, index=index)
    search_svc = FaqSearchService(adapter=adapter, index=index, repo=faq_repo)

    if questions_answers is None:
        questions_answers = [("Q1?", "A1."), ("Q2?", "A2.")]

    for q, a in questions_answers:
        faq = faq_repo.create(db_session, question=q, answer=a)
        db_session.flush()
        emb_svc.generate_and_store(db_session, faq)
    db_session.commit()
    return search_svc


def test_search_service_returns_candidates(db_session):
    """search が FaqSearchResult を返し、候補が含まれること。"""
    from app.faq.services import FaqSearchResult
    svc = _setup_search_service(db_session)
    result = svc.search(db_session, "質問", top_k=5)
    assert isinstance(result, FaqSearchResult)
    assert result.query == "質問"
    assert len(result.candidates) > 0


def test_search_service_confidence_in_range(db_session):
    """confidence は 0.0〜1.0 の範囲内であること。"""
    svc = _setup_search_service(db_session)
    result = svc.search(db_session, "テスト", top_k=5)
    for c in result.candidates:
        assert 0.0 <= c.confidence <= 1.0


def test_search_service_is_match_when_high_confidence(db_session):
    """全件同一ベクトルのため confidence が高く is_match=True になること。"""
    svc = _setup_search_service(db_session)
    result = svc.search(db_session, "テスト", top_k=5)
    # モックアダプターは全テキストに同一ベクトルを返すため confidence≒1.0
    assert all(c.is_match for c in result.candidates)
    assert result.has_match is True


def test_search_service_raises_when_adapter_not_ready(db_session):
    """adapter 未準備時に FaqEmbeddingError が送出されること。"""
    from app.faq.embedding import FaqEmbeddingAdapter, FaqEmbeddingError
    from app.faq.repositories import FaqRepository
    from app.faq.search_index import FaqSearchIndex
    from app.faq.services import FaqSearchService

    adapter = FaqEmbeddingAdapter(model_path=None)
    svc = FaqSearchService(adapter=adapter, index=FaqSearchIndex(), repo=FaqRepository())
    with pytest.raises(FaqEmbeddingError):
        svc.search(db_session, "テスト", top_k=5)


# ---------------------------------------------------------------------------
# Task 3.3: FaqAdminService
# ---------------------------------------------------------------------------

def _make_admin_service(db_session):
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    from app.faq.search_index import FaqSearchIndex
    from app.faq.markdown_parser import MarkdownParser
    from app.faq.services import FaqEmbeddingService, FaqAdminService
    adapter = _make_mock_adapter(dim=4)
    faq_repo = FaqRepository()
    emb_svc = FaqEmbeddingService(
        adapter=adapter,
        repo=FaqEmbeddingRepository(),
        index=FaqSearchIndex(),
    )
    return FaqAdminService(repo=faq_repo, parser=MarkdownParser(), embedding_service=emb_svc)


VALID_MD_2 = "## Q1?\n\nA1.\n\n## Q2?\n\nA2.\n"


def test_admin_service_import_faqs_success(db_session):
    """有効なMarkdownからFAQが一括登録されること。"""
    svc = _make_admin_service(db_session)
    saved = svc.import_faqs(db_session, VALID_MD_2)
    db_session.commit()
    assert len(saved) == 2
    assert saved[0].question == "Q1?"
    assert saved[1].question == "Q2?"


def test_admin_service_parse_error_raises(db_session):
    """Markdown 形式エラー時は MarkdownParseError が送出されること。"""
    from app.faq.markdown_parser import MarkdownParseError
    svc = _make_admin_service(db_session)
    with pytest.raises(MarkdownParseError):
        svc.import_faqs(db_session, "H2見出しなし\n")


def test_admin_service_duplicate_question_raises(db_session):
    """既存の質問文と重複する場合は ValueError が送出されること。"""
    svc = _make_admin_service(db_session)
    svc.import_faqs(db_session, "## Q1?\n\nA1.\n")
    db_session.commit()
    with pytest.raises(ValueError, match="すでに登録"):
        svc.import_faqs(db_session, "## Q1?\n\nA1 new.\n")


def test_admin_service_rollback_on_error(db_session):
    """エラー時はコミット済み分以外がロールバックされること。"""
    from app.faq.repositories import FaqRepository
    svc = _make_admin_service(db_session)
    # ファイル内重複でエラー
    from app.faq.markdown_parser import MarkdownParseError
    with pytest.raises(MarkdownParseError):
        svc.import_faqs(db_session, "## Q?\n\nA.\n\n## Q?\n\nA2.\n")
    # DB には何も保存されていないこと
    assert len(FaqRepository().list_all(db_session)) == 0


def test_faq_migration_idempotent():
    """同じマイグレーションを2回適用してもエラーにならない。"""
    DatabaseEngine().init(Settings())
    # 2回目 init は idempotent（_initialized フラグで守られる）
    DatabaseEngine().init(Settings())
    with DatabaseEngine().engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM foundation_meta WHERE schema_version = '003_faq_management_and_search'"))
        assert result.scalar() == 1


# ---------------------------------------------------------------------------
# Task 5.2: FAQ 結合テスト（HTTP レイヤー）
# ---------------------------------------------------------------------------

SAMPLE_MD = "## 有給休暇の申請方法は？\n\n3営業日前までに申請システムから申請してください。\n\n## 交通費の精算期限は？\n\n当月末日までに精算してください。\n"


def _make_test_client(adapter_ready: bool = True):
    """
    in-memory DB を使った TestClient を作成する。

    sqlite:///:memory: は接続ごとに異なるDBを作るため、StaticPool を使って
    全接続が同じ in-memory DB を共有するようにする。
    get_db / サービス依存を dependency_overrides で差し替える。

    Args:
        adapter_ready: False の場合は is_ready()==False のアダプターを使用する。
    """
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.faq.dependencies import get_faq_admin_service, get_faq_search_service
    from app.faq.embedding import FaqEmbeddingAdapter
    from app.faq.search_index import FaqSearchIndex
    from app.faq.repositories import FaqRepository, FaqEmbeddingRepository
    from app.faq.markdown_parser import MarkdownParser
    from app.faq.services import FaqEmbeddingService, FaqAdminService, FaqSearchService
    from app.dependencies import get_db
    from app.migrations import MigrationRunner
    from main import create_app

    # StaticPool: 全接続が同一の in-memory DB を共有する
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    migrations_dir = Path(__file__).parent.parent / "migrations"
    MigrationRunner(test_engine, migrations_dir).apply_migrations()

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()

    class FakeModel:
        def encode(self, text: str):
            return np.ones(4, dtype=np.float32)

    mock_adapter = FaqEmbeddingAdapter(model_path=None)
    if adapter_ready:
        mock_adapter._model = FakeModel()

    shared_index = FaqSearchIndex()

    def make_admin_service():
        emb_svc = FaqEmbeddingService(
            adapter=mock_adapter,
            repo=FaqEmbeddingRepository(),
            index=shared_index,
        )
        return FaqAdminService(
            repo=FaqRepository(),
            parser=MarkdownParser(),
            embedding_service=emb_svc,
        )

    def make_search_service():
        return FaqSearchService(
            adapter=mock_adapter,
            index=shared_index,
            repo=FaqRepository(),
        )

    # 認証依存をテスト用スタブで上書き（Cookie "session" で判定）
    from app.auth.dependencies import require_admin as _ra, require_authenticated_user as _rau
    from app.auth.schemas import CurrentUser as _CU
    from fastapi import Cookie as _Cookie, HTTPException as _HTTPExc

    def mock_require_admin(session: str | None = _Cookie(default=None, alias="session")) -> _CU:
        if session == "admin-session":
            return _CU(id=1, username="admin", role="admin")
        if session is None:
            raise _HTTPExc(status_code=401, detail="Authentication required")
        raise _HTTPExc(status_code=403, detail="Forbidden")

    def mock_require_authenticated(session: str | None = _Cookie(default=None, alias="session")) -> _CU:
        if session in ("admin-session", "user-session"):
            role = "admin" if session == "admin-session" else "user"
            return _CU(id=1 if role == "admin" else 2, username=role, role=role)
        raise _HTTPExc(status_code=401, detail="Authentication required")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_faq_admin_service] = make_admin_service
    app.dependency_overrides[get_faq_search_service] = make_search_service
    app.dependency_overrides[_ra] = mock_require_admin
    app.dependency_overrides[_rau] = mock_require_authenticated

    return TestClient(app, raise_server_exceptions=False), shared_index


def test_api_upload_faqs_admin_success():
    """管理者が有効な Markdown をアップロードすると 201 が返ること。"""
    client, _ = _make_test_client()
    resp = client.post(
        "/api/faqs/upload",
        files={"file": ("faqs.md", SAMPLE_MD.encode(), "text/markdown")},
        cookies={"session": "admin-session"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert len(data) == 2
    assert data[0]["question"] == "有給休暇の申請方法は？"


def test_api_upload_faqs_no_auth_returns_401():
    """未認証でアップロードすると 401 が返ること。"""
    client, _ = _make_test_client()
    resp = client.post(
        "/api/faqs/upload",
        files={"file": ("faqs.md", SAMPLE_MD.encode(), "text/markdown")},
    )
    assert resp.status_code == 401, resp.text


def test_api_upload_faqs_non_admin_returns_403():
    """一般ユーザーでアップロードすると 403 が返ること。"""
    client, _ = _make_test_client()
    resp = client.post(
        "/api/faqs/upload",
        files={"file": ("faqs.md", SAMPLE_MD.encode(), "text/markdown")},
        cookies={"session": "user-session"},
    )
    assert resp.status_code == 403, resp.text


def test_api_upload_faqs_wrong_extension_returns_415():
    """拡張子が .md でないファイルは 415 が返ること。"""
    client, _ = _make_test_client()
    resp = client.post(
        "/api/faqs/upload",
        files={"file": ("faqs.txt", b"content", "text/plain")},
        cookies={"session": "admin-session"},
    )
    assert resp.status_code == 415, resp.text


def test_api_upload_faqs_too_large_returns_413():
    """10MB 超のファイルは 413 が返ること。"""
    client, _ = _make_test_client()
    big_content = b"x" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        "/api/faqs/upload",
        files={"file": ("faqs.md", big_content, "text/markdown")},
        cookies={"session": "admin-session"},
    )
    assert resp.status_code == 413, resp.text


def test_api_upload_faqs_invalid_markdown_returns_422():
    """H2 見出しなしの Markdown は 422 が返ること。"""
    client, _ = _make_test_client()
    resp = client.post(
        "/api/faqs/upload",
        files={"file": ("faqs.md", b"H2\xe8\xa6\x8b\xe5\x87\xba\xe3\x81\x97\xe3\x81\xaa\xe3\x81\x97", "text/markdown")},
        cookies={"session": "admin-session"},
    )
    assert resp.status_code == 422, resp.text


def test_api_upload_then_embedding_stored_and_index_updated():
    """アップロード後に faq_embedding が作成され、索引が同期されること。"""
    from app.faq.repositories import FaqEmbeddingRepository
    client, shared_index = _make_test_client()
    resp = client.post(
        "/api/faqs/upload",
        files={"file": ("faqs.md", SAMPLE_MD.encode(), "text/markdown")},
        cookies={"session": "admin-session"},
    )
    assert resp.status_code == 201
    # 索引に2件追加されていること
    assert len(shared_index._faq_ids) == 2


def test_api_search_returns_results():
    """認証済みユーザーが検索すると候補が返ること。"""
    client, shared_index = _make_test_client()
    # まずFAQを登録
    client.post(
        "/api/faqs/upload",
        files={"file": ("faqs.md", SAMPLE_MD.encode(), "text/markdown")},
        cookies={"session": "admin-session"},
    )
    resp = client.post(
        "/api/faqs/search",
        json={"query": "有給休暇", "top_k": 5},
        cookies={"session": "user-session"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "candidates" in data
    assert "has_match" in data


def test_api_search_no_auth_returns_401():
    """未認証で検索すると 401 が返ること。"""
    client, _ = _make_test_client()
    resp = client.post(
        "/api/faqs/search",
        json={"query": "テスト", "top_k": 5},
    )
    assert resp.status_code == 401, resp.text


def test_api_search_adapter_not_ready_returns_503():
    """Embedding adapter 未準備の場合は 503 が返ること。"""
    client, _ = _make_test_client(adapter_ready=False)
    resp = client.post(
        "/api/faqs/search",
        json={"query": "テスト", "top_k": 5},
        cookies={"session": "user-session"},
    )
    assert resp.status_code == 503, resp.text


def test_ui_upload_page_requires_admin():
    """GET /faqs/upload は未認証だと 401 が返ること。"""
    client, _ = _make_test_client()
    resp = client.get("/faqs/upload")
    assert resp.status_code == 401, resp.text


def test_ui_upload_page_admin_returns_200():
    """管理者は GET /faqs/upload で 200 HTML が返ること。"""
    client, _ = _make_test_client()
    resp = client.get("/faqs/upload", cookies={"session": "admin-session"})
    assert resp.status_code == 200
    assert "FAQ" in resp.text
