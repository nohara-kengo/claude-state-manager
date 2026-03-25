from __future__ import annotations

import asyncio
import logging
import signal

from task_runner.config import Config
from task_runner.executor import TaskExecutor
from task_runner.git_manager import GitManager
from task_runner.models import TaskResult
from task_runner.sources.github_source import GitHubSource

logger = logging.getLogger("task_runner.daemon")


class Runner:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._running = True
        self._source = GitHubSource(config.github)
        self._executor = TaskExecutor(config)
        self._git = GitManager(config.workspace_dir, config.github.token)

    async def run_once(self) -> int:
        """Fetch all pending tasks, process them sequentially, then exit.

        Returns the number of tasks processed.
        """
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown)

        try:
            logger.info("Fetching tasks from repos=%s", self._config.github.repos)
            tasks = await self._source.fetch_pending_tasks()

            if not tasks:
                logger.info("No pending tasks found. Done.")
                return 0

            logger.info("Found %d pending task(s)", len(tasks))
            processed = 0

            for task in tasks:
                if not self._running:
                    logger.info("Shutdown requested, stopping after %d task(s)", processed)
                    break

                logger.info(
                    "[%d/%d] Processing: %s (%s)",
                    processed + 1, len(tasks), task.id, task.title,
                )

                if not await self._source.claim_task(task):
                    logger.info("Could not claim task %s, skipping", task.id)
                    continue

                await self._process_task(task)
                processed += 1

            logger.info("Finished. Processed %d task(s).", processed)
            return processed
        finally:
            await self._source.close()

    async def run_watch(self) -> None:
        """Poll continuously until stopped (daemon mode)."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._shutdown)

        logger.info(
            "Watch mode started (poll_interval=%ds, repos=%s)",
            self._config.poll_interval,
            self._config.github.repos,
        )

        try:
            while self._running:
                tasks = await self._source.fetch_pending_tasks()
                if tasks:
                    task = tasks[0]
                    logger.info("Processing task: %s (%s)", task.id, task.title)
                    if await self._source.claim_task(task):
                        await self._process_task(task)
                else:
                    logger.info("No pending tasks found")

                if self._running:
                    await self._sleep(self._config.poll_interval)
        finally:
            await self._source.close()
            logger.info("Watch mode stopped")

    async def _process_task(self, task) -> None:
        try:
            repo_dir = await self._git.ensure_repo(task.repo)
            self._git.write_claude_settings(task.repo, self._config.allowed_bash_commands)
            branch = await self._git.create_branch(task.repo, task)

            result = await asyncio.wait_for(
                self._executor.execute(task, repo_dir, branch),
                timeout=self._config.task_timeout,
            )

            if result.success and await self._git.has_changes(task.repo):
                pushed = await self._git.commit_and_push(task.repo, task, branch)
                if pushed:
                    pr_url = await self._git.create_pr(task.repo, task, branch)
                    result.pr_url = pr_url
            elif result.success:
                result.summary = "Task completed but no code changes were made."

            await self._source.report_result(task, result)

        except asyncio.TimeoutError:
            logger.error("Task %s timed out after %ds", task.id, self._config.task_timeout)
            result = TaskResult(
                task=task,
                success=False,
                error=f"Task timed out after {self._config.task_timeout}s",
            )
            await self._source.report_result(task, result)
        except Exception as e:
            logger.error("Unexpected error processing task %s: %s", task.id, e, exc_info=True)
            result = TaskResult(task=task, success=False, error=str(e))
            await self._source.report_result(task, result)

    async def _sleep(self, seconds: int) -> None:
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            self._running = False

    def _shutdown(self) -> None:
        logger.info("Shutdown signal received")
        self._running = False
