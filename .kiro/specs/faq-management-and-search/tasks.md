# Implementation Plan

## 実装タスク

- [ ] 1. FAQ用スキーマと設定を追加する
- [ ] 1.1 FAQとEmbeddingテーブルのマイグレーションを追加する
  - `faq` テーブル（質問文・回答文）と `faq_embedding` テーブル（ベクトルバイト列）を定義する。
  - `faq_embedding.faq_id` に外部キー（CASCADE）と一意索引を設定する。
  - foundation の `MigrationRunner` を通じて、認証スキーマの次に適用する。
  - 完了状態: 空DBおよび認証スキーマ適用済みDBの双方でマイグレーションが成功し、両テーブルが存在する。
  - _Requirements: 1.1, 1.5, 3.1, 3.3, 5.2_
  - _Boundary: FaqMigration_

- [ ] 1.2 FAQ用設定を機能ローカルに追加する
  - `FaqSettings` を作成し、Embedding モデル固有の設定を含む。
  - foundation の `ConfigManager` 拡張ポイントを通じて読み込み・検証する。
  - 完了状態: FAQ固有設定が読み込まれ、不正値は起動前に拒否される。
  - _Requirements: 5.1_
  - _Boundary: FaqSettings_

- [ ] 2. FAQ登録の基盤パーツを実装する
- [ ] 2.1 (P) FAQエンティティとリポジトリを実装する
  - `BaseEntity` を継承した `Faq` と `FaqRepository` を実装する。
  - 作成・一覧・ID取得を提供し、質問文の重複はアプリケーション層で検証できるようにする。
  - トランザクション境界は呼び出し元に委ね、リポジトリ内で commit しない。
  - 完了状態: テスト用DBでFAQの作成・一覧・取得がトランザクション内で一貫して動作する。
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - _Boundary: FaqRepository_
  - _Depends: 1.1_

- [ ] 2.2 (P) Markdownパーサーを実装する
  - H2 見出しを質問文、後続の段落を回答文として解釈する。
  - 空の質問・回答、ファイル内重複、有効なQ&Aが1つもない場合を検出する。
  - 完了状態: 正しいMarkdownはQ&Aリストを返し、不正な入力はエラーとなる。
  - _Requirements: 1.1, 1.4, 1.5_
  - _Boundary: MarkdownParser_

- [ ] 2.3 (P) Embeddingアダプターを実装する
  - 設定されたローカルモデルパスがあればロードし、未設定時は `is_ready()` が False を返す。
  - `encode(text)` は `numpy.float32` ベクトルを CPU で生成する。
  - 未検証モデルの自動ダウンロード・外部AIサービスへの送信を行わない。
  - 完了状態: モックまたは有効なローカルモデルパスで質問文からfloat32ベクトルが取得できる。
  - _Requirements: 3.1, 3.3, 3.4, 5.1, 5.3_
  - _Boundary: FaqEmbeddingAdapter_
  - _Depends: 1.2_

- [ ] 2.4 (P) Embeddingリポジトリを実装する
  - `FaqEmbedding` エンティティと `FaqEmbeddingRepository` を実装する。
  - `float32` 配列のバイト列と次元数を永続化し、`faq_id` での upsert/load_all を提供する。
  - 完了状態: ベクトルの保存・読み出しが正しく動作し、`faq_id` の一意性が保たれる。
  - _Requirements: 3.1, 3.4_
  - _Boundary: FaqEmbeddingRepository_
  - _Depends: 1.1_

- [ ] 2.5 検索索引を実装する
  - インメモリコサイン類似度索引を構築し、`build`/`upsert`/`search`/`is_consistent_with_db` を提供する。
  - DBから全ベクトルを読み出して再構築でき、検索時にDB接続を必要としない。
  - 完了状態: FAQ変更後の検索結果が最新DB内容を反映する。
  - _Requirements: 3.2, 3.4, 4.1_
  - _Boundary: FaqSearchIndex_
  - _Depends: 2.4_

- [ ] 3. FAQドメインサービスを実装する
- [ ] 3.1 Embedding生成サービスを実装する
  - FAQ保存時に質問文を `FaqEmbeddingAdapter` で encode し、`FaqEmbeddingRepository` と `FaqSearchIndex` へ upsert する。
  - アダプター未準備時は何も書き込まず、検索側で 503 となる状態を残す。
  - 完了状態: FAQ作成後に `faq_embedding` テーブルとインメモリ索引に対応するベクトルが存在する。
  - _Requirements: 3.1, 3.2, 3.5_
  - _Boundary: FaqEmbeddingService_
  - _Depends: 2.1, 2.3, 2.4, 2.5_

