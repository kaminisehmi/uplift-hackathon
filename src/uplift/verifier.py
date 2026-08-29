"""
verifier logic — runs pytest, applies BC-006 test fix, writes reports.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# pytest runner
# ---------------------------------------------------------------------------

def run_pytest(cwd: Path | None = None) -> tuple[bool, int]:
    """Run ``python -m pytest`` and return ``(passed, failure_count)``.

    *failure_count* is parsed from pytest output on failure; 0 on success.
    """
    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=no", "-q"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    passed = result.returncode == 0
    failure_count = 0
    if not passed:
        # Parse e.g. "5 failed" from pytest summary line
        m = re.search(r"(\d+) failed", result.stdout + result.stderr)
        if m:
            failure_count = int(m.group(1))
        else:
            # Any non-zero exit with no "failed" text → assume 1
            failure_count = 1
    return passed, failure_count


# ---------------------------------------------------------------------------
# BC-006 test fix
# ---------------------------------------------------------------------------

def fix_test_assertions(needs_human_review: list[dict[str, Any]]) -> None:
    """Apply BC-006 fix: replace TypeError with ValidationError in test files.

    Only edits files listed in *needs_human_review* with bc_id == "BC-006".
    """
    for item in needs_human_review:
        if item.get("bc_id") != "BC-006":
            continue
        file_path = Path(item["file"])
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")

        # Ensure ValidationError is imported
        if "from pydantic import" in text and "ValidationError" not in text:
            text = re.sub(
                r"(from pydantic import )([^\n]+)",
                lambda m: m.group(1) + ", ".join(
                    sorted(set(m.group(2).split(", ") + ["ValidationError"]))
                ),
                text,
            )
        elif "ValidationError" not in text:
            # Add import at top after existing imports
            text = "from pydantic import ValidationError\n" + text

        # Replace pytest.raises(TypeError) with pytest.raises(ValidationError)
        new_text, n = re.subn(
            r"pytest\.raises\(TypeError\)",
            "pytest.raises(ValidationError)",
            text,
        )
        if n > 0:
            file_path.write_text(new_text, encoding="utf-8")
            # Update the status in the review item
            item["status"] = "auto-applied"


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------

def write_upgrade_report(
    report_data: dict[str, Any],
    report_path: Path,
) -> None:
    """Write upgrade-report.json and UPGRADE_REPORT.md."""
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # JSON report
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report_data, fh, indent=2)

    # Markdown report
    md_path = report_path.parent.parent / "UPGRADE_REPORT.md"
    _write_markdown_report(report_data, md_path)

    print(f"[verifier] Wrote {report_path}")
    print(f"[verifier] Wrote {md_path}")


def _write_markdown_report(report_data: dict[str, Any], md_path: Path) -> None:
    lines: list[str] = [
        "# UpLift Upgrade Report",
        "",
        f"**Target:** {report_data.get('target', 'unknown')}  ",
        f"**From:** {report_data.get('from_version', '?')}  ",
        f"**To:** {report_data.get('to_version', '?')}  ",
        f"**Final Status:** `{report_data.get('final_status', 'unknown')}`  ",
        "",
        "## Files Modified",
        "",
    ]

    for f in report_data.get("files_modified", []):
        lines.append(f"- `{f}`")

    lines += [
        "",
        "## Breaking Changes Applied",
        "",
        "| BC ID | File | Line | Description |",
        "|-------|------|------|-------------|",
    ]
    for change in report_data.get("changes", []):
        bc_id = change.get("bc_id", "")
        file_ = change.get("file", "")
        line_ = change.get("line", "")
        desc = change.get("description", "")
        lines.append(f"| {bc_id} | `{file_}` | {line_} | {desc} |")

    lines += [
        "",
        "## Test Run History",
        "",
        "| Attempt | Passed | Failures |",
        "|---------|--------|----------|",
    ]
    for run in report_data.get("test_runs", []):
        attempt = run.get("attempt", "")
        passed = "✅" if run.get("passed") else "❌"
        failures = run.get("failure_count", 0)
        lines.append(f"| {attempt} | {passed} | {failures} |")

    nhr = report_data.get("needs_human_review", [])
    if nhr:
        lines += [
            "",
            "## Needs Human Review",
            "",
            "| BC ID | File | Line | Reason | Status |",
            "|-------|------|------|--------|--------|",
        ]
        for item in nhr:
            bc_id = item.get("bc_id", "")
            file_ = item.get("file", "")
            line_ = item.get("line", "")
            reason = item.get("reason", "")
            status = item.get("status", "")
            lines.append(f"| {bc_id} | `{file_}` | {line_} | {reason} | {status} |")

    lines += ["", "---", "", "*Generated by UpLift*", ""]

    md_path.write_text("\n".join(lines), encoding="utf-8")
