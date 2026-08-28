# Implementation Plan

## Task Format Template

- Major tasks group related sub-tasks.
- Each executable sub-task includes at least one observable completion condition.
- `_Requirements: N` lists only numeric requirement IDs from `requirements.md`.
- `_Boundary: ComponentName` declares the design component the task owns.

## 前提条件

本仕様の実装は `local-user-authentication` の以下が実装済みであることを前提とする:
- `app/auth/schemas.py` の `CurrentUser`・`Role` 型
- `app/auth/dependencies.py` の `get_current_user_optional()` 依存関数
- `app/router_registry.py` の共有モジュールレベル `router_registry` インスタンス（`local-user-authentication` タスク 0.1）

## 実装タスク

- [ ] 1. ナビゲーションポリシーと型定義を実装する
- [ ] 1.1 NavLinkState・HeaderMenuContext の型定義を作成する
  - `app/navigation/schemas.py` に `NavLinkState`・`HeaderMenuContext` dataclass を実装する。
  - `NavLinkState`: `key`（`Literal["question", "history", "faq_admin"]`）、`href`、`label`、`active` を持つ frozen dataclass。
  - `HeaderMenuContext`: `links: tuple[NavLinkState, NavLinkState, NavLinkState]`、`show_user_info`、`show_logout`、`username`、`role` を持つ frozen dataclass。
  - `CurrentUser` 型は `app.auth.schemas` から import し、本仕様側で再定義しない。
  - 完了状態: `from app.navigation.schemas import HeaderMenuContext, NavLinkState` が成功する。
  - _Requirements: 2.1, 3.1, 4.1, 5.1_
  - _Boundary: NavLinkPolicy_

- [ ] 1.2 NavLinkPolicy を実装する
  - `app/navigation/policy.py` に `NavLinkPolicy` クラスを実装する。
  - `build(current_user: CurrentUser | None) -> HeaderMenuContext` を実装し、`current_user` のみを入力として決定的にリンク活性状態と表示要否を返す。DBアクセス・副作用を持たない純粋関数とする。
  - Postconditions:
    - `current_user is None`: 全リンク `active=False`、`show_user_info=False`、`show_logout=False`。
    - `current_user.role == "user"`: `question`・`history` が `active=True`、`faq_admin` が `active=False`、`show_user_info=True`、`show_logout=True`。
    - `current_user.role == "admin"`: 全リンク `active=True`、`show_user_info=True`、`show_logout=True`。
  - `links` は常に `question`・`history`・`faq_admin` の 3 件・固定順で返す（非表示にはしない）。
  - 完了状態: 単体テストで全 Postcondition が検証される。
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 4.1, 4.2, 4.3, 5.1, 5.2, 6.1, 6.2_
  - _Boundary: NavLinkPolicy_
  - _Depends: 1.1_

- [ ] 2. Jinja2 テンプレートを実装する
- [ ] 2.1 _header_menu.html を実装する
  - `app/templates/navigation/_header_menu.html` を作成する。
  - テンプレートコンテキストの `header_menu_context: HeaderMenuContext` を参照して描画する（判定ロジックを持たない）。
  - サービスタイトル「HELPO」は `<span>` 等の非リンク要素として描画し、クリックで遷移を発生させない（Req 1.2）。
  - 非活性リンク（`active=False`）は `<span aria-disabled="true">` または `pointer-events: none` な要素として描画し、`href` による遷移を発生させない（Req 3.2, 4.2）。
  - `show_user_info=False` の場合は利用者名・基本ロール表示要素を描画しない（Req 5.2）。
  - `show_logout=False` の場合はログアウトボタンを描画しない（Req 6.2）。
  - ログアウトボタンは `<form method="post" action="/logout">` へのフォーム送信として実装し、`GET` リンクにはしない（Req 6.3）。
  - 完了状態: `Jinja2Templates.TemplateResponse` でテンプレートを描画し、HTML にサービスタイトル・リンク・利用者情報・ログアウトボタンが要件通り含まれる。
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3_
  - _Boundary: HeaderMenuView_
  - _Depends: 1.2_

