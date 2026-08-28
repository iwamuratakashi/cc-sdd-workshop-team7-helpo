# Implementation Plan

## 実装方針（スタブAI回答 ＋ FAQモック）

本タスクではLLM生成の実装を除外し、スタブ方式でAI回答を実現する。
`is_match=true`の候補が存在する場合、適合上位FAQの登録回答に「（AIによる回答予定）」を
付加した文字列を、`ai_answer`ステータスのAI回答として返す。

内部のステータス体系・DTO・APIはLLM実装を前提とした設計を維持する。

### FAQ依存の扱い（faq-management-and-search 未実装）

`faq-management-and-search` スペックはまだ実装されていないため、
FAQテーブル・`FaqSearchService` ともに存在しない。以下の方針を採る。

| 項目 | 方針 |
|---|---|
| `FaqCandidate` / `FaqSearchResult` | デザイン定義どおりの型を `app/chat/faq_types.py` に定義し、上流実装に差し替え可能にする |
| `FaqSearchService` | `app/chat/faq_mock.py` に固定データを返すモック実装を作成し、`ChatService` に注入する |
| モックデータ | 実際の業務シナリオを想定した数件の固定FAQデータを `app/chat/faq_mock.py` 内に定義する |
| 上流実装後の差し替え | `ChatService` はインターフェース型にのみ依存するため、モッククラスを本物のクラスに差し替えるだけで完結する |

### 既存インフラ（helpo-foundation）との接点

| 既存リソース | chat feature での利用方法 |
|---|---|
| `app/dependencies.py:get_db` | `ChatService.ask` の DB セッション注入に使用（FAQモック使用中はDB参照しないが引数として受け取る） |
| `app/router_registry.py:RouterRegistry` | chat router 登録に使用（`pages_router` より先に登録） |
| `app/templates/base.html` | `app/templates/chat/index.html` で `{% extends "base.html" %}` |
| `app/config.py:Settings` | 変更しない。ChatSettings は `app/chat/settings.py` に独立して作成 |
| `app/routers/pages.py` | `GET /chat` プレースホルダーを削除し、chat router に置き換える |
| `main.py` | `registry.register_router(chat_router)` を `pages_router` 登録前に追加する |
| `app/migrations.py:MigrationRunner` | FAQテーブルなし・DBマイグレーションなし（chat-historyスペックが担う） |

### 除外・延期する要件（LLM実装フェーズで対応）

| 要件ID | 内容 | 延期理由 |
|--------|------|---------|
| 3.3 | Windows CPU-only実行 | LLM未実装のため不要 |
| 3.4 | モデル採用ゲート | LLM未実装のため不要 |
| 3.5 | 不正生成出力のFAQ直接回答フォールバック | スタブは常に検証済み出力を返すため不要 |
| 4.1 | LLM利用不能時のFAQ直接回答 | LLM未実装のため不要 |
| 4.2 | タイムアウト時のFAQ直接回答 | LLM未実装のため不要 |
| 4.3 | LLM利用不能＋適合なし時のAI利用不可 | LLM未実装のため不要 |
| 6.3 | CPU負荷下収束 | LLM未実装のため不要 |
| 6.5 | モデル変更時の再検証 | LLM未実装のため不要 |

## 実装タスク

- [x] 1. チャット設定とFAQ型・モックを整備する
- [x] 1.1 ChatSettingsを実装する
  - `app/chat/settings.py` に `pydantic_settings.BaseSettings` を継承した `ChatSettings` を作成し、`.env` から `CHAT_MAX_QUESTION_CHARS`（正整数）・`CHAT_CONTACT_GUIDANCE`（trim後1〜1000文字、制御文字禁止）・`CHAT_SERVER_ERROR_MESSAGE` を読み込む（`app/config.py` の `Settings` と同じ読み込みパターン）
  - 不正な値はアプリ起動前に Pydantic バリデーションで拒否し、LLMパス・タイムアウト・manifest設定は保持しない
  - `app/config.py` は変更しない
  - 完了状態: 正常な設定値でアプリが起動し、不正値の場合は起動前にバリデーションエラーを観測できる
  - _Requirements: 6.2_
  - _Boundary: ChatSettings_

