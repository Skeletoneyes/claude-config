#!/usr/bin/env python3
"""
DevRunner Brief Author - Step-based workflow for brief.json authoring sub-agent.

Guides a quality-reviewer sub-agent through structured authoring of brief.json
claims from plan acceptance criteria and manifest.json artifact topology.

Three steps:
  1. Read Plan Criteria - extract acceptance criteria for the milestone
  2. Read Manifest     - extract step labels and artifact paths
  3. Author Brief      - write brief.json with severity-tagged claims

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.

Follows planner step-based workflow pattern (see devrunner/analysis.py).
Trust boundary: this script is dispatched as quality-reviewer, never developer.
"""

from skills.planner.devrunner.constants import BRIEF_SCHEMA_FIELDS


STEPS = {
    1: "Read Plan Criteria",
    2: "Read Manifest",
    3: "Author Brief",
}


def get_step_guidance(
    step: int, module_path: str = None, **kwargs
) -> dict:
    """Return guidance for the given step.

    Args:
        step: Current step number (1-indexed)
        module_path: Module path for -m invocation
        **kwargs: Additional context (plan_file, milestone, manifest_path, output_path)
    """
    MODULE_PATH = module_path or "skills.planner.devrunner.brief_author"
    plan_file = kwargs.get("plan_file", "$PLAN_FILE")
    milestone = kwargs.get("milestone", "$MILESTONE")
    manifest_path = kwargs.get("manifest_path", "test_output/manifest.json")
    output_path = kwargs.get("output_path", "test_output/brief.json")

    if step == 1:
        return {
            "title": STEPS[1],
            "actions": [
                "INPUTS (from your prompt):",
                f"  PLAN_FILE: {plan_file}",
                f"  MILESTONE: {milestone}",
                f"  MANIFEST_PATH: {manifest_path}",
                f"  OUTPUT_PATH: {output_path}",
                "",
                "1. Read PLAN_FILE.",
                "   Locate the milestone section matching MILESTONE.",
                "   Extract ALL acceptance criteria and requirements for that milestone.",
                "",
                "2. Write out the extracted criteria before proceeding:",
                "   ACCEPTANCE CRITERIA for [milestone]:",
                "   | # | criterion                                          |",
                "   | - | -------------------------------------------------- |",
                "   | 1 | [acceptance criterion text from plan]              |",
                "",
                "IMPORTANT: Read plan FIRST, before manifest or any artifacts.",
                "Plan criteria are the authoritative source of behavioral expectations.",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 2",
        }

    elif step == 2:
        return {
            "title": STEPS[2],
            "actions": [
                f"1. Attempt to read MANIFEST_PATH: {manifest_path}",
                "",
                "   FALLBACK (manifest does not exist):",
                f"   If {manifest_path} does not exist or cannot be read:",
                "     - Note: 'manifest.json not found; using plan criteria only'",
                "     - Proceed directly to Step 3",
                "     - In Step 3, set artifact=null for all claims",
                "     - Set step='unknown' for all claims",
                "     - Set type='visual' and severity='MUST' as conservative defaults",
                "",
                "   IF manifest exists:",
                "   2. Extract all steps from the 'steps' array.",
                "      Each step has: label, directory, artifacts.screenshot, artifacts.gamestate",
                "",
                "   3. Write correlation table between plan criteria and manifest steps:",
                "      | criterion # | plan criterion summary | manifest step label | artifact paths |",
                "      | ----------- | ---------------------- | ------------------- | -------------- |",
                "      | 1           | [criterion summary]    | [label]             | [paths]        |",
                "",
                "   4. Note any plan criteria with no matching manifest step.",
                "      These will get step='unknown' and artifact=null in brief.json.",
            ],
            "next": f"python3 -m {MODULE_PATH} --step 3",
        }

    elif step == 3:
        field_list = ", ".join(f'"{f}"' for f in BRIEF_SCHEMA_FIELDS)
        return {
            "title": STEPS[3],
            "actions": [
                f"Write brief.json at {output_path} with the following schema:",
                "",
                '  {',
                '    "schema": "devrunner-brief-v1",',
                '    "claims": [',
                '      {',
                f'        {field_list}',
                '      }',
                '    ]',
                '  }',
                "",
                "CLAIM AUTHORING RULES:",
                "",
                "  step:            Use the manifest step label that corresponds to this",
                "                   acceptance criterion. Use 'unknown' if no manifest or",
                "                   no matching step was found.",
                "",
                "  type:            Select claim type based on what can be verified:",
                "                     'visual'  - screenshot comparison (default when uncertain)",
                "                     'state'   - gamestate.json field check",
                "                     'log'     - GD.Print output (note: log capture not yet",
                "                                 implemented; set type='log' only if no other",
                "                                 artifact can verify the criterion)",
                "",
                "  artifact:        Artifact path from manifest.json for this step.",
                "                   Use null if manifest was not found.",
                "",
                "  condition:       The pass condition. Derive directly from the acceptance",
                "                   criterion text. Be specific and testable.",
                "                   Example: 'Score display shows 30 after 3-row clear'",
                "",
                "  failure_pattern: The inverse of condition. Describes what failure looks like.",
                "                   Example: 'Score display shows value other than 30'",
                "",
                "  search:          Optional search hint for log/state claims.",
                "                   Use null for visual claims.",
                "",
                "  severity:        Assign based on criterion importance:",
                "                     'MUST'   - Acceptance criteria from plan (blocking)",
                "                     'SHOULD' - Behavioral outcomes implied by spec",
                "                     'COULD'  - Cosmetic or polish observations",
                "                   When uncertain, assign 'MUST' (conservative).",
                "",
                "SEVERITY ASSIGNMENT GUIDANCE:",
                "  - Plan acceptance criteria -> MUST",
                "  - Expected game behavior not in acceptance criteria -> SHOULD",
                "  - Visual polish (alignment, color, spacing) -> COULD",
                "",
                "OUTPUT: Write the complete brief.json file to OUTPUT_PATH.",
                "Verify the JSON is valid before completing.",
            ],
            "next": "Return result to orchestrator. Brief authoring complete.",
        }

    return {"error": f"Invalid step {step}"}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "DevRunner Brief Author: acceptance criteria to brief.json claims",
        extra_args=[
            (["--plan-file"], {"default": None, "help": "Path to plan file (required)"}),
            (["--milestone"], {"default": None, "help": "Milestone ID (e.g., M-001)"}),
            (["--manifest-path"], {"default": "test_output/manifest.json", "help": "Path to manifest.json"}),
            (["--output-path"], {"default": "test_output/brief.json", "help": "Output path for brief.json"}),
        ],
    )
