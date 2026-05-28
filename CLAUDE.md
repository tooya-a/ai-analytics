# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクトの目的

このリポジトリは「チームメンバーのAI活用スキルを可視化・改善する**メタツール**」。単なる利用ログの可視化ではなく、`pivot_count`（試行錯誤の量）/ `resolution`（解決可否）/ `category` / `blockers` といった**行動データ**を蓄積し、AIとの協働能力そのものを継続的に高めることを最終目的とする（詳細は `README.md` 冒頭の「最終目的」セクション）。

機能追加や修正の判断は、この目的（＝AIの使い方を学習する仕組み）に沿うかどうかを基準にすること。

## 主要コマンド

```bash
# 依存インストール
pip install -r requirements.txt

# 起動（http://localhost:8501）
streamlit run app.py

# 共有ログディレクトリを使う場合
LOGS_DIR=~/ai-logs/sessions streamlit run app.py
```

ビルド／リント／テストフレームワークは導入されていない（単一ファイル Streamlit アプリ）。動作確認はブラウザでの目視。

## アーキテクチャ

**単一ファイル Streamlit アプリ**（`app.py`、約190行）。レイヤ分けはしないこと。データフローは以下の一方向：

```
logs/sessions/*.json  ──▶  load_logs()  ──▶  pd.DataFrame  ──▶  3 tabs (KPI / per-user / AI機能)
                                                  │
                                                  └─ tab3 (AI機能) only: Anthropic API (claude-haiku-4-5 / claude-sonnet-4-6)
```

### 重要な設計ポイント

- **JSON スキーマがインターフェース**: `logs/sessions/*.json` のフィールド（`user` / `date` / `pivot_count` / `resolution` / `category` / `approach` / `key_decisions` / `blockers` など）は `app.py` が直接参照する。スキーマを変える場合は `README.md` の「ログのJSONスキーマ」セクションと、ログを生成する `.claude/skills/session-log/` の両方を併せて更新すること。
- **ログ生成の本体は外部スキル**: ログ JSON を作るのは `/session-log` スラッシュコマンド（`.claude/skills/session-log/`）。app.py は読み込み専用。
- **`LOGS_DIR` 環境変数**: デフォルトは `logs/sessions/`（リポジトリ内・個人データなので `.gitignore` 済み）。複数プロジェクトのログを集約する場合は `LOGS_DIR` で切り替える前提。パスをハードコードしないこと。
- **`@st.cache_data`**: `load_logs()` はキャッシュされる。新規ログを追加した直後はサイドバーの「キャッシュ更新」ボタンを押さないと反映されない。
- **API キー解決順**: `st.secrets["ANTHROPIC_API_KEY"]` → `os.getenv("ANTHROPIC_API_KEY")` の順で読む。未設定時はボタンクリック時にトースト通知を出す（フォールバック）。この**フォールバックは仕様**なので削らないこと。
- **モデル ID**: ログ自動生成は `claude-haiku-4-5-20251001`、パターン分析は `claude-sonnet-4-6` で固定。変える場合は最新のモデル ID を確認すること。
- **タブ構成**: `📈 概要` / `👤 ユーザー別` / `🤖 AI機能` の3タブ。AI機能タブはログ生成（上部）とパターン分析（下部）を統合。

## ファイル運用ルール

- `.streamlit/secrets.toml` と `logs/sessions/` は `.gitignore` 済み（個人データ／秘密情報）。コミット対象に入れないこと。
- `.claude/settings.local.json` も同様（個人の Claude 上書き設定）。
- `docs/decisions/`（`/design-doc` の出力先）はまだ存在しない場合がある。生成スキルが作る前提。

## 関連スキル

このリポジトリには 3 つのプロジェクトスキルが入っている（`.claude/skills/`）：

| スキル | 役割 | 出力先 |
|--------|------|--------|
| `/session-log` | セッションを JSON でログ記録（このアプリの入力源） | `logs/sessions/` |
| `/design-doc` | 設計判断を Markdown で保存 | `docs/decisions/` |
| `/task-report` | 作業レポートを Google Drive に保存 | Google Drive |

`/session-log` はこのアプリの**データ供給源**なので、出力 JSON のスキーマを変える変更はアプリ側と必ず同期させること。
