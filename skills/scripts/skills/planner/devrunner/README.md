# DevRunner: Artifact-Based Test Verification

DevRunner is a verification workflow that analyzes test artifacts (screenshots, game state files) produced by a test execution to determine if acceptance criteria have been met.

**Key files:**
- `constants.py` - Configuration constants and severity filtering logic
- `brief_author.py` - Brief authoring sub-agent (quality-reviewer)
- `analysis.py` - Artifact analysis sub-agent
- Controlled by `orchestrator/executor.py` step 3 (implementation wave loop)

---

## Trust Boundary: Brief Authoring

### The Problem
Developers should not verify their own work. The original design had the developer write brief.json claims ("here's what should be true"), then the developer ran analysis to verify those claims. This violates the separation-of-concerns principle that quality review requires independent verification.

### The Solution
A dedicated **quality-reviewer sub-agent** (brief_author.py) authors brief.json claims from:
1. **Plan acceptance criteria** - the behavioral requirements the plan specifies
2. **Manifest.json artifact topology** - the structural layout of test outputs (step labels, artifact paths)

The brief author never reads implementation source code and cannot be influenced by how the developer built the feature. This enforces the trust boundary: the developer writes code, the quality reviewer defines what to verify, and a separate analysis agent checks the artifacts.

### Dispatcher Roles
- **Developer**: Implements code, runs tests (DevRunnerCapture)
- **Quality-Reviewer**: Authors brief.json (brief_author.py step 1)
- **Developer** (again): Runs artifact analysis (analysis.py step 1 cursory)
- **Quality-Reviewer** (again): Runs deeper artifact analysis (analysis.py step 1 thorough)

The alternating roles ensure no single agent owns the full verify-and-judge cycle.

---

## Brief Authoring Workflow

The brief authoring agent follows a 3-step structured workflow (brief_author.py):

### Step 1: Read Plan Criteria
Locate the plan file (from PLAN_FILE argument) and extract acceptance criteria for the milestone being tested (from MILESTONE argument).

Output a table listing all acceptance criteria with their text and requirement level (from plan).

### Step 2: Read Manifest
Read manifest.json (test output artifact) to understand the test structure:
- All step labels and their artifact paths (screenshot, gamestate.json)
- Fallback: if manifest.json does not exist (e.g., developer test failed before capture), skip this step and proceed to Step 3 with conservative defaults (type='visual', severity='MUST')

Output a correlation table matching plan criteria to manifest steps.

### Step 3: Author Brief
Write brief.json with a `claims` array. Each claim includes:

| Field | Purpose | Example |
|-------|---------|---------|
| `step` | Manifest step label this claim tests | `"place_piece_left"` |
| `type` | Claim verification method (`'visual'` \| `'state'` \| `'log'`) | `"visual"` |
| `artifact` | Path to artifact from manifest (relative to project) | `"test_output/place_piece_left/screenshot.png"` |
| `condition` | Pass condition (what should be true) | `"Score display shows '10' after placing one piece"` |
| `failure_pattern` | Failure condition (inverse of condition) | `"Score display shows any value other than '10'"` |
| `search` | Optional: search hint for state/log claims | `"score"` or `null` |
| `severity` | Claim importance: `MUST` \| `SHOULD` \| `COULD` | `"MUST"` |

**Severity Assignment Guide:**
- **MUST**: Acceptance criteria from the plan (blocking — plan cannot pass without it)
- **SHOULD**: Behavioral outcomes implied by the specification (structural — worth fixing soon)
- **COULD**: Visual polish, alignment, cosmetic details (de-escalated first under iteration pressure)

**Claim Types:**
- **`'visual'`**: Requires screenshot comparison. Used for most UI-based claims. (Default when uncertain)
- **`'state'`**: Requires checking gamestate.json fields. Used for game logic state verification.
- **`'log'`**: Requires GD.Print output capture. (Not yet implemented; use as placeholder only)

---

## Constants Module (devrunner/constants.py)

Configuration constants and utility functions for DevRunner iteration management.

### Iteration Limits
```python
DEVRUNNER_ITERATION_LIMIT = 5          # Maximum analysis iterations per milestone
DEVRUNNER_ITERATION_DEFAULT = 1         # Starting iteration number
```

