from __future__ import annotations

import logging

import httpx

from task_runner.config import GitHubConfig
from task_runner.models import Task, TaskResult, TaskStatus

logger = logging.getLogger("task_runner.github_source")

API_BASE = "https://api.github.com"


class GitHubSource:
    def __init__(self, config: GitHubConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={
                "Authorization": f"token {config.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def fetch_pending_tasks(self) -> list[Task]:
        tasks: list[Task] = []
        for repo in self._config.repos:
            try:
                resp = await self._client.get(
                    f"/repos/{repo}/issues",
                    params={
                        "labels": self._config.task_label,
                        "state": "open",
                        "per_page": 10,
                        "sort": "created",
                        "direction": "asc",
                    },
                )
                resp.raise_for_status()
                for issue in resp.json():
                    labels = [lb["name"] for lb in issue.get("labels", [])]
                    if self._config.in_progress_label in labels:
                        continue
                    if issue.get("pull_request"):
                        continue
                    tasks.append(
                        Task(
                            id=f"github-{repo}-{issue['number']}",
                            source="github",
                            repo=repo,
                            title=issue["title"],
                            body=issue.get("body", "") or "",
                            issue_number=issue["number"],
                            labels=labels,
                        )
                    )
            except httpx.HTTPError as e:
                logger.error("Failed to fetch issues from %s: %s", repo, e)
        return tasks

    async def claim_task(self, task: Task) -> bool:
        try:
            resp = await self._client.get(
                f"/repos/{task.repo}/issues/{task.issue_number}",
            )
            resp.raise_for_status()
            labels = [lb["name"] for lb in resp.json().get("labels", [])]
            if self._config.in_progress_label in labels:
                logger.info("Task %s already claimed", task.id)
                return False

            resp = await self._client.post(
                f"/repos/{task.repo}/issues/{task.issue_number}/labels",
                json={"labels": [self._config.in_progress_label]},
            )
            resp.raise_for_status()
            task.status = TaskStatus.IN_PROGRESS
            logger.info("Claimed task %s", task.id)
            return True
        except httpx.HTTPError as e:
            logger.error("Failed to claim task %s: %s", task.id, e)
            return False

    async def report_result(self, task: Task, result: TaskResult) -> None:
        repo = task.repo
        issue = task.issue_number
        try:
            if result.success:
                body = f"## Claude Code completed this task\n\n{result.summary}"
                if result.pr_url:
                    body += f"\n\nPR: {result.pr_url}"
            else:
                body = (
                    f"## Claude Code failed on this task\n\n"
                    f"Error: {result.error}"
                )

            await self._client.post(
                f"/repos/{repo}/issues/{issue}/comments",
                json={"body": body},
            )

            new_labels = [self._config.done_label]
            remove_labels = [
                self._config.task_label,
                self._config.in_progress_label,
            ]
            for label in remove_labels:
                await self._client.delete(
                    f"/repos/{repo}/issues/{issue}/labels/{label}",
                )

            await self._client.post(
                f"/repos/{repo}/issues/{issue}/labels",
                json={"labels": new_labels},
            )

            if result.success:
                await self._client.patch(
                    f"/repos/{repo}/issues/{issue}",
                    json={"state": "closed"},
                )

            logger.info("Reported result for task %s (success=%s)", task.id, result.success)
        except httpx.HTTPError as e:
            logger.error("Failed to report result for task %s: %s", task.id, e)

    async def close(self) -> None:
        await self._client.aclose()
