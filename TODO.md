# 残件・改善タスク

## 優先度: 高

### テスト・品質

- [ ] pytest ユニットテスト追加 (`tests/` ディレクトリ)
  - config.py, models.py, github_source.py, git_manager.py, daemon.py の各コンポーネント
  - 現在は手動テストスクリプトのみ
- [ ] Docker イメージのビルド確認・実機での E2E テスト
  - テスト用リポジトリで Issue → PR の一連のフローを通す
- [ ] CI/CD パイプライン (GitHub Actions)
  - lint (ruff), type check (mypy), test (pytest)

### 信頼性

- [ ] claim のレースコンディション対策
  - 現在: fetch → claim の間に他プロセスが claim する可能性あり
  - 対策案: GitHub API の条件付き更新 or ロック機構
- [ ] daemon 異常終了時の `claude-in-progress` ラベル残り問題
  - タイムアウトで自動解除する仕組み or 起動時に古いラベルをクリーンアップ
- [ ] poll cycle 中の例外でデーモン全体が死なないようにする
  - 現在: `_poll_cycle` 内で catch しているが、`fetch_pending_tasks` の異常は未対処
- [ ] API レート制限のハンドリング
  - GitHub API: 5000 req/hour (authenticated)
  - httpx のリトライ / バックオフ

### 機能

- [ ] デフォルトブランチの自動検出
  - 現在 `main` 固定 → `master` や他のブランチ名に非対応
  - GitHub API の `GET /repos/{owner}/{repo}` から `default_branch` を取得する
- [ ] 同一 Issue の再実行対策
  - ブランチ `claude/{issue_number}` が既に存在する場合のハンドリング
  - `git checkout -b` が失敗する

## 優先度: 中

### 機能拡張

- [ ] Backlog アダプタ (`sources/backlog_source.py`)
  - `TaskSource` Protocol を実装
  - Backlog API (課題取得 / ステータス更新 / コメント)
- [ ] 複数タスクの並行処理
  - 現在: 1 サイクル 1 タスクの順次処理
  - `asyncio.Semaphore` で同時実行数を制限しつつ並行化
- [ ] タスクの優先度制御
  - ラベル (`priority-high`, `priority-low`) や Issue のマイルストーンで順序を決める
- [ ] リトライ機構
  - Claude 実行が失敗した場合に N 回まで自動リトライ
  - `claude-retry` ラベルで手動リトライ指示
- [ ] プロンプトのカスタマイズ
  - リポジトリごとの CLAUDE.md / システムプロンプトを設定可能にする
  - Issue テンプレートとの連携

### 運用

- [ ] ヘルスチェック用の HTTP エンドポイント
  - Docker の `healthcheck` や監視ツール連携用
  - 最終ポーリング時刻 / 処理中タスク / エラー数
- [ ] メトリクス収集
  - タスク処理時間 / 成功率 / Claude のターン数・トークン使用量
- [ ] Slack / Discord 通知
  - タスク完了時や失敗時に通知
- [ ] workspace ボリュームの肥大化対策
  - 古いブランチのクリーンアップ
  - clone 済みリポジトリの定期的な gc

### セキュリティ

- [ ] Issue 本文のサニタイズ
  - プロンプトインジェクション対策（悪意ある Issue 本文への防御）
  - 許可された操作者のみが `claude-task` ラベルを付けられるようにする運用ルール
- [ ] トークンのローテーション対応
  - 環境変数の再読み込み or シークレット管理サービス連携
- [ ] Docker コンテナのセキュリティ強化
  - 非 root ユーザーでの実行
  - read-only ファイルシステム (workspace 以外)

## 優先度: 低

- [ ] Web UI ダッシュボード
  - タスク一覧 / ステータス / ログ表示
- [ ] GitHub App 化
  - Personal Access Token ではなく GitHub App として認証
  - Webhook でリアルタイム Issue 検知 (ポーリング不要)
- [ ] 複数デーモンインスタンスの協調動作
  - 分散ロック (Redis etc.) でタスクの取り合いを防止
