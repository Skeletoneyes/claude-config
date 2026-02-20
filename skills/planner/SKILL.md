---
name: planner
description: Interactive planning and execution for complex tasks. IMMEDIATELY invoke when user asks to use planner.
---

## Activation

When this skill activates, IMMEDIATELY invoke the corresponding script. The
script IS the workflow.

| Mode      | Intent                             | Command                                                                                                          |
| --------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| planning  | "plan", "design", "architect"      | `<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.planner.orchestrator.planner --step 1" />`  |
| execution | "execute", "implement", "run plan" | `<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.planner.orchestrator.executor --step 1" />` |

## State Management

The planner and executor handle state differently:

| Mode      | Step Parameter | State Dir Parameter | State Discovery          |
| --------- | -------------- | ------------------- | ------------------------ |
| planning  | `--step N`     | `--state-dir <path>` | Explicit (passed to each step) |
| execution | `--step N`     | **NOT ACCEPTED**    | Auto-discovered from temp dir  |

**Critical**: Do NOT pass `--state-dir` to the executor. It auto-discovers the state from the planner session and will error if you try to pass it explicitly.

## Common Mistakes

### ❌ Passing --state-dir to executor

```bash
# WRONG - executor doesn't accept this parameter
python3 -m skills.planner.orchestrator.executor --step 3 --state-dir /path/to/state
```

**Error**: `executor.py: error: unrecognized arguments: --state-dir ...`

### ✅ Correct executor invocation

```bash
# RIGHT - executor auto-discovers state
python3 -m skills.planner.orchestrator.executor --step 3
```

**Explanation**: The planner explicitly passes `--state-dir` between its steps for clarity and control. The executor auto-discovers the most recent planner state directory from the system temp folder, so you only need to specify `--step`. This prevents accidental state mixing if multiple planning sessions are running.
