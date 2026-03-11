import time
from sim.core import (EnergyNode, NodeType, Agent, AgentType,
                      FleetManager, TaskGenerator)
from sim.allocator_baseline import BaselineAllocator


def main():
    # --- California microgrid layout (meters) ---
    nodes = {
        # Solar arrays (west side)
        "SOL1": EnergyNode("SOL1", 5, 5, NodeType.SOLAR),
        "SOL2": EnergyNode("SOL2", 5, 25, NodeType.SOLAR),
        # Substations (center)
        "SUB1": EnergyNode("SUB1", 25, 10, NodeType.SUBSTATION),
        "SUB2": EnergyNode("SUB2", 25, 20, NodeType.SUBSTATION),
        # Battery storage (east)
        "BAT1": EnergyNode("BAT1", 40, 8, NodeType.BATTERY_STORAGE),
        "BAT2": EnergyNode("BAT2", 40, 22, NodeType.BATTERY_STORAGE),
        # Charging station (central hub)
        "CHG1": EnergyNode("CHG1", 22, 15, NodeType.CHARGING_STATION),
    }

    # --- Agents ---
    # 2 inspection drones (fast, higher battery drain)
    # 3 ground service bots (slower, more efficient)
    agents = {
        "D1": Agent("D1", AgentType.DRONE, x=22, y=13,
                    speed_mps=3.0, battery_drain_per_m=0.5),
        "D2": Agent("D2", AgentType.DRONE, x=22, y=17,
                    speed_mps=3.0, battery_drain_per_m=0.5),
        "G1": Agent("G1", AgentType.GROUND_BOT, x=20, y=12,
                    speed_mps=1.2, battery_drain_per_m=0.2),
        "G2": Agent("G2", AgentType.GROUND_BOT, x=20, y=15,
                    speed_mps=1.2, battery_drain_per_m=0.2),
        "G3": Agent("G3", AgentType.GROUND_BOT, x=20, y=18,
                    speed_mps=1.2, battery_drain_per_m=0.2),
    }

    # assign all agents to the charging hub
    for a in agents.values():
        a.home_node_id = "CHG1"

    fm = FleetManager(nodes=nodes, agents=agents)
    allocator = BaselineAllocator()

    # drones inspect everything, ground bots service substations + batteries
    inspectable = ["SOL1", "SOL2", "SUB1", "SUB2", "BAT1", "BAT2"]
    serviceable = ["SUB1", "SUB2", "BAT1", "BAT2"]
    gen = TaskGenerator(inspectable_ids=inspectable,
                        serviceable_ids=serviceable, seed=7)

    dt = 0.05
    task_prob = 0.02
    print(f"[config] dt={dt} task_prob={task_prob} seed=7 "
          f"agents={len(agents)} (drones=2, ground=3) nodes={len(nodes)}")
    t0 = time.time()
    last_print = t0

    while True:
        now = time.time()

        task = gen.maybe_generate(now, probability_per_tick=task_prob)
        if task:
            print(f"[new_task] t={now - t0:6.1f}s  {task.task_id}  "
                  f"{task.task_type.value:7s} -> {task.target_node_id}")
            fm.add_task(task)

        fm.tick(now=now, dt=dt, allocator=allocator)

        if now - last_print >= 3.0:
            total_time = max(now - t0, 1e-6)
            util = (sum(a.busy_time_s for a in fm.agents.values())
                    / (len(fm.agents) * total_time))
            avg_bat = (sum(a.battery for a in fm.agents.values())
                       / len(fm.agents))
            charging = sum(1 for a in fm.agents.values()
                          if a.state.value == "CHARGING")

            print(
                f"[metrics] done={fm.metrics.completed:3d}  "
                f"fail={fm.metrics.failed:2d}  "
                f"thru~{fm.metrics.throughput_per_min():5.2f}/min  "
                f"avg_t={fm.metrics.avg_completion_time():5.1f}s  "
                f"wait={fm.metrics.avg_queue_wait():4.1f}s  "
                f"util={util * 100:4.1f}%  "
                f"bat={avg_bat:4.1f}%  "
                f"chrg={charging}  "
                f"queue={len(fm.task_queue):2d}"
            )
            last_print = now

        time.sleep(dt)


if __name__ == "__main__":
    main()
