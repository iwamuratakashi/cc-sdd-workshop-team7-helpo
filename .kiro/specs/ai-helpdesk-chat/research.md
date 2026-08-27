# Research & Design Decisions

## Summary
- **Feature**: ai-helpdesk-chat
- **Discovery Scope**: Complex Integration（既存FastAPIモノリスと3上流仕様への統合）
- **Key Findings**:
  - 上流の`FaqSearchService`は単一実装かつ十分に安定した契約であり、薄い`FaqSearchPort`は境界価値を増やさない。`ChatService`から直接利用する。
  - Windows CPU推論のhard timeoutには`spawn`プロセス境界が必要である。イベントループとDB `Session`を子プロセスへ渡さず、timeout時は要求取消後にworkerを破棄・再生成する。
  - runtime/modelは未選定とし、承認済み`ModelAdoptionManifest`とローカル設定・ファイルhashが一致するときだけ推論を有効化する。
  - 生成根拠制約はpromptだけでは保証できない。構造化source IDを生成結果に要求し、検証失敗時は決定的なFAQ直接回答へ退避する。
  - SQLiteの`ON DELETE SET NULL`は全接続で`PRAGMA foreign_keys=ON`が保証される場合だけ成立するため、Foundation接続契約を起動時に検証する。
  - timeout時だけでなくapplication shutdown時にもworkerを取消・terminate・joinし、子processを残さないlifecycle契約が必要である。
  - 外部公式情報はこの実行環境からlive verificationできなかった。下記URLは調査候補として記録し、採用時に公式最新版を再確認する必要がある。

## Research Log

### 上流仕様とfeature境界
- **Context**: Foundation、認証、FAQ検索の所有権を侵害せず統合する必要がある。
- **Sources Consulted**: `.kiro/specs/helpo-foundation/{requirements,design,tasks}.md`、`.kiro/specs/local-user-authentication/{requirements,design,tasks}.md`、`.kiro/specs/faq-management-and-search/{requirements,design,tasks}.md`。
- **Findings**:
  - Foundation契約は`BaseEntity`、commitしない`BaseRepository`、`Session`、`MigrationRunner.apply_migrations`、`ErrorHandler`、`WebLayout`、`RouterRegistry`である。
  - 認証契約は`CurrentUser`、`require_authenticated_user`、adminバイパスを持たない`require_owner`である。
  - FAQ契約は`FaqSearchService.search(db, query, top_k=5)`、`FaqSearchResult(query,candidates,has_match)`、`FaqCandidate(faq_id,question,answer,confidence,is_match)`である。適合閾値はFAQ側の固定判断で、chat側に設定や再計算を置けない。
  - featureは`app/chat`配下とfeatureテンプレート、`004` migrationを所有する。foundation所有の`config.py`、`dependencies.py`、`base.html`、`main.py`を変更せず、設定・router登録の拡張点を使う。
  - migration順は`foundation baseline.sql` → `002` auth → `003` FAQ → `004` chatであり、foundationを`001`とは呼ばない。
- **Implications**: 新規wrapperや共有設定変更を避け、上流型を直接注入する。古いfoundation health-check参照を設計へ持ち込まない。

### Windows spawn workerとhard timeout
- **Context**: 同期CPU推論がFastAPI event loopを塞がず、timeout後にCPU使用が収束しなければならない。
- **Sources Consulted**: Python multiprocessing公式ドキュメント https://docs.python.org/3/library/multiprocessing.html 、FastAPI async公式説明 https://fastapi.tiangolo.com/async/ 。本環境ではlive verification未実施。
- **Findings**:
  - Windowsの子プロセスは`spawn`前提で、引数は直列化可能なplain dataに限定すべきである。
  - futureの待機取消だけではnative推論を停止できない。queue待機・prompt構築・生成を一つのdeadlineで覆い、取消通知、短いgrace、残存時terminate/joinの順でworkerを破棄する必要がある。
  - FastAPI event loop、request、dependency、SQLAlchemy `Session`をworkerへ渡さない。親でFAQ検索と永続化を行い、workerには文字列・source ID・数値制限のみを渡す。
  - MVP同時生成数は1。timeout後のworker instanceは再利用せずclean processを遅延再生成する。
