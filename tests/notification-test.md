# 通知機能テスト仕様書

## 概要

`run-tasks` コマンド（`.claude/commands/run-tasks.md`）が呼び出す3経路の通知機能を検証するためのテスト仕様。

---

## テスト対象の通知経路

| # | 経路 | 呼び出し箇所 | 関数 |
|---|------|-------------|------|
| 1 | Backlog コメント（GitHub Issue 作成後） | `run-tasks.md` L37 | `add_issue_comment` |
| 2 | Backlog コメント（Draft PR 作成後） | `run-tasks.md` L57 | `add_issue_comment` |
| 3 | Backlog Wiki 投稿（実行サマリー） | `run-tasks.md` L67–69 | `add_wiki` |

---

## テストケース

### TC-01: Backlog コメント – GitHub Issue 作成通知

**前提条件**
- Backlog に「処理中」課題が存在すること
- GitHub Issue が正常に作成されること

**手順**
1. `run-tasks` を実行し Phase 1 を完了させる
2. 対象の Backlog 課題のコメント一覧を確認する

**期待結果**
- コメントが1件追加されること
- コメント本文が `GitHub Issue 作成: https://github.com/nohara-kengo/claude-state-manager/issues/{N}` の形式であること
- URL が実際に存在する GitHub Issue を指していること

**確認方法**
```
mcp__backlog__get_issue_comments(issueIdOrKey="{issueKey}")
→ comments[-1].content に "GitHub Issue 作成: https://github.com/..." が含まれる
```

---

### TC-02: Backlog コメント – Draft PR 作成通知

**前提条件**
- Phase 1 が成功し GitHub Issue が存在すること
- Draft PR が正常に作成されること

**手順**
1. `run-tasks` を実行し Phase 2 を完了させる
2. 対象の Backlog 課題のコメント一覧を確認する

**期待結果**
- Phase 1 のコメントに加え、もう1件コメントが追加されること
- コメント本文が `Draft PR 作成: https://github.com/nohara-kengo/claude-state-manager/pull/{N}` の形式であること
- URL が実際に存在する Draft PR を指していること

**確認方法**
```
mcp__backlog__get_issue_comments(issueIdOrKey="{issueKey}")
→ comments[-1].content に "Draft PR 作成: https://github.com/..." が含まれる
```

---

### TC-03: Backlog Wiki – 実行サマリー投稿

**前提条件**
- `run-tasks` が少なくとも1件の課題を処理し終了すること

**手順**
1. `run-tasks` を実行し全フェーズを完了させる
2. Backlog Wiki の一覧を確認する

**期待結果**
- タイトルが `ログ/AI実行/YYYY-MM-DD/HH:mm` 形式の Wiki ページが作成されること
- 本文にサマリーテーブル（`| 課題キー | 優先度 | モデル | ...`）が含まれること
- 失敗課題がある場合、エラー詳細セクションが含まれること

**確認方法**
```
mcp__backlog__get_wiki_pages(projectIdOrKey="NOHARATEST")
→ 最新ページのタイトルが "ログ/AI実行/YYYY-MM-DD/HH:mm" にマッチすること
mcp__backlog__get_wiki(wikiId={id})
→ content にサマリーテーブルが含まれること
```

---

### TC-04: 通知失敗時のエラーハンドリング

**前提条件**
- Backlog API Key が無効または権限が不足している状態を模擬する

**手順**
1. 環境変数 `BACKLOG_API_KEY` に不正な値を設定して `run-tasks` を実行する
2. エラーログを確認する

**期待結果**
- 通知失敗がサマリーに記録されること
- 通知失敗によってメイン処理（Issue/PR 作成）が中断されないこと
- エラーメッセージに失敗した通知の種別と対象 issueKey が含まれること

---

## テスト結果記録フォーマット

テスト実施後、以下のフォーマットで結果を記録する。

```markdown
## 通知テスト実施結果

- **実施日時**: YYYY-MM-DD HH:mm
- **実施者**: （担当者名）
- **対象ブランチ**: task/NOHARATEST-21

| テストケース | 結果 | 備考 |
|-------------|------|------|
| TC-01: Backlogコメント（Issue作成後） | PASS / FAIL | |
| TC-02: Backlogコメント（PR作成後）   | PASS / FAIL | |
| TC-03: Backlog Wiki投稿              | PASS / FAIL | |
| TC-04: エラーハンドリング            | PASS / FAIL | |

### 失敗詳細
（FAIL の場合のみ記載）
```

---

## 参照

- `.claude/commands/run-tasks.md` – 通知呼び出し箇所: L37, L57, L67–69
- Backlog MCP: `add_issue_comment`, `add_wiki`
- 対象リポジトリ: `nohara-kengo/claude-state-manager`
