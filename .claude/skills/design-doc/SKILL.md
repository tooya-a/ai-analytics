---
name: design-doc
description: 会話から実装・設計のナレッジドキュメントを生成し docs/decisions/ に保存する。
tags: [documentation, knowledge, design, ナレッジ共有]
---

# 設計ドキュメント生成

## テンプレート参照

!`cat .claude/skills/design-doc/references/01-doc-template.md`

## 手順

1. **会話の分析**
   - 現在の会話から以下を抽出する：
     - 解決した課題・実装した機能
     - 採用した設計・アプローチとその理由
     - 検討して却下した選択肢
     - 変更したファイル
     - ハマりポイント・注意事項
   - `$ARGUMENTS` にトピック名が指定されている場合はファイル名に使用する
   - 指定がない場合は会話内容から適切なトピック名を英語スネークケースで生成する

2. **ドキュメント生成**
   - テンプレートに沿って内容を埋める
   - カテゴリは内容から判断する（bug_fix / feature / design / refactor / infrastructure）
   - 作成者は git config user.name を使用する：
     ```bash
     git config user.name
     ```
   - ファイル名: `YYYY-MM-DD-{topic}.md`（今日の日付を使用）

3. **保存先の確認**
   - `docs/decisions/` ディレクトリが存在しない場合は作成する：
     ```bash
     mkdir -p docs/decisions
     ```
   - ドキュメントを `docs/decisions/YYYY-MM-DD-{topic}.md` に保存する

4. **内容の確認**
   - 生成したドキュメントを表示して「この内容でよいですか？」と確認する
   - 修正依頼があれば対応してから保存する

5. **保存完了の報告**
   - 保存したファイルパスを表示する
   - 「git add して commit しますか？」と確認する
   - 承認された場合、以下のコマンドで commit する：
     ```bash
     git add docs/decisions/
     git commit -m "docs: add design doc for {topic}"
     ```

## 注意事項

- ドキュメントは日本語で書く
- 「何を作ったか」より「なぜそうしたか」を重視して記述する
- コードスニペットは必要最小限にとどめ、ファイルパスの参照で代替する
- 推測で書かず、会話に出ていない情報は「未記載」とする
