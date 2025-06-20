from __future__ import annotations

"""Central orchestrator for all sprint agents."""

import asyncio
from typing import Any, Dict

from .agents import AGENTS
from .task_queue import Task, TaskQueue
from .validation import VALIDATORS


class Orchestrator:
    def __init__(self) -> None:
        self.queue = TaskQueue()
        self.active: Dict[int, Task] = {}

    async def submit(self, sprint: str, payload: dict[str, Any] | None = None) -> None:
        await self.queue.add(Task(sprint=sprint, payload=payload))

    async def worker(self) -> None:
        while True:
            task = await self.queue.get()
            self.active[id(task)] = task
            agent = AGENTS.get(task.sprint)
            if not agent:
                task.log.append(f"unknown sprint {task.sprint}")
                task.status = "error"
            else:
                try:
                    task.status = "running"
                    result = agent.run()
                    task.result = result
                    task.status = "done"
                except Exception as exc:  # noqa: BLE001
                    task.log.append(str(exc))
                    task.status = "error"
            self.active.pop(id(task), None)
            await self.queue.mark_done(task)

    async def start(self, initial: list[str]) -> None:
        for sprint in initial:
            await self.submit(sprint)
        worker_task = asyncio.create_task(self.worker())
        await self.queue._queue.join()
        worker_task.cancel()
