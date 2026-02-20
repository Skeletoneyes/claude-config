"""DevRunner workflow constants and brief schema definition.

Mirrors qr/constants.py API shape for conceptual consistency.
Kept separate from qr/constants.py per DL-002: DevRunner is a different
verification paradigm (artifact analysis vs. code review), and DevRunner
changes must not ripple through QR infrastructure.
"""

DEVRUNNER_ITERATION_LIMIT = 5
DEVRUNNER_ITERATION_DEFAULT = 1

# Canonical brief.json claim schema (authoritative definition).
# Each claim in the 'claims' array must include all fields listed here.
#
# Field definitions:
#   step          - Step label string matching a manifest.json step label
#   type          - Claim type: 'visual' | 'state' | 'log'
#   artifact      - Artifact path (relative to project) or null if no manifest
#   condition     - Human-readable pass condition derived from acceptance criteria
#   failure_pattern - Inverse of condition; describes what failure looks like
#   search        - Optional search hint for log/state claims (null if unused)
#   severity      - Severity from {MUST, SHOULD, COULD}:
#                     MUST  = acceptance criteria (blocking; plan cannot pass without it)
#                     SHOULD = behavioral outcomes (structural; worth fixing soon)
#                     COULD = cosmetic / nice-to-have (de-escalated first under iteration pressure)
BRIEF_SCHEMA_FIELDS = (
    "step",
    "type",
    "artifact",
    "condition",
    "failure_pattern",
    "search",
    "severity",
)


def get_devrunner_blocking_severities(iteration: int) -> frozenset[str]:
    """Return severities that block at given DevRunner analysis iteration.

    Progressive de-escalation narrows blocking scope as iterations increase,
    accepting lower-severity issues rather than looping indefinitely:
        iteration 1-2: MUST + SHOULD + COULD
        iteration 3:   MUST + SHOULD
        iteration 4+:  MUST only

    Thresholds match QR_ITERATION_LIMIT for consistency (DL-004).
    Rationale mirrors qr/constants.py:get_blocking_severities().

    Args:
        iteration: DevRunner analysis loop iteration count (1-indexed)

    Returns:
        Frozenset of severity strings that block at this iteration
    """
    if iteration >= 4:
        return frozenset({"MUST"})
    if iteration >= 3:
        return frozenset({"MUST", "SHOULD"})
    return frozenset({"MUST", "SHOULD", "COULD"})


def get_devrunner_iteration_guidance(iteration: int) -> str:
    """Get user-facing message about current DevRunner iteration state."""
    blocking = get_devrunner_blocking_severities(iteration)
    severity_order = ["MUST", "SHOULD", "COULD"]
    levels = ", ".join(s for s in severity_order if s in blocking)
    return f"DevRunner iteration {iteration}: blocking on {levels}."