- [ ] 2.2 _page_base.html を実装する
  - `app/templates/_page_base.html` を作成する。
  - `{% extends "base.html" %}` した上で、`{% block nav_extra %}{% include "navigation/_header_menu.html" %}{% endblock %}` のみを定義する。
  - `content` 等の他ブロックは素通しし、画面テンプレート側の責務を変更しない。
  - `header_menu_context` が未設定の場合のデフォルト（全リンク非活性）フォールバックをコメントで明記する。
  - 完了状態: `_page_base.html` を継承したダミーテンプレートが、`base.html` の `content` ブロックとヘッダーメニューを両方正しく描画する。
  - _Requirements: 1.1, 1.3_
  - _Boundary: PageBaseTemplate_
  - _Depends: 2.1_

- [ ] 3. nav.js を更新し server-side 描画と共存させる
- [ ] 3.1 app/static/js/nav.js に既存コンテンツ確認を追加する
  - `app/static/js/nav.js` の `initHeaderMenu()` 関数を更新し、`#app-header` 要素の `innerHTML.trim()` が空でない場合は描画をスキップするよう修正する。
  - これにより、server-side で `nav_extra` ブロックが埋まったページでは nav.js が干渉しなくなる。
  - placeholder ページや未実装画面では引き続き client-side 描画が機能する。
  - 完了状態: `_page_base.html` を使うページで nav.js が header を上書きしない（ブラウザで確認）。
  - _Requirements: 1.1, 1.3_
  - _Boundary: HeaderMenuView_

- [ ] 4. ページルーターへのヘッダーメニューコンテキスト組み込み
- [ ] 4.1 auth ルーターに header_menu_context を組み込む
  - `app/auth/router.py` の `GET /login` ハンドラで `get_current_user_optional()` と `NavLinkPolicy().build()` を呼び出し、`header_menu_context` をテンプレートコンテキストへ渡す。
  - `app/templates/auth/login.html` の継承先を `base.html` から `_page_base.html` へ変更する（この変更は本仕様が行う）。
  - 完了状態: ログイン画面でヘッダーメニューが表示され（未ログイン状態のため全リンク非活性）、サービスタイトルが見える。
  - _Requirements: 1.1, 3.1, 5.2, 6.2_
  - _Boundary: HeaderMenuView_
  - _Depends: 2.2, 3.1_

- [ ] 5. テストを作成する
- [ ] 5.1 NavLinkPolicy の単体テストを作成する
  - `tests/test_navigation_unit.py` に `NavLinkPolicy.build()` の単体テストを作成する。
  - `build(None)`・`build(user_user)`・`build(admin_user)` それぞれで Postconditions を検証する。
  - `links` が常に 3 件・固定順で返ることを検証する。
  - 完了状態: `pytest tests/test_navigation_unit.py` が全件合格する。
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 4.1, 4.2, 4.3_
  - _Boundary: NavLinkPolicy_
  - _Depends: 1.2_

- [ ] 5.2 テンプレート描画の結合テストを作成する
  - `tests/test_navigation_integration.py` に Jinja2 テンプレート描画テストを作成する。
  - `_header_menu.html` を `header_menu_context=None` 相当（全非活性）・一般利用者・管理者それぞれで描画し、HTML 出力を検証する。
  - 非活性リンクに `href` 属性が含まれないまたは `aria-disabled` 属性が付くことを検証する（Req 3.2）。
  - `_page_base.html` を継承したダミーテンプレートが `content` ブロックとヘッダーメニューを両方描画することを検証する（Req 1.1, 1.3）。
  - 完了状態: `pytest tests/test_navigation_integration.py` が全件合格する。
  - _Requirements: 1.1, 1.3, 2.1, 2.4, 3.2, 4.1, 4.3, 5.1, 6.1_
  - _Boundary: HeaderMenuView, PageBaseTemplate_
  - _Depends: 2.2_
