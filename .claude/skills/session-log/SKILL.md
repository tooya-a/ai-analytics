---
name: session-log
description: AIとの壁打ちセッションをJSON形式でログとして記録する。AI活用の可視化・分析用データ収集。
tags: [logging, analytics, ai-usage, チーム可視化]
---

# セッションログ記録

## スキーマ参照

!`cat .claude/skills/session-log/references/01-schema.json`

## 手順

1. **会話の分析**
   - 現在の会話全体を振り返り、スキーマの各フィールドを埋める
   - `user` は以下で取得する：
     ```bash
     git config user.name
     ```
   - `pivot_count`: 方針転換（「やっぱりこうしよう」「別のアプローチを試す」など）の回数を数える
   - `resolution` の判断基準：
     - `resolved` — 目的の課題が解決できた
     - `unresolved` — 解決できなかった・諦めた
     - `in_progress` — まだ継続中・途中で終わった
   - 会話に出ていない情報は `null` または空配列にする（推測で埋めない）

2. **保存先の確認**
   - `logs/sessions/` ディレクトリが存在しない場合は作成する：
     ```bash
     mkdir -p logs/sessions
     ```
   - ファイル名: `YYYY-MM-DD-{user}-{topic_snake_case}.json`

3. **内容の確認**
   - 生成したJSONを表示して「この内容でよいですか？」と確認する
   - `topic`・`approach`・`resolution` は特に確認する（分析の核心になるため）
   - 修正依頼があれば対応してから保存する

4. **保存完了の報告**
   - 保存したファイルパスを表示する
   - git commitは行わない（ログは随時蓄積するため）

## 注意事項

- ログは分析用データなので簡潔に・事実ベースで記述する
- `approach` は「何をどの順番で試したか」のプロセスを重視する
- `pivot_count` はアプローチの試行錯誤の多さを示す指標になる
- このログが蓄積されることで「よく壁打ちする人の行動パターン」が見えてくる
- ログの保存先: `ai-analytics/logs/sessions/`（PatternBへの移行時は LOGS_DIR 環境変数で変更可能）
