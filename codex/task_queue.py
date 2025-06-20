from __future__ import annotations

"""Simple in-memory task queue."""

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    sprint: str
    payload: dict[str, Any] | None = None
    status: str = "pending"
    result: Any | None = None
    log: list[str] = field(default_factory=list)


class TaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self.completed: list[Task] = []

    async def add(self, task: Task) -> None:
        await self._queue.put(task)

    async def get(self) -> Task:
        task = await self._queue.get()
        return task

    async def mark_done(self, task: Task) -> None:
        self.completed.append(task)
        self._queue.task_done()
