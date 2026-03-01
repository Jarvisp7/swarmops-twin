# SwarmOps Twin
### Simulation-first multi-robot fleet coordination benchmark (engine-first)

[![status](https://img.shields.io/badge/status-Phase%201%20Complete-brightgreen)](https://github.com/Jarvisp7/swarmops-twin)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![roadmap](https://img.shields.io/badge/roadmap-Phase%201.5%20Next-yellow)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Overview






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