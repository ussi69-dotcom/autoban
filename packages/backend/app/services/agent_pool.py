"""
Agent Pool Manager for AutoBan.

Manages a pool of agent processes, handling spawning, stopping, health checks,
and automatic restart on failure.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

from app.database import AsyncSessionLocal
from app.models.agent import AgentInstance, AgentStatus as DbAgentStatus

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status states for an agent process."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class ResourceMetrics:
    """Resource usage metrics for an agent (placeholder implementation)."""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def update(self, cpu: float = 0.0, memory: float = 0.0) -> None:
        """Update resource metrics."""
        self.cpu_percent = cpu
        self.memory_mb = memory
        self.last_updated = time.time()


@dataclass
class AgentInfo:
    """Information about a managed agent process."""
    agent_id: str
    process: Optional[subprocess.Popen] = None
    status: AgentStatus = AgentStatus.INITIALIZING
    last_heartbeat: float = field(default_factory=time.time)
    started_at: float = field(default_factory=time.time)
    restart_count: int = 0
    current_session_id: Optional[str] = None
    resources: ResourceMetrics = field(default_factory=ResourceMetrics)
    error_message: Optional[str] = None

    def update_heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = time.time()

    def is_healthy(self, timeout_seconds: float = 30.0) -> bool:
        """Check if the agent is healthy based on heartbeat."""
        if self.status in (AgentStatus.STOPPED, AgentStatus.STOPPING, AgentStatus.ERROR):
            return False
        return (time.time() - self.last_heartbeat) < timeout_seconds


class AgentPoolManager:
    """
    Manages a pool of agent processes for handling user sessions.

    Features:
    - Spawn and stop agent processes
    - Track agent status and health
    - Auto-restart failed agents
    - Resource monitoring (placeholder)
    """

    def __init__(
        self,
        min_agents: int = 2,
        max_agents: int = 10,
        heartbeat_interval: float = 5.0,
        heartbeat_timeout: float = 30.0,
        max_restart_attempts: int = 3,
        agent_command: Optional[List[str]] = None,
        default_agent_type: str = "implement",
        default_agent_model: str = "claude-3-5-sonnet-20241022",
        backend_url: Optional[str] = None,
        db_session_factory=AsyncSessionLocal,
    ):
        """
        Initialize the agent pool manager.

        Args:
            min_agents: Minimum number of agents to maintain in the pool
            max_agents: Maximum number of agents allowed
            heartbeat_interval: Seconds between health checks
            heartbeat_timeout: Seconds before considering an agent unhealthy
            max_restart_attempts: Max restarts before giving up on an agent
            agent_command: Command to spawn an agent process
            default_agent_type: Default agent type for spawned agents
            default_agent_model: Default model name for spawned agents
            backend_url: WebSocket URL for agent IPC
            db_session_factory: Session factory for persisting agent records
        """
        self.min_agents = min_agents
        self.max_agents = max_agents
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_restart_attempts = max_restart_attempts
        self.agent_command = agent_command or ["python", "-m", "autoban.agent"]
        self.default_agent_type = default_agent_type
        self.default_agent_model = default_agent_model
        self.backend_url = backend_url
        self._db_session_factory = db_session_factory

        self._agents: Dict[str, AgentInfo] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        self._on_agent_status_change: Optional[Callable[[str, AgentStatus], None]] = None
        self._stdout_tasks: Dict[str, asyncio.Task] = {}
        self._stderr_tasks: Dict[str, asyncio.Task] = {}

    @property
    def agents(self) -> Dict[str, AgentInfo]:
        """Get all managed agents."""
        return self._agents.copy()

    @property
    def idle_agents(self) -> List[AgentInfo]:
        """Get list of idle agents available for work."""
        return [a for a in self._agents.values() if a.status == AgentStatus.IDLE]

    @property
    def busy_agents(self) -> List[AgentInfo]:
        """Get list of busy agents."""
        return [a for a in self._agents.values() if a.status == AgentStatus.BUSY]

    def set_status_callback(
        self, callback: Callable[[str, AgentStatus], None]
    ) -> None:
        """Set a callback for agent status changes."""
        self._on_agent_status_change = callback

    async def start(self) -> None:
        """Start the agent pool manager and spawn initial agents."""
        if self._running:
            logger.warning("Agent pool manager already running")
            return

        self._running = True
        logger.info(f"Starting agent pool manager (min={self.min_agents}, max={self.max_agents})")

        # Spawn minimum number of agents
        for _ in range(self.min_agents):
            await self.spawn_agent()

        # Start health check loop
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Agent pool manager started")

    async def stop(self) -> None:
        """Stop the agent pool manager and all agents."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping agent pool manager")

        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Stop all agents
        agent_ids = list(self._agents.keys())
        await asyncio.gather(*[self.stop_agent(aid) for aid in agent_ids])
        logger.info("Agent pool manager stopped")

    async def spawn_agent(
        self,
        agent_type: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """
        Spawn a new agent process.

        Returns:
            The agent ID if successful, None otherwise.
        """
        async with self._lock:
            if len(self._agents) >= self.max_agents:
                logger.warning("Cannot spawn agent: max agents reached")
                return None

            agent_id = str(uuid.uuid4())
            agent_info = AgentInfo(agent_id=agent_id)
            self._agents[agent_id] = agent_info

        logger.info(f"Spawning agent {agent_id}")
        agent_type = agent_type or self.default_agent_type
        model = model or self.default_agent_model

        try:
            await self._ensure_agent_instance(agent_id, agent_type, model)
            process = await self._spawn_process(agent_id, agent_type)
            if process is None:
                raise RuntimeError("Agent process failed to start")
            await asyncio.sleep(0.1)
            if process.poll() is not None:
                raise RuntimeError(
                    f"Agent process exited early with code {process.returncode}"
                )

            async with self._lock:
                agent_info.process = process
                agent_info.status = AgentStatus.IDLE
                agent_info.update_heartbeat()

            await self._update_agent_instance(
                agent_id,
                status=AgentStatus.IDLE,
                pid=process.pid,
                last_heartbeat=self._now(),
            )
            self._notify_status_change(agent_id, AgentStatus.IDLE)
            logger.info(f"Agent {agent_id} spawned and ready")
            return agent_id

        except Exception as e:
            logger.error(f"Failed to spawn agent {agent_id}: {e}")
            async with self._lock:
                agent_info.status = AgentStatus.ERROR
                agent_info.error_message = str(e)
            await self._update_agent_instance(
                agent_id,
                status=AgentStatus.ERROR,
                error_message=str(e),
            )
            self._notify_status_change(agent_id, AgentStatus.ERROR)
            return None

    async def _spawn_process(
        self,
        agent_id: str,
        agent_type: str,
    ) -> Optional[subprocess.Popen]:
        """
        Spawn the actual agent process.

        In production, this would:
        1. Spawn a subprocess running the agent code
        2. Set up IPC channels (pipes, sockets, etc.)
        3. Wait for the agent to signal ready

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            The subprocess.Popen object or None
        """
        env = os.environ.copy()
        env["AGENT_ID"] = agent_id
        env.setdefault("AGENT_TYPE", agent_type)
        if self.backend_url:
            env["BACKEND_URL"] = self.backend_url
        env.setdefault("BACKEND_URL", env.get("BACKEND_URL", "ws://localhost:8000"))

        process = subprocess.Popen(
            self.agent_command,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )

        self._stdout_tasks[agent_id] = asyncio.create_task(
            self._monitor_agent_stdout(agent_id, process)
        )
        self._stderr_tasks[agent_id] = asyncio.create_task(
            self._monitor_agent_stderr(agent_id, process)
        )
        return process

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _parse_uuid(self, value: Optional[str]) -> Optional[uuid.UUID]:
        if not value:
            return None
        try:
            return uuid.UUID(value)
        except ValueError:
            return None

    def _map_status(self, status: AgentStatus) -> DbAgentStatus:
        return DbAgentStatus(status.value)

    async def _ensure_agent_instance(
        self,
        agent_id: str,
        agent_type: str,
        model: str,
    ) -> None:
        if not self._db_session_factory:
            return
        agent_uuid = self._parse_uuid(agent_id)
        if not agent_uuid:
            return
        try:
            async with self._db_session_factory() as session:
                instance = await session.get(AgentInstance, agent_uuid)
                if instance:
                    instance.status = DbAgentStatus.INITIALIZING
                    instance.agent_type = agent_type
                    instance.model = model
                    instance.last_heartbeat = self._now()
                else:
                    session.add(
                        AgentInstance(
                            id=agent_uuid,
                            agent_type=agent_type,
                            model=model,
                            status=DbAgentStatus.INITIALIZING,
                            last_heartbeat=self._now(),
                        )
                    )
                await session.commit()
        except Exception as exc:
            logger.warning(f"Failed to persist agent instance {agent_id}: {exc}")

    async def _update_agent_instance(self, agent_id: str, **updates) -> None:
        if not self._db_session_factory:
            return
        agent_uuid = self._parse_uuid(agent_id)
        if not agent_uuid:
            return
        if not updates:
            return
        try:
            async with self._db_session_factory() as session:
                instance = await session.get(AgentInstance, agent_uuid)
                if not instance:
                    return
                if "status" in updates:
                    status_value = updates.pop("status")
                    if isinstance(status_value, AgentStatus):
                        updates["status"] = self._map_status(status_value)
                    elif isinstance(status_value, DbAgentStatus):
                        updates["status"] = status_value
                    elif isinstance(status_value, str):
                        try:
                            updates["status"] = DbAgentStatus(status_value)
                        except ValueError:
                            pass
                if "last_heartbeat" in updates:
                    heartbeat = updates["last_heartbeat"]
                    if isinstance(heartbeat, (int, float)):
                        updates["last_heartbeat"] = datetime.fromtimestamp(
                            heartbeat, tz=timezone.utc
                        )
                if "current_session_id" in updates:
                    updates["current_session_id"] = self._parse_uuid(
                        updates["current_session_id"]
                    )
                for key, value in updates.items():
                    setattr(instance, key, value)
                await session.commit()
        except Exception as exc:
            logger.warning(f"Failed to update agent instance {agent_id}: {exc}")

    async def _monitor_agent_stdout(
        self,
        agent_id: str,
        process: subprocess.Popen,
    ) -> None:
        if not process.stdout:
            return
        try:
            while True:
                line = await asyncio.to_thread(process.stdout.readline)
                if not line:
                    break
                text = line.strip()
                if not text:
                    continue
                await self._handle_agent_output(agent_id, text)
        finally:
            self._stdout_tasks.pop(agent_id, None)
            await self._handle_process_exit(agent_id, process)

    async def _monitor_agent_stderr(
        self,
        agent_id: str,
        process: subprocess.Popen,
    ) -> None:
        if not process.stderr:
            return
        try:
            while True:
                line = await asyncio.to_thread(process.stderr.readline)
                if not line:
                    break
                text = line.strip()
                if text:
                    logger.warning(f"Agent {agent_id} stderr: {text}")
        finally:
            self._stderr_tasks.pop(agent_id, None)
            return

    async def _handle_agent_output(self, agent_id: str, text: str) -> None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.debug(f"Agent {agent_id} output: {text}")
            return

        message_type = payload.get("type")
        message_payload = payload.get("payload", payload)
        if message_type == "heartbeat":
            await self.update_heartbeat(agent_id)
            cpu = message_payload.get("cpu_percent", message_payload.get("cpuPercent"))
            memory = message_payload.get("memory_mb", message_payload.get("memoryMb"))
            if cpu is not None and memory is not None:
                await self.update_resources(agent_id, float(cpu), float(memory))
            return

        if message_type == "status":
            status_value = message_payload.get("status")
            if status_value:
                try:
                    status = AgentStatus(status_value)
                except ValueError:
                    return
                await self._set_agent_status(agent_id, status)

    async def _handle_process_exit(
        self,
        agent_id: str,
        process: subprocess.Popen,
    ) -> None:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent or agent.status in (AgentStatus.STOPPING, AgentStatus.STOPPED):
                return
            agent.status = AgentStatus.ERROR
            agent.error_message = f"Process exited with code {process.returncode}"
            agent.last_heartbeat = 0.0
        await self._update_agent_instance(
            agent_id,
            status=AgentStatus.ERROR,
            error_message=f"Process exited with code {process.returncode}",
            stopped_at=self._now(),
        )
        self._notify_status_change(agent_id, AgentStatus.ERROR)

    async def _set_agent_status(self, agent_id: str, status: AgentStatus) -> None:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return
            agent.status = status
        await self._update_agent_instance(agent_id, status=status)
        self._notify_status_change(agent_id, status)

    async def _cancel_agent_tasks(self, agent_id: str) -> None:
        task = self._stdout_tasks.pop(agent_id, None)
        if task:
            task.cancel()
        task = self._stderr_tasks.pop(agent_id, None)
        if task:
            task.cancel()

    async def stop_agent(self, agent_id: str, force: bool = False) -> bool:
        """
        Stop an agent process.

        Args:
            agent_id: The agent to stop
            force: If True, kill immediately without graceful shutdown

        Returns:
            True if the agent was stopped successfully
        """
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False

            if agent.status in (AgentStatus.STOPPING, AgentStatus.STOPPED):
                return True

            agent.status = AgentStatus.STOPPING
            self._notify_status_change(agent_id, AgentStatus.STOPPING)

        logger.info(f"Stopping agent {agent_id} (force={force})")

        try:
            await self._update_agent_instance(agent_id, status=AgentStatus.STOPPING)
            if agent.process:
                if force:
                    agent.process.kill()
                    try:
                        await asyncio.wait_for(
                            asyncio.to_thread(agent.process.wait),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"Agent {agent_id} did not exit after kill")
                else:
                    agent.process.terminate()
                    try:
                        # Wait for graceful shutdown
                        await asyncio.wait_for(
                            asyncio.to_thread(agent.process.wait),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"Agent {agent_id} did not stop gracefully, killing")
                        agent.process.kill()
                await self._cancel_agent_tasks(agent_id)

            async with self._lock:
                agent.status = AgentStatus.STOPPED
                self._notify_status_change(agent_id, AgentStatus.STOPPED)
                del self._agents[agent_id]

            await self._update_agent_instance(
                agent_id,
                status=AgentStatus.STOPPED,
                stopped_at=self._now(),
                current_session_id=None,
                pid=None,
            )
            logger.info(f"Agent {agent_id} stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping agent {agent_id}: {e}")
            return False

    async def get_available_agent(self) -> Optional[str]:
        """
        Get an available (idle) agent from the pool.

        If no idle agents are available and we haven't reached max,
        spawn a new one.

        Returns:
            Agent ID of an available agent, or None if none available
        """
        async with self._lock:
            # Try to find an idle agent
            for agent_id, agent in self._agents.items():
                if agent.status == AgentStatus.IDLE:
                    return agent_id

        # No idle agents, try to spawn one
        if len(self._agents) < self.max_agents:
            return await self.spawn_agent()

        return None

    async def assign_agent(self, agent_id: str, session_id: str) -> bool:
        """
        Assign an agent to a session, marking it as busy.

        Args:
            agent_id: The agent to assign
            session_id: The session to assign to

        Returns:
            True if assignment was successful
        """
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False
            if agent.status != AgentStatus.IDLE:
                return False

            agent.status = AgentStatus.BUSY
            agent.current_session_id = session_id
            self._notify_status_change(agent_id, AgentStatus.BUSY)

        await self._update_agent_instance(
            agent_id,
            status=AgentStatus.BUSY,
            current_session_id=session_id,
        )
        logger.info(f"Agent {agent_id} assigned to session {session_id}")
        return True

    async def release_agent(self, agent_id: str) -> bool:
        """
        Release an agent back to idle status.

        Args:
            agent_id: The agent to release

        Returns:
            True if release was successful
        """
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False

            agent.status = AgentStatus.IDLE
            agent.current_session_id = None
            self._notify_status_change(agent_id, AgentStatus.IDLE)

        await self._update_agent_instance(
            agent_id,
            status=AgentStatus.IDLE,
            current_session_id=None,
        )
        logger.info(f"Agent {agent_id} released to idle")
        return True

    async def update_heartbeat(self, agent_id: str) -> bool:
        """
        Update the heartbeat timestamp for an agent.

        Args:
            agent_id: The agent to update

        Returns:
            True if update was successful
        """
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False
            agent.update_heartbeat()
            heartbeat = agent.last_heartbeat
        await self._update_agent_instance(agent_id, last_heartbeat=heartbeat)
        return True

    async def update_resources(
        self, agent_id: str, cpu_percent: float, memory_mb: float
    ) -> bool:
        """
        Update resource metrics for an agent.

        Args:
            agent_id: The agent to update
            cpu_percent: CPU usage percentage
            memory_mb: Memory usage in MB

        Returns:
            True if update was successful
        """
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False
            agent.resources.update(cpu_percent, memory_mb)
        await self._update_agent_instance(
            agent_id,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
        )
        return True

    async def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """Get the current status of an agent."""
        agent = self._agents.get(agent_id)
        return agent.status if agent else None

    async def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """Get full information about an agent."""
        return self._agents.get(agent_id)

    async def get_pool_stats(self) -> Dict:
        """Get statistics about the agent pool."""
        status_counts = {}
        for agent in self._agents.values():
            status_counts[agent.status.value] = status_counts.get(agent.status.value, 0) + 1

        return {
            "total_agents": len(self._agents),
            "min_agents": self.min_agents,
            "max_agents": self.max_agents,
            "status_counts": status_counts,
            "idle_count": len(self.idle_agents),
            "busy_count": len(self.busy_agents),
        }

    async def _health_check_loop(self) -> None:
        """Background task that performs periodic health checks."""
        while self._running:
            try:
                await self._perform_health_checks()
                await self._ensure_minimum_agents()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _perform_health_checks(self) -> None:
        """Check health of all agents and restart unhealthy ones."""
        async with self._lock:
            agents_to_restart = []
            agents_to_mark_error = []

            for agent_id, agent in self._agents.items():
                if agent.status in (AgentStatus.STOPPING, AgentStatus.STOPPED):
                    continue

                if agent.process and agent.process.poll() is not None:
                    exit_code = agent.process.returncode
                    agent.status = AgentStatus.ERROR
                    agent.error_message = f"Process exited with code {exit_code}"
                    agents_to_mark_error.append((agent_id, agent.error_message))
                    self._notify_status_change(agent_id, AgentStatus.ERROR)
                    if agent.restart_count < self.max_restart_attempts:
                        agents_to_restart.append(agent_id)
                    else:
                        self._notify_status_change(agent_id, AgentStatus.ERROR)
                    continue

                if not agent.is_healthy(self.heartbeat_timeout):
                    logger.warning(f"Agent {agent_id} failed health check")
                    agent.status = AgentStatus.ERROR
                    agent.error_message = "Heartbeat timeout"
                    agents_to_mark_error.append((agent_id, agent.error_message))
                    self._notify_status_change(agent_id, AgentStatus.ERROR)

                    if agent.restart_count < self.max_restart_attempts:
                        agents_to_restart.append(agent_id)
                    else:
                        logger.error(
                            f"Agent {agent_id} exceeded max restart attempts, marking as error"
                        )
                        agent.error_message = "Exceeded max restart attempts"
                        agents_to_mark_error.append((agent_id, agent.error_message))
                        self._notify_status_change(agent_id, AgentStatus.ERROR)

        for agent_id, error_message in agents_to_mark_error:
            await self._update_agent_instance(
                agent_id,
                status=AgentStatus.ERROR,
                error_message=error_message,
                stopped_at=self._now(),
            )

        # Restart unhealthy agents outside the lock
        for agent_id in agents_to_restart:
            await self._restart_agent(agent_id)

    async def _restart_agent(self, agent_id: str) -> None:
        """Restart a failed agent."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return
            restart_count = agent.restart_count

        logger.info(f"Restarting agent {agent_id} (attempt {restart_count + 1})")

        # Stop the old agent
        await self.stop_agent(agent_id, force=True)

        # Spawn a replacement
        new_agent_id = await self.spawn_agent()
        if new_agent_id:
            async with self._lock:
                new_agent = self._agents.get(new_agent_id)
                if new_agent:
                    new_agent.restart_count = restart_count + 1
            await self._update_agent_instance(
                new_agent_id,
                restart_count=restart_count + 1,
            )

    async def _ensure_minimum_agents(self) -> None:
        """Ensure we have at least the minimum number of healthy agents."""
        async with self._lock:
            healthy_count = sum(
                1 for a in self._agents.values()
                if a.status in (AgentStatus.IDLE, AgentStatus.BUSY, AgentStatus.INITIALIZING)
            )

        while healthy_count < self.min_agents and len(self._agents) < self.max_agents:
            agent_id = await self.spawn_agent()
            if agent_id:
                healthy_count += 1
            else:
                break

    def _notify_status_change(self, agent_id: str, status: AgentStatus) -> None:
        """Notify callback of status change."""
        if self._on_agent_status_change:
            try:
                self._on_agent_status_change(agent_id, status)
            except Exception as e:
                logger.error(f"Error in status change callback: {e}")
