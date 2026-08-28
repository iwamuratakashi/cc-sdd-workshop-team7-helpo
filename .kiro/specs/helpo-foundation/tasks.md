# Implementation Plan

## Task Format Template

- Major tasks group related sub-tasks.
- Each executable sub-task includes at least one observable completion condition.
- `_Requirements: N` lists only numeric requirement IDs from `requirements.md`.
- `_Boundary: ComponentName` declares the design component the task owns.

## 実装タスク

- [x] 1. プロジェクト構造と依存関係の整備
- [x] 1.1 Pythonプロジェクト設定を作成し、必要なパッケージを宣言する
  - `pyproject.toml` に FastAPI、Uvicorn、SQLAlchemy、Pydantic、Jinja2、python-dotenv を追加する
  - `.env.example` と `.gitignore` を追加する
  - `app` パッケージディレクトリと必要なサブディレクトリを作成する
  - 完了状態: `pip install -e .` が成功し、`app` パッケージを `import` できる
  - _Requirements: 8_
  - _Boundary: AppServer_
- [x] 1.2 テンプレート・静的ファイル用のディレクトリを整備する
  - `app/templates/` と `app/static/css/` を作成する
  - 空の `base.html`、`index.html`、`main.css` を配置する
  - 完了状態: FastAPI の `StaticFiles` と `Jinja2Templates` マウントパスが存在する
  - _Requirements: 5, 8_
  - _Boundary: WebLayout_

- [x] 2. 環境設定管理の実装
- [x] 2.1 設定モデルを作成し、読み込みと検証を行う
  - Pydantic Settings でデータベースURL、ホスト、ポート、デバッグフラグ、ローカルAIモデルパスを定義する
  - 必須項目が欠落している場合は起動前に明確なメッセージを出力して停止する
  - 設定値を下位モジュールに提供するインターフェースを整える
  - 完了状態: 単体テストで正しい値が読み込まれ、不正な値は拒否される
  - _Requirements: 2, 6_
  - _Boundary: ConfigManager_

- [x] 3. SQLite接続・マイグレーション基盤
- [x] 3.1 ローカルデータベース接続エンジンを作成する
  - SQLAlchemy SQLite エンジンとセッションファクトリを実装する
  - 接続先パスは ConfigManager から取得する
  - FastAPI 用の `get_db` 依存関数を提供する
  - 完了状態: テスト用 DB ファイルが作成され、セッションを開閉できる
  - _Requirements: 3, 4_
  - _Boundary: DatabaseEngine_
- [x] 3.2 マイグレーション実行の仕組みを実装する
  - 初期スキーマファイルまたは最小 Alembic 設定を用意する
  - 起動時に未適用のベーススキーマを適用する
  - 完了状態: 空のデータベース起動後にスキーマバージョンテーブルが存在する
  - _Requirements: 3_
  - _Boundary: MigrationRunner_

- [x] 4. 共通データアクセス層
- [x] 4.1 基本データモデルとリポジトリを実装する
  - 共通の Declarative Base と `created_at`/`updated_at` を持つ BaseEntity を定義する
  - セッションを受け取る基本 Repository パターンを実装する
  - 完了状態: テストエンティティの作成・検索・更新・削除が一貫して動作する
  - _Requirements: 4_
  - _Boundary: BaseRepository_

- [x] 5. 基本Web画面構成
- [x] 5.1 共通レイアウトとトップページを実装する
  - ヘッダー・メイン領域・フッターを持つ base テンプレートを作成する
  - 後続機能への仮ナビゲーションリンクを配置する（リンク先は実装せずプレースホルダー）
  - 完了状態: ブラウザでルートパスにアクセスするとレイアウトと仮リンクが表示される
  - _Requirements: 5_
  - _Boundary: WebLayout_
- [x] 5.2 静的スタイルを整備する
  - 全ページで共通の CSS を読み込む
  - 完了状態: ページのスタイルが一貫して適用されている
  - _Requirements: 5_
  - _Boundary: WebLayout_