### Progressive De-Escalation
As iterations increase, the set of "blocking" severities narrows, accepting lower-quality artifacts rather than looping forever:

```
Iteration 1-2: blocking = {MUST, SHOULD, COULD}  # All claims block
Iteration 3:   blocking = {MUST, SHOULD}         # Drop COULD; accept cosmetic issues
Iteration 4+:  blocking = {MUST}                 # MUST only; accept behavioral issues too
```

**Function:** `get_devrunner_blocking_severities(iteration: int) -> frozenset[str]`

Returns the set of severity levels that block (produce ISSUES verdict) at a given iteration.

**Guidance:** `get_devrunner_iteration_guidance(iteration: int) -> str`

Returns a user-facing message about the current iteration state.

### Brief Schema
```python
BRIEF_SCHEMA_FIELDS = (
    "step",              # Manifest step label
    "type",              # 'visual' | 'state' | 'log'
    "artifact",          # Artifact path or null
    "condition",         # Pass condition
    "failure_pattern",   # Failure condition
    "search",            # Optional search hint
    "severity",          # MUST | SHOULD | COULD
)
```

This constant is the authoritative definition of brief.json claim fields. Brief authoring guidance references this to ensure consistency.

---

## Artifact Analysis Workflow

The analysis agent follows a 4-step workflow (analysis.py) to verify brief.json claims against artifacts.

### Step 1: Read Brief
Load brief.json and filter claims by:
1. **Type filter** (based on ANALYSIS_TIER)
   - Cursory: visual claims only
   - Thorough: all claim types (visual + state + log)

2. **Severity filter** (based on --blocking-severities argument)
   - Keep only claims where `claim.severity` is in the blocking set for this iteration
   - Other claims are marked SKIP (deferred to later iteration)

### Step 2: Read Manifest
Load manifest.json to correlate claims with test artifacts:
- For each claim, locate the manifest step with matching `step.label`
- Note artifact paths (screenshot, gamestate.json) for artifact examination

### Step 3: Examine Artifacts
For each filtered claim, read the corresponding artifact and evaluate the condition:
- **Visual**: Compare screenshot against the visual condition
- **State**: Parse gamestate.json and check field values
- **Log**: Deferred; mark as SKIP (log capture not yet implemented)

### Step 4: Report
For each claim, render a verdict:
- **PASS**: Condition met, failure pattern not present
- **ISSUES**: Condition not met OR failure pattern present
- **SKIP**: Claim deferred (severity filtered or log not captured)

