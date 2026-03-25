from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    source: str
    repo: str
    title: str
    body: str
    issue_number: int
    labels: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class TaskResult:
    task: Task
    success: bool
    branch_name: str = ""
    pr_url: str = ""
    error: str = ""
    summary: str = ""
