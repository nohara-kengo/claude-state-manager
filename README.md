# Claude State Manager

Claude Code のスラッシュコマンド + MCP で、GitHub Issue → コード修正 → PR 作成 → Backlog 連携を自動化するプラグイン。

業務後に `/run-tasks` を実行して放置、翌朝 PR を確認する運用を想定。

## 全体フロー

```mermaid
sequenceDiagram
    participant User as 人間
    participant Claude as Claude Code
    participant GHMCP as GitHub MCP
    participant BLMCP as Backlog MCP
    participant Repo as Git Repository

    User->>Claude: /run-tasks owner/repo

    Claude->>GHMCP: claude-task ラベル付き Issue を取得

    loop 各 Issue を順次処理
        Claude->>Claude: Issue 内容を分析
        Claude->>Repo: git checkout -b fix/issue-{番号}
        Claude->>Repo: コード修正
        Claude->>Repo: git commit & push
        Claude->>GHMCP: PR 作成 (Closes #{番号})
        Claude->>BLMCP: 対応する Backlog 課題のステータス更新
    end

    Claude->>User: 処理結果サマリーを表示
    User->>GHMCP: 翌朝 PR をレビュー
```

## アーキテクチャ

```mermaid
graph TB
    subgraph "Claude Code"
        CMD["/run-tasks コマンド<br/>.claude/commands/run-tasks.md"]
        CMD --> Claude["Claude Code エージェント"]
    end

    subgraph "MCP Servers"
        GHMCP["GitHub MCP Server<br/>@modelcontextprotocol/server-github"]
        BLMCP["Backlog MCP Server<br/>（自作 or 既存）"]
    end

    subgraph "外部サービス"
        GH["GitHub<br/>Issue / PR / Labels"]
        BL["Backlog<br/>課題 / ステータス"]
    end

    Claude -->|Issue取得・PR作成| GHMCP
    Claude -->|課題ステータス更新| BLMCP
    Claude -->|git操作| Git["Git Repository"]
    GHMCP --> GH
    BLMCP --> BL
```

## 権限制御

```mermaid
graph TD
    subgraph "settings.json（共有・git管理）"
        Perm["permissions.allow:<br/>Bash(git *)<br/>mcp__github<br/>mcp__backlog"]
    end

    subgraph "settings.local.json（個人・git管理外）"
        GHToken["GitHub MCP<br/>GITHUB_PERSONAL_ACCESS_TOKEN"]
        BLToken["Backlog MCP<br/>BACKLOG_SPACE_URL / API_KEY"]
    end

    Perm --> Claude["Claude Code 実行"]
    GHToken --> GHMCP["GitHub MCP Server"]
    BLToken --> BLMCP["Backlog MCP Server"]
    GHMCP --> Claude
    BLMCP --> Claude
```

## ファイル構成

```
claude-state-manager/
├── README.md
├── .gitignore
└── .claude/
    ├── settings.json          # 共有設定（permissions）
    ├── settings.local.json    # 個人設定（MCP・トークン）※git管理外
    └── commands/
        └── run-tasks.md       # /run-tasks スラッシュコマンド
```

## セットアップ

### 1. クローン

```bash
git clone https://github.com/nohara-kengo/claude-state-manager.git
cd claude-state-manager
```

### 2. 個人設定

`settings.local.json` にトークンを記入:

```bash
vi .claude/settings.local.json
```

| 環境変数 | 説明 |
|---------|------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub Personal Access Token（repo スコープ） |
| `BACKLOG_SPACE_URL` | Backlog スペース URL（例: `https://xxx.backlog.com`） |
| `BACKLOG_API_KEY` | Backlog API キー |

### 3. ラベル作成

対象リポジトリに `claude-task` ラベルを作成:

```bash
gh label create claude-task --repo owner/repo --color 0E8A16
```

### 4. タスクを積む

対象リポジトリで Issue を作成し、`claude-task` ラベルを付与。
Issue 本文がそのまま Claude へのプロンプトになる。

### 5. 実行

```bash
cd 対象リポジトリ
/run-tasks owner/repo
```

## 使い方

```bash
# 1. Issue に claude-task ラベルを付けてタスクを積む
# 2. 帰る前に実行
/run-tasks owner/repo
# 3. 翌朝 PR を確認してマージ
```