- **Implications**: `LocalLlmWorker`をプロセス境界、`LocalLlmAdapter`を親側deadline/生存期間管理境界とする。max output tokensとcharsを両方強制する。

### runtime/model候補と採用ゲート
- **Context**: Windows GPUなし、完全ローカル、ライセンス確認済みの構成だけを許可する一方、現時点でモデルを固定できない。
- **Sources Consulted**: llama.cpp https://github.com/ggml-org/llama.cpp 、llama-cpp-python https://github.com/abetlen/llama-cpp-python 、ONNX Runtime GenAI https://github.com/microsoft/onnxruntime-genai 、ONNX Runtime GenAI docs https://onnxruntime.ai/docs/genai/ 。いずれも本環境ではlive verification未実施。
- **Findings**:
  - **一次PoC候補**: `llama.cpp` + `llama-cpp-python`。ローカル量子化CPU推論候補だが、Windows build、停止性、モデル/tokenizer/template整合、各licenseを採用時に公式情報と実機で再検証する。
  - **条件付き候補**: ONNX Runtime GenAI。対象モデル対応、API成熟度、Windows CPU性能、停止方法を公式最新版で確認できた場合のみ比較する。
  - **却下**: cloud LLM/API（外部送信）、Transformersの自動取得経路（offline/no-download境界に不適合）、プロセス内native推論（hard timeout不能）。
  - **条件付き代替**: Transformers等を完全ローカル固定ファイルで用いる案は、CPU性能・配布物・停止性の採用証跡を満たす場合に限り再評価する。
- **Implications**: design/依存ファイルでruntime/model名を確定しない。採用時のfresh official verification完了まで`approved=false`とする。

### ModelAdoptionManifest
- **Context**: 「確認済み」の判断を再現可能かつfail-closedにする必要がある。
- **Sources Consulted**: Python hashlib https://docs.python.org/3/library/hashlib.html 、SPDX License List https://spdx.org/licenses/ 。本環境ではlive verification未実施。
- **Findings**:
  - ローカルartifact/recordにruntime、model、tokenizer、prompt templateの各version/hash、runtime/model等のlicenseと証跡、offline verification、対象Windows CPU benchmark、timeout停止・CPU収束 evidence、`approved`を保持できる。
  - 設定したartifact path/hashとmanifest記録が一致しない場合は準備未完了として扱える。
- **Implications**: `ManifestValidator`はlocal設定に固定した期待manifest hashとmanifest bytesを照合し、その後`approved=true`とartifact群のhash一致を要求する。期待hashをmanifest自身へ置く自己参照方式は採用しない。`LocalLlmAdapter.is_ready`は検証失敗時falseとする。repo ID、URL、download処理、network clientをruntime設定・実装に持たない。

### prompt injectionと構造化出力
- **Context**: 利用者質問と管理者登録FAQはいずれも命令を含み得るuntrusted dataである。
- **Sources Consulted**: OWASP LLM Prompt Injection Prevention Cheat Sheet https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html 、Pydantic models https://docs.pydantic.dev/latest/concepts/models/ 。本環境ではlive verification未実施。
- **Findings**:
  - prompt上でinstructionとdataを分離し、FAQをopaqueなsource ID付き構造データとして扱う。`is_match=true`だけを含め、履歴・tools・外部知識を与えない。
  - 出力を`answer`と`source_ids`のschemaに限定し、parse失敗、空、token/char超過、未知または未許可IDを拒否できる。
  - 意味的groundingの完全判定はできないため、検証失敗時は登録済み回答をそのまま返す方が安全である。
- **Implications**: fallbackは適合候補を`confidence DESC, faq_id ASC`で並べた先頭とする。HTMLはJinja autoescape/テキスト挿入を維持する。

