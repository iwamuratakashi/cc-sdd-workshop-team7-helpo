# Research & Design Decisions

## Summary

- **Feature**: faq-management-and-search
- **Discovery Scope**: Extension (greenfield-like implementation; no existing application code, only specifications)
- **Key Findings**:
  - 既存のアプリケーションコードは存在せず、仕様書（requirements.md, design.md, tasks.md）のみが整備されている状態である。
  - プロジェクトの方向性として、Python 3.10+、FastAPI、SQLAlchemy 2.x、SQLite、Pydantic v2、Jinja2 を前提とする（roadmap.md より）。
  - FAQ 登録は Markdown ファイルアップロードに一本化され、一覧表示・更新・削除は不要となった。
  - Embedding モデルはライセンス・動作確認後に選定する必要があり、現時点では未確定とする。
  - Markdown の Q&A 抽出は、社内運用で制御可能な簡易構文（H2 見出し＝質問、後続段落＝回答）で十分である。

## Research Log

### Topic: Markdown ファイルの Q&A 抽出方式

- **Context**: FAQ 登録を Markdown ファイルアップロードに変更したため、ファイル内から質問文と回答文を機械的に抽出する方法が必要。
- **Sources Consulted**:
  - Python-Markdown 公式ドキュメント
  - mistletoe リポジトリ
  - 一般的な Markdown AST パーサーの比較情報
- **Findings**:
  - Python-Markdown は広く使われているが、AST 取得には拡張が必要。
  - mistletoe は軽量で AST 取得が容易。
  - ただし、本機能で求められるのは「H2 見出し＝質問、直後の段落＝回答」という決まった構造の抽出であり、フルパーサーは過剰である。
  - 正規表現または軽量トークナイザーで十分に実装可能で、外部依存を減らせる。
- **Implications**:
  - `MarkdownParser` を FAQ ドメイン内に実装し、抽出ルールをドメイン側で制御する。
  - フル Markdown への対応は将来の拡張として扱い、現時点では簡易構文に限定する。

### Topic: ファイルアップロードの設計

- **Context**: FAQ 登録を Markdown ファイルアップロードに変更したため、HTTP ファイルアップロードの取り扱いが必要。
- **Sources Consulted**:
  - FastAPI 公式ドキュメント（File / UploadFile）
  - multipart/form-data 周辺のセキュリティベストプラクティス
- **Findings**:
  - FastAPI の `UploadFile` は非同期ファイル読み取りをサポートし、大容量ファイルのメモリ消費を抑えられる。
  - ファイルサイズはミドルウェアまたはエンドポイント側で検証可能。
  - 許可する MIME type / 拡張子を絞ることで、誤った形式を事前に防げる。
- **Implications**:
  - エンドポイントは `multipart/form-data` とし、`UploadFile` を利用する。
  - 拡張子 `.md` と MIME type `text/markdown` を許可し、それ以外は拒否する。
  - 10MB を超えるファイルは 413 相当のエラーで拒否する。

### Topic: Embedding モデルの未確定性

- **Context**: 社内 PC（Windows、GPU なし）で動作する軽量 Embedding モデルが必要。
- **Sources Consulted**:
  - sentence-transformers ドキュメント
  - ONNX Runtime 推論の Windows CPU 対応情報
  - 日本語・多言語対応の軽量モデル候補情報
- **Findings**:
  - モデル選定はライセンス条項と実測性能を確認する必要がある。
  - 未検証のモデルを自動ダウンロード・選択することは避けるべき。
  - アダプター層を設ければ、モデル選定後に差し替え可能。
- **Implications**:
  - `FaqEmbeddingAdapter` のみを設計し、内部実装は未確定とする。
  - モデル未設定時は検索不可として 503 を返す。

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| モノリシ内ドメインパッケージ | foundation の層構造を拡張し、`app/faq/` 配下にドメインを配置する | 既存の `helpo-foundation` との整合性が高い、実装が集中する | FAQ 件数が増えた場合のスケーラビリティ | 前回の design.md と同様の方針 |
| 独立マイクロサービス | FAQ 機能を独立したサービスとして切り出す | 境界が明確 | 研修用 MVP には過大、運用コスト増 | 採用しない |
| Hexagonal Architecture | コアドメインを_ports/adapters_で囲む | テスト容易性、外部依存の分離 | シンプルな CRUD/検索には抽象化が過剰 | 採用しない |

**Selected**: モノリシ内ドメインパッケージ（`app/faq/`）

## Design Decisions

### Decision: Markdown Q&A 抽出ルール

- **Context**: Markdown ファイルから質問文と回答文を機械的に抽出する必要がある。
- **Alternatives Considered**:
  1. フル Markdown 構文対応（見出しレベル自由、複雑なリスト対応）
  2. 簡易構文：H2 見出しを質問、後続段落を回答として扱う
  3. 専用 YAML frontmatter 付き Markdown
- **Selected Approach**: 簡易構文（H2 見出し＝質問、後続段落＝回答）
- **Rationale**: 社内管理者が運用する FAQ データであり、決まった雛形に従わせる運用が現実的。実装・レビュー・テストがシンプルになる。
- **Trade-offs**: 表や箇条書きを含む高度な Markdown は自然な抽出が難しくなるが、研修用 MVP では許容範囲。
- **Follow-up**: 運用検証で構文の拡張要望が出た場合は design.md を更新する。

### Decision: FAQ 登録はアップロード API のみとする

- **Context**: 一覧表示・更新・削除を要件から削除した。
- **Alternatives Considered**:
  1. 登録 API のみ提供
  2. 管理画面も残しつつ、更新・削除は非表示にする
- **Selected Approach**: 登録 API（と最小限のアップロード画面）のみ提供
- **Rationale**: 要件に一覧・更新・削除がないため、不要な UI/API は実装しない。社内運用ではファイルを修正して再アップロードすることで対応可能。
- **Trade-offs**: 個別 FAQ の修正・削除はできないが、管理コストを削減できる。
- **Follow-up**: 運用で必要になった場合は別途仕様追加する。

### Decision: Embedding アダプターの未確定モデル対応

- **Context**: ローカル CPU 動作する Embedding モデルが必要だが、ライセンス確認が未済。
- **Alternatives Considered**:
  1. モデルを固定して実装する
  2. アダプター層だけ定義し、内部実装は未確定とする
- **Selected Approach**: アダプター層のみ定義
- **Rationale**: requirements.md に「ライセンス未確認のモデルを勝手に選ばない」と明記されているため、未確定を明示する。
- **Trade-offs**: 初期状態では検索が使えない場合があるが、安全側に寄せた設計。
- **Follow-up**: モデル選定後にアダプター実装を差し替える。

## Risks & Mitigations

- **Markdown 構文の多様性** — 簡易構文を運用ルールで制限し、パーサーのテストカバレッジを高める。
- **Embedding モデル未確定** — アダプター層で抽象化し、モデル未設定時は明確な 503 エラーで対応。
- **誤登録の訂正手段がない** — ファイルを修正して再アップロードする運用でカバー。運用で問題になれば削除機能を追加検討。
- **大容量ファイルのメモリ消費** — `UploadFile` を使い、10MB 上限を設ける。

## References

- FastAPI UploadFile: https://fastapi.tiangolo.com/tutorial/request-files/
- Python-Markdown: https://python-markdown.github.io/
- mistletoe: https://github.com/miyuchina/mistletoe