- [x] 6. 起動・エラー処理の統合
- [x] 6.1 ASGI アプリと起動フローを統合する
  - 設定読み込み、DB 初期化、マイグレーション、ルーター登録を `create_app` にまとめる
  - ルーター登録は `RouterRegistry` 拡張インターフェースを通じて行い、下位機能が `app/routers/` や `main.py` を直接変更しないようにする
  - Uvicorn 起動コマンドを文書化する
  - 完了状態: Uvicorn 起動コマンドでサーバーが起動し、ルートパスに応答する
  - _Requirements: 1, 8_
  - _Boundary: AppServer_
- [x] 6.2 例外処理とロギングを実装する
  - 未処理例外をキャッチして汎用エラーレスポンスを返す
  - 起動失敗時は明確なメッセージを出力して終了する
  - 完了状態: 不正な設定で起動しようとするとエラーメッセージが表示され、正常時はエラーログが残る
  - _Requirements: 7, 1_
  - _Boundary: ErrorHandler_
- [x] 6.3 ルーター登録の拡張インターフェースを実装する
  - `app/router_registry.py` に `RouterRegistry` を作成し、`register_router` / `include_registered_routers` を定義する
  - foundation の `app/routers/` と `main.py` を下位機能が直接変更できないように、拡張ポイントとして機能する
  - 完了状態: 下位機能のルーターが登録用メソッドを通じて FastAPI アプリに include される
  - _Requirements: 1, 5, 8_
  - _Boundary: RouterRegistry_

- [x] 7. スモークテストと動作確認
- [x] 7.1 結合テストを作成する
  - 起動、トップページ、DB マイグレーションを検証する
  - 完了状態: `pytest` がすべて合格する
  - _Requirements: 1, 3, 5, 8_
  - _Boundary: TestSuite_

- [x] 8. 設計 Contracts の不足実装を補完する（要件・設計修正対応）
- [x] 8.1 ConfigManager に設計 Contracts で定義されたメソッドと型を追加する
  - `LocalAISettings` 型を `app/config.py` に追加する
  - `Settings.get_database_url() -> str` メソッドを実装する
  - `Settings.get_local_ai_settings() -> LocalAISettings | None` メソッドを実装する
  - 単体テストで各メソッドの動作を検証する
  - 完了状態: `pytest` が全件合格し、メソッドが設計の Contracts 通りに動作する
  - _Requirements: 2, 6_
  - _Boundary: ConfigManager_
- [x] 8.2 ロギング設定モジュールを作成し、エラーハンドラに組み込む
  - `app/logging_conf.py` を新規作成し、`configure_logging(debug)` と `log_exception(exc, context)` を実装する
  - `main.py` の `handle_exception` を `async` 対応にして `log_exception` を呼び出す
  - `lifespan` 起動時に `configure_logging()` を呼び出す
  - 完了状態: 未処理例外が発生した際にサーバーログへ詳細が記録され、利用者には汎用エラーレスポンスが返る
  - _Requirements: 7, 1_
  - _Boundary: ErrorHandler_
- [x] 8.3 base.html に `nav_extra` ブロックを追加する
  - `app/templates/base.html` の `<header>` 内に `{% block nav_extra %}{% endblock %}` を追加する
  - 下位機能がナビゲーション要素を `base.html` を直接変更せずに差し込める拡張ポイントを確保する
  - 完了状態: 下位機能テンプレートが `{% block nav_extra %}` を上書きすることでヘッダー内に独自 HTML を注入できる
  - _Requirements: 5, 6_
  - _Boundary: WebLayout_

## Implementation Notes
- `Settings` は `extra="ignore"` を設定しており、下位機能は独自の `BaseSettings` サブクラスを定義して拡張できる（`app/config.py` を直接変更しない）。
- `handle_exception` は `async def` が必須。FastAPI の例外ハンドラは非同期関数として登録する必要がある。
- `logging_conf.py` の `configure_logging()` は重複ハンドラを防ぐため `if not root_logger.handlers:` で条件付き追加している。テスト環境では `lifespan` を経由しない場合があるため、`get_logger()` で取得したロガーは既存設定を引き継ぐ。