- [x] 1.2 FAQ型定義とモック検索サービスを実装する
  - `app/chat/faq_types.py` にデザイン定義どおりの `FaqCandidate(faq_id, question, answer, confidence, is_match)` と `FaqSearchResult(query, candidates, has_match)` をデータクラスまたは Pydantic モデルで定義する（上流実装との差し替えを想定した型契約）
  - `app/chat/faq_mock.py` に `FaqMockSearchService` クラスを作成し、`search(db, query, top_k) -> FaqSearchResult` メソッドが固定FAQデータから `query` 文字列に部分一致する候補を返すか、一致がなければ `has_match=False` の結果を返すモック実装にする
  - モックデータは休暇・経費・福利厚生など実際の業務シナリオを想定した5件程度の固定FAQを `app/chat/faq_mock.py` 内に定義する（`is_match=True`・`confidence` 付き）
  - `ChatService` は `FaqSearchResult` / `FaqCandidate` 型にのみ依存し、`FaqMockSearchService` を直接importしない（依存注入で切り替え可能にする）
  - 完了状態: `FaqMockSearchService.search` がクエリ文字列に応じて適合ありまたは適合なしの `FaqSearchResult` を返し、型が `faq_types.py` の定義と一致する
  - _Requirements: 2.1_
  - _Boundary: FaqTypes, FaqMockSearchService_

- [x] 2. FAQ根拠選択とスタブAI回答を実装する
- [x] 2.1 信頼できるFAQ根拠だけを安定選択する
  - `FaqSearchResult` から `has_match=True` かつ `is_match=True` の候補だけを `confidence` 降順・`faq_id` 昇順で安定ソートし選択する
  - 未適合候補（`is_match=False`）、外部文書、会話履歴が選択結果に含まれないことを保証する
  - 完了状態: 同じ検索結果から常に同じ適合候補順が得られ、`is_match=False` の候補が選択結果に現れない
  - _Requirements: 2.1, 2.2, 2.4, 3.1_
  - _Boundary: GroundingPolicy_

- [x] 2.2 適合上位FAQの回答にスタブ文言を付加し、AI回答として生成する
  - 適合候補の先頭1件の登録回答文末に「（AIによる回答予定）」を付加したテキストを回答として生成する
  - 使用した候補1件だけを回答根拠として返し、残りの適合候補を回答根拠に含めない
  - 完了状態: 適合候補の先頭FAQ回答に文言が付加された文字列と、その1件のみを根拠とした結果が返る
  - _Requirements: 3.1, 5.2_
  - _Boundary: GroundingPolicy_

- [x] 3. チャット回答サービスを統合する
- [x] 3.1 FAQ検索からスタブAI回答・該当FAQなしへの状態遷移を統合する
  - `ChatService.ask(db: Session, current: CurrentUser, question: str)` が注入された検索サービス（現時点では `FaqMockSearchService`）の `search(db, query, top_k=5)` を呼び出し、適合候補あり→`ai_answer`・適合候補なし→`no_match` のいずれかへ収束させる
  - FAQ検索失敗・予期しない例外は `ChatStatus` に変換せず、そのまま上位へ伝播させて Foundation の `handle_exception`（`main.py`）に HTTP 500 を委譲する
  - `app/chat/dependencies.py` に `get_chat_service` FastAPI 依存を定義し、`ChatService` が `get_db`（`app.dependencies`）と `GroundingPolicy` と検索サービスを受け取れるようにする。検索サービスは `FaqMockSearchService` を `get_chat_service` 内で直接インスタンス化して注入する
  - chatサービスが通常ログに status・duration だけを記録し、質問全文・FAQ全文・回答全文を出さない
  - `no_match` 時は `sources=[]` とし、回答テキストには `ChatSettings.contact_guidance` を使用する
  - 完了状態: 適合候補ありの質問では `ai_answer` と根拠1件が、適合候補なしでは `no_match` と空根拠が返り、検索失敗時は例外が伝播して HTTP 500 となる
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 4.4, 4.5, 5.3, 6.1, 6.4_
  - _Boundary: ChatService_
  - _Depends: 2.2_

- [x] 4. 認証済みチャットAPIとUI画面を実装する
- [x] 4.1 質問受付APIを認証・入力検証へ接続し、プレースホルダーを置き換える
  - `ChatQuestionRequest`・`ChatSourceResponse`・`ChatAnswerResponse` の Pydantic v2 DTO と `ChatStatus` 型（`"ai_answer" | "no_match"`）を `app/chat/schemas.py` に定義し、question を trim 後に空値と最大長で 422 拒否する
  - `require_authenticated_user` を全 route に適用し、HTML 未認証は 303、API 未認証は JSON 401（本文なし）で返す
  - `app/chat/router.py` の `APIRouter` を作成し、`app/routers/pages.py` の `GET /chat` プレースホルダーを削除した上で、`main.py` の `create_app` 内で `registry.register_router(chat_router)` を `pages_router` より前に追加して chat route が優先されるようにする
  - `GET /chat`（HTML）と `POST /api/chat`（JSON）を登録し、成功は HTTP 200、FAQ検索失敗・予期しないエラーは HTTP 500 で返す
  - `Jinja2Templates(directory="app/templates")` を使い、テンプレートを `"chat/index.html"` として参照する
  - 完了状態: 認証済みの有効質問だけが `ChatService.ask` に渡り、未認証・空入力・文字数超過・FAQ検索失敗が仕様どおりのHTTPステータスと内容で返る
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.4, 4.5, 5.1_
  - _Boundary: ChatRouter, ChatSchemas_

