## Project Structure

```
swarmops_twin/
└── sim/
    ├── core.py                  # Task model + Fleet Manager + state machine + metrics
    ├── allocator_baseline.py    # FIFO + nearest-idle allocation strategy
    ├── run_headless.py          # Simulation runner (20 Hz)
    └── __init__.py
```

---

## Architecture (Diagram)

```
              +----------------------+
              |     TaskGenerator    |
              | (stochastic arrivals)|
              +----------+-----------+
                         |
                         v
        +----------------+------------------+
        |              FleetManager         |
        |  - task queue (FIFO)              |
        |  - robot registry                 |
        |  - state machine tick             |
        |  - metrics collection             |
        +----------------+------------------+
                         |
                         v
              +----------+-----------+
              |  BaselineAllocator   |
              | FIFO + nearest idle  |
              +----------+-----------+
                         |
               assigns task to robot
                         |
                         v
         +---------------+------------------+
         |        Robot State Machine       |
         | IDLE → TO_PICKUP → PICKING       |
         |      → TO_DROPOFF → DROPPING     |
         +----------------------------------+
```