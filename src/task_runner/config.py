from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class GitHubConfig:
    repos: list[str] = field(default_factory=list)
    task_label: str = "claude-task"
    in_progress_label: str = "claude-in-progress"
    done_label: str = "claude-done"
    token: str = ""


@dataclass
class Config:
    poll_interval: int = 60
    workspace_dir: str = "/workspace"
    max_turns: int = 50
    task_timeout: int = 1800  # 30 minutes
    permission_mode: str = "acceptEdits"
    allowed_bash_commands: list[str] = field(default_factory=lambda: [
        "git status *",
        "git diff *",
        "git log *",
        "git show *",
        "git branch *",
        "git checkout *",
        "git add *",
        "git commit *",
        "git push *",
        "git fetch *",
        "git stash *",
        "git rm *",
        "git mv *",
        "git tag *",
        "npm *",
        "python *",
        "pytest *",
        "make *",
        "ls *",
        "cat *",
        "find *",
        "grep *",
    ])
    github: GitHubConfig = field(default_factory=GitHubConfig)
    anthropic_api_key: str = ""


def load_config(config_path: str | None = None) -> Config:
    data: dict = {}
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

    gh_data = data.get("github", {})
    gh = GitHubConfig(
        repos=gh_data.get("repos", []),
        task_label=gh_data.get("task_label", "claude-task"),
        in_progress_label=gh_data.get("in_progress_label", "claude-in-progress"),
        done_label=gh_data.get("done_label", "claude-done"),
        token=os.environ.get("GITHUB_TOKEN", gh_data.get("token", "")),
    )

    return Config(
        poll_interval=data.get("poll_interval", 60),
        workspace_dir=data.get("workspace_dir", "/workspace"),
        max_turns=data.get("max_turns", 50),
        task_timeout=data.get("task_timeout", 1800),
        permission_mode=data.get("permission_mode", "acceptEdits"),
        allowed_bash_commands=data.get("allowed_bash_commands", Config().allowed_bash_commands),
        github=gh,
        anthropic_api_key=os.environ.get(
            "ANTHROPIC_API_KEY", data.get("anthropic_api_key", "")
        ),
    )
