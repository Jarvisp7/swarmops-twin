import time
from sim.core import Station, Robot, FleetManager, TaskGenerator
from sim.allocator_baseline import BaselineAllocator


def main():
    # Predefined warehouse-style stations (meters)
    stations = {
        # pickups
        "P1": Station("P1", 2, 2, "PICKUP"),
        "P2": Station("P2", 2, 8, "PICKUP"),
        "P3": Station("P3", 2, 14, "PICKUP"),
        # dropoffs
        "D1": Station("D1", 18, 3, "DROPOFF"),
        "D2": Station("D2", 18, 9, "DROPOFF"),
        "D3": Station("D3", 18, 15, "DROPOFF"),
    }

    # 3 robots staged in the middle
    robots = {
        "R1": Robot("R1", x=10, y=2),
        "R2": Robot("R2", x=10, y=9),
        "R3": Robot("R3", x=10, y=16),
    }

    fm = FleetManager(stations=stations, robots=robots)
    allocator = BaselineAllocator()
    gen = TaskGenerator(pickup_ids=["P1", "P2", "P3"], dropoff_ids=["D1", "D2", "D3"], seed=7)

    dt = 0.05        # 20 Hz tick
    task_prob = 0.08 # task generation probability per tick
    t0 = time.time()
    last_print = t0

    while True:
        now = time.time()

        task = gen.maybe_generate(now, probability_per_tick=task_prob)
        if task:
            fm.add_task(task)

        fm.tick(now=now, dt=dt, allocator=allocator)

        if now - last_print >= 2.0:
            util = sum(r.busy_time_s for r in fm.robots.values()) / (len(fm.robots) * max(now - t0, 1e-6))
            print(
                f"tasks_done={fm.metrics.completed:4d}  "
                f"throughput~{fm.metrics.throughput_per_min():5.2f}/min  "
                f"avg_complete={fm.metrics.avg_completion_time():5.2f}s  "
                f"avg_wait={fm.metrics.avg_queue_wait():5.2f}s  "
                f"util={util*100:5.1f}%  "
                f"queue_len={len(fm.task_queue):3d}"
            )
            last_print = now

        time.sleep(dt)


if __name__ == "__main__":
    main()