# Requirements Document

## Introduction
HELPOの社員は人事・総務に関する定型的な問い合わせを、自分の言葉で自己解決したい。管理者は正確なFAQを登録・更新し、社員が表現の違う質問からでも該当FAQを見つけられるようにしたい。本仕様「faq-management-and-search」は、FAQのCRUD、管理者認可、ローカルCPU環境でのEmbedding生成、検索用索引の整合性維持、類似検索、および適合判定を定義する。FAQとEmbeddingは外部AIサービスへ送信せず、WindowsのGPUなしPC上で動作する研修用MVPとする。

## Boundary Context
- **In scope**: FAQデータの登録・一覧・取得・更新・削除、FAQ操作に対する管理者認可、FAQ質問文のローカルEmbedding生成、検索用索引との整合性維持、認証済み利用者からの類似検索、各候補の正規化類似度、実装所有の固定適合基準による適合判定、適合候補を返す検索API、管理者が検索品質を確認するための `/search` 画面、直接回答として提示可能な候補のインターフェース。
- **Out of scope**: 一般文書やPDF・Office文書の取込み・分割・RAG、LLMによる回答文生成、社員向けチャットUI、質問・回答履歴、利用分析ダッシュボード、外部Embedding/LLMサービス呼出、GPU分散推論。
- **Adjacent expectations**: helpo-foundationの設定、SQLite永続化、マイグレーション、共通エラー処理、ログ、BaseEntity/BaseRepository、基本画面レイアウトを利用する。local-user-authenticationの`CurrentUser`、`require_authenticated_user`、`require_admin`を使い、管理者判定を自ら適用する。ai-helpdesk-chatは本仕様の検索APIと適合判定を消費するが、本仕様は回答生成・履歴・チャットUIを所有しない。社員向けメイン検索入口は `/chat`（ai-helpdesk-chat）とし、本仕様の `/search` は管理者向け検索品質確認画面とする。

## Requirements

### Requirement 1: FAQの登録・編集・削除
**Objective:** 管理者として、社員から寄せられる定型問い合わせとその回答を登録・一覧・更新・削除できるようにしたい。これにより、知識基盤の中身を正確に保守できる。

#### Acceptance Criteria
1. When 管理者が新規FAQを作成したとき、the FAQ管理機能 shall 質問文と回答文を保存し、重複する質問文が存在しない場合に一意なFAQ IDを返す。
2. When 管理者が既存FAQの質問文または回答文を更新したとき、the FAQ管理機能 shall 指定されたFAQだけを変更し、更新日時を記録する。
3. When 管理者が既存FAQを削除したとき、the FAQ管理機能 shall 該当FAQを完全に削除し、関連する索引/表現を整合性を保って破棄する。
4. If 管理者が必須項目（質問文または回答文）を欠いてFAQ作成または更新を試行した場合、the FAQ管理機能 shall 保存を拒否し、入力エラーを通知する。
5. The FAQ管理機能 shall FAQ一覧に全ての登録FAQの質問文と更新日時を表示する。

### Requirement 2: FAQ管理者認可
**Objective:** 管理者として、FAQ操作が管理者ロールに限定されるようにしたい。これにより、誰でもFAQを書き換えられる危険を防ぐ。

#### Acceptance Criteria
1. When 利用者がFAQの作成・更新・削除を要求したとき、the FAQ管理機能 shall local-user-authenticationの管理者判定を利用して、基本ロールが`admin`であることを確認する。
2. If 認証済み利用者が基本ロール`admin`でない場合、the FAQ管理機能 shall FAQの作成・更新・削除を拒否し、権限不足を通知する。
3. If 未認証の利用者がFAQ管理画面または管理APIにアクセスした場合、the FAQ管理機能 shall 認証を要求し、対象データを返さない。
4. The FAQ管理機能 shall 認可判定の成否に応じて、local-user-authenticationの401/403応答契約を維持する。
5. The FAQ管理機能 shall 管理者ロールの判定ロジックを複製せず、local-user-authenticationの提供する認可依存を呼び出す。

### Requirement 3: ローカルEmbeddingと索引整合性
**Objective:** 管理者として、FAQの質問文から検索用表現を生成し、FAQ更新時に索引を最新に保ちたい。これにより、類似検索が正しく動く。

#### Acceptance Criteria
1. When 新規FAQが保存されたとき、the FAQ知識基盤 shall ライセンスとCPU動作が確認済みのローカルEmbeddingモデルを使って、質問文のベクトル表現を生成し保存する。
2. When 既存FAQの質問文が更新されたとき、the FAQ知識基盤 shall 古いベクトル表現を置き換え、索引を更新する。
3. When FAQが削除されたとき、the FAQ知識基盤 shall 対応するベクトル表現と索引エントリを削除する。
4. If 起動時に索引とFAQテーブルに不整合が検出された場合、the FAQ知識基盤 shall 不整合を解消して索引を再構築する。
5. The FAQ知識基盤 shall FAQ文またはEmbeddingを外部AIサービスへ送信しない。
6. The FAQ知識基盤 shall Embedding生成をWindowsのCPUのみで実行可能な仕組みとし、GPUを必須としない。

### Requirement 4: 類似検索と適合判定
**Objective:** 認証済み社員として、自然な言い回しでFAQを検索したい。これにより、自分の言葉で答えを探せる。

#### Acceptance Criteria
1. When 認証済み利用者が自然な問い合わせを送信したとき、the FAQ検索機能 shall ローカルEmbeddingを使ってFAQ候補を類似度順に返す。
2. The FAQ検索機能 shall 各候補に対してFAQ ID、質問文、回答文、および正規化された類似度を含む。
3. When 検索結果の上位候補が実装所有の固定適合基準を満たす場合、the FAQ検索機能 shall そのFAQを回答提示可能な候補としてマークする。
4. If 全ての候補が適合基準を満たさない場合、the FAQ検索機能 shall 回答提示可能としてマークされた候補を返さず、マッチなしを示す応答を返す。このとき、管理者による検索品質確認のため、回答には利用されない不適合候補を診断情報として含めてもよい。
5. The FAQ検索機能 shall 検索対象をFAQデータのみに限定し、他の文書または外部知識を含めない。

### Requirement 5: FAQ管理・検索のローカルMVP制約
**Objective:** 運用者として、外部サービスやGPUなしWindows PCでもFAQ管理・検索を動かしたい。これにより、研修環境ですぐに試せる。

#### Acceptance Criteria
1. The FAQ管理・検索機能 shall 外部AIサービスへのネットワーク接続を必須としない。
2. The FAQ管理・検索機能 shall FAQの保存・Embedding生成・類似検索をすべて同一ローカルPC上で完結させる。
3. The FAQ管理・検索機能 shall 使用するEmbeddingモデルのライセンスを、実際のモデル選定時に再確認し、未検証のモデルを自動選択して使用しない。
4. The FAQ管理・検索機能 shall 検索結果を直接回答として返すだけのインターフェースを提供し、LLM回答生成を含めない。
