from __future__ import annotations

import logging
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from task_runner.config import Config
from task_runner.models import Task, TaskResult

logger = logging.getLogger("task_runner.executor")


class TaskExecutor:
    def __init__(self, config: Config) -> None:
        self._config = config

    async def execute(self, task: Task, repo_dir: Path, branch: str) -> TaskResult:
        prompt = (
            f"You are working on the following task from GitHub Issue #{task.issue_number}.\n"
            f"Title: {task.title}\n\n"
            f"Description:\n{task.body}\n\n"
            f"Work in the repository at {repo_dir} on branch {branch}.\n"
            f"Make the necessary code changes to complete this task. "
            f"Do not create a git commit - changes will be committed automatically."
        )

        logger.info("Executing task %s with Claude Code", task.id)
        try:
            result_text = ""
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    max_turns=self._config.max_turns,
                    permission_mode=self._config.permission_mode,
                    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                    setting_sources=["project"],
                    cwd=str(repo_dir),
                ),
            ):
                if isinstance(message, ResultMessage):
                    result_text = message.result

            summary = result_text[:2000] if result_text else "Task completed."
            logger.info("Task %s completed successfully", task.id)
            return TaskResult(
                task=task,
                success=True,
                branch_name=branch,
                summary=summary,
            )
        except Exception as e:
            logger.error("Task %s failed: %s", task.id, e)
            return TaskResult(
                task=task,
                success=False,
                branch_name=branch,
                error=str(e),
            )
