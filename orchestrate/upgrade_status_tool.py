"""
UpLift — watsonx Orchestrate ADK tool.

Reads reports/upgrade-report.json and returns a structured upgrade-status
summary for the Upgrade Approval Agent.

Usage (ADK):
    from orchestrate.upgrade_status_tool import upgrade_status
    result = upgrade_status()
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# watsonx Orchestrate ADK — tool decorator
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

# Path is resolved relative to the repo root so it works whether the tool is
# run locally or imported by the Orchestrate runtime.
_REPORT_PATH = Path(__file__).resolve().parent.parent / "reports" / "upgrade-report.json"


@tool(
    name="upgrade_status",
    description=(
        "Returns the UpLift pydantic migration upgrade status. "
        "Includes overall pass/fail status, per-breaking-change results, "
        "and any items flagged for human review."
    ),
    permission=ToolPermission.READ_ONLY,
)
def upgrade_status() -> dict[str, Any]:
    """Read reports/upgrade-report.json and return structured upgrade status.

    Returns
    -------
    dict with keys:
        target          – dependency that was upgraded (e.g. "pydantic")
        from_version    – version upgraded from
        to_version      – version upgraded to
        final_status    – "green" | "red" | "partial"
        files_modified  – list of file paths that were changed
        bc_results      – list of {bc_id, file, line, description, applied}
        needs_human_review – list of {bc_id, file, line, reason, status}
        test_runs       – list of {attempt, passed, failure_count}
    """
    if not _REPORT_PATH.exists():
        return {
            "error": f"Upgrade report not found at {_REPORT_PATH}. "
                     "Run `python -m uplift upgrade pydantic` first.",
        }

    with _REPORT_PATH.open() as fh:
        report: dict[str, Any] = json.load(fh)

    return {
        "target": report.get("target", "unknown"),
        "from_version": report.get("from_version", "unknown"),
        "to_version": report.get("to_version", "unknown"),
        "final_status": report.get("final_status", "unknown"),
        "files_modified": report.get("files_modified", []),
        "bc_results": report.get("changes", []),
        "needs_human_review": report.get("needs_human_review", []),
        "test_runs": report.get("test_runs", []),
    }
