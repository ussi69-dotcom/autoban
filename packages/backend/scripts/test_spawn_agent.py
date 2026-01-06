import asyncio
import sys
import time
import uuid

from app.database import AsyncSessionLocal, close_db, init_db
from app.models.agent import AgentInstance
from app.services.agent_pool import AgentPoolManager

DUMMY_AGENT_CODE = r'''
import json
import os
import signal
import time

running = True

def _stop(*_args):
    global running
    running = False

signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

agent_id = os.environ.get("AGENT_ID", "unknown")
print(json.dumps({"type": "heartbeat", "payload": {"agentId": agent_id}}), flush=True)

while running:
    payload = {
        "type": "heartbeat",
        "payload": {
            "agentId": agent_id,
            "cpu_percent": 0.1,
            "memory_mb": 10.0,
            "timestamp": time.time(),
        },
    }
    print(json.dumps(payload), flush=True)
    time.sleep(1)
'''


async def main() -> None:
    db_ready = True
    try:
        await init_db()
    except Exception as exc:
        db_ready = False
        print(f"Database init failed, continuing without DB checks: {exc}")

    manager = AgentPoolManager(
        min_agents=0,
        max_agents=1,
        heartbeat_interval=1.0,
        heartbeat_timeout=3.0,
        agent_command=[sys.executable, "-u", "-c", DUMMY_AGENT_CODE],
        db_session_factory=AsyncSessionLocal if db_ready else None,
    )

    agent_id = await manager.spawn_agent()
    if not agent_id:
        raise SystemExit("Failed to spawn agent")

    await asyncio.sleep(2.0)
    status = await manager.get_agent_status(agent_id)
    print(f"Agent status after spawn: {status}")

    session_id = str(uuid.uuid4())
    await manager.assign_agent(agent_id, session_id)
    await asyncio.sleep(0.5)
    await manager.release_agent(agent_id)

    agent_info = await manager.get_agent_info(agent_id)
    if agent_info:
        age = time.time() - agent_info.last_heartbeat
        print(f"Heartbeat age: {age:.2f}s")

    await manager.stop_agent(agent_id)

    if db_ready:
        async with AsyncSessionLocal() as session:
            instance = await session.get(AgentInstance, uuid.UUID(agent_id))
            if instance:
                print(f"DB status: {instance.status}, pid: {instance.pid}")

        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
