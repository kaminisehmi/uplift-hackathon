"""
Orchestrator — sequences analyst → scanner → migrators → verifier.

Each stage is a pure Python function; no direct Bob-mode invocations here.
The orchestrator is pydantic-v2-compatible in style but does NOT import pydantic.
"""

from __future__ import annotations

import concurrent.futures
import json
import sys
from pathlib import Path
from typing import Any

from uplift.analyst import extract_breaking_changes
from uplift.scanner import scan_usages
from uplift.migrator import apply_migrations, file_split
from uplift.verifier import run_pytest, fix_test_assertions, write_upgrade_report

# ---------------------------------------------------------------------------
# Paths (relative to cwd, which is always the project root)
# ---------------------------------------------------------------------------
REPORTS_DIR = Path("reports")
BREAKING_CHANGES_PATH = REPORTS_DIR / "breaking-changes.json"
USAGE_MAP_PATH = REPORTS_DIR / "usage-map.json"
UPGRADE_REPORT_PATH = REPORTS_DIR / "upgrade-report.json"
MIGRATION_GUIDE_PATH = Path("docs/migration-guide.md")
REQUIREMENTS_PATH = Path("requirements.txt")
SRC_ROOT = Path("src")
TEST_ROOT = Path("tests")

# UpLift's own package and its unit tests hold the pydantic v1 API patterns as
# string literals (detection hints, transform rules, fixtures). They must never
# be scanned or patched — otherwise the tool migrates itself.
SELF_PACKAGE_ROOT = Path(__file__).resolve().parent
SELF_EXCLUDE = [SELF_PACKAGE_ROOT, TEST_ROOT / "test_uplift_orchestrator.py"]


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------

def run_changelog_analyst(force: bool = False) -> list[dict[str, Any]]:
    """Parse migration guide and write breaking-changes.json.

    If the file already exists (pre-populated by a Bob mode run) it is read
    directly — unless *force* is True, in which case it is always regenerated
    from docs/migration-guide.md so judges see the live document→code pipeline.
    """
    if BREAKING_CHANGES_PATH.exists() and not force:
        with BREAKING_CHANGES_PATH.open() as fh:
            return json.load(fh)

    if not MIGRATION_GUIDE_PATH.exists():
        raise FileNotFoundError(
            f"Migration guide not found: {MIGRATION_GUIDE_PATH}. "
            "Run the changelog-analyst Bob mode first, or provide docs/migration-guide.md."
        )

    bc_list = extract_breaking_changes(MIGRATION_GUIDE_PATH)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with BREAKING_CHANGES_PATH.open("w") as fh:
        json.dump(bc_list, fh, indent=2)
    print(f"[analyst] extracted {len(bc_list)} breaking changes")
    return bc_list


