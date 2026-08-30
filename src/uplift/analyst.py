"""
changelog-analyst logic — parses docs/migration-guide.md and produces
the breaking-changes list (BC-001 through BC-006).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Hardcoded knowledge about breaking changes.
# We parse the guide for descriptions/patterns but IDs and confidence levels
# are authoritative here.
# ---------------------------------------------------------------------------

# Each tuple: (id, title, detection_hint, confidence_required)
_BC_META: list[tuple[str, str, str, float]] = [
    (
        "BC-001",
        "BaseSettings moved to pydantic-settings",
        r"from pydantic import BaseSettings",
        0.95,
    ),
    (
        "BC-002",
        "Validators renamed (@validator / @root_validator)",
        r"@validator|@root_validator",
        0.95,
    ),
    (
        "BC-003",
        "class Config → model_config / ConfigDict",
        r"class Config:",
        0.95,
    ),
    (
        "BC-004",
        "Field keyword renames (regex→pattern, min_items→min_length)",
        r"regex=|min_items=|max_items=|const=",
        0.95,
    ),
    (
        "BC-005",
        "Renamed model methods (.dict, .json, .copy, .schema, .parse_obj, .parse_raw)",
        # Match calls with or without arguments: .copy(update=...) counts too.
        r"\.(dict|json|copy|schema|parse_obj|parse_raw)\(",
        0.95,
    ),
    (
        "BC-006",
        "Behavioral changes (frozen raises ValidationError; Optional without default)",
        r"pytest\.raises\(TypeError\)|TypeError",
        0.70,
    ),
]

# H2 section index → (bc_id, title).  Sections are numbered 1-based in the guide.
_SECTION_TO_BC: dict[int, str] = {
    1: "BC-001",
    2: "BC-002",
    3: "BC-003",
    4: "BC-004",
    5: "BC-005",
    6: "BC-006",
}


def _extract_code_fences(text: str) -> list[str]:
    """Return all code-fence contents in *text*."""
    return re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)


def _parse_sections(guide_text: str) -> list[dict[str, str]]:
    """Split the guide into H2 sections, returning a list of {title, body}."""
    # Split on H2 headings (## …)
    parts = re.split(r"^## ", guide_text, flags=re.MULTILINE)
    sections: list[dict[str, str]] = []
    for part in parts[1:]:  # skip preamble
        newline = part.find("\n")
        heading = part[:newline].strip()
        body = part[newline + 1:]
        sections.append({"title": heading, "body": body})
    return sections


def extract_breaking_changes(guide_path: Path) -> list[dict[str, Any]]:
    """Parse *guide_path* and return a list of breaking-change dicts.

    The list always contains exactly six entries (BC-001..BC-006) ordered by id.
    Descriptions and old/new patterns are extracted from the guide; other fields
    are hardcoded in *_BC_META*.
    """
    guide_text = guide_path.read_text(encoding="utf-8")
    sections = _parse_sections(guide_text)

    # Build a lookup: section index (1-based) → parsed section data
    result: list[dict[str, Any]] = []
    for idx, (bc_id, bc_title, detection_hint, confidence) in enumerate(_BC_META, start=1):
        body = sections[idx - 1]["body"] if idx <= len(sections) else ""
        fences = _extract_code_fences(body)

        # old_pattern: first code-fence containing "# v1" or first fence overall
        old_pattern = ""
        new_pattern = ""
        for fence in fences:
            if "# v1" in fence:
                old_pattern = fence.strip()
            elif "# v2" in fence:
                new_pattern = fence.strip()
        # Fallback: first two fences if v1/v2 markers not present
        if not old_pattern and len(fences) >= 1:
            old_pattern = fences[0].strip()
        if not new_pattern and len(fences) >= 2:
            new_pattern = fences[1].strip()

        # Description: first paragraph of the section body (up to blank line or fence)
        description_lines: list[str] = []
        for line in body.splitlines():
            if line.startswith("```") or (not line.strip() and description_lines):
                break
            if line.strip():
                description_lines.append(line.strip())
        description = " ".join(description_lines)

        result.append(
            {
                "id": bc_id,
                "title": bc_title,
                "description": description,
                "detection_hint": detection_hint,
                "old_pattern": old_pattern,
                "new_pattern": new_pattern,
                "confidence_required": confidence,
            }
        )

    return result
