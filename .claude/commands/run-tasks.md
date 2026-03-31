以下の手順でGitHub Issueを処理してPRを作成してください。
MCPツール（github, backlog）を使って操作してください。

## 手順

1. GitHub MCPで `claude-task` ラベル付きのopenなIssueを一覧取得する
2. 各Issueに対して以下を実行:
   - Issueの内容を読み、何を修正すべきか理解する
   - `git checkout -b fix/issue-{番号}` でブランチを作成
   - 必要なコード修正を行う
   - gitでコミット・プッシュする
   - GitHub MCPでPRを作成（本文に `Closes #{番号}` を含める）
   - Backlog MCPで対応する課題があればステータスを更新する
3. 完了したら処理結果のサマリーを表示

対象リポジトリ: $ARGUMENTS
