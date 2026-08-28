# Brief: header-navigation-menu

## Problem
現在、各画面のヘッダーには機能へのリンクや現在の利用者情報がなく、社員は質問画面・履歴画面・FAQ管理画面を行き来する統一された手段を持たない。また、ログイン状態や権限（一般利用者・管理者）に応じてどの機能へ遷移できるかが画面上で分からない。

## Current State
helpo-foundationの`base.html`はヘッダー・フッターの土台と`nav_extra`等の拡張ブロックのみを提供する。local-user-authenticationはRequirement 4.2で「共通画面に現在のユーザー名・基本ロール・ログアウト操作を表示する」ことを定めているが、質問画面・履歴画面・FAQ管理画面への遷移リンクや、それらのアクティブ/非アクティブ制御は仕様化されていない。

## Desired Outcome
全画面共通のヘッダーに、サービスタイトル「HELPO」、質問画面・履歴画面・FAQ管理画面への遷移リンク、現在ログイン中の利用者名・ロール表示、ログアウトボタンを一元的に表示する。リンクの有効/無効はログイン状態と権限（一般利用者/管理者）に応じて切り替わる。

## Approach
helpo-foundationの`base.html`が提供する`nav_extra`（または同等の）拡張ブロックを利用し、ヘッダーメニュー用のfeature-localテンプレートを追加する。現在利用者情報（ID・ユーザー名・ロール）はlocal-user-authenticationが提供する現在利用者解決の仕組みをそのまま利用し、本仕様側で新たな認証・認可ロジックは持たない。

## Scope
- **In**: ヘッダー内の「HELPO」サービスタイトル表示（非活性・非リンク）、質問画面・履歴画面・FAQ管理画面への遷移リンクとその活性/非活性制御、ログイン中の利用者名・ロール表示、ログアウトボタンの表示制御。
- **Out**: 質問画面・履歴画面・FAQ管理画面自体の内容や実装、認証・認可の判定ロジック自体（現在利用者解決、ログイン/ログアウト処理）、ロール定義や権限モデルの変更、ヘッダー以外のレイアウト（フッター等）。

## Boundary Candidates
- ヘッダーメニューの表示内容とリンクの活性/非活性制御
- 現在ログイン中の利用者名・ロール表示、ログアウト操作の起点（実処理はlocal-user-authenticationに委譲）
- 各機能画面への遷移リンク（遷移先の内容そのものは所有しない）

## Out of Boundary
- 質問画面（`/chat`）・履歴画面（`/chat/history`）・FAQ管理画面（`/faqs/upload`）の画面内容・業務ロジック — 各所有仕様（ai-helpdesk-chat、faq-management-and-search）が持つ
- 現在利用者・ロールの解決、ログイン・ログアウトの実処理 — local-user-authenticationが持つ
- 管理者判定・本人所有判定などの認可ロジック自体 — local-user-authenticationが持つ

## Upstream / Downstream
- **Upstream**: helpo-foundation（`base.html`と拡張ブロック）、local-user-authentication（現在利用者情報、ロール、ログアウト処理、`require_admin`等の判定境界）
- **Downstream**: ai-helpdesk-chat（質問画面・履歴画面への遷移元）、faq-management-and-search（FAQ管理画面への遷移元）

## Existing Spec Touchpoints
- **Extends**: なし（新規スコープ）。ただし、local-user-authenticationのRequirement 4.2（共通画面での利用者名・ロール・ログアウト操作の表示）は本仕様がその表示責務を引き継ぐことが望ましく、後続で`@kiro-spec-requirements local-user-authentication`による整理（重複排除）を推奨する。
- **Adjacent**: helpo-foundationの`base.html`拡張ブロック規約を維持し、直接変更しない。

## Constraints
- 既存のルーティングを変更しない（質問画面=`/chat`、履歴画面=`/chat/history`、FAQ管理画面=`/faqs/upload`という既存仕様のルートに合わせる）。
- 非アクティブなリンクは常にヘッダー上に表示されるが、クリックしても遷移しない（非表示にはしない）。
- 未ログイン状態では利用者名・ロール表示およびログアウトボタンを表示しない。
- 研修用ローカルMVPの制約（外部認証サービス不要、少人数利用）を踏襲する。
