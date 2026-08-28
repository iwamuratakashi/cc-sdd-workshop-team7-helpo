# Gap Analysis: header-navigation-menu

## 1. 現状調査（Current State）

### 実装コードの有無
- リポジトリ内に実アプリケーションコード（`app/`、`pyproject.toml`等）は存在しない。`helpo-foundation`・`local-user-authentication`・`faq-management-and-search`・`ai-helpdesk-chat`はいずれも`design.md`/`tasks.md`まで作成済みだが、実装フェーズはまだ着手されていない（greenfield）。
- 現在存在する実体は `mockup/` 配下の静的HTMLモックアップ3点のみ：
  - `mockup/login.html`（local-user-authentication のログイン画面モック）
  - `mockup/chat.html`（ai-helpdesk-chat のチャット画面モック）
  - `mockup/upload.html`（faq-management-and-search のFAQアップロード画面モック）

### モックアップの現状のヘッダー実装
- 3画面とも同一パターンの `<header class="header"><div class="header-title">...</div></header>` を**画面ごとに個別実装**しており、共有コンポーネントは存在しない。
- `header-title` の内容は画面ごとに異なる（例: `chat.html`は「Helpo / AI社内ヘルプデスク」、`upload.html`は「Helpo / FAQ管理」、`login.html`は「Helpo / AI社内ヘルプデスク」）。統一された「HELPO」というサービスタイトル表示や、質問・履歴・FAQ管理へのナビゲーションリンクは3画面のいずれにも存在しない。
- ログイン中の利用者名・ロール表示、ログアウトボタンもモックアップには実装されていない（`login.html`では認証成功後に`chat.html`へ`window.location.href`で遷移するのみ）。
- `chat.html`には「履歴一覧」への`nav-link`（`<a href="/chat/history">`）が本文下部に1つだけ存在するが、これはヘッダー内のナビゲーションではなく本文内リンクであり、本仕様が対象とするヘッダーメニューとは別物。

### 設計済み仕様（design.md）における関連ポイント
- **helpo-foundation**: `base.html`が`header`/`main`/`footer`と、下位機能が拡張できる`nav_extra`/`header_extra`ブロックを提供する設計になっている。トップページ`index.html`は認証・FAQ・チャットへの「仮リンク」を表示する設計（実装未着手）。`base.html`本体は下位機能から直接変更不可という契約。
- **local-user-authentication**: `app/templates/auth/_nav.html`という feature-local テンプレートで`base.html`の`nav_extra`拡張ブロックを上書きし、`current_user`の有無に応じたナビゲーション（ユーザー名・ロール・ログアウト）を表示する設計が既にある（Requirement 4.2 相当、AuthWebUIコンポーネント）。**これは本仕様のRequirement 5・6と責務が重複する**。
- **faq-management-and-search**、**ai-helpdesk-chat**: いずれも`base.html`の`header`/`main`/`footer`/`content`ブロックを維持するのみで、独自のナビゲーションリンクは設計していない。

## 2. 要件フィージビリティ分析

| Requirement | 技術的ニーズ | 既存資産 | ギャップ種別 |
|---|---|---|---|
| 1. 共通ヘッダーとサービスタイトル | 全画面共通のヘッダー表示コンポーネント（クリック無反応） | 各モックアップに個別の`.header`/`.header-title`実装あり（タイトル文言は画面ごとに不統一） | Missing（共通化）／Constraint（既存モックアップの文言差異） |
| 2. 機能画面への遷移リンク | 質問(`/chat`)・履歴(`/chat/history`)・FAQ管理(`/faqs/upload`)への恒常的なリンク | ルートは各仕様のdesign.mdで定義済み。`chat.html`に本文内リンクの前例はあるがヘッダー内リンクはなし | Missing |
| 3. 未ログイン時のリンク非活性化 | ログイン状態に基づく活性/非活性の視覚的区別とクリック無効化 | 判定材料となる現在利用者情報はlocal-user-authenticationの`AuthContext`が提供予定だが未実装 | Missing／Unknown（非活性の具体的なHTML/CSS表現は設計フェーズで決定） |
| 4. 一般利用者へのFAQ管理リンク非活性化 | 基本ロール(`user`/`admin`)に基づく活性/非活性制御 | ロール情報は`CurrentUser.role`として設計済みだが未実装。ロールに応じたUI分岐の前例はモックアップになし | Missing |
| 5. ログイン中の利用者情報表示 | 現在利用者名・基本ロールの表示 | **local-user-authenticationの`_nav.html`が同等機能を設計済み（重複）** | Constraint（責務重複の解消が必要） |
| 6. ログアウト操作 | ログアウトボタンとログアウト処理の起動 | **local-user-authenticationの`_nav.html`/AuthRouterの`POST /logout`が既に設計済み（重複）** | Constraint（責務重複の解消が必要） |