def run_usage_scanner(
    bc_list: list[dict[str, Any]], force: bool = False
) -> dict[str, list[dict[str, Any]]]:
    """Scan src/ and tests/ for usages and write usage-map.json.

    If the file already exists it is read directly — unless *force* is True,
    in which case the scan is always re-run live.
    """
    if USAGE_MAP_PATH.exists() and not force:
        with USAGE_MAP_PATH.open() as fh:
            return json.load(fh)

    usage_map = scan_usages(
        bc_list, root_dirs=[SRC_ROOT, TEST_ROOT], exclude=SELF_EXCLUDE
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with USAGE_MAP_PATH.open("w") as fh:
        json.dump(usage_map, fh, indent=2)
    total = sum(len(v) for v in usage_map.values())
    print(f"[scanner] found {total} usage sites")
    return usage_map


def _run_single_migrator(
    label: str,
    usage_map: dict[str, list[dict[str, Any]]],
    bc_list: list[dict[str, Any]],
    assigned_files: set[str],
) -> list[dict[str, Any]]:
    changes = apply_migrations(usage_map, bc_list, assigned_files)
    applied = sum(1 for c in changes if c.get("applied"))
    flagged = len(changes) - applied
    summary = f"[migrator-{label}] Applied {applied} changes"
    if flagged:
        summary += f" ({flagged} flagged for human review)"
    print(summary)
    return changes


def run_code_migrators(
    usage_map: dict[str, list[dict[str, Any]]],
    bc_list: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run Migrator A and Migrator B in parallel; return combined change list."""
    files_a, files_b = file_split()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(_run_single_migrator, "A", usage_map, bc_list, files_a)
        fut_b = pool.submit(_run_single_migrator, "B", usage_map, bc_list, files_b)
        changes_a = fut_a.result()
        changes_b = fut_b.result()

    return changes_a + changes_b


def run_verifier(
    changes: list[dict[str, Any]],
    needs_human_review: list[dict[str, Any]],
    max_retries: int = 2,
) -> tuple[bool, list[dict[str, Any]]]:
    """Run pytest, applying BC-006 test fix on first failure; retry up to max_retries.

    Returns (success, test_runs).
    """
    test_runs: list[dict[str, Any]] = []

    for attempt in range(1, max_retries + 2):  # attempts: 1..max_retries+1
        passed, failure_count = run_pytest()
        test_runs.append({"attempt": attempt, "passed": passed, "failure_count": failure_count})
        print(
            f"[verifier] Attempt {attempt}: {'PASSED' if passed else f'FAILED ({failure_count} failures)'}"
        )

        if passed:
            return True, test_runs

        if attempt <= max_retries:
            # Try to fix test-side assertions (BC-006)
            fix_test_assertions(needs_human_review)

    return False, test_runs


# ---------------------------------------------------------------------------
# Top-level coordinator
# ---------------------------------------------------------------------------

def upgrade(library: str, force: bool = False) -> bool:
    """Drive the full migration pipeline for *library*.

    Args:
        library: The library name to upgrade (e.g. ``"pydantic"``).
        force:   When True, cached reports/*.json are ignored and both the
                 changelog analyst and usage scanner re-run live so the full
                 document→code pipeline is visible.
    """
    print(f"[uplift] Starting upgrade: {library}" + (" (--force)" if force else ""))

    # Stage 1 — changelog analyst
    bc_list = run_changelog_analyst(force=force)

    # Stage 2 — usage scanner
    usage_map = run_usage_scanner(bc_list, force=force)

    # Stage 3 — code migrators (parallel)
    changes = run_code_migrators(usage_map, bc_list)

    # Collect needs_human_review items (BC-006 or low-confidence)
    # Both migrators can flag the same site, so de-duplicate by (bc, file, line)
    # to keep the report's review list one row per real item.
    needs_human_review: list[dict[str, Any]] = []
    _seen_review: set[tuple[Any, Any, Any]] = set()
    for c in changes:
        if not c.get("needs_human_review"):
            continue
        key = (c.get("bc_id"), c.get("file"), c.get("line"))
        if key in _seen_review:
            continue
        _seen_review.add(key)
        needs_human_review.append(c)

    # Nothing was applied and a report already exists: the target is already
    # migrated. Writing now would replace a real report with an empty one, so
    # stop before Stage 5 and leave the existing artifact alone.
    if not any(c.get("applied") for c in changes) and UPGRADE_REPORT_PATH.exists():
        print(
            f"[uplift] Nothing to migrate — {library} usage is already on the "
            f"target version. Left {UPGRADE_REPORT_PATH} untouched."
        )
        return True

    # Stage 4 — verifier with retry
    passed, test_runs = run_verifier(changes, needs_human_review, max_retries=2)

    # Stage 5 — write final reports
    files_modified = sorted({c["file"] for c in changes if c.get("applied")})
    report_data: dict[str, Any] = {
        "target": library,
        "from_version": "1.x",
        "to_version": "2.x",
        "files_modified": files_modified,
        "changes": [c for c in changes if not c.get("needs_human_review")],
        "needs_human_review": needs_human_review,
        "test_runs": test_runs,
        "final_status": "green" if passed else "red",
    }
    write_upgrade_report(report_data, UPGRADE_REPORT_PATH)

    if passed:
        print("[uplift] Migration complete — all tests green.")
    else:
        print("[uplift] Migration finished but tests are still failing. Review UPGRADE_REPORT.md.", file=sys.stderr)

    return passed
