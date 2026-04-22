# AI壁打ち Analytics

チームメンバーごとのAI壁打ちパターンを可視化するStreamlitアプリ。

## ローカル起動手順

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. APIキーの設定

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

`.streamlit/secrets.toml` をエディタで開き、APIキーを入力：

```toml
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"
```

### 3. 起動

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 が自動的に開きます。

### 4. ログの場所

デフォルトは `../reservation-system/logs/sessions/*.json` を読み込みます。
別のディレクトリを指定したい場合は環境変数で上書きできます：

```bash
LOGS_DIR=/path/to/logs streamlit run app.py
```

### キャッシュのクリア

ログファイルを追加した後は、サイドバーの「キャッシュ更新」ボタンを押すと最新データが反映されます。
