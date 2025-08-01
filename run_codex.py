from __future__ import annotations

import asyncio

from codex.orchestrator import Orchestrator


async def main() -> None:
    orc = Orchestrator()
    await orc.submit("TR01")
    await orc.submit("AV01")
    await orc.submit("SM01")
    await orc.submit("ST01")
    await orc.start([])


if __name__ == "__main__":
    asyncio.run(main())