### Research Needed（設計フェーズへの持ち越し事項）
- local-user-authenticationの`_nav.html`（Req 4.2相当）と本仕様の関係整理: (a) 本仕様が`_nav.html`を置き換える、(b) 本仕様が`_nav.html`を拡張する、(c) 責務を分割し続ける、のいずれを採用するか。ブリーフでは(a)方向を推奨済みだが、local-user-authenticationのrequirements.md/design.mdの実際の修正是非は未確定。
- 非活性リンクの具体的なマークアップ（`<a>`にdisabled相当のクラスを付与するか、`<span>`に置き換えるか等）は本ギャップ分析の対象外とし、design.mdで決定する。
- ヘッダーメニューを`base.html`の新規拡張ブロック（例: `nav_menu`）として追加するか、既存の`nav_extra`を再利用するかはfoundation側の設計変更を伴うため要確認。

## 3. 実装アプローチの選択肢

### Option A: 既存コンポーネントの拡張
- helpo-foundationの`base.html`の`nav_extra`ブロックと、local-user-authenticationの`_nav.html`を拡張し、質問・履歴・FAQ管理リンクとロール別活性制御を追加する。
- ✅ 新規ファイルが少なく、既存の拡張ブロック機構をそのまま利用できる。
- ❌ `_nav.html`の所有者が実質的にlocal-user-authenticationのままとなり、header-navigation-menu独自の責務境界が曖昧になる。将来の変更（リンク追加等）がlocal-user-authenticationの仕様変更を要求してしまう。

### Option B: 新規コンポーネントとして分離
- header-navigation-menu専用のfeature-localテンプレート（例: `app/navigation/templates/_header_menu.html`）を新設し、`base.html`の拡張ブロックを介して注入する。local-user-authenticationの`_nav.html`はログイン専用画面向けの最小表示に縮小するか廃止する。
- ✅ 責務境界が明確。今後、画面追加時のリンク拡張が本仕様だけで完結する。
- ❌ local-user-authenticationのrequirements.md（Req 4.2）・design.md（AuthWebUI/_nav.html）の是正が必要になり、影響範囲が本仕様外にも及ぶ。

### Option C: ハイブリッド
- 現在利用者・ロール解決は引き続きlocal-user-authenticationのAuthContextに委譲しつつ、表示コンポーネント（テンプレート）自体はheader-navigation-menuが新設して`nav_extra`を占有する。local-user-authenticationのRequirement 4.2は「現在利用者情報の提供」に縮小し、表示自体は本仕様が担う。
- ✅ ロジックとプレゼンテーションの責務が分かれ、依存方向（foundation → auth → 他機能）を保ちやすい。
- ❌ local-user-authenticationのrequirements.md/design.mdの軽微な修正が前提となるため、実装順序として先にlocal-user-authentication側の整理が必要。

## 4. 実装複雑度とリスク

- **Effort**: S〜M（1–5日相当）。既存の`base.html`拡張ブロック機構とAuthContextの型（`CurrentUser`）をそのまま利用でき、新規の複雑なロジックはない。ロール別リンク活性制御はテンプレート内の条件分岐で実現可能。
- **Risk**: Medium。技術的な難易度は低いが、local-user-authenticationとの責務重複（Req 4.2）の整理が前提となるため、**仕様間の調整（設計順序）がリスク要因**となる。調整を後回しにすると、実装時にどちらの機能が`nav_extra`を所有するかで衝突する。

