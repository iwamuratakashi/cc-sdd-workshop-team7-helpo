# Research & Design Decisions

## Summary
- **Feature**: helpo-foundation
- **Discovery Scope**: New Feature / greenfield
- **Key Findings**:
  - FastAPI + Uvicorn + SQLAlchemy + SQLite の一体型構成が、Windows CPU 研修用 MVP の起動・永続化要件を満たす。
  - Pydantic Settings を使うことで、環境変数と `.env` ファイルの型安全な読み込み・検証が統一できる。
  - RouterRegistry パターンにより、後続仕様が `app/routers/` や `main.py` を直接変更せずにルーター追加できる。

## Research Log

### Technology Stack Selection
- **Context**: Windows GPU なし PC で動作し、外部クラウドサービスを必須としないアプリ基盤を選定する必要がある。
- **Sources Consulted**:
  - FastAPI 公式ドキュメント
  - SQLAlchemy 2.x ドキュメント
  - Pydantic Settings ドキュメント
- **Findings**:
  - FastAPI は ASGI 対応で、Python 3.10+ と Uvicorn で簡易に起動できる。
  - SQLAlchemy 2.x は SQLite ファイル永続化に対応し、追加ミドルウェア不要。
  - Jinja2 + FastAPI static files によるサーバーサイドレンダリングで、SPA 構築を不要にできる。
- **Implications**: 最小限の依存関係で起動・画面表示・永続化を実現できる。

### Configuration Management
- **Context**: データベースパス、ホスト、ポート、ローカル AI モデルパスを外部化したい。
- **Sources Consulted**: Pydantic Settings 公式ドキュメント
- **Findings**:
  - Pydantic v2 Settings により、`DATABASE_URL`, `APP_HOST`, `APP_PORT`, `DEBUG`, `LOCAL_LLM_PATH`, `LOCAL_EMBEDDING_PATH` を型安全に読み込める。
  - 必須項目の欠落は起動前に検証し、fail-fast できる。
- **Implications**: `app/config.py` に集約し、下位モジュールへ `Settings` 依存注入で提供する。

### Persistence Strategy
- **Context**: 追加 DB サーバー不要で、ローカルファイルにデータを保存したい。
- **Findings**:
  - SQLite ファイル接続で十分（`sqlite:///./helpo.db`）。
  - 起動時に baseline SQL を適用する最小マイグレーションで、Alembic 導入前の MVP を支えられる。
  - SQLAlchemy `DeclarativeBase` 継承で下位モジュールのモデル拡張を統一できる。
- **Implications**: `app/db.py` にエンジン・セッションを、`app/base_models.py` に `BaseEntity` を定義する。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Monolith | 単一 FastAPI アプリケーション内にレイヤー配置 | シンプル、1 コマンド起動、研修に適合 | 大規模化時に分解が必要 | 選択。MVP スコープに最適 |
| Microservices | 認証・FAQ・AI を別サービス化 | 独立スケール | ネットワーク・運用コストが大きい | 研修用に過大 |
| Clean Architecture | ドメイン層とインフラ層を分離 | テスト容易 | ボイラーレートが増える | 採用せず、依存方向のみ規律で保つ |

## Design Decisions

### Decision: 単体 FastAPI Monolith
- **Context**: 研修参加者がすぐに動かせる基盤が必要。
- **Alternatives Considered**:
  1. Microservices — 運用複雑性が高い
  2. Django — 学習曲線と不要な機能が多い
- **Selected Approach**: FastAPI + SQLAlchemy + SQLite の単体アプリケーション
- **Rationale**: 依存方向を Types → Config → Repository → Service → Runtime → UI に規律することで、拡張性を保ちつつ最小構成を実現できる。
- **Trade-offs**: 大規模化時には再設計が必要だが、MVP では可読性と起動容易性を優先。

### Decision: RouterRegistry 拡張ポイント
- **Context**: 後続仕様が foundation の `app/routers/` や `main.py` を直接変更しないようにしたい。
- **Alternatives Considered**:
  1. 各機能が `app/routers/` にファイルを追加 — 競合リスクが高い
  2. 下位モジュールが FastAPI インスタンスを直接取得 — 結合が強い
- **Selected Approach**: `app/router_registry.py` に `register_router` / `include_registered_routers` を提供し、`create_app` で include する。
- **Rationale**: 下位仕様は自己のルーター登録のみ責任を持ち、foundation は一貫した起動フローを保つ。

### Decision: Pydantic Settings による設定管理
- **Context**: 環境ごとの設定を安全に読み込みたい。
- **Selected Approach**: `pydantic-settings` で `app/config.py` を実装。
- **Rationale**: 型検証、`.env` 読み込み、デフォルト値を 1 つのモデルで表現できる。
- **Follow-up**: ローカル AI モデルパスは必須でなく、未設定時は `None` を許容する。

### Decision: SQLite ファイル永続化と最小マイグレーション
- **Context**: 追加ミドルウェアなしでデータ保存したい。
- **Selected Approach**: SQLAlchemy SQLite エンジン + `migrations/baseline.sql` による起動時マイグレーション。
- **Rationale**: 追加 DB サーバー不要、Windows CPU で動作、軽量。
- **Follow-up**: スキーマ変更時には `alembic_version` または `foundation_meta` テーブルでバージョン追跡する。

## Risks & Mitigations
- **Risk**: 後続仕様が foundation ファイルを直接変更して結合が強くなる — `RouterRegistry` と依存方向ルールで明示的に分離する。
- **Risk**: SQLite の同時書き込み制限 — MVP では少人数利用を想定し、必要時に接続プール調整を検討する。
- **Risk**: ローカル AI モデルパスが未設定でもアプリが起動しない — Pydantic Settings で必須ではなく、下位モジュールが `None` をハンドルする。

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Uvicorn](https://www.uvicorn.org/)
