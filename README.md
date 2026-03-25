# Claude Code Auto Task Runner

GitHub Issues からタスクを自動取得し、Claude Code (Agent SDK) で実行 → PR 作成まで行うバッチ型タスクランナー。

起動すると未処理タスクを全件取得 → 順次処理 → 全部終わったら自動終了。
業務後に起動して放置、翌朝 PR を確認する使い方を想定。

## 全体フロー

```mermaid
sequenceDiagram
    participant User as 人間
    participant CLI as task-runner
    participant GH as GitHub
    participant C as Claude Agent SDK
    participant Repo as Git Repository

    User->>CLI: 起動 (python -m task_runner)

    CLI->>GH: claude-task ラベル付き Issue を全件取得

    loop 取得した Issue を順次処理
        CLI->>GH: claude-in-progress ラベル付与 (claim)
        CLI->>Repo: clone / fetch + reset
        CLI->>Repo: .claude/settings.json 書き出し
        CLI->>Repo: claude/{issue番号} ブランチ作成
        CLI->>C: Issue 本文をプロンプトとして実行
        C->>Repo: ファイル読み書き + Bash 実行
        C-->>CLI: 実行結果
        CLI->>Repo: git add → commit → push
        CLI->>GH: PR 作成 (gh CLI)
        CLI->>GH: Issue にコメント + claude-done ラベル + close
    end

    CLI->>CLI: 全タスク完了 → 自動終了

    User->>GH: 翌朝 PR をレビュー
```

## アーキテクチャ

```mermaid
graph TB
    subgraph "python -m task_runner"
        Main["__main__.py<br/>引数解析 + バリデーション"]
        Main --> Runner["Runner.run_once()"]

        Runner --> Fetch["source.fetch_pending_tasks()<br/>全件取得"]
        Fetch --> Loop

        subgraph Loop ["タスクごとに順次実行"]
            Claim["source.claim_task()"]
            Claim --> Ensure["git.ensure_repo()"]
            Ensure --> Settings["git.write_claude_settings()"]
            Settings --> Branch["git.create_branch()"]
            Branch --> Exec["executor.execute()<br/>Claude Agent SDK"]
            Exec --> Changes{"変更あり?"}
            Changes -->|Yes| Push["git.commit_and_push()"]
            Push --> PRCreate["git.create_pr()"]
            PRCreate --> Report["source.report_result()"]
            Changes -->|No| Report
        end

        Loop --> Done["全タスク完了 → exit"]
    end

    Signal["SIGTERM / SIGINT"] -.->|残りスキップして終了| Runner

    subgraph External
        GitHub["GitHub API"]
        Anthropic["Anthropic API"]
    end

    Fetch -->|httpx| GitHub
    Exec -->|claude_agent_sdk| Anthropic
    Push -->|git + gh| GitHub
```

### 権限制御の仕組み

```mermaid
graph TD
    subgraph "Claude Agent SDK 起動時の権限"
        PM["permission_mode: acceptEdits<br/>→ ファイル操作を自動承認"]
        AT["allowed_tools:<br/>Read, Write, Edit, Bash, Glob, Grep"]
        SS["setting_sources: [project]<br/>→ .claude/settings.json を読み込み"]
    end

    subgraph ".claude/settings.json (リポジトリに書き出し)"
        Allow["allowedTools:<br/>Bash(git status *)<br/>Bash(git commit *)<br/>Bash(git push *)<br/>Bash(npm *)<br/>..."]
        Block["ブロック (記載なし):<br/>git merge<br/>git rebase<br/>git pull"]
    end

    PM --> Claude["Claude Code 実行"]
    AT --> Claude
    SS --> Allow
    Allow -->|自動承認| Claude
    Block -->|拒否| Claude
```

## クイックスタート

```bash
# 1. クローン
git clone https://github.com/your-org/claude-state-manager.git
cd claude-state-manager

# 2. 環境変数
cp .env.example .env
# .env を編集: GITHUB_TOKEN, ANTHROPIC_API_KEY を記入

# 3. 設定
cp config.example.yml config.yml
# config.yml を編集: github.repos にリポジトリを記入

# 4. 対象リポジトリにラベル作成
gh label create claude-task --repo your-org/your-repo --color 0E8A16
gh label create claude-in-progress --repo your-org/your-repo --color FBCA04
gh label create claude-done --repo your-org/your-repo --color 5319E7

# 5. 実行 (タスク完了後に自動終了)
docker compose run --rm task-runner
```

## 使い方

```bash
# 業務後にタスクを積んでおいて…
# Issue に claude-task ラベルを付ける

# 帰る前に実行
docker compose run --rm task-runner

# 翌朝: PR を確認してマージ
```

1. 監視対象リポジトリに Issue を作成
2. `claude-task` ラベルを付与
3. Issue 本文にタスク内容を記述（これが Claude へのプロンプトになる）
4. `docker compose run --rm task-runner` で実行
5. 全タスク処理後に自動終了 → 翌朝 PR をレビュー

## セットアップ詳細

### GitHub Token

GitHub Personal Access Token (classic) を作成:

| スコープ | 用途 |
|---------|------|
| `repo` | clone / push / PR 作成 / Issue 操作 |

作成: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)

> Fine-grained token の場合: 対象リポジトリに Contents (read/write), Issues (read/write), Pull requests (read/write) を付与。

### 認証フロー

```mermaid
graph LR
    Token["GITHUB_TOKEN<br/>(1つで全て賄う)"]
    Token -->|"Authorization: token ..."| API["GitHub API (httpx)<br/>Issue / ラベル / コメント"]
    Token -->|"x-access-token in URL"| GitOps["git clone / push"]
    Token -->|"GH_TOKEN 環境変数<br/>(docker-compose が自動セット)"| GhCLI["gh pr create"]
```

### 環境変数

| 変数 | 必須 | 説明 |
|------|------|------|
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token (repo スコープ) |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API Key |
| `GIT_USER_NAME` | No | コミットの author name (default: `claude-task-runner`) |
| `GIT_USER_EMAIL` | No | コミットの author email (default: `claude-task-runner@noreply.github.com`) |

## 実行方法

### Docker (推奨)

```bash
# バッチ実行 (タスク全部やって終了)
docker compose run --rm task-runner

# ログを見ながら実行
docker compose run --rm task-runner -c /app/config.yml --log-level DEBUG
```

### ローカル (Docker なし)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

export GITHUB_TOKEN=ghp_xxx
export GH_TOKEN=$GITHUB_TOKEN
export ANTHROPIC_API_KEY=sk-ant-xxx
python -m task_runner -c config.yml
```

### Watch モード (従来のデーモン動作)

継続的にポーリングしたい場合は `--watch` フラグ:

```bash
# Docker
docker compose run --rm task-runner --watch

# ローカル
python -m task_runner -c config.yml --watch
```

## 設定リファレンス

### config.yml

| キー | デフォルト | 説明 |
|------|-----------|------|
| `workspace_dir` | `/workspace` | リポジトリの clone 先 |
| `max_turns` | `50` | Claude の最大ターン数 / タスク |
| `task_timeout` | `1800` | タスクのタイムアウト（秒、デフォルト 30 分） |
| `permission_mode` | `acceptEdits` | Claude の権限モード |
| `allowed_bash_commands` | (下記参照) | Bash 自動承認パターン |
| `github.repos` | `[]` | 監視対象リポジトリ (`owner/repo` 形式) |
| `github.task_label` | `claude-task` | タスク Issue のラベル |
| `github.in_progress_label` | `claude-in-progress` | 実行中ラベル |
| `github.done_label` | `claude-done` | 完了ラベル |

### Bash 自動承認パターン

`allowed_bash_commands` で Claude が Bash で実行できるコマンドを制御。
デフォルトでは `git merge` / `git rebase` / `git pull` は **ブロック**（マージは PR 経由の想定）。

```yaml
allowed_bash_commands:
  # git (merge/rebase/pull を除外)
  - "git status *"
  - "git diff *"
  - "git log *"
  - "git show *"
  - "git branch *"
  - "git checkout *"
  - "git add *"
  - "git commit *"
  - "git push *"
  - "git fetch *"
  - "git stash *"
  - "git rm *"
  - "git mv *"
  - "git tag *"
  # build / test
  - "npm *"
  - "python *"
  - "pytest *"
  - "make *"
  # read-only shell
  - "ls *"
  - "cat *"
  - "find *"
  - "grep *"
```

全コマンド許可する場合は `["*"]` に変更。

内部的にはリポジトリの `.claude/settings.json` に `allowedTools: ["Bash(<pattern>)"]` として書き出され、
`setting_sources: ["project"]` で Claude Agent SDK に読み込まれる。

## ファイル構成

```
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── config.example.yml
├── .env.example
├── TODO.md                  # 残件・改善タスク
└── src/task_runner/
    ├── __main__.py          # CLI エントリポイント
    ├── daemon.py            # Runner (バッチ実行 / watch モード)
    ├── config.py            # YAML + 環境変数から設定読み込み
    ├── models.py            # Task, TaskResult データクラス
    ├── sources/
    │   ├── base.py          # TaskSource Protocol (抽象インターフェース)
    │   └── github_source.py # GitHub Issues アダプタ
    ├── executor.py          # Claude Agent SDK 呼び出し
    ├── git_manager.py       # git clone/branch/commit/push/PR + 認証
    └── logging_config.py    # JSON 構造化ログ
```

## タスクソースの拡張

`TaskSource` Protocol を実装するだけで Backlog 等の新しいソースを追加可能:

```python
class TaskSource(Protocol):
    async def fetch_pending_tasks(self) -> list[Task]: ...
    async def claim_task(self, task: Task) -> bool: ...
    async def report_result(self, task: Task, result: TaskResult) -> None: ...
```

## 既知の制限事項

- デフォルトブランチが `main` 固定（`master` 等には未対応）
- Issue 本文のプロンプトインジェクション対策なし
- 同一 Issue のブランチが既存の場合にエラーになる可能性

詳細は [TODO.md](./TODO.md) を参照。