## 5. 設計フェーズへの推奨

- **推奨アプローチ**: Option C（ハイブリッド）。現在利用者情報の解決はlocal-user-authenticationに委譲し、ヘッダーメニューの表示コンポーネント自体はheader-navigation-menuが新設して所有する。
- **鍵となる決定事項**:
  - `base.html`の拡張ブロックのうち、どれをheader-navigation-menuが占有するか（既存`nav_extra`の再利用か、新規ブロック追加か）をfoundation側の変更範囲として設計時に明確化する。
  - local-user-authenticationのRequirement 4.2・design.md（`_nav.html`/AuthWebUI）の扱いについて、設計確定前に整理方針を確認する（本仕様のdesign.md内でBoundary Commitmentsとして明記し、必要ならlocal-user-authentication側の`@kiro-spec-requirements`再実行を別途提案する）。
  - 非活性リンクの具体的なUI表現（クラス付与/要素置換）を設計時に決定する。
- **持ち越す調査事項**: 上記「Research Needed」の3点。

---

# Design Discovery Log（design フェーズ）

## Discovery Type
Light Discovery（既存システム拡張）。実コードは未着手のため、helpo-foundation・local-user-authenticationの`design.md`を正典として拡張点を分析した。

## Extension Point Analysis
- helpo-foundationの`base.html`は`header`/`main`/`footer`ブロックに加え、下位機能が上書き可能な`nav_extra`/`header_extra`拡張ブロックを持つ契約になっている（`base.html`本体は直接変更禁止）。
- local-user-authenticationは既に`nav_extra`を`_nav.html`で上書きし、現在利用者名・ロール・ログアウトを表示する設計を持つ。本仕様がこの表示責務を引き継ぐ（ユーザーとの合意済み）ため、`_nav.html`相当の内容は本仕様の`_header_menu.html`に一本化する。
- 各画面テンプレート（`login.html`、`chat.html`、`history.html`、`detail.html`、`upload.html`）は個別に`base.html`を継承しており、単純に`nav_extra`ブロックを上書きする方式では画面ごとに同じ`{% include %}`記述を重複させる必要がある。

## Design Decision: 中間テンプレート方式
- 重複を避けるため、本仕様が`app/templates/_page_base.html`という中間テンプレートを新設する。これは`base.html`を継承し、`nav_extra`ブロックを`_header_menu.html`のincludeで一度だけ上書きする。
- 各画面所有仕様（local-user-authentication、ai-helpdesk-chat、faq-management-and-search）は、自身の画面テンプレートの継承先を`base.html`から`_page_base.html`へ変更するだけでヘッダーメニューを取得できる。この継承先変更自体は各画面所有仕様の実装タスク側で行う想定とし、本仕様は「どのテンプレート名を継承すべきか」という契約の提供までを責務とする。
- Build vs Adopt: Jinja2の標準的なテンプレート継承チェーン（`base.html` → `_page_base.html` → 画面テンプレート）のみで要件を満たせるため、新規ライブラリやJSフレームワークは採用しない。
- Simplification: 活性/非活性判定は状態を持たない純粋関数（`NavLinkPolicy`）に閉じ込め、テンプレート側は判定結果を描画するだけに留める。これにより単体テストが容易になり、テンプレート内に分岐ロジックを埋め込まない。
- Generalization: `NavLinkPolicy`は「ログイン状態」「基本ロール」からリンクの活性/非活性を導く一般的なインタフェースとして設計し、将来リンクが追加されても同一の関数形状で拡張できるようにする（現時点の実装スコープは質問・履歴・FAQ管理の3リンクのみ）。

## Boundary Coordination Note
- local-user-authenticationのRequirement 4.2（共通画面での利用者名・ロール・ログアウト表示）は本仕様のRequirement 5・6と重複する。本設計では本仕様が表示責務を持つ前提で`_nav.html`を`_header_menu.html`に置き換えることとし、local-user-authentication側の重複要件の整理（`@kiro-spec-requirements local-user-authentication`の再実行）を別途推奨事項として記録する。

