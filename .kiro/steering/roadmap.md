# Roadmap

## Overview
HELPOは、人事・総務に寄せられる定型的な問い合わせを社員が自己解決できる、社内FAQ向けAIヘルプデスクである。初期段階では研修用MVPとして、登録済みFAQを検索し、その内容だけを根拠としてローカルLLMが回答する体験を提供する。

PythonとFastAPIを中心とした一体型構成を採用し、WindowsのGPUなしPC上で外部AIサービスへ社内データを送信せずに動作させる。認証、FAQ知識基盤、AIチャットを独立した仕様境界に分け、依存順に検証可能な構成とする。

## Approach Decision
- **Chosen**: ハイブリッドFAQ型。ローカルEmbeddingによるFAQ類似検索と、取得したFAQだけを根拠に回答する小型ローカルLLMを組み合わせる。
- **Why**: 登録FAQの正確性を維持しながら表現揺れに対応でき、「登録FAQへの回答」「生成AI連携」「ローカル中心」という要件を満たせるため。LLMが利用困難な場合も、登録回答を直接提示するフォールバックを設けられる。
- **Rejected alternatives**: FAQ検索特化型は軽量だが生成AI連携の希望を満たさない。ローカル文書RAG型は文書取込・分割・引用・更新管理が必要となり、研修用MVPには過大である。

## Scope
- **In**: FastAPIとSQLiteによるアプリ基盤、ローカルユーザー認証、管理者と一般利用者の基本ロール、FAQ管理、ローカルEmbeddingによる類似検索、FAQを根拠とするローカルLLM回答、社員向けチャットUI、根拠FAQ表示、回答不能時の窓口案内、本人の質問・回答履歴。
- **Out**: 一般文書RAG、利用分析とダッシュボード、管理者による全社員の履歴閲覧、履歴の共有・CSV出力、社員SSO、部署別・役職別の高度な権限制御、大人数の同時利用、分散構成。

## Constraints
- WindowsのGPUなしPCで動作すること。
- 社内FAQ、質問、回答を外部AIサービスへ送信しないこと。
- CPUで実行可能な小型量子化モデルと短い回答を前提とすること。
- 一人または少人数での利用を初期対象とすること。
- 検索適合基準未満の場合は推測回答を生成せず、人事・総務窓口を案内すること。
- 使用するLLMおよびEmbeddingモデルのライセンスは、具体的なモデル選定時に確認すること。

## Boundary Strategy
- **Why this split**: アプリ基盤、本人確認、FAQ知識基盤、AI利用体験を独立させることで、各段階を個別に要件定義・検証できる。AIチャット完成前にも認証とFAQ検索を動作確認でき、LLM固有の問題を他領域から分離できる。
- **Shared seams to watch**: 認証が提供するユーザーIDとロール、FAQ検索APIと適合判定、AIチャットが保存する履歴と根拠FAQの参照整合性、管理操作と本人履歴に対する認可。

## Specs (dependency order)
- [x] helpo-foundation -- FastAPI、SQLite、設定、共通データモデル、基本画面構成からなるアプリケーション基盤。Dependencies: none
- [x] local-user-authentication -- ローカルユーザーのログインと管理者・一般利用者ロールを提供する。Dependencies: helpo-foundation
- [x] faq-management-and-search -- FAQ管理、Embedding生成、類似検索、適合判定を提供する。Dependencies: helpo-foundation, local-user-authentication
- [x] ai-helpdesk-chat -- FAQを根拠にしたAIチャット、根拠表示、回答不能時の案内、本人の質問・回答履歴を提供する。Dependencies: helpo-foundation, local-user-authentication, faq-management-and-search
- [ ] header-navigation-menu -- 全画面共通のヘッダーメニュー（サービスタイトル、質問・履歴・FAQ管理画面へのリンクとその活性/非活性制御、ログイン中の利用者名・ロール表示、ログアウトボタン）を提供する。Dependencies: helpo-foundation, local-user-authentication, ai-helpdesk-chat, faq-management-and-search
