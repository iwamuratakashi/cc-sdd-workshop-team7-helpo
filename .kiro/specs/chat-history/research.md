# Research & Design Decisions

## Summary
- **Feature**: `chat-history`
- **Discovery Scope**: Extension（既存ai-helpdesk-chatの履歴データ構造に対する読み取り側サービスと表示レイヤーの追加）
- **Key Findings**:
  - ai-helpdesk-chatの設計書が`chat_history`・`chat_source_snapshot`テーブル、ORM モデル、`ChatHistoryRepository`、履歴関連エンドポイントを既に定義している。chat-historyはこれらのデータ構造を利用し、読み取り側のサービス・表示を担当する。
  - FAQ削除時の`SET NULL`外部キー戦略と`faq_id_at_answer`フィールドにより、FAQライフサイクルに依存しないスナップショット再現が実現される。
  - `require_owner`はadminバイパスを持たない設計（local-user-authentication）であり、本人所有判定の要件を直接満たす。

## Research Log

### ai-helpdesk-chatとの境界分析
- **Context**: ロードマップは「チャット回答と履歴永続化を分離することで、回答生成ロジックと履歴管理を独立して進化させられる」と述べている。一方、ai-helpdesk-chatの設計書は`chat_history`テーブル、`ChatHistoryRepository`、履歴一覧・詳細エンドポイントを自身のスコープ内に定義している。
- **Sources Consulted**: `.kiro/steering/roadmap.md`、`.kiro/specs/ai-helpdesk-chat/design.md`、`.kiro/specs/chat-history/requirements.md`
- **Findings**:
  - ai-helpdesk-chatは回答生成と永続化を`ChatService.ask()`内で原子的に実行する設計である。冪等キー`(owner_user_id, request_id)`による重複防止もこの層で処理される。
  - 依存方向はchat-history → ai-helpdesk-chatであり、コードレベルでもchat-historyがai-helpdesk-chatのモデル・型を参照する方向が自然。
  - 永続化の書き込み側はai-helpdesk-chatの`ChatService`フロー内で実行され、chat-historyは読み取り側（一覧・詳細・owner検証・表示）を担当する。
- **Implications**: chat-historyモジュール（`app/history/`）はai-helpdesk-chatの`app/chat/models.py`からORMモデルを参照し、独自のリポジトリ・サービス・ルーター・テンプレートで履歴表示を提供する。書き込み側の要件（1.1〜1.5）はai-helpdesk-chatの`ChatService`・`ChatHistoryRepository`が実装し、chat-historyの設計が永続化仕様を定義する。

### 本人所有判定と認可方式
- **Context**: 要件2.4は「管理者ロールであっても本人所有判定で拒否し、対象内容を返さない」と規定している。
- **Sources Consulted**: `.kiro/specs/local-user-authentication/design.md`
- **Findings**:
  - `require_owner(current: CurrentUser, owner_user_id: int) -> None`はadminバイパスを持たない。これは意図的な設計で、管理者による全社員履歴閲覧を防ぐため。
  - `CurrentUser(id: int, username: str, role: Literal["user", "admin"])`は不変のデータクラスとして後続仕様へ提供される。
- **Implications**: chat-historyの詳細エンドポイントは`require_owner`をそのまま利用し、追加の認可ロジックを実装しない。一覧はSQL WHERE句で`owner_user_id`を条件にし、他利用者の履歴をクエリ結果に含めない。

### FAQスナップショットと削除後の再現性
- **Context**: 要件3.1〜3.3は、FAQ更新・削除後も回答時点の根拠を保持し再現することを要求している。
- **Sources Consulted**: `.kiro/specs/ai-helpdesk-chat/design.md`（Physical Data Model）、`.kiro/specs/faq-management-and-search/design.md`
- **Findings**:
  - `chat_source_snapshot`テーブルの`faq_id`は`FK faq.id ON DELETE SET NULL`であり、FAQ削除時にNULLになる。
  - `faq_id_at_answer`（NOT NULL）とスナップショットフィールド（`question_snapshot`、`answer_snapshot`、`confidence_snapshot`）は不変で残る。
  - FAQ更新時はスナップショット値がテーブル内で変化しないため、回答時点の内容が自動的に保存される。
  - `is_deleted`フラグはDB列ではなく、`faq_id IS NULL`のランタイム判定で算出する。
- **Implications**: 詳細表示時に`faq_id`がNULLなら「削除済み」ラベルを表示する。スナップショット値はORMモデルから直接取得できる。

### 画面設計の参照
- **Context**: 要件の修正により、詳細画面と画面遷移がスコープ外となった。履歴画面は一覧画面のみで完結し、各履歴に質問日時・質問内容・回答・出典をインライン表示する。
- **Sources Consulted**: `.kiro/specs/chat-history/requirements.md`（修正後）、`.kiro/specs/ai-helpdesk-chat/design.md`（画面仕様セクション）、`mockup/chat.html`、`mockup/history.html`
- **Findings**:
  - 履歴一覧: `/chat/history`、offset/limitページネーション、新しい順ソート
  - 要件2.5により詳細画面（`/chat/history/{history_id}`）は提供しない
  - 各履歴カードに質問全文・回答全文・出典FAQスナップショットをインライン表示する
  - テーブル形式からカード形式に変更し、出典を各カード内に埋め込む
  - チャット画面から「履歴一覧」へのリンクが既に存在する
  - テンプレートはfoundationの`base.html`を継承する
