from __future__ import annotations
from typing import Optional
from sim.core import TaskStatus, RobotState, dist


class BaselineAllocator:
    """FIFO tasks, assign to nearest idle robot to pickup."""
    def allocate(self, now: float, fm) -> None:
        while True:
            task_id = self._next_new_task(fm)
            if task_id is None:
                return

            idle = fm.get_idle_robots()
            if not idle:
                return

            task = fm.tasks[task_id]
            pu = fm.stations[task.pickup_station_id]
            pu_pos = (pu.x, pu.y)

            best = min(idle, key=lambda r: dist(r.pos(), pu_pos))

            task.status = TaskStatus.ASSIGNED
            task.assigned_robot_id = best.robot_id
            task.assigned_ts = now

            best.task_id = task.task_id
            best.state = RobotState.TO_PICKUP

    def _next_new_task(self, fm) -> Optional[str]:
        while fm.task_queue:
            tid = fm.task_queue[0]
            t = fm.tasks.get(tid)
            if t and t.status == TaskStatus.NEW:
                return tid
            fm.task_queue.pop(0)
        return None