自分が担当する Backlog「処理中」課題を調査 → GitHub Issue → Draft PR まで一気通貫で実行。CLAUDE.md に従う。

## 0. 事前準備

1. CLAUDE.md から設定読み込み（ドメイン、プロジェクトキー、projectId）
2. BACKLOG_API_KEY: 環境変数 `BACKLOG_API_KEY` から取得。未設定なら `grep -A5 backlog ~/.claude.json` でフォールバック
3. 「AI処理済み」ステータス確認・追加 → statusId 控える
4. `get_myself` → 自分の Backlog ID 控える
5. 重複防止: 既に同じプロジェクトで実行中のプロセスがないか確認（`/tmp/claude-state-manager-{projectKey}.lock` が存在すれば終了）。なければロックファイル作成、終了時に削除

## 1. 課題取得

```
get_issues(projectId=[CLAUDE.mdのprojectId], statusId=[2], assigneeId=[自分のid], sort="priority", order="asc")
```

issueKey, summary, description, priorityId, issueType.name, estimatedHours だけ抽出。0件なら終了。

## 2. Phase 1: 調査 → GitHub Issue

最大3件バッチで Plan サブエージェント並列起動。4件以上は3件ずつ順次バッチ実行。

- `subagent_type`: "Plan" / `model`: "sonnet"

プロンプト:
```
{issueKey}「{summary}」を調査。コード変更不可。
説明: {description}
見積工数: {estimatedHours}h
Glob/Grep/Read で関連ファイル特定 → 修正方針をまとめる。
報告: 課題キー / 関連ファイル(path:行) / 修正方針(番号リスト) / 影響範囲 / 使用モデル
```

**調査失敗時**: エラーを分類して記録し、その課題は Phase 2 に渡さない。サマリーに失敗理由・エラーコードを記載。
- エラー分類:
  - `MCP_FAILURE`: Backlog/GitHub MCP 呼び出し失敗（接続エラー、認証エラー等）
  - `TIMEOUT`: サブエージェントの応答タイムアウト
  - `CONTEXT_INSUFFICIENT`: コードベース調査で十分な情報が得られなかった
  - `UNKNOWN`: 上記に該当しないエラー

調査結果を元にメインが `.github/ISSUE_TEMPLATE/ai-planned.md` のフォーマットで GitHub Issue 作成。
Backlog にコメント: `GitHub Issue 作成: {issueUrl}`

## 3. Phase 2: Issue → Draft PR

Phase 1 で成功した Issue のみ対象。最大3件バッチで実装サブエージェント並列起動。4件以上は3件ずつ順次バッチ実行。

- `subagent_type`: "general-purpose"
- `model`: CLAUDE.md マトリクス
- `isolation`: "worktree"

ブランチ命名: `{種別prefix}/{issueKey}`（バグ→`fix/`, タスク→`task/`, 要望→`feature/`）

プロンプト:
```
Issue #{issueNumber} に基づき Draft PR 作成。
{issueBody}
Backlog: {issueKey} / https://{domain}/view/{issueKey} / statusId={statusId}
ブランチ: {種別prefix}/{issueKey}
手順: 既存ブランチ確認 → checkout → 修正 → push → gh pr create --draft(Closes #N) → Backlog更新・コメント
PR本文は .github/PULL_REQUEST_TEMPLATE/ai-fix.md のフォーマットに従う。
Backlogコメント: `Draft PR 作成: {prUrl}`
制約: Issue方針に従う。Glob/Grep優先。GitHub MCPはPRのみ。Backlog get_issue不可。リトライ不可。孫不可。
報告: 課題キー / 成功or失敗 / PR URL / エラー
```

**実装失敗時**: Phase 1 と同様にエラーを分類（`MCP_FAILURE` / `TIMEOUT` / `CONTEXT_INSUFFICIENT` / `UNKNOWN`）して記録。

## 4. サマリー・ログ

### ログレベル

出力する情報にログレベルを付与し、段階的に出力を制御する。

| レベル | 用途 | 例 |
|--------|------|-----|
| INFO | 正常系の進捗・結果 | 課題取得完了、Issue作成、PR作成 |
| WARN | 処理は継続するが注意が必要 | estimatedHours未設定、worktreeクリーンアップ失敗 |
| ERROR | 処理失敗・中断 | MCP接続エラー、サブエージェントタイムアウト |

デフォルトは全レベル出力。将来的に環境変数 `LOG_LEVEL` で制御可能とする。

### サマリーテーブル

| 課題キー | 優先度 | モデル | サマリー | Issue | Draft PR | 結果 | 処理時間 | エラーコード |
|----------|--------|--------|----------|-------|----------|------|----------|--------------|

- **処理時間**: Phase 1 + Phase 2 の合計（秒単位）。サブエージェント起動から完了までを計測
- **エラーコード**: 失敗時のみ記載（`MCP_FAILURE` / `TIMEOUT` / `CONTEXT_INSUFFICIENT` / `UNKNOWN`）。成功時は `-`

### Wiki 投稿

実行ログを Backlog Wiki に投稿（`add_wiki`）:
- タイトル: `ログ/{リポジトリ名}/AI実行/{YYYY-MM-DD}/{HH:mm}`
- 内容: 上記サマリーテーブル + 失敗課題のエラー詳細（エラーコード・エラーメッセージ含む）

※ タイトルにリポジトリ名を含めることで、複数リポジトリの実行ログを区別可能にする。

### クリーンアップ

`.claude/worktrees/` が残っていれば削除。
- [INFO] 削除成功: `worktree クリーンアップ完了`
- [WARN] 削除失敗: `worktree クリーンアップ失敗: {エラーメッセージ}` — 手動削除を促す

ロックファイル削除。

対象リポジトリ: $ARGUMENTS