### 冪等送信、履歴、snapshot
- **Context**: UI二重クリック抑止だけではretryや複数tabによる重複保存を防げない。
- **Sources Consulted**: SQLite UNIQUE constraints https://www.sqlite.org/lang_createtable.html 、SQLite foreign keys https://www.sqlite.org/foreignkeys.html 。本環境ではlive verification未実施。
- **Findings**:
  - client生成UUID `request_id`と`UNIQUE(owner_user_id, request_id)`を永続化境界に置くと利用者間の衝突なく冪等化できる。
  - 同じkeyの再要求は既存のpersisted resultを返し、二行目を作らない。MVPは同期APIのため、同時競合で既存行がまだ取得不能なら短い再読後409として再試行可能にし、別生成を開始しない。
  - SQLiteには単純な`limit/offset`が十分であり、`created_at DESC, id DESC`で安定順序にする。
  - FAQ FKはnullable `ON DELETE SET NULL`、`faq_id_at_answer`とquestion/answer/confidence snapshotは不変である。`BaseEntity.updated_at`があってもsnapshot rowは更新しない。
  - SQLiteの外部キー制約は接続ごとの`PRAGMA foreign_keys=ON`が前提である。migration接続だけでなく通常Sessionの全接続でFoundationが有効化し、chat起動時に検証する必要がある。
- **Implications**: 生成結果と全snapshotを一transactionで保存し、失敗時はrollbackする。FK enforcementが無効ならchatをfail-fastで起動不能にし、Foundationの接続所有権をchat側で迂回しない。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| feature-based monolith + process adapter | 既存FastAPI内でchatを構成し推論だけspawn workerへ隔離 | 上流整合、DB一貫性、hard timeout | worker lifecycle検証が必要 | 採用 |
| `FaqSearchPort` wrapper | 上流serviceを薄く包む | mock差替え | 単一実装を重複抽象化 | 却下、直接注入 |
| process内推論 | 同一workerでnative runtimeを実行 | 単純 | event loop占有、停止不能 | 却下 |
| 外部LLM API | cloud生成 | 運用容易 | 情報外部送信、offline不可 | 却下 |
| 非同期job基盤 | durable queueで生成 | 高並列 | MVPに過大、状態追加 | 却下 |
| FAQ直接回答のみ | 生成しない | 最安全 | 自然文生成要件を満たさない | fallbackとして採用 |

## Design Decisions

### Decision: FAQ検索serviceを直接採用する
- **Context**: 検索は既に上流が明確な型付き契約と単一実装を提供する。
- **Alternatives Considered**: 薄い`FaqSearchPort`、`FaqSearchService`直接注入。
- **Selected Approach**: `ChatService`が`FaqSearchService`を直接受け取る。
- **Rationale**: speculative abstractionを除去し、適合判断の所有者を明確化する。
- **Trade-offs**: 上流契約変更はchatのrevalidationを直接発生させる。
- **Follow-up**: integration testでは実service contractのfake/stubを注入する。

### Decision: deadline付きprocess isolation
- **Context**: timeoutが応答だけでなくCPU計算停止を保証する必要がある。
- **Alternatives Considered**: thread/future取消、常駐spawn worker、requestごとのprocess。
- **Selected Approach**: 同時実行1の常駐workerをadapterが管理し、deadline超過時は取消、grace、terminate、破棄、clean再生成とする。
- **Rationale**: load costを抑えつつnative hangをprocess terminationで封じる。
- **Trade-offs**: timeout後の次回はreload costが発生する。
- **Follow-up**: 対象Windows CPUで停止後CPU収束を実測しmanifestへ記録する。

### Decision: 採用manifestでfail-closedにする
- **Context**: runtime/modelを今固定せず、未検証artifact利用を禁止する。
- **Alternatives Considered**: model名固定、設定flagだけ、証跡付きmanifest。
- **Selected Approach**: version/hash/license/offline/benchmark/timeout evidenceを持つ`ModelAdoptionManifest`をローカルに置く。
- **Rationale**: 採用と変更のgateを監査可能にする。
- **Trade-offs**: 初回導入に手動検証作業が必要。
- **Follow-up**: 採用時に上記公式URLをfresh verificationし証跡へ日付と結果を残す。

