"""
Agent Pool Manager for AutoBan.

Manages a pool of agent processes, handling spawning, stopping, health checks,
and automatic restart on failure.
"""

import asyncio
import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

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
        if self.status in (AgentStatus.STOPPED, AgentStatus.STOPPING):
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
        """
        self.min_agents = min_agents
        self.max_agents = max_agents
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_restart_attempts = max_restart_attempts
        self.agent_command = agent_command or ["python", "-m", "autoban.agent"]

        self._agents: Dict[str, AgentInfo] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        self._on_agent_status_change: Optional[Callable[[str, AgentStatus], None]] = None

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

    async def spawn_agent(self) -> Optional[str]:
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

        try:
            # Placeholder: In a real implementation, this would spawn an actual process
            # For now, we simulate the process spawn
            process = await self._spawn_process(agent_id)

            async with self._lock:
                agent_info.process = process
                agent_info.status = AgentStatus.IDLE
                agent_info.update_heartbeat()

            self._notify_status_change(agent_id, AgentStatus.IDLE)
            logger.info(f"Agent {agent_id} spawned and ready")
            return agent_id

        except Exception as e:
            logger.error(f"Failed to spawn agent {agent_id}: {e}")
            async with self._lock:
                agent_info.status = AgentStatus.ERROR
                agent_info.error_message = str(e)
            self._notify_status_change(agent_id, AgentStatus.ERROR)
            return None

    async def _spawn_process(self, agent_id: str) -> Optional[subprocess.Popen]:
        """
        Spawn the actual agent process.

        This is a placeholder implementation. In production, this would:
        1. Spawn a subprocess running the agent code
        2. Set up IPC channels (pipes, sockets, etc.)
        3. Wait for the agent to signal ready

        Args:
            agent_id: Unique identifier for the agent

        Returns:
            The subprocess.Popen object or None
        """
        # Placeholder: Simulate process spawn with a small delay
        await asyncio.sleep(0.1)

        # In production, uncomment and modify:
        # env = os.environ.copy()
        # env["AGENT_ID"] = agent_id
        # process = subprocess.Popen(
        #     self.agent_command,
        #     env=env,
        #     stdin=subprocess.PIPE,
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE,
        # )
        # return process

        return None  # Placeholder - no actual process

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
            if agent.process:
                if force:
                    agent.process.kill()
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

            async with self._lock:
                agent.status = AgentStatus.STOPPED
                self._notify_status_change(agent_id, AgentStatus.STOPPED)
                del self._agents[agent_id]

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

            for agent_id, agent in self._agents.items():
                if agent.status in (AgentStatus.STOPPING, AgentStatus.STOPPED):
                    continue

                if not agent.is_healthy(self.heartbeat_timeout):
                    logger.warning(f"Agent {agent_id} failed health check")

                    if agent.restart_count < self.max_restart_attempts:
                        agents_to_restart.append(agent_id)
                    else:
                        logger.error(
                            f"Agent {agent_id} exceeded max restart attempts, marking as error"
                        )
                        agent.status = AgentStatus.ERROR
                        agent.error_message = "Exceeded max restart attempts"
                        self._notify_status_change(agent_id, AgentStatus.ERROR)

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
