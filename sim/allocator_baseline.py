from __future__ import annotations
from typing import Optional
from sim.core import (TaskType, TaskStatus, AgentState, AgentType,
                      AgentState, dist)


class BaselineAllocator:
    """FIFO queue. Drones inspect, ground bots service. Nearest idle agent."""

    def allocate(self, now: float, fm) -> None:
        while True:
            task_id = self._next_new_task(fm)
            if task_id is None:
                return

            task = fm.tasks[task_id]

            # match task type to agent type
            if task.task_type == TaskType.INSPECT:
                needed = AgentType.DRONE
            else:
                needed = AgentType.GROUND_BOT

            idle = fm.get_idle_agents(agent_type=needed)

            # fallback: if no matching type available, try any idle agent
            if not idle:
                idle = fm.get_idle_agents()
            if not idle:
                return

            target_node = fm.nodes[task.target_node_id]
            target_pos = (target_node.x, target_node.y)

            best = min(idle, key=lambda a: dist(a.pos(), target_pos))

            task.status = TaskStatus.ASSIGNED
            task.assigned_agent_id = best.agent_id
            task.assigned_ts = now

            best.task_id = task.task_id
            best.state = AgentState.NAVIGATING

            # remove from queue
            fm.task_queue.remove(task_id)

    def _next_new_task(self, fm) -> Optional[str]:
        for tid in fm.task_queue:
            t = fm.tasks.get(tid)
            if t and t.status == TaskStatus.NEW:
                return tid
        return None
