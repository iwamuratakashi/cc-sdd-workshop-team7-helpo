# Brief: chat-history

## Problem
社員がAIヘルプデスクチャットで得た質問と回答を後から確認できなければ、同じ問い合わせを繰り返すことになる。また、根拠FAQが後から変更・削除された場合に過去の回答根拠が失われると、履歴の意味が変わってしまう。

## Current State
質問・回答の永続化、履歴一覧、履歴詳細表示、根拠FAQのスナップショット保存は存在しない。

## Desired Outcome
認証済み社員が自分の過去の質問・回答を新しい順に一覧表示し、詳細と根拠FAQを再確認できる。根拠FAQが変更・削除されても、回答時点のスナップショットで履歴の意味が保たれる。他の利用者の履歴は参照できない。

## Approach
ai-helpdesk-chatが返す質問・回答・回答状態・根拠FAQを、所有者ユーザーIDとともに永続化する。根拠FAQは回答時点のスナップショットとして保存し、FAQ変更・削除後も履歴を再現できるようにする。本人所有判定により、他の利用者の履歴へのアクセスを拒否する。

## Scope
- **In**: 質問・回答・状態・根拠・所有者・日時の永続化、本人の履歴一覧と詳細表示、回答時点の根拠FAQスナップショット保存、FAQ変更・削除後の履歴再現。
- **Out**: チャットUIでの質問送信・回答生成・フォールバック処理、FAQ CRUD・Embedding・索引、管理者による全社員の履歴閲覧、履歴共有、CSV出力、履歴分析、一般文書RAG、複数利用者間の会話共有。

## Boundary Candidates
- 質問・回答履歴の永続化
- 本人所有の履歴一覧と詳細表示
- 根拠FAQ変更・削除時の履歴再現性

## Out of Boundary
- チャット画面での質問送信と回答生成
- FAQの登録・編集・索引生成
- ユーザー資格情報とログインセッションの管理
- 管理者向け利用分析
- 履歴共有・エクスポート・分析

## Upstream / Downstream
- **Upstream**: helpo-foundation、local-user-authentication、ai-helpdesk-chat、faq-management-and-search
- **Downstream**: 将来の利用分析、有人引継ぎ機能の候補。ただし初期MVPでは対象外。

## Existing Spec Touchpoints
- **Extends**: なし
- **Adjacent**: ai-helpdesk-chatの回答結果（質問・回答・状態・根拠FAQ）を永続化の入力として受け取る。local-user-authenticationのユーザーIDで履歴所有者を識別する。faq-management-and-searchのFAQ IDで根拠参照を管理する。

## Constraints
履歴データを外部サービスへ送信しないこと。他ユーザーの履歴を取得できないこと。アプリ再起動やログアウト後も履歴を保持すること。他利用者の履歴内容を通常ログへ出力しないこと。
