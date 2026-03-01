\# RESULTS



This file tracks benchmark snapshots and comparisons as SwarmOps Twin evolves.



> Rule: If we change behavior, we record metrics before/after.



---



\## Phase 1 — Baseline (FIFO + nearest)



\*\*Environment\*\*

\- Robots: 3

\- Stations: 3 pickup / 3 dropoff

\- Tick rate: 20 Hz (`dt=0.05`)

\- Movement: straight-line

\- Pickup/Dropoff dwell: 1.0s each



\*\*Workload\*\*

\- Task generation: `task\_prob = 0.02` (moderate load)

\- Seed: 7



\*\*Metrics to Record\*\*

\- Throughput (tasks/min)

\- Avg completion time (s)

\- Avg queue wait (s)

\- Utilization (%)

\- Queue length (steady-state)



\*\*Snapshot Template\*\*

\- Date:

\- Commit:

\- Runtime:

\- Throughput:

\- Avg completion:

\- Avg wait:

\- Utilization:

\- Queue behavior:



---



\## Phase 1.5 — Congestion Penalty (Planned)



We will introduce a proximity-based speed penalty and re-run the same workload.



\*\*Goal\*\*

Quantify throughput degradation and queue growth caused by congestion.



---



\## Phase 2 — Policy Comparison (Planned)



We will compare:

\- Baseline: FIFO + nearest

\- Improved: resource-aware / load-aware policy



\*\*Acceptance Criteria\*\*

Improved policy must outperform baseline under congestion on at least:

\- Throughput

\- Queue growth rate

\- Avg completion time

