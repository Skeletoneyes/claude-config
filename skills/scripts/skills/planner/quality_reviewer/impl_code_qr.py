#!/usr/bin/env python3
"""QR coordinator for impl-code phase.

Thin coordinator combining decomposition (steps 1-13) and
parallel verify dispatch (steps 14-15).

Steps 1-13: Delegate to impl_code_qr_decompose (item generation + grouping).
Step 14: Read qr-impl-code.json, dispatch parallel verify agents per group.
Step 15: Aggregate verify results, output PASS or FAIL for executor gate.
"""

from skills.planner.quality_reviewer import impl_code_qr_decompose
from skills.planner.shared.qr.utils import load_qr_state, has_qr_failures
from skills.planner.shared.qr.utils import format_qr_result


PHASE = "impl-code"
WORKFLOW = "executor"

# Module path for -m invocation (used in next commands)
_MODULE_PATH = "skills.planner.quality_reviewer.impl_code_qr"

# Verify module path for --qr-item dispatch
_VERIFY_MODULE = "skills.planner.quality_reviewer.impl_code_qr_verify"


def _group_items(items: list[dict]) -> dict[str, list[str]]:
    """Group items by group_id. Ungrouped items become singletons.

    Returns dict mapping group label -> list of item IDs.
    Singletons use the item id as the group label.
    """
    groups: dict[str, list[str]] = {}
    for item in items:
        gid = item.get("group_id") or item["id"]
        groups.setdefault(gid, []).append(item["id"])
    return groups


def _build_verify_dispatch(group_label: str, item_ids: list[str], state_dir: str) -> list[str]:
    """Build dispatch instructions for one group of items."""
    item_flags = " ".join(f"--qr-item {iid}" for iid in item_ids)
    cmd = (
        f"python3 -m {_VERIFY_MODULE} --step 1"
        f" --state-dir {state_dir}"
        f" {item_flags}"
    )
    lines = [
        f"GROUP: {group_label} ({len(item_ids)} item(s))",
        f"  Items: {', '.join(item_ids)}",
        f"  Command: {cmd}",
    ]
    return lines


def _step_14_dispatch(state_dir: str, module_path: str) -> dict:
    """Step 14: Read qr-impl-code.json and generate parallel verify dispatch."""
    qr_state = load_qr_state(state_dir, PHASE)
    if not qr_state:
        return {
            "title": "QR Impl-Code Step 14: Verify Dispatch",
            "actions": [
                f"ERROR: Could not load qr-{PHASE}.json from {state_dir}",
                "Run steps 1-13 first to generate QR items.",
            ],
            "next": "",
        }

    items = [i for i in qr_state.get("items", []) if i.get("status") == "TODO"]
    if not items:
        # All items already verified; proceed to step 15
        return {
            "title": "QR Impl-Code Step 14: Verify Dispatch",
            "actions": [
                "No TODO items found in qr-impl-code.json.",
                "All items already verified. Proceeding to step 15.",
            ],
            "next": f"python3 -m {module_path} --step 15 --state-dir {state_dir}",
        }

    groups = _group_items(items)

    actions = [
        "PARALLEL VERIFY DISPATCH",
        "",
        f"Total TODO items: {len(items)}",
        f"Groups to dispatch: {len(groups)}",
        "",
        "For EACH group below, dispatch ONE quality-reviewer agent in parallel.",
        "All groups can be dispatched simultaneously (multiple Task calls).",
        "",
    ]

    for group_label, item_ids in sorted(groups.items()):
        actions.extend(_build_verify_dispatch(group_label, item_ids, state_dir))
        actions.append("")

    actions.extend([
        "DISPATCH PROTOCOL:",
        "  1. Invoke Task(quality-reviewer) for EACH group command above.",
        "  2. All groups run in PARALLEL (one Task call per group).",
        "  3. Each agent runs its full verify workflow and updates qr-impl-code.json.",
        "  4. Wait for ALL agents to complete.",
        "  5. Proceed to step 15.",
        "",
        "After all agents complete:",
    ])

    return {
        "title": "QR Impl-Code Step 14: Verify Dispatch",
        "actions": actions,
        "next": f"python3 -m {module_path} --step 15 --state-dir {state_dir}",
    }


def _step_15_verdict(state_dir: str) -> dict:
    """Step 15: Aggregate verify results, output PASS or FAIL."""
    passed = not has_qr_failures(state_dir, PHASE)
    result = format_qr_result(WORKFLOW, PHASE, passed, state_dir)

    actions = [
        "AGGREGATING VERIFY RESULTS",
        "",
        f"Read qr-{PHASE}.json: check all item statuses.",
        "",
        "PASS if: all items are PASS (no FAIL items at blocking severity).",
        "FAIL if: any item is FAIL at blocking severity for current iteration.",
        "",
        "=" * 60,
        result,
        "=" * 60,
    ]

    return {
        "title": "QR Impl-Code Step 15: Verdict",
        "actions": actions,
        "next": "",
    }


def get_step_guidance(step: int, module_path: str = None, **kwargs) -> dict:
    """Route step to appropriate handler.

    Steps 1-13: Delegate to impl_code_qr_decompose with this module as path.
    Step 14: Generate parallel verify dispatch from qr-impl-code.json.
    Step 15: Aggregate results and output PASS or FAIL.
    """
    module_path = module_path or _MODULE_PATH
    state_dir = kwargs.get("state_dir", "")

    if 1 <= step <= 13:
        guidance = impl_code_qr_decompose.get_step_guidance(step, module_path, **kwargs)
        # Step 13 normally ends with next="". Override to chain into step 14.
        if step == 13 and guidance.get("next") == "":
            state_dir_arg = f" --state-dir {state_dir}" if state_dir else ""
            guidance["next"] = f"python3 -m {module_path} --step 14{state_dir_arg}"
        return guidance

    if step == 14:
        return _step_14_dispatch(state_dir, module_path)

    if step == 15:
        return _step_15_verdict(state_dir)

    return {
        "title": "Error",
        "actions": [f"Invalid step {step}. Valid range: 1-15."],
        "next": "",
    }


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "QR-Impl-Code: Post-implementation code quality review workflow",
        extra_args=[
            (["--state-dir"], {"type": str, "required": True, "help": "State directory path"}),
            (["--qr-item"], {"action": "append", "help": "Item ID (repeatable)"}),
            (["--mode"], {"choices": ["decompose", "verify"], "help": "Execution mode"}),
        ],
    )
