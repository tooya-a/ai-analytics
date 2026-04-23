# AI壁打ち Analytics

チームメンバーのAI活用状況を可視化・分析するStreamlitダッシュボード。  
Claude Codeとのセッションログ（JSON）を読み込み、思考パターンや解決率をグラフで表示する。

---

## 概要

```
ai-analytics/
├── app.py                        # Streamlitアプリ本体
├── logs/
│   └── sessions/                 # セッションログ置き場（.gitignore済み）
│       └── YYYY-MM-DD-user-topic.json
├── docs/
│   └── decisions/                # 設計ドキュメント（/design-doc で生成）
└── .claude/
    └── skills/
        ├── session-log/          # セッションをJSONでログ記録するスキル
        ├── design-doc/           # 設計ナレッジをMarkdownで保存するスキル
        └── task-report/          # 作業レポートをGoogle Driveに保存するスキル
```

---

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. APIキーの設定

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

`.streamlit/secrets.toml` を開いてAPIキーを入力：

```toml
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxx"
```

### 3. 起動

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 が自動的に開く。

---

## ログの記録方法

セッション終了時に Claude Code で以下を実行：

```
/session-log
```

`logs/sessions/YYYY-MM-DD-{user}-{topic}.json` に自動保存される。  
保存後はアプリのサイドバー「キャッシュ更新」を押すと反映される。

### ログのJSONスキーマ

```json
{
  "user": "git config user.name の値",
  "date": "YYYY-MM-DD",
  "started_at": "HH:MM",
  "category": "bug_fix | feature | design | refactor | infrastructure | question",
  "topic": "何に取り組んだか（1行）",
  "problem": "解こうとした課題の説明",
  "approach": "どのようにAIと壁打ちしたか（試行錯誤の流れ）",
  "resolution": "resolved | unresolved | in_progress",
  "output": "成果物（PR番号、ファイルパスなど）",
  "pivot_count": 2,
  "key_decisions": ["重要な判断とその理由"],
  "blockers": ["解決できなかった点"],
  "notes": "その他メモ"
}
```

---

## 画面構成

### タブ1：概要（📈）

| 指標 | 説明 |
|------|------|
| 総セッション数 | 読み込んだログファイルの件数 |
| ユーザー数 | ユニークな `user` の数 |
| 平均ピボット数 | 方針転換の平均回数（高いほど試行錯誤が多い） |
| 解決率 | `resolution == "resolved"` の割合 |

セッション数の時系列推移を棒グラフで表示。

### タブ2：ユーザー別（👤）

- **ピボット数分布（箱ひげ図）**: ユーザーごとの試行錯誤のばらつきを比較
- **カテゴリ分布（積み上げ棒グラフ）**: bug_fix / feature / design などの割合
- **解決率（棒グラフ）**: ユーザーごとの成功率
- **セッション一覧テーブル**: 日付・カテゴリ・ピボット数などを一覧表示

### タブ3：テキスト分析（🤖）

蓄積されたログをClaudeが読んで以下を分析：

1. ユーザーごとの思考・アプローチの特徴
2. ピボットが多い場合のパターン
3. チーム全体として改善できそうな点

「分析を実行」ボタンを押すと実行される（`ANTHROPIC_API_KEY` が必要）。

---

## サイドバー

| 操作 | 説明 |
|------|------|
| ユーザー選択 | 特定のユーザーに絞り込む |
| 期間フィルター | 日付範囲を指定 |
| キャッシュ更新 | 新しいログファイルを反映 |

---

## ログの保存先について

デフォルトは `logs/sessions/`（このリポジトリ内）。  
複数プロジェクトのログを一か所に集約したい場合（パターンB）は環境変数で切り替え可能：

```bash
# 共通ディレクトリに集約する例
LOGS_DIR=~/ai-logs/sessions streamlit run app.py
```

---

## 利用可能なスキル

| スキル | 使い方 | 保存先 |
|--------|--------|--------|
| `/session-log` | セッション終了時に実行 → JSONをログ記録 | `logs/sessions/` |
| `/design-doc` | 設計・実装のナレッジを文書化 | `docs/decisions/` |
| `/task-report` | 作業レポートをGoogle Driveに保存 | Google Drive |