### Decision: 根拠限定生成を構造検証とfallbackで一般化する
- **Context**: 3.1、3.5、4.1-4.4、5.2は「許可根拠集合から逸脱しない」という同一問題である。
- **Alternatives Considered**: promptのみ、自由文heuristic、source ID付きschema + deterministic fallback。
- **Selected Approach**: 許可source ID集合を入力・出力で検証し、失敗時は`confidence DESC, faq_id ASC`先頭の登録回答へ退避する。
- **Rationale**: 検証可能な範囲を型と集合制約へ落とし込む。
- **Trade-offs**: 意味的逸脱を完全検知はできない。
- **Follow-up**: malicious question/FAQ、未知source ID、parse failureをtest fixture化する。

### Decision: DB制約を冪等性のauthorityとする
- **Context**: 1.5の重複抑止はclient stateだけでは不足する。
- **Alternatives Considered**: button disable、process memory cache、DB unique key。
- **Selected Approach**: client UUIDと`UNIQUE(owner_user_id, request_id)`を用い、既存persisted resultを再利用する。
- **Rationale**: 再起動・複数process・HTTP retryにも一貫する。
- **Trade-offs**: 同時in-flight競合時の409再試行契約が必要。
- **Follow-up**: 同時POSTと同一UUID再送をintegration testする。

### Decision: build-vs-adoptとsimplification
- **Context**: 最小MVPを維持する。
- **Alternatives Considered**: 推論engine自作、既存runtime採用、会話履歴、queue、多言語、configurable threshold。
- **Selected Approach**: 推論runtimeは採用ゲート後にadoptし、業務固有adapter/policyだけbuildする。会話履歴投入、tools、network、streaming、queue、多言語subsystem、FAQ threshold設定を作らない。窓口案内は検証済みlocal plain textとする。
- **Rationale**: 現要求を満たす最小の責任境界である。
- **Trade-offs**: MVPは同時生成1、単発質問、日本語UIに限定される。
- **Follow-up**: 負荷要件が変わった場合のみarchitectureを再評価する。

## Risks & Mitigations
- Prompt injection/根拠外生成 — instruction/data分離、許可ID schema検証、登録回答fallback、HTML escape。
- timeout後のnative処理残存 — grace後terminate/join、worker破棄、Windows実機でCPU収束証跡。
- application shutdown後の子process残存 — feature lifecycleで受付停止、取消、grace、terminate/joinを実施する。
- SQLite外部キー無効化によるsnapshot参照不整合 — 全接続の`PRAGMA foreign_keys=ON`をFoundation契約と起動検証で保証する。
- artifact差替え・license drift — manifest hash照合、`approved` gate、変更時fresh official verification。
- duplicate生成/履歴 — owner scoped UUID unique constraint、既存結果再利用、in-flight競合で二重生成禁止。
- FAQ更新削除による履歴変質 — nullable FK `ON DELETE SET NULL`と不変snapshot。
- 所有者漏えい — owner絞込み一覧、admin bypassなし`require_owner`、本文をlogしない。
- SQLite競合/部分保存 — 推論をtransaction外で行い、回答とsnapshotのみ短い単一transactionで保存・rollback。
- 外部情報の鮮度 — 本調査ではlive verification不能と明記し、採用manifest承認前に公式URLを再確認する。

## References
- [Python multiprocessing](https://docs.python.org/3/library/multiprocessing.html) — Windows spawnとprocess管理。
- [Python hashlib](https://docs.python.org/3/library/hashlib.html) — artifact hash検証。
- [FastAPI async](https://fastapi.tiangolo.com/async/) — event loop境界。
- [llama.cpp](https://github.com/ggml-org/llama.cpp) — 一次PoC runtime候補。
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) — 一次PoC Python binding候補。
- [ONNX Runtime GenAI](https://github.com/microsoft/onnxruntime-genai) / [docs](https://onnxruntime.ai/docs/genai/) — 条件付き候補。
- [OWASP Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) — untrusted prompt data対策。
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) — 構造化出力境界。
- [SQLite CREATE TABLE](https://www.sqlite.org/lang_createtable.html) / [Foreign Keys](https://www.sqlite.org/foreignkeys.html) — unique/FK制約。
- [SPDX License List](https://spdx.org/licenses/) — license識別候補。
- `.kiro/specs/helpo-foundation/design.md`、`.kiro/specs/local-user-authentication/design.md`、`.kiro/specs/faq-management-and-search/design.md` — 正規上流契約。