- [x] 4.2 チャット画面を実装する
  - `app/templates/chat/index.html` を作成し、`{% extends "base.html" %}` で既存の `app/templates/base.html` を継承する
  - 質問入力（textarea・文字数カウンター・送信ボタン）と回答エリア（状態ラベル・回答テキスト・出典FAQ一覧）を構成し、全テキストは Jinja2 の autoescape で HTML エスケープして表示する
  - 送信開始時に送信ボタンを非活性化して重複操作を抑止し、回答受信後に再活性化する
  - バリデーションエラー（空入力・文字数超過）は入力フォームのすぐ上に表示し、通信エラー（HTTP 500・ネットワークエラー）は画面上部（ヘッダー直下）の共通エラーエリアに内部詳細なしで表示する
  - `no_match` 時は出典エリアに「出典が見つかりません」のみを表示し、それ以外の文言を出典エリアに追加しない
  - 完了状態: ブラウザ上で質問を送信し、処理中表示から回答・出典の一体表示へ遷移でき、未認証時はログイン画面へリダイレクトされる
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 4.4, 4.5, 5.1, 5.2, 5.3_
  - _Boundary: ChatUI_

- [x] 6. チャット画面に初期表示エリアを追加する
- [x] 6.1 質問未送信時の初期表示メッセージを実装する
  - `app/templates/chat/index.html` の回答エリアが非表示の間（質問未送信時・画面初期表示時）、代わりに `empty_state` エリアとして「ご質問をどうぞ」等の文言を表示する
  - 送信ボタン押下後（送信開始時）に `empty_state` エリアを非表示にし、処理中インジケータを表示する
  - 回答受信後は `empty_state` エリアを非表示のままにし、回答エリアを表示する（一度質問した後はリセットまで `empty_state` を再表示しない）
  - 完了状態: 画面初期表示時に `empty_state` の文言が表示され、送信後は非表示になり、回答エリアと同時に表示されることがない
  - _Requirements: 1.1, 1.2_
  - _Boundary: ChatUI_

- [x] 5. 境界・受入条件を検証する
- [x] 5.1 根拠・状態・ログのコンポーネントテストを追加する
  - `FaqMockSearchService` を直接使用し（外部モック不要）、`GroundingPolicy` と `ChatService` を単体でテストする
  - `GroundingPolicy` の安定根拠選択・未適合候補排除・スタブ文言付加・使用根拠の絞り込みをユニットテストで確認する
  - `ChatService.ask` の `ai_answer`/`no_match` ステータスごとに回答と根拠が厳密に一致し、FAQ検索失敗時に例外が `ChatStatus` に変換されず伝播することをテストする
  - `ChatSettings` のバリデーション境界値（最大文字数・制御文字・空文字列）を fail-closed でテストする
  - 通常ログに質問全文・FAQ全文・回答全文が含まれないことをテストする
  - `test_foundation.py` と同じ `DatabaseEngine.reset()` + インメモリ SQLite パターンを使用する
  - 完了状態: `tests/chat/` 配下の全ユニットテストが合格し、未適合候補の混入・機密本文ログを検出できる
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 3.1, 5.2, 6.2, 6.4_
  - _Boundary: ChatTestSuite_

- [x] 5.2 実際の上流境界を通す結合・E2Eテストを追加する
  - `TestClient(create_app())` を使い（`test_foundation.py` の `test_root_page` と同じパターン）、`POST /api/chat` からレスポンスまでの主要フローを `FaqMockSearchService` 経由で検証する
  - `ai_answer`（モック適合あり質問）と `no_match`（モック適合なし質問）の各経路を確認する
  - HTML 303・API 401・422・500 の各エラー経路を確認する
  - networkをブロックした状態でも回答が返り、外部AIサービスへの通信が発生しないことを確認する
  - `app/routers/pages.py` の `/chat` プレースホルダーが削除され、chat router が正しく優先されることを確認する
  - 完了状態: 結合・E2Eテストが主要フローと拒否系を通過し、範囲外route（履歴・共有・export等）が存在しない
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.5, 3.2, 4.4, 4.5, 5.1, 5.3, 6.1_
  - _Boundary: ChatIntegrationTestSuite_
