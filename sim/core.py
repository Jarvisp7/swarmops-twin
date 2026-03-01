from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple
import math
import time
import random


class TaskStatus(str, Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    PICKED = "PICKED"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Station:
    station_id: str
    x: float
    y: float
    station_type: str


@dataclass
class Task:
    task_id: str
    pickup_station_id: str
    dropoff_station_id: str
    created_ts: float
    status: TaskStatus = TaskStatus.NEW
    assigned_robot_id: Optional[str] = None
    assigned_ts: Optional[float] = None
    picked_ts: Optional[float] = None
    completed_ts: Optional[float] = None


class RobotState(str, Enum):
    IDLE = "IDLE"
    TO_PICKUP = "TO_PICKUP"
    PICKING = "PICKING"
    TO_DROPOFF = "TO_DROPOFF"
    DROPPING = "DROPPING"


@dataclass
class Robot:
    robot_id: str
    x: float
    y: float
    speed_mps: float = 1.2
    state: RobotState = RobotState.IDLE
    task_id: Optional[str] = None
    dwell_until_ts: Optional[float] = None
    busy_time_s: float = 0.0

    def pos(self) -> Tuple[float, float]:
        return (self.x, self.y)


def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def move_toward(robot: Robot, target: Tuple[float, float], dt: float) -> None:
    rx, ry = robot.x, robot.y
    tx, ty = target
    d = dist((rx, ry), (tx, ty))
    if d < 1e-6:
        return
    step = robot.speed_mps * dt
    if step >= d:
        robot.x, robot.y = tx, ty
    else:
        robot.x += (tx - rx) / d * step
        robot.y += (ty - ry) / d * step


@dataclass
class Metrics:
    completed: int = 0
    completion_times: List[float] = field(default_factory=list)
    queue_wait_times: List[float] = field(default_factory=list)

    def throughput_per_min(self) -> float:
        if not self.completion_times:
            return 0.0
        avg = sum(self.completion_times) / len(self.completion_times)
        return 60.0 / max(avg, 1e-6)

    def avg_completion_time(self) -> float:
        return sum(self.completion_times) / len(self.completion_times) if self.completion_times else 0.0

    def avg_queue_wait(self) -> float:
        return sum(self.queue_wait_times) / len(self.queue_wait_times) if self.queue_wait_times else 0.0


class TaskGenerator:
    def __init__(self, pickup_ids: List[str], dropoff_ids: List[str], seed: int = 7):
        self.pickup_ids = pickup_ids
        self.dropoff_ids = dropoff_ids
        self.rng = random.Random(seed)
        self.counter = 0

    def maybe_generate(self, now: float, probability_per_tick: float) -> Optional[Task]:
        if self.rng.random() > probability_per_tick:
            return None
        self.counter += 1
        t_id = f"T{self.counter:04d}"
        pu = self.rng.choice(self.pickup_ids)
        do = self.rng.choice(self.dropoff_ids)
        return Task(task_id=t_id, pickup_station_id=pu, dropoff_station_id=do, created_ts=now)


class FleetManager:
    def __init__(self, stations: Dict[str, Station], robots: Dict[str, Robot]):
        self.stations = stations
        self.robots = robots
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []
        self.metrics = Metrics()

        self.arrival_tol_m = 0.25
        self.pickup_dwell_s = 1.0
        self.dropoff_dwell_s = 1.0

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task
        self.task_queue.append(task.task_id)

    def get_idle_robots(self) -> List[Robot]:
        return [r for r in self.robots.values() if r.state == RobotState.IDLE and r.task_id is None]

    def tick(self, now: float, dt: float, allocator) -> None:
        allocator.allocate(now, self)
        for r in self.robots.values():
            was_busy = (r.state != RobotState.IDLE)
            self._tick_robot(now, dt, r)
            if was_busy:
                r.busy_time_s += dt

    def _tick_robot(self, now: float, dt: float, r: Robot) -> None:
        if r.task_id is None:
            r.state = RobotState.IDLE
            return

        task = self.tasks.get(r.task_id)
        if task is None:
            r.state = RobotState.IDLE
            r.task_id = None
            return

        pu = self.stations[task.pickup_station_id]
        do = self.stations[task.dropoff_station_id]
        pu_pos = (pu.x, pu.y)
        do_pos = (do.x, do.y)

        if r.state == RobotState.TO_PICKUP:
            move_toward(r, pu_pos, dt)
            if dist(r.pos(), pu_pos) <= self.arrival_tol_m:
                r.state = RobotState.PICKING
                r.dwell_until_ts = now + self.pickup_dwell_s

        elif r.state == RobotState.PICKING:
            if now >= (r.dwell_until_ts or now):
                task.status = TaskStatus.PICKED
                task.picked_ts = now
                r.state = RobotState.TO_DROPOFF

        elif r.state == RobotState.TO_DROPOFF:
            move_toward(r, do_pos, dt)
            if dist(r.pos(), do_pos) <= self.arrival_tol_m:
                r.state = RobotState.DROPPING
                r.dwell_until_ts = now + self.dropoff_dwell_s

        elif r.state == RobotState.DROPPING:
            if now >= (r.dwell_until_ts or now):
                task.status = TaskStatus.DONE
                task.completed_ts = now
                self.metrics.completed += 1
                self.metrics.completion_times.append(task.completed_ts - task.created_ts)
                if task.assigned_ts is not None:
                    self.metrics.queue_wait_times.append(task.assigned_ts - task.created_ts)
                r.task_id = None
                r.state = RobotState.IDLE