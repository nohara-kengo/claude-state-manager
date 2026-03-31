# プロジェクト設定

## Backlog
- ドメイン: comthink06.backlog.com
- プロジェクトキー: NOHARATEST
- projectId: （初回実行時に `get_project` で取得し、ここに記入）
- API Key: 環境変数 `BACKLOG_API_KEY` を優先。未設定時は `grep -A5 backlog ~/.claude.json` でフォールバック

## GitHub
- リポジトリ: nohara-kengo/claude-state-manager

## モデル選択（実装サブエージェント用）

|            | バグ    | タスク  | 要望     |
|------------|---------|---------|----------|
| 高(pid=2)  | opus    | opus    | opus     |
| 中(pid=3)  | sonnet  | sonnet  | opus     |
| 低(pid=4)  | haiku   | haiku   | sonnet   |

estimatedHours 補正: 2h以上→1段階UP / 0.5h以下→1段階DOWN

## ルール

- Glob/Grep 優先。Read はピンポイント
- 読まない: node_modules/, dist/, build/, .git/, ロックファイル, バイナリ
- GitHub MCP は Issue/PR 作成のみ。Backlog get_issue はサブから呼ばない
- 孫エージェント禁止。エラー時リトライ不可
- 予算目安: 課題数 × $0.50
