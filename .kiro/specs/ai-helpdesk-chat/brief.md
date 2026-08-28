# Brief: ai-helpdesk-chat

## Problem
社員は休暇、経費、福利厚生、社内制度について人事・総務へ問い合わせる前に、自然な会話で自己解決したい。登録FAQを単に検索するだけでは利用体験が限定される一方、根拠を制限しない生成AIは誤回答の危険がある。

## Current State
社員向けチャットUI、ローカルLLM回答、根拠表示、回答不能時の案内は存在しない。

## Desired Outcome
ログインした社員がチャット形式で質問し、検索された登録FAQだけを根拠とする自然な回答と根拠FAQを確認できる。適切なFAQがない場合は推測せず人事・総務窓口へ案内される。

## Approach
faq-management-and-searchが返すFAQ候補と適合判定を入力として、CPU実行可能な小型量子化ローカルLLMに根拠限定の短い回答を生成させる。適合なし、LLM停止、タイムアウト時には登録回答の直接提示または窓口案内へフォールバックする。

## Scope
- **In**: 社員向けチャット画面、質問送信、FAQ検索連携、ローカルLLM回答、回答根拠の制限、根拠FAQ表示、回答不能時の人事・総務窓口案内、LLM障害時のフォールバック。
- **Out**: 質問・回答の永続化・履歴一覧・履歴詳細、管理者による全社員の履歴閲覧、履歴共有、CSV出力、履歴分析、一般文書RAG、複数利用者間の会話共有、長文生成。

## Boundary Candidates
- FAQ検索結果からの根拠限定回答生成
- チャット操作と回答状態の表示
- 適合なし・LLM障害時の安全なフォールバック

## Out of Boundary
- FAQの登録・編集・索引生成
- ユーザー資格情報とログインセッションの管理
- 質問・回答履歴の永続化・一覧・詳細表示
- 管理者向け利用分析
- 社員SSOと高度なアクセス制御

## Upstream / Downstream
- **Upstream**: helpo-foundation、local-user-authentication、faq-management-and-search
- **Downstream**: chat-history（質問・回答・状態・根拠の永続化と履歴表示）、将来の一般文書RAG、利用分析、有人引継ぎ機能の候補。ただし初期MVPではchat-history以外は対象外。

## Existing Spec Touchpoints
- **Extends**: なし
- **Adjacent**: faq-management-and-searchの検索候補・適合判定を回答根拠として利用する。chat-historyが本仕様の回答結果を永続化する。

## Constraints
質問、FAQ、回答を外部AIサービスへ送信しないこと。WindowsのGPUなしPCで動く小型量子化モデルを用い、回答は短くすること。使用モデルのライセンスを採用時に確認すること。検索適合基準未満の場合はLLMに推測させないこと。
