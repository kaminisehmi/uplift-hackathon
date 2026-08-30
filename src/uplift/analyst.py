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


def _split_v1_v2(fence: str) -> tuple[str, str]:
    """Split one code fence that carries both halves into (v1_part, v2_part)."""
    lines = fence.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("# v2"):
            return "\n".join(lines[:i]).strip(), "\n".join(lines[i:]).strip()
    return fence.strip(), ""


def _table_pairs(body: str) -> list[tuple[str, str]]:
    """Extract (old, new) pairs from a two-column markdown mapping table.

    Header and separator rows are skipped; cells are stripped of backticks so
    the values read as bare API names.
    """
    pairs: list[tuple[str, str]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`").strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        left, right = cells[0], cells[1]
        if not left or not right:
            continue
        if set(left) <= set("-: ") or set(right) <= set("-: "):
            continue  # separator row
        if left.lower().startswith("v1") or "option" in left.lower():
            continue  # header row
        pairs.append((left, right))
    return pairs


def _arrow_pairs(body: str) -> list[tuple[str, str]]:
    """Extract (old, new) pairs from bullet lines written as ``old -> new``."""
    pairs: list[tuple[str, str]] = []
    for line in body.splitlines():
        line = line.strip().lstrip("-*").strip()
        if "→" not in line and "->" not in line:
            continue
        sep = "→" if "→" in line else "->"
        left, _, right = line.partition(sep)
        left_codes = re.findall(r"`([^`]+)`", left)
        right_codes = re.findall(r"`([^`]+)`", right)
        if left_codes and right_codes:
            pairs.append((left_codes[0].strip(), right_codes[0].strip()))
    return pairs


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

        # old_pattern / new_pattern: guides express the before/after either as
        # code fences (sometimes one fence holding both halves) or as a
        # two-column markdown table. Handle all three shapes.
        old_pattern = ""
        new_pattern = ""
        for fence in fences:
            has_v1, has_v2 = "# v1" in fence, "# v2" in fence
            if has_v1 and has_v2:
                old_half, new_half = _split_v1_v2(fence)
                old_pattern = old_pattern or old_half
                new_pattern = new_pattern or new_half
            elif has_v1:
                old_pattern = old_pattern or fence.strip()
            elif has_v2:
                new_pattern = new_pattern or fence.strip()
        # Fallback: first two fences if v1/v2 markers not present
        if not old_pattern and len(fences) >= 1:
            old_pattern = fences[0].strip()
        if not new_pattern and len(fences) >= 2:
            new_pattern = fences[1].strip()
        # Fallback: a two-column "v1 | v2" mapping table
        if not old_pattern and not new_pattern:
            pairs = _table_pairs(body) or _arrow_pairs(body)
            if pairs:
                old_pattern = "\n".join(old for old, _ in pairs)
                new_pattern = "\n".join(new for _, new in pairs)

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
