"""
usage-scanner logic — walks source/test directories and finds every line
matching a breaking-change detection_hint.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_SKIP_EXTENSIONS = {".pyc", ".pyo", ".so", ".pyd"}


def scan_usages(
    bc_list: list[dict[str, Any]],
    root_dirs: list[Path],
) -> dict[str, list[dict[str, Any]]]:
    """For each breaking change in *bc_list*, find all matching lines in *root_dirs*.

    Returns a dict keyed by bc_id, each value a list of
    ``{"file": str, "line": int, "snippet": str}``.
    """
    # Compile patterns once
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for bc in bc_list:
        hint = bc.get("detection_hint", "")
        if hint:
            try:
                compiled.append((bc["id"], re.compile(hint)))
            except re.error:
                # Treat malformed hint as literal
                compiled.append((bc["id"], re.compile(re.escape(hint))))

    usage_map: dict[str, list[dict[str, Any]]] = {bc["id"]: [] for bc in bc_list}

    for root in root_dirs:
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if any(path.suffix == ext for ext in _SKIP_EXTENSIONS):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue

            for lineno, line_text in enumerate(lines, start=1):
                for bc_id, pattern in compiled:
                    if pattern.search(line_text):
                        usage_map[bc_id].append(
                            {
                                "file": str(path),
                                "line": lineno,
                                "snippet": line_text.rstrip(),
                            }
                        )

    return usage_map
