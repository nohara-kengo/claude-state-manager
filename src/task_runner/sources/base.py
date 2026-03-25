from __future__ import annotations

from typing import Protocol

from task_runner.models import Task, TaskResult


class TaskSource(Protocol):
    async def fetch_pending_tasks(self) -> list[Task]:
        """Fetch tasks that are ready to be worked on."""
        ...

    async def claim_task(self, task: Task) -> bool:
        """Mark a task as in-progress. Returns False if already claimed."""
        ...

    async def report_result(self, task: Task, result: TaskResult) -> None:
        """Report the result of a completed task (success or failure)."""
        ...