**Overall verdict rules:**
- If all non-SKIP claims are PASS → OVERALL PASS
- If any non-SKIP claim is ISSUES → OVERALL ISSUES
- SKIP claims do not affect verdict (they're intentionally deferred)

---

## Executor Integration: Step 3 Implementation Wave Loop

DevRunner is integrated into the executor's step 3 (Implementation) as a sub-workflow within each wave execution:

### Sub-Step 3a: Developer Dispatch
- Developers implement code and run tests
- DevRunnerCapture produces test_output/manifest.json with step labels and artifact paths
- Developers commit code changes

### Sub-Step 3b: Brief Authoring Dispatch (NEW)
- **Agent**: quality-reviewer (not developer)
- **Script**: `devrunner/brief_author.py --step 1`
- **Inputs**: PLAN_FILE, MILESTONE, manifest.json path, brief.json output path
- **Output**: test_output/brief.json with severity-tagged claims
- **Run frequency**: Once per milestone (first iteration only, or if manifest structure changed)
- **Error handling**: If brief authoring fails, skip DevRunner analysis for that iteration; wave proceeds

### Sub-Step 3c: DevRunner Analysis Dispatch (Enhanced)
Runs a loop of analysis iterations, with progressive de-escalation:

#### Iteration Loop
1. **Iteration 1**: Analyze all claims (MUST + SHOULD + COULD blocking)
2. **Iteration 2**: Same as iteration 1
3. **Iteration 3**: Drop COULD; analyze only MUST + SHOULD
4. **Iteration 4+**: MUST only; skip SHOULD and COULD claims
5. **Iteration > 5**: Stop; accept remaining issues

#### Per-Iteration Dispatch
For each iteration N:
```
devrunner_iteration = N

cursory_analysis(--blocking-severities MUST,SHOULD,COULD)  # iteration 1-2
cursory_analysis(--blocking-severities MUST,SHOULD)        # iteration 3
cursory_analysis(--blocking-severities MUST)               # iteration 4+

if PASS → thorough_analysis(--blocking-severities SAME)
if ISSUES → increment iteration, loop back (cursory next time)
```

#### Blocking Severities Table (emitted in executor guidance)
The executor emits a table showing which severities block at each iteration:
```
     iter 1: --blocking-severities MUST,SHOULD,COULD
     iter 2: --blocking-severities MUST,SHOULD,COULD
     iter 3: --blocking-severities MUST,SHOULD
     iter 4: --blocking-severities MUST
     iter 5: --blocking-severities MUST
```

The orchestrating agent (you) is responsible for:
1. Initializing `devrunner_iteration = DEVRUNNER_ITERATION_DEFAULT` (1) at wave start
2. Incrementing on ISSUES verdicts
3. Checking against DEVRUNNER_ITERATION_LIMIT (5) before dispatching analysis
4. Substituting [BLOCKING_SEVERITIES] with the correct values from the table

---

## Dual-Filter Model: Type + Severity

Analysis.py implements two independent filters:

### Type Filter (based on ANALYSIS_TIER)
- **Cursory**: Keep only `type == 'visual'` claims (quick smoke test)
- **Thorough**: Keep all claim types (comprehensive verification)

### Severity Filter (based on --blocking-severities)
- Progressively narrows blocking scope as iterations increase
- Claims filtered out are marked SKIP (deferred, not failed)
- Allows graceful degradation: if all thorough claims are ISSUES, iteration 3 re-analyzes dropping cosmetic (COULD) claims; iteration 4 re-analyzes dropping behavioral (SHOULD) claims too

**Verdict rules:**
- Only claims passing BOTH filters contribute to verdict
- Type-filtered claims are SKIP
- Severity-filtered claims are SKIP
- SKIP claims do not affect OVERALL verdict

**Example:** If you run thorough analysis (all types) at iteration 3 (MUST+SHOULD blocking):
- Visual MUST claims → analyzed (pass or issues)
- Visual SHOULD claims → analyzed
- Visual COULD claims → SKIP (not in blocking set)
- State SHOULD claims → analyzed
- Log claims → SKIP (not implemented)

---

## Error Handling and Fallbacks

### Brief Author Failure
If brief_author.py crashes or times out:
1. Log the error
2. Skip DevRunner analysis (step 4b) for this iteration
3. Continue to next iteration (retry brief authoring)
4. If brief authoring fails all iterations, milestone completes without DevRunner verification (degraded mode)

### Missing Manifest
If manifest.json does not exist when brief author runs:
1. Brief author step 2 detects the missing file
2. Falls back to authoring claims from plan criteria alone
3. Sets `artifact=null`, `step='unknown'`, `type='visual'`, `severity='MUST'` as conservative defaults
4. Analysis proceeds with limited artifact availability (will likely find ISSUES for 'unknown' steps)

---

## Module Boundaries

- **devrunner/constants.py** is a configuration leaf (no behavioral imports; only stdlib)
- **devrunner/brief_author.py** imports only constants
- **devrunner/analysis.py** imports only constants
- **orchestrator/executor.py** imports from devrunner.constants (but not devrunner.brief_author or devrunner.analysis directly)

This structure prevents DevRunner changes from rippling into QR infrastructure (mirroring the decision in DL-002).

---

## Key Design Decisions Reference

| Decision | Details |
|----------|---------|
| **DL-002** | DevRunner constants in separate module, not qr/constants.py (different paradigm, no ripple effects) |
| **DL-003** | Brief author dispatched AFTER developer (manifest.json exists), BEFORE analysis |
| **DL-004** | De-escalation thresholds match QR exactly for cognitive consistency |
| **DL-007** | Brief author reads plan + manifest, NOT implementation code (preserves trust boundary) |
| **DL-008** | Brief author runs once per milestone (inputs stable after first run) |
| **DL-012** | Severity filtering native in analysis.py --blocking-severities CLI arg (no prompt injection) |
