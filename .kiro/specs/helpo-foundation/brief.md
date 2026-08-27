# Brief: helpo-foundation

## Problem
HELPOは新規プロジェクトであり、認証、FAQ管理、検索、AIチャットを安全かつ一貫して実装するための共通アプリケーション基盤が存在しない。後続機能が個別に基盤を持つと、データアクセスや設定、画面構成が重複する。

## Current State
Kiroの開発テンプレートだけが存在し、実装コード、データベース、共通設定、画面基盤は未作成である。

## Desired Outcome
WindowsのGPUなしPC上で起動でき、後続仕様が共通利用できるPython/FastAPIアプリケーション、SQLite接続、設定管理、共通データモデル、基本画面構成が整っている。

## Approach
PythonとFastAPIを中心とした一体型構成を採用し、永続化にはSQLiteを使用する。研修用MVPとして構成要素を抑えながら、認証、FAQ管理、AIチャットを明確なモジュール境界で追加できる基盤を作る。

## Scope
- **In**: FastAPIアプリケーション、SQLite接続とマイグレーション方針、環境設定、共通データアクセス、基本レイアウト、後続機能向けモジュール構成。
- **Out**: ユーザーログイン、FAQの業務機能、Embedding、LLM連携、チャット、質問・回答履歴。

## Boundary Candidates
- Webアプリケーションと画面の共通基盤
- SQLite永続化と共通データアクセス
- ローカルAI実行設定を追加できる設定境界

## Out of Boundary
- 認証・認可ルール
- FAQ検索アルゴリズム
- AI回答生成と会話管理
- 本番向け分散構成と高可用性

## Upstream / Downstream
- **Upstream**: なし
- **Downstream**: local-user-authentication、faq-management-and-search、ai-helpdesk-chat

## Existing Spec Touchpoints
- **Extends**: なし
- **Adjacent**: 後続3仕様が本仕様のアプリ構成、設定、永続化方式を利用する

## Constraints
WindowsのGPUなしPCで容易にセットアップできること。PythonとFastAPIを中心とし、外部クラウドサービスを必須にしないこと。研修用MVPとして不要なインフラ複雑性を導入しないこと。
