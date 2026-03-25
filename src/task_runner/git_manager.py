from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from task_runner.models import Task

logger = logging.getLogger("task_runner.git_manager")


class GitManager:
    def __init__(self, workspace_dir: str, github_token: str) -> None:
        self._workspace = Path(workspace_dir)
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._token = github_token

    def _repo_dir(self, repo: str) -> Path:
        return self._workspace / repo.replace("/", "_")

    async def _run(self, *args: str, cwd: Path | None = None) -> str:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"Command {args} failed (rc={proc.returncode}): {stderr.decode()}"
            )
        return stdout.decode().strip()

    async def _ensure_git_config(self, repo_dir: Path) -> None:
        """Set git user config if not already set (needed for commits)."""
        try:
            await self._run("git", "config", "user.name", cwd=repo_dir)
        except RuntimeError:
            await self._run(
                "git", "config", "user.name", "claude-task-runner", cwd=repo_dir
            )
        try:
            await self._run("git", "config", "user.email", cwd=repo_dir)
        except RuntimeError:
            await self._run(
                "git", "config", "user.email",
                "claude-task-runner@noreply.github.com", cwd=repo_dir,
            )

    async def ensure_repo(self, repo: str) -> Path:
        repo_dir = self._repo_dir(repo)
        if (repo_dir / ".git").exists():
            logger.info("Updating existing repo %s", repo)
            await self._run("git", "fetch", "origin", cwd=repo_dir)
            await self._run(
                "git", "checkout", "main", cwd=repo_dir
            )
            await self._run(
                "git", "reset", "--hard", "origin/main", cwd=repo_dir
            )
            await self._run("git", "clean", "-fdx", cwd=repo_dir)
        else:
            logger.info("Cloning repo %s", repo)
            clone_url = f"https://x-access-token:{self._token}@github.com/{repo}.git"
            await self._run("git", "clone", clone_url, str(repo_dir))
        await self._ensure_git_config(repo_dir)
        return repo_dir

    def write_claude_settings(self, repo: str, allowed_bash_commands: list[str]) -> None:
        """Write .claude/settings.json to auto-approve Bash commands."""
        repo_dir = self._repo_dir(repo)
        claude_dir = repo_dir / ".claude"
        claude_dir.mkdir(exist_ok=True)

        allowed_tools = [f"Bash({pattern})" for pattern in allowed_bash_commands]
        settings = {"allowedTools": allowed_tools}

        settings_path = claude_dir / "settings.json"
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        logger.info("Wrote %s with allowedTools=%s", settings_path, allowed_tools)

    async def create_branch(self, repo: str, task: Task) -> str:
        repo_dir = self._repo_dir(repo)
        branch = f"claude/{task.issue_number}"
        await self._run("git", "checkout", "-b", branch, cwd=repo_dir)
        logger.info("Created branch %s in %s", branch, repo)
        return branch

    async def has_changes(self, repo: str) -> bool:
        repo_dir = self._repo_dir(repo)
        status = await self._run("git", "status", "--porcelain", cwd=repo_dir)
        return bool(status.strip())

    async def commit_and_push(self, repo: str, task: Task, branch: str) -> bool:
        repo_dir = self._repo_dir(repo)
        if not await self.has_changes(repo):
            logger.info("No changes to commit for task %s", task.id)
            return False

        await self._run("git", "add", "-A", cwd=repo_dir)
        await self._run(
            "git", "commit", "-m", f"feat: {task.title}\n\nResolves #{task.issue_number}",
            cwd=repo_dir,
        )
        await self._run("git", "push", "-u", "origin", branch, cwd=repo_dir)
        logger.info("Pushed branch %s for task %s", branch, task.id)
        return True

    async def create_pr(self, repo: str, task: Task, branch: str) -> str:
        repo_dir = self._repo_dir(repo)
        title = f"feat: {task.title}"
        body = (
            f"Resolves #{task.issue_number}\n\n"
            f"Automated by Claude Code Task Runner."
        )
        output = await self._run(
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", "main",
            "--head", branch,
            cwd=repo_dir,
        )
        pr_url = output.strip().splitlines()[-1]
        logger.info("Created PR %s for task %s", pr_url, task.id)
        return pr_url
