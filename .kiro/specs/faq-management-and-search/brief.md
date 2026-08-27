# Brief: faq-management-and-search

## Problem
人事・総務の定型的な問い合わせに対して、表現の異なる質問から適切な登録FAQを見つける知識基盤が必要である。単純な完全一致検索では言い換えに弱く、根拠のない生成AI回答では社内制度について誤案内する危険がある。

## Current State
FAQの保存・管理、Embedding、類似検索、適合判定は存在しない。

## Desired Outcome
管理者がFAQを登録・編集・削除でき、社員の自然な質問に近いFAQをローカル環境で検索できる。検索結果には類似度と適合判定があり、適合基準未満では回答生成に使わない判断ができる。

## Approach
FAQの質問と回答をSQLiteに保存し、ローカルで実行できる軽量Embeddingモデルを用いて検索用表現を生成する。類似度順の候補と適合判定を返し、FAQ更新時には索引との整合性を維持する。

## Scope
- **In**: FAQの登録・一覧・編集・削除、管理者認可、Embedding生成・更新、類似検索、検索候補、適合判定、FAQ回答の直接提示に利用可能な検索インターフェース。
- **Out**: 一般文書の取込と分割、PDF・Office文書RAG、LLMによる回答文生成、社員向けチャットUI、利用分析。

## Boundary Candidates
- FAQライフサイクル管理
- ローカルEmbeddingと索引整合性
- 類似検索と回答可否を決める適合判定

## Out of Boundary
- FAQ以外の社内文書検索
- 質問・回答履歴
- LLMモデルの起動とプロンプト制御
- FAQ利用件数の分析ダッシュボード

## Upstream / Downstream
- **Upstream**: helpo-foundation、local-user-authentication
- **Downstream**: ai-helpdesk-chat

## Existing Spec Touchpoints
- **Extends**: なし
- **Adjacent**: local-user-authenticationの管理者ロールでFAQ変更を認可し、ai-helpdesk-chatへ根拠候補と適合判定を提供する

## Constraints
FAQとEmbeddingを外部AIサービスへ送信しないこと。WindowsのGPUなしPCで実用可能な軽量モデルを選ぶこと。モデルのライセンスを採用時に確認すること。適合基準未満の候補をAI回答の根拠にしないこと。
