# orchestrator/

Main workflow entry points: planning and execution orchestration.

## Index

| File | Contents (WHAT) | Read When (WHEN) |
| --- | --- | --- |
| `planner.py` | 11-step planning workflow (plan-init through plan-docs-qr-gate) | Understanding planning phases, modifying planner step handlers |
| `executor.py` | 9-step execution workflow (planning through retrospective); wave-aware developer dispatch, brief-author dispatch (step 4a), DevRunner analysis dispatch (step 4b) with iteration tracking and progressive de-escalation | Understanding execution phases, modifying wave loop behavior, DevRunner integration |
