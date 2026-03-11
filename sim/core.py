from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple
import math
import random


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    SOLAR = "SOLAR"
    SUBSTATION = "SUBSTATION"
    BATTERY_STORAGE = "BATTERY_STORAGE"
    CHARGING_STATION = "CHARGING_STATION"


class TaskType(str, Enum):
    INSPECT = "INSPECT"
    SERVICE = "SERVICE"


class TaskStatus(str, Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentState(str, Enum):
    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    WORKING = "WORKING"
    RETURNING = "RETURNING"
    CHARGING = "CHARGING"


class AgentType(str, Enum):
    DRONE = "DRONE"
    GROUND_BOT = "GROUND_BOT"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnergyNode:
    node_id: str
    x: float
    y: float
    node_type: NodeType


@dataclass
class Task:
    task_id: str
    task_type: TaskType
    target_node_id: str
    created_ts: float
    status: TaskStatus = TaskStatus.NEW
    assigned_agent_id: Optional[str] = None
    assigned_ts: Optional[float] = None
    work_started_ts: Optional[float] = None
    completed_ts: Optional[float] = None


@dataclass
class Agent:
    agent_id: str
    agent_type: AgentType
    x: float
    y: float
    speed_mps: float
    battery: float = 100.0
    battery_drain_per_m: float = 0.3
    charge_rate_per_s: float = 5.0
    low_battery_threshold: float = 20.0
    state: AgentState = AgentState.IDLE
    task_id: Optional[str] = None
    home_node_id: Optional[str] = None
    dwell_until_ts: Optional[float] = None
    busy_time_s: float = 0.0

    def pos(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def needs_charge(self) -> bool:
        return self.battery <= self.low_battery_threshold


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def move_toward(agent: Agent, target: Tuple[float, float], dt: float) -> float:
    rx, ry = agent.x, agent.y
    tx, ty = target
    d = dist((rx, ry), (tx, ty))
    if d < 1e-6:
        return 0.0
    step = agent.speed_mps * dt
    if step >= d:
        agent.x, agent.y = tx, ty
        return d
    else:
        agent.x += (tx - rx) / d * step
        agent.y += (ty - ry) / d * step
        return step


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class Metrics:
    completed: int = 0
    failed: int = 0
    completion_times: List[float] = field(default_factory=list)
    queue_wait_times: List[float] = field(default_factory=list)
    energy_per_task: List[float] = field(default_factory=list)

    def throughput_per_min(self) -> float:
        if not self.completion_times:
            return 0.0
        avg = sum(self.completion_times) / len(self.completion_times)
        return 60.0 / max(avg, 1e-6)

    def avg_completion_time(self) -> float:
        return (sum(self.completion_times) / len(self.completion_times)
                if self.completion_times else 0.0)

    def avg_queue_wait(self) -> float:
        return (sum(self.queue_wait_times) / len(self.queue_wait_times)
                if self.queue_wait_times else 0.0)

    def avg_energy_per_task(self) -> float:
        return (sum(self.energy_per_task) / len(self.energy_per_task)
                if self.energy_per_task else 0.0)


# ---------------------------------------------------------------------------
# Task generator
# ---------------------------------------------------------------------------

class TaskGenerator:
    def __init__(self, inspectable_ids: List[str], serviceable_ids: List[str],
                 seed: int = 7):
        self.inspectable_ids = inspectable_ids
        self.serviceable_ids = serviceable_ids
        self.rng = random.Random(seed)
        self.counter = 0

    def maybe_generate(self, now: float, probability_per_tick: float) -> Optional[Task]:
        if self.rng.random() > probability_per_tick:
            return None
        self.counter += 1
        t_id = f"T{self.counter:04d}"
        if self.rng.random() < 0.6:
            task_type = TaskType.INSPECT
            target = self.rng.choice(self.inspectable_ids)
        else:
            task_type = TaskType.SERVICE
            target = self.rng.choice(self.serviceable_ids)
        return Task(task_id=t_id, task_type=task_type,
                    target_node_id=target, created_ts=now)


# ---------------------------------------------------------------------------
# Fleet manager
# ---------------------------------------------------------------------------

class FleetManager:
    def __init__(self, nodes: Dict[str, EnergyNode], agents: Dict[str, Agent]):
        self.nodes = nodes
        self.agents = agents
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []
        self.metrics = Metrics()

        self.arrival_tol_m = 0.25
        self.work_duration_s = 3.0
        self.charge_duration_s = 5.0

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task
        self.task_queue.append(task.task_id)

    def get_idle_agents(self, agent_type: Optional[AgentType] = None) -> List[Agent]:
        idle = [a for a in self.agents.values()
                if a.state == AgentState.IDLE and a.task_id is None]
        if agent_type:
            idle = [a for a in idle if a.agent_type == agent_type]
        return idle

    def get_charging_station(self, agent: Agent) -> Optional[EnergyNode]:
        if agent.home_node_id and agent.home_node_id in self.nodes:
            return self.nodes[agent.home_node_id]
        chargers = [n for n in self.nodes.values()
                    if n.node_type == NodeType.CHARGING_STATION]
        if not chargers:
            return None
        return min(chargers, key=lambda n: dist(agent.pos(), (n.x, n.y)))

    def tick(self, now: float, dt: float, allocator) -> None:
        for a in self.agents.values():
            if a.state == AgentState.IDLE and a.needs_charge():
                self._send_to_charge(a, now)
        allocator.allocate(now, self)
        for a in self.agents.values():
            was_busy = (a.state != AgentState.IDLE)
            self._tick_agent(now, dt, a)
            if was_busy:
                a.busy_time_s += dt

    def _send_to_charge(self, agent: Agent, now: float) -> None:
        charger = self.get_charging_station(agent)
        if charger is None:
            return
        agent.state = AgentState.RETURNING
        agent.task_id = None

    def _tick_agent(self, now: float, dt: float, a: Agent) -> None:
        if a.state == AgentState.IDLE:
            return

        if a.state == AgentState.NAVIGATING:
            task = self.tasks.get(a.task_id)
            if task is None:
                a.state = AgentState.IDLE
                a.task_id = None
                return
            target_node = self.nodes[task.target_node_id]
            target_pos = (target_node.x, target_node.y)
            traveled = move_toward(a, target_pos, dt)
            a.battery -= traveled * a.battery_drain_per_m
            if a.needs_charge():
                task.status = TaskStatus.FAILED
                self.metrics.failed += 1
                a.task_id = None
                self._send_to_charge(a, now)
                return
            if dist(a.pos(), target_pos) <= self.arrival_tol_m:
                a.state = AgentState.WORKING
                a.dwell_until_ts = now + self.work_duration_s
                task.status = TaskStatus.IN_PROGRESS
                task.work_started_ts = now

        elif a.state == AgentState.WORKING:
            if now >= (a.dwell_until_ts or now):
                task = self.tasks.get(a.task_id)
                if task:
                    task.status = TaskStatus.COMPLETED
                    task.completed_ts = now
                    self.metrics.completed += 1
                    self.metrics.completion_times.append(
                        task.completed_ts - task.created_ts)
                    if task.assigned_ts is not None:
                        self.metrics.queue_wait_times.append(
                            task.assigned_ts - task.created_ts)
                a.task_id = None
                self._send_to_charge(a, now)

        elif a.state == AgentState.RETURNING:
            charger = self.get_charging_station(a)
            if charger is None:
                a.state = AgentState.IDLE
                return
            charger_pos = (charger.x, charger.y)
            traveled = move_toward(a, charger_pos, dt)
            a.battery -= traveled * a.battery_drain_per_m
            a.battery = max(a.battery, 0.0)
            if dist(a.pos(), charger_pos) <= self.arrival_tol_m:
                a.state = AgentState.CHARGING
                a.dwell_until_ts = now + self.charge_duration_s

        elif a.state == AgentState.CHARGING:
            a.battery = min(100.0, a.battery + a.charge_rate_per_s * dt)
            if a.battery >= 100.0 and now >= (a.dwell_until_ts or now):
                a.state = AgentState.IDLE
