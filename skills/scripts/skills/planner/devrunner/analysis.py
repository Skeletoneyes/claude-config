#!/usr/bin/env python3
"""
DevRunner Analysis - Step-based workflow for artifact analysis sub-agent.

Guides sub-agents through structured verification of DevRunner test artifacts:
- Read brief.json and filter claims by ANALYSIS_TIER
- Correlate manifest.json step labels with claims
- Examine artifacts (screenshot, gamestate, log) per claim type
- Report PASS or ISSUES with per-claim findings

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.

Follows planner step-based workflow pattern (see developer/exec_implement_execute.py).
"""


STEPS = {
    1: "Read Brief",
    2: "Read Manifest",
    3: "Examine Artifacts",
    4: "Report",
}


def get_step_guidance(
    step: int, module_path: str = None, **kwargs
) -> dict:
    """Return guidance for the given step.

    Args:
        step: Current step number (1-indexed)
        module_path: Module path for -m invocation
        **kwargs: Additional context (analysis_tier, blocking_severities, etc.)
    """
    MODULE_PATH = module_path or "skills.planner.devrunner.analysis"
    tier = kwargs.get("analysis_tier", "cursory")
    blocking_severities_raw = kwargs.get("blocking_severities", "MUST,SHOULD,COULD")
    if isinstance(blocking_severities_raw, frozenset):
        blocking_severities = blocking_severities_raw
    else:
        blocking_severities = frozenset(s.strip() for s in str(blocking_severities_raw).split(",") if s.strip())

    if step == 1:
        return {
            "title": STEPS[1],
            "actions": [
                "INPUTS (from your prompt):",
                "  BRIEF_PATH: path to brief.json",
                "  MANIFEST_PATH: path to manifest.json",
                f"  ANALYSIS_TIER: {tier}",
                "",
                "1. Read BRIEF_PATH (brief.json).",
                "   Extract all claims from the 'claims' array.",
                "",
                "2. Filter claims by ANALYSIS_TIER:",
                "   - cursory tier: keep only claims where type == 'visual'",
                "   - thorough tier: keep all claims (visual, state, log)",
                "",
                f"3. SEVERITY FILTER: From the tier-filtered claims, keep only claims",
                f"   where claim.severity is in the blocking severities set: {{{', '.join(sorted(blocking_severities))}}}",
                "   Claims with severity NOT in this set are treated as SKIP for this iteration.",
                "   (Progressive de-escalation: blocking severities narrow as iterations increase.)",
                "",
                "4. Write out the filtered claim list before proceeding:",
                f"   FILTERED CLAIMS (tier={tier}, blocking={{{', '.join(sorted(blocking_severities))}}}):",
                "   | # | step       | type   | severity | condition                  |",
                "   | - | ---------- | ------ | -------- | -------------------------- |",
                "   | 1 | [label]    | visual | MUST     | [condition text from brief] |",
                "",
                "IMPORTANT: Read brief FIRST, before manifest or any artifacts.",
                "Brief ordering is the authoritative analysis protocol.",
                "",
                "NOTE: Steps 1-4 above are claim filtering steps. Step 3 (artifact examination)",
                "in this script refers to the NEXT script step (--step 3), not filter step 3.",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 2",
        }

    elif step == 2:
        return {
            "title": STEPS[2],
            "actions": [
                "1. Read MANIFEST_PATH (manifest.json).",
                "   Extract all steps from the 'steps' array.",
                "   Each step has: label, directory, artifacts.screenshot, artifacts.gamestate",
                "",
                "2. Correlate manifest steps with filtered claims from Step 1:",
                "   For each claim, find the manifest step where step.label == claim.step",
                "   Note the artifact paths for that step.",
                "",
                "3. Write correlation table:",
                "   | claim # | step       | screenshot path | gamestate path |",
                "   | ------- | ---------- | --------------- | -------------- |",
                "   | 1       | [label]    | [path]          | [path]         |",
                "",
                "If a claim's step has no matching manifest step:",
                "  Record as ISSUES: 'Step label not found in manifest: [label]'",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 3",
        }

    elif step == 3:
        return {
            "title": STEPS[3],
            "actions": [
                "For EACH filtered claim from Step 1:",
                "",
                "  If claim.type == 'visual':",
                "    Read the screenshot file at artifacts.screenshot path.",
                "    Evaluate claim.condition visually against the screenshot.",
                "    Note what you observe.",
                "",
                "  If claim.type == 'state':",
                "    Read the gamestate.json file at artifacts.gamestate path.",
                "    Check claim.condition against the JSON fields.",
                "    Note the actual values observed.",
                "",
                "  If claim.type == 'log':",
                "    Log artifact capture is not implemented; Godot GD.Print output has no capturable file artifact.",
                "    Mark claim as SKIP with reason: 'log artifacts not captured; GD.Print has no file output'",
                "",
                "For each claim, record:",
                "  | claim # | type   | condition          | artifact observed              |",
                "  | ------- | ------ | ------------------ | ------------------------------ |",
                "  | 1       | visual | [condition text]   | [what the screenshot shows]    |",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 4",
        }

    elif step == 4:
        return {
            "title": STEPS[4],
            "actions": [
                "For EACH claim, compare claim.condition and claim.failure_pattern against",
                "the artifact evidence you observed in Step 3.",
                "",
                "Verdict per claim:",
                "  PASS: condition met, failure_pattern not triggered",
                "  ISSUES: condition not met OR failure_pattern triggered",
                "  SKIP: claim was deferred (log capture not yet implemented, OR claim severity",
                "        was not in blocking severities set from Step 1 filtering); omit from OVERALL verdict",
                "",
                "If all non-SKIP claims are PASS, OVERALL is PASS.",
                "If any non-SKIP claim (after BOTH type and severity filtering from Step 1) is ISSUES,",
                "OVERALL is ISSUES. Claims that were SKIP due to severity filtering do not affect",
                "OVERALL verdict.",
                "",
                "Output format:",
                "",
                "  ANALYSIS_TIER: [cursory | thorough]",
                "  OVERALL: [PASS | ISSUES]",
                "",
                "  | claim # | step       | type   | verdict | evidence summary                     |",
                "  | ------- | ---------- | ------ | ------- | ------------------------------------ |",
                "  | 1       | [label]    | visual | PASS    | [what was observed]                  |",
                "  | 2       | [label]    | log    | SKIP    | log artifacts not captured             |",
                "",
                "If OVERALL is PASS: return exactly 'RESULT: PASS'",
                "If OVERALL is ISSUES: return:",
                "  RESULT: ISSUES",
                "  [per-claim findings table above]",
            ],
            "next": "Return result to orchestrator. Sub-agent task complete.",
        }

    return {"error": f"Invalid step {step}"}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "DevRunner Analysis: artifact verification workflow",
        extra_args=[
            (["--analysis-tier"], {"default": "cursory", "choices": ["cursory", "thorough"], "help": "Analysis tier"}),
            (["--blocking-severities"], {"default": "MUST,SHOULD,COULD", "help": "Comma-separated severity levels that block (e.g., MUST,SHOULD)"}),
        ],
    )
