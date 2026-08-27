# Research & Design Decisions

## Summary
- **Feature**: local-user-authentication
- **Discovery Scope**: Extension（helpo-foundation上に追加）
- **Key Findings**:
  - 社内MVP・Windows GPUなしPC・外部認証基盤なしの制約から、サーバー側SQLiteセッション方式が最もシンプルかつ即時失効可能。
  - パスワードハッシュは既存のArgon2id実装（argon2-cffi）を採用し、自作ハッシュを避ける。
  - 後続仕様（faq-management-and-search、ai-helpdesk-chat）へ認可判定を提供する場合、認証境界と業務データアクセスは分離する必要がある。

## Research Log

### 認証方式の選定
- **Context**: 外部IdPなし、少人数、研修用MVPで認証状態を維持する方法を決める必要がある。
- **Sources Consulted**: OWASP Session Management Cheat Sheet、FastAPI Cookies/Depends ドキュメント、Argon2id PHC winner仕様。
- **Findings**:
  - JWTや署名Cookieは即時失効が困難。管理者が利用者を無効化しても既存セッションが残る。
  - サーバー側セッションは即時失効可能で、トークンダイジェストを保存すれば生トークン漏洩時の影響を抑えられる。
  - 状態変更はPOSTに限定し、SameSite=Laxを最低条件とすればCSRFリスクはMVP範囲で許容できる。
- **Implications**: 生トークンはCookie設定時にのみ扱い、DBにはSHA-256ダイジェストを保存する。セッション有効期限と失効時刻を保持する。

### パスワードハッシュライブラリの選定
- **Context**: 平文・復号可能な保存を禁止しており、安全なハッシュ方式が必要。
- **Sources Consulted**: argon2-cffi ドキュメント、OWASP Password Storage Cheat Sheet、Python `hashlib` ドキュメント。
- **Findings**:
  - Argon2idは現時点で推奨されるパスワードハッシュ方式であり、python実装としてargon2-cffiが広く利用されている。
  - ライブラリ既定値は時折更新されるが、明示的なパラメータを固定しすぎると将来のセキュリティアップデートを阻害する。ハッシュ文字列にパラメータを含めるため、検証時に自動解釈される。
- **Implications**: `argon2-cffi` を依存関係に追加し、`PasswordHasher`でラップして入力・出力をログに渡さない。

### 認可境界の分離
- **Context**: FAQ管理操作への認可適用と、チャット履歴の本人所有強制は、どの仕様が責任を持つべきか。
- **Sources Consulted**: 既存requirements.mdとbrief.md、roadmap.md。
- **Findings**:
  - local-user-authenticationは認証・基本ロール・所有者ID一致の判定までを提供すべき。
  - 実際の業務データ（FAQ、履歴）へのアクセス制御は、データを所有する仕様が`require_admin`/`require_owner`を呼び出して適用する。
- **Implications**: `require_owner`にはadminバイパスを持たせない。管理者による全社員履歴閲覧は明示的にout of scopeとする。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| サーバー側SQLiteセッション | 生トークンをCookieに保存し、DBにはダイジェストを保存 | 即時失効、実装が小規模、外部依存が不要 | スケール時にDB負荷、期限切れセッションの定期削除が必要 | MVP・少人数向け |
| 署名付きJWT Cookie | クライアントに署名済みトークンを保存 | サーバー状態が不要、スケールしやすい | 即時失効が困難、トークンサイズ増加 | out of scope |
| 外部IdP/OIDC | Microsoft Entra ID等を利用 | 企業統合に最適 | 外部ネットワーク依存、MVPに過大 | out of scope |

## Design Decisions

### Decision: サーバー側SQLiteセッション方式の採用
- **Context**: 即時失効が必要かつ、外部認証サービスを使わないローカルMVP環境で動作させたい。
- **Alternatives Considered**:
  1. JWT署名Cookie方式 — 即時失効が困難。
  2. 外部IdP連携 — MVPに不要な運用・ネットワーク依存。