- [ ] 3.2 類似検索サービスを実装する
  - クエリを encode し、`FaqSearchIndex` で上位K件を取得後、FAQ詳細を `FaqRepository` から読み出す。
  - 生のコサイン類似度を 0-1 に正規化・クランプし、実装所有の固定適合基準で `is_match`/`has_match` を判定する。
  - アダプター未準備時は 503 にマップされる専用例外を発生させる。
  - 完了状態: サンプル質問に対し、正しいFAQ候補が類似度順に返り、適合判定が正しく動作する。
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - _Boundary: FaqSearchService_
  - _Depends: 2.1, 2.3, 2.5_

- [ ] 3.3 FAQ登録サービスを実装する
  - Markdown コンテンツをパースし、各 FAQ を保存後に Embedding 生成サービスを呼び出す。
  - パースエラー、重複、または 1 件も保存できない場合はトランザクションをロールバックして例外を送出する。
  - 完了状態: 有効なMarkdownはFAQとEmbeddingが一括登録され、不正な入力はロールバックされる。
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.5_
  - _Boundary: FaqAdminService_
  - _Depends: 2.2, 3.1_

- [ ] 4. FAQ API と最小UIを実装する
- [ ] 4.1 FAQアップロードAPIと画面を実装する
  - `POST /api/faqs/upload` と `/faqs/upload` を実装し、`require_admin` を適用する。
  - ファイル形式 `.md` / MIME `text/markdown`、サイズ 10MB 以下を検証する。
  - 未認証は `/login` へ 303、非管理者は 403、形式/サイズ/内容エラーは 400/413/415/422 を返す。
  - 完了状態: 管理者でMarkdownアップロードが成功し、一般ユーザー/未認証は拒否される。
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_
  - _Boundary: FaqRouter, FaqUploadUI_
  - _Depends: 3.3_

- [ ] 4.2 FAQ検索APIを実装する
  - `POST /api/faqs/search` を実装し、`require_authenticated_user` を適用する。
  - Embedding 未準備時は 503、未認証は 401 を返す。
  - レスポンスは `FaqSearchResult` スキーマに従い、候補と `has_match` を含める。
  - 完了状態: 認証済みユーザーが問い合わせを送信すると、適合基準以上の候補が `is_match=True` で返る。
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - _Boundary: FaqRouter_
  - _Depends: 3.2_

- [ ] 5. 統合・テスト・起動時処理を実装する
- [ ] 5.1 FAQルーターと索引ライフサイクルを統合する
  - `FaqRouter` を foundation の `RouterRegistry` に登録する。
  - 起動時または索引不整合検出時に `FaqSearchIndex.build()` を呼び出す。
  - 完了状態: アプリ起動後、FAQアップロード・検索エンドポイントが利用可能になり、索引が最新状態を反映する。
  - _Requirements: 3.2, 5.1, 5.2_
  - _Boundary: FaqRouter, AppServer_
  - _Depends: 4.1, 4.2_

- [ ] 5.2 FAQ結合テストを作成する
  - `tests/test_faq.py` に、FAQアップロードの認可・形式・サイズ・内容エラー、Embedding更新・索引同期、類似検索・適合判定、503応答を検証するテストを作成する。
  - foundation の ASGI アプリ、DBセッション、マイグレーション、認証を通して実行する。
  - 完了状態: `pytest` ですべてのFAQ関連テストが合格する。
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3_
  - _Boundary: FaqTestSuite_
  - _Depends: 5.1_

- [ ]* 5.3 ローカルWindows CPU動作のスモークテストを実施する
  - Windows の GPU なし PC で `uvicorn` 起動し、FAQアップロードAPI/検索APIを手動または自動で動作確認する。
  - 外部AIサービスへのネットワーク呼び出しが発生しないことを確認する。
  - 完了状態: Windows CPU環境でFAQ作成から類似検索までの一連の動作が確認できる。
  - _Requirements: 5.1, 5.2_
  - _Boundary: FaqTestSuite_
  - _Depends: 5.2_