- **Implications**: chat-historyは一覧画面（`list.html`）のみを`app/templates/history/`に配置する。詳細テンプレート（`detail.html`）は不要。リポジトリは出典のeager loadを一覧取得時に行う。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| 読み取り専用モジュール | ai-helpdesk-chatのデータ構造に対する読み取り側サービス | 境界が明確、依存方向が自然、変更影響が小さい | 書き込み側の仕様をai-helpdesk-chatに委任する | 採用 |
| 完全分離モジュール | 永続化の書き込み側もchat-historyが所有 | 履歴の完全所有 | 循環依存、ai-helpdesk-chatの設計変更が必要 | 不採用 |
| 共有モデル方式 | 履歴モデルを共通モジュールに配置 | 参照の一元化 | MVP に不要な抽象化 | 不採用 |

## Design Decisions

### Decision: 読み取り専用モジュールとしてのchat-history
- **Context**: ai-helpdesk-chatが既に`chat_history`・`chat_source_snapshot`のテーブル、ORMモデル、永続化リポジトリ、冪等キー制御を設計済みであり、依存方向はchat-history → ai-helpdesk-chatである。
- **Alternatives Considered**:
  1. chat-historyが書き込み側も所有し、ai-helpdesk-chatがchat-historyのサービスをDI経由で利用する — 依存方向の逆転が必要。
  2. 共有モデルモジュールを導入する — MVPに不要な抽象化。
- **Selected Approach**: chat-historyは読み取り側モジュール（`app/history/`）として、ai-helpdesk-chatの`app/chat/models.py`からORMモデルを参照し、独自のリポジトリ・サービス・ルーター・テンプレートで履歴の一覧・詳細表示を提供する。永続化の書き込みはai-helpdesk-chatの`ChatService.ask()`フロー内で行われるが、永続化仕様（保存項目、スナップショット内容、不変性）はchat-historyの設計が定義する。
- **Rationale**: 依存方向を維持しつつ、履歴表示の責務を明確に分離できる。書き込み側の仕様をchat-historyが定義し、ai-helpdesk-chatが実装する形で要件の追跡性を確保する。
- **Trade-offs**: 書き込み側のコードはai-helpdesk-chatモジュール内に存在するが、仕様はchat-historyが定義する。実装時の追跡性に注意が必要。
- **Follow-up**: ai-helpdesk-chatの実装時に、chat-historyの永続化仕様（1.1〜1.5, 3.1〜3.3）への適合を検証する。

### Decision: テーブル定義の所有権
- **Context**: ai-helpdesk-chatの設計書が`004_ai_helpdesk_chat.sql`でテーブルを定義済み。
- **Selected Approach**: テーブル物理定義は`004_ai_helpdesk_chat.sql`に残し、chat-historyは新規マイグレーションを作成しない。chat-historyの設計書でテーブル構造を再掲し、永続化仕様の根拠とする。
- **Rationale**: 既存の設計との整合性を維持し、マイグレーション順序の混乱を避ける。

### Decision: 画面エンドポイントの所有権
- **Context**: ai-helpdesk-chatの設計書が`/chat/history`・`/chat/history/{id}`エンドポイントとテンプレートを定義済みだったが、要件修正により詳細画面がスコープ外となった。
- **Selected Approach**: chat-historyは一覧エンドポイント（`/chat/history`、`/api/chat/history`）のみの実装所有権を持つ。`app/history/router.py`と`app/templates/history/list.html`に配置する。詳細エンドポイント（`/chat/history/{id}`）は提供しない。ai-helpdesk-chatの`ChatRouter`は`/chat`と`/api/chat`のみを担当する。
- **Rationale**: 要件2.5「詳細画面への遷移や別画面への画面遷移を提供せず、履歴画面単体で完結する」に準拠。一覧画面内で各履歴の質問・回答・出典を完結表示するため、詳細画面は不要。

### Decision: 一覧画面でのカード形式＋出典インライン表示
- **Context**: 要件修正により、詳細画面が廃止され、一覧画面で質問日時・質問内容・回答・出典を確認する設計が求められる。
- **Alternatives Considered**:
  1. テーブル形式で質問・回答を抜粋表示＋詳細リンク — 要件2.5に違反（詳細画面への遷移）。
  2. テーブル形式で全文＋出典を表示 — テーブルでは出典の複数行表示が難しい。
  3. カード形式で全文＋出典をインライン表示 — 各カードが質問・回答・出典を含む自己完結型。
- **Selected Approach**: カード形式のリスト表示。各カードにヘッダー（日時＋ステータス）、質問全文、回答全文、出典FAQテーブルを含める。
- **Rationale**: カード形式は各履歴が自己完結しており、出典テーブルの埋め込みが自然。一覧ページのスクロールで全情報が確認可能。
- **Trade-offs**: 出典を含むためレスポンスサイズが大きくなるが、ページネーション（limit=20）で制御する。

## Risks & Mitigations
- ai-helpdesk-chatの永続化実装がchat-historyの仕様を満たさないリスク → chat-historyの要件追跡テーブルで永続化仕様を明記し、実装時に`@kiro-validate-impl`で検証する。
- ORMモデル参照の結合 → chat-historyはai-helpdesk-chatの`ChatHistory`・`ChatSourceSnapshot`モデルを直接参照するため、モデル変更時に両方の設計を更新する必要がある。再検証トリガーに明記。
- テンプレートの二重所有 → ai-helpdesk-chatの設計書から履歴テンプレート（`history.html`、`detail.html`）の参照を除外し、chat-historyが唯一の所有者とする。

## References
- `.kiro/specs/ai-helpdesk-chat/design.md` — 履歴テーブル定義、ChatHistoryRepository、エンドポイント仕様
- `.kiro/specs/local-user-authentication/design.md` — CurrentUser、require_owner
- `.kiro/specs/faq-management-and-search/design.md` — FaqSearchResult、FaqCandidate
- `.kiro/specs/helpo-foundation/design.md` — BaseEntity、BaseRepository、Session、WebLayout
