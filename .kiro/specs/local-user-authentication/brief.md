# Brief: local-user-authentication

## Problem
HELPOには社員本人とFAQ管理者を識別する仕組みが必要である。認証がなければ、FAQ管理操作を制限できず、質問・回答履歴を本人だけに表示することもできない。

## Current State
ユーザー、ログインセッション、ロール、認可の仕組みは存在しない。

## Desired Outcome
ローカル登録された利用者がユーザー名とパスワードでログイン・ログアウトでき、一般利用者と管理者を区別できる。後続仕様は認証済みユーザーIDとロールを安全に利用できる。

## Approach
SQLiteにローカルユーザーを保存し、パスワードは平文で保持せず安全なパスワードハッシュを使用する。FastAPIのアプリケーション内でセッションを管理し、管理操作と本人所有データに対する認可の基礎を提供する。

## Scope
- **In**: ローカルユーザー、パスワードハッシュ、ログイン、ログアウト、認証セッション、管理者・一般利用者ロール、現在の利用者情報、後続機能向け認可境界。
- **Out**: 社員SSO、Microsoft Entra ID連携、多要素認証、部署・役職別権限、管理者による全社員の質問履歴閲覧。

## Boundary Candidates
- 資格情報の検証とセッション管理
- ユーザーIDと基本ロールの提供
- 管理者操作と本人所有データに対する認可インターフェース

## Out of Boundary
- FAQ操作への認可適用（faq-management-and-searchが`require_admin`を呼び出す）
- 履歴の永続化・表示・本人所有強制（ai-helpdesk-chatが`require_owner`を呼び出す）
- 利用状況の監査・分析
- 外部IDプロバイダー連携

## Upstream / Downstream
- **Upstream**: helpo-foundation
- **Downstream**: faq-management-and-search、ai-helpdesk-chat

## Existing Spec Touchpoints
- **Extends**: なし
- **Adjacent**: helpo-foundationの永続化と画面基盤を利用し、後続仕様へユーザーIDとロールを提供する

## Constraints
認証情報をログへ出力しないこと。パスワードを平文または復号可能な形式で保存しないこと。本人の質問・回答履歴が他ユーザーへ漏れない認可境界を提供すること。研修用MVPのため外部認証サービスを必須にしないこと。
