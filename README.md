# HELPO

社内FAQ向けAIヘルプデスク（研修用MVP）の FastAPI ベースアプリケーションです。

## 前提

- Python 3.13 以上
- Windows PowerShell または macOS Terminal

## セットアップ

### Windows（PowerShell）

```powershell
cd "C:\Users\t-ono\Documents\70_研修\helpo"
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### macOS（Terminal）

```bash
cd "/Users/$(whoami)/Documents/70_研修/helpo"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## 環境変数

`.env.example` をコピーして `.env` を作成し、必要に応じて値を変更してください。

### Windows

```powershell
copy .env.example .env
```

### macOS

```bash
cp .env.example .env
```

主要な設定項目：

| 変数名 | デフォルト | 説明 |
|--------|------------|------|
| `DATABASE_URL` | `sqlite:///./helpo.db` | データベース接続URL |
| `APP_HOST` | `127.0.0.1` | サーバーホスト |
| `APP_PORT` | `8000` | サーバーポート |
| `DEBUG` | `false` | デバッグモード |

## ローカル起動

### Windows

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

`--reload` 付きで開発モード起動：

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### macOS

```bash
source .venv/bin/activate
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

`--reload` 付きで開発モード起動：

```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

起動後、ブラウザで以下にアクセスできます。

- トップページ： http://127.0.0.1:8000/
- 履歴（mock）： http://127.0.0.1:8000/history
- API ドキュメント： http://127.0.0.1:8000/docs

## テスト実行

### Windows

```powershell
.venv\Scripts\python.exe -m pytest -q
```

### macOS

```bash
source .venv/bin/activate
python3 -m pytest -q
```

## ディレクトリ構成

```text
helpo/
├── app/                 # アプリケーションコード
│   ├── config.py        # Pydantic Settings
│   ├── db.py            # DatabaseEngine
│   ├── migrations.py    # MigrationRunner
│   ├── base_models.py   # BaseEntity
│   ├── base_repository.py
│   ├── router_registry.py
│   ├── dependencies.py
│   ├── routers/
│   │   └── pages.py     # ページルート
│   ├── templates/       # Jinja2 テンプレート
│   ├── static/          # CSS / JS
│   └── ...
├── migrations/          # SQL マイグレーションファイル
├── tests/               # pytest テスト
├── main.py              # ASGI アプリ作成
├── pyproject.toml       # パッケージ設定
└── requirements.txt     # 依存関係
```

## 備考

- DB はデフォルトで `sqlite:///./helpo.db` のファイル SQLite を使用します。
- テスト実行時には `sqlite:///:memory:` が使用されます。
- ヘッダーナビゲーションは `app/static/js/nav.js` で、localStorage を使ったモック状態で動作します。