- **Selected Approach**: `secrets.token_urlsafe(32)`以上でランダムトークンを発行し、SHA-256ダイジェストをSQLiteの`auth_sessions`テーブルに保存する。有効期限と失効時刻を管理する。
- **Rationale**: 少人数・ローカル環境ではDB検索コストは無視でき、即時失効によるセキュリティ利得が大きい。
- **Trade-offs**: スケール時にはRedis等への移行が必要だが、MVPではSQLiteで十分。
- **Follow-up**: 期限切れセッションの定期削除は将来の課題とし、レコード増加が問題になった時点で再検証する。

### Decision: Argon2idによるパスワードハッシュ
- **Context**: 平文・復号可能な資格情報保存を禁止している。
- **Alternatives Considered**:
  1. bcrypt — 広く使われるが、Argon2idの方がメモリハード特性が強い。
  2. scrypt — 利用例はあるが、Argon2idがPHC優勝者として推奨されている。
  3. 自作ハッシュ — 絶対に避ける。
- **Selected Approach**: `argon2-cffi`を用いてArgon2idハッシュを生成・検証する。
- **Rationale**: 業界標準でメンテナンスされたライブラリを採用し、自作のリスクを排除する。
- **Trade-offs**: ハッシュ計算コストによりログイン処理が若干遅延するが、MVP・少人数では許容範囲。
- **Follow-up**: 結合テスト時にWindows CPUでのログイン応答時間を確認する。

### Decision: 認可境界を認証仕様で提供し、業務適用は後続仕様に委譲
- **Context**: 後続仕様が管理者操作や本人履歴を制御する必要がある。
- **Alternatives Considered**:
  1. 認証仕様がFAQ・履歴へ直接アクセスして判定する — 認証が業務知識を持ちすぎる。
  2. 後続仕様が自らロール・所有者IDを比較する — 重複実装のリスク。
- **Selected Approach**: `require_authenticated_user`・`require_admin`・`require_owner`を認証仕様の`AuthContext`/`AuthorizationPolicy`に提供し、後続仕様はこれらを呼び出して自らのデータに適用する。
- **Rationale**: 認証と認可判定を分離し、業務データの所有権は業務仕様が責任を持つ。
- **Trade-offs**: 後続仕様実装者が`require_owner`を呼び出すことを忘れると漏洩リスクがあるが、これはレビューとテストで担保する。
- **Follow-up**: `require_owner`のadminバイパスを絶対に追加しないことは設計・実装レビューで確認する。

### Decision: Cookie属性の固定と設定駆動Secureフラグ
- **Context**: ローカルHTTP環境で動作させつつ、将来HTTPS移行も見据える。
- **Alternatives Considered**:
  1. Secureを常にtrue — ローカルHTTPではCookieが保存されない。
  2. Secureをfalse固定 — HTTPS移行時にセキュリティ低下。
- **Selected Approach**: HttpOnly=true、SameSite=Lax、Path=/は固定。Secureは`AuthSettings.auth_cookie_secure`で設定可能とし、既定値はローカル向けにfalse。
- **Rationale**: 研修用MVPをローカルで動かしつつ、本番移行時は設定変更のみで対応できる。
- **Trade-offs**: 既定値がfalseのため、本番利用時は運用者が明示的にtrueに設定する必要がある。
- **Follow-up**: 運用手順にSecure=trueの設定を含める。

## Risks & Mitigations
- **Risk**: foundationの`BaseEntity`・`MigrationRunner`・`RouterRegistry`等の具体的な契約が未確定のため、設計が仮定に依存している。 — Mitigation: 実装時にfoundationの実装を確認し、必要に応じてdesign.mdとtasks.mdを再検証する。
- **Risk**: Argon2idのコストパラメータがWindows CPUでは重すぎる可能性がある。 — Mitigation: 結合テストで実測し、許容範囲を超える場合はパラメータを調整する。
- **Risk**: 期限切れセッションがDBに蓄積される。 — Mitigation: MVPでは定期削除を実装せず、レコード数が増加してきた時点で再検証する。
- **Risk**: 管理者が全社員履歴を閲覧したいという要望が後から出る。 — Mitigation: `require_owner`にadminバイパスを持たせない設計で明示的に拒否し、必要なら新仕様として検討する。

## References
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) — セッション識別子のランダム性、有効期限、失効のガイドライン。
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) — Argon2id推奨。
- [argon2-cffi ドキュメント](https://argon2-cffi.readthedocs.io/) — Python用Argon2idバインディング。
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) — `Depends`による依存注入。
