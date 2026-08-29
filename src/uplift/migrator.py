"""
code-migrator logic — applies per-BC source patches to src/uplift_demo/.

File ownership:
  Migrator A — src/uplift_demo/models.py       (BC-002, BC-003, BC-004)
  Migrator B — src/uplift_demo/settings.py,
               src/uplift_demo/service.py,
               requirements.txt               (BC-001, BC-003, BC-005)

BC-006 is never patched here; it goes straight to needs_human_review.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# File-ownership split
# ---------------------------------------------------------------------------

def file_split() -> tuple[set[str], set[str]]:
    """Return (files_a, files_b) — the two disjoint migrator ownership sets."""
    files_a: set[str] = {
        "src/uplift_demo/models.py",
    }
    files_b: set[str] = {
        "src/uplift_demo/settings.py",
        "src/uplift_demo/service.py",
        "requirements.txt",
    }
    return files_a, files_b


# ---------------------------------------------------------------------------
# Per-BC transformation rules (operate on full file text)
# ---------------------------------------------------------------------------

def _transform_bc001(text: str) -> tuple[str, int]:
    """BC-001 — Replace 'from pydantic import BaseSettings' in settings.py."""
    count = 0
    # Replace bare BaseSettings import
    new_text, n = re.subn(
        r"from pydantic import BaseSettings",
        "from pydantic_settings import BaseSettings, SettingsConfigDict",
        text,
    )
    count += n
    # Replace class Config: env_prefix = "X_" with model_config = SettingsConfigDict(env_prefix="X_")
    # Pattern: optional blank lines, then "    class Config:\n        env_prefix = "..."
    new_text, n = re.subn(
        r"\n\s{4}class Config:\s*\n\s{8}env_prefix\s*=\s*(['\"])(.*?)\1",
        r'\n    model_config = SettingsConfigDict(env_prefix=\1\2\1)',
        new_text,
    )
    count += n
    return new_text, count


def _transform_bc002(text: str) -> tuple[str, int]:
    """BC-002 — Rename @validator / @root_validator."""
    count = 0

    # Update imports: add field_validator, model_validator; remove validator, root_validator
    # Replace: from pydantic import ..., validator, root_validator, ...
    def _fix_import(m: re.Match[str]) -> str:
        names_str = m.group(1)
        names = [n.strip() for n in names_str.split(",")]
        has_validator = "validator" in names
        has_root = "root_validator" in names
        names = [n for n in names if n not in ("validator", "root_validator")]
        if has_validator:
            names.append("field_validator")
        if has_root:
            names.append("model_validator")
        names_sorted = sorted(set(names))
        return f"from pydantic import {', '.join(names_sorted)}"

    new_text, n = re.subn(
        r"from pydantic import ([^\n]+)",
        _fix_import,
        text,
    )
    count += n

    # Replace @validator("field") with @field_validator("field") + @classmethod
    # Pattern: @validator(<args>) followed by def <name>(cls, ...):
    def _fix_validator(m: re.Match[str]) -> str:
        indent = m.group(1)
        args = m.group(2)
        func_line = m.group(3)
        return f"{indent}@field_validator({args})\n{indent}@classmethod\n{indent}{func_line}"

    new_text, n = re.subn(
        r"^( *)@validator\(([^)]*)\)\n\1(def \w+.*:)",
        _fix_validator,
        new_text,
        flags=re.MULTILINE,
    )
    count += n

    # Replace @root_validator with @model_validator(mode="after") + @classmethod
    def _fix_root_validator(m: re.Match[str]) -> str:
        indent = m.group(1)
        func_line = m.group(2)
        return f'{indent}@model_validator(mode="after")\n{indent}@classmethod\n{indent}{func_line}'

    new_text, n = re.subn(
        r"^( *)@root_validator\n\1(def \w+.*:)",
        _fix_root_validator,
        new_text,
        flags=re.MULTILINE,
    )
    count += n

    return new_text, count


def _transform_bc003_models(text: str) -> tuple[str, int]:
    """BC-003 — class Config → model_config = ConfigDict(...) in models.py."""
    count = 0

    # Add ConfigDict to pydantic imports if not already present
    def _add_configdict(m: re.Match[str]) -> str:
        names_str = m.group(1)
        names = [n.strip() for n in names_str.split(",")]
        if "ConfigDict" not in names:
            names.append("ConfigDict")
        return f"from pydantic import {', '.join(sorted(set(names)))}"

    new_text, n = re.subn(
        r"from pydantic import ([^\n]+)",
        _add_configdict,
        text,
    )
    count += n

    # Replace:
    #     class Config:
    #         allow_mutation = False
    # With:
    #     model_config = ConfigDict(frozen=True)
    new_text, n = re.subn(
        r"\n( {4})class Config:\s*\n\1    allow_mutation\s*=\s*False",
        r"\n\1model_config = ConfigDict(frozen=True)",
        new_text,
    )
    count += n

    return new_text, count


def _transform_bc004(text: str) -> tuple[str, int]:
    """BC-004 — Field keyword renames."""
    count = 0
    replacements = [
        (r"\bregex=", "pattern="),
        (r"\bmin_items=", "min_length="),
        (r"\bmax_items=", "max_length="),
    ]
    new_text = text
    for pattern, repl in replacements:
        new_text, n = re.subn(pattern, repl, new_text)
        count += n
    return new_text, count


def _transform_bc005(text: str) -> tuple[str, int]:
    """BC-005 — Renamed model methods."""
    count = 0
    replacements = [
        (r"\.parse_obj\(", ".model_validate("),
        (r"\.parse_raw\(", ".model_validate_json("),
        (r"\.dict\(\)", ".model_dump()"),
        (r"\.json\(\)", ".model_dump_json()"),
        (r"\.copy\(", ".model_copy("),
        (r"\.schema\(\)", ".model_json_schema()"),
    ]
    new_text = text
    for pattern, repl in replacements:
        new_text, n = re.subn(pattern, repl, new_text)
        count += n
    return new_text, count


# Map bc_id → (transform_fn, applicable_files_filter)
# The filter is checked against the assigned_files set.
_TRANSFORMS: dict[str, Any] = {
    "BC-001": _transform_bc001,
    "BC-002": _transform_bc002,
    "BC-003": _transform_bc003_models,
    "BC-004": _transform_bc004,
    "BC-005": _transform_bc005,
}


def _bc_applies_to_file(bc_id: str, file_path: str) -> bool:
    """Return True if a given BC transformation should run on this file."""
    fname = Path(file_path).name
    rules: dict[str, list[str]] = {
        "BC-001": ["settings.py"],
        "BC-002": ["models.py"],
        "BC-003": ["models.py"],
        "BC-004": ["models.py"],
        "BC-005": ["service.py"],
    }
    allowed = rules.get(bc_id, [])
    return fname in allowed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_migrations(
    usage_map: dict[str, list[dict[str, Any]]],
    bc_list: list[dict[str, Any]],
    assigned_files: set[str],
) -> list[dict[str, Any]]:
    """Apply migration patches for each BC that has hits in *assigned_files*.

    Returns a list of change records suitable for the upgrade report.
    """
    changes: list[dict[str, Any]] = []

    # Collect unique files that need patching
    files_to_patch: set[str] = set()
    for bc_id, usages in usage_map.items():
        if bc_id == "BC-006":
            continue  # handled by verifier
        for usage in usages:
            if usage["file"] in assigned_files:
                files_to_patch.add(usage["file"])

    # Apply transformations file by file
    for file_path in sorted(files_to_patch):
        path = Path(file_path)
        if not path.exists():
            continue

        original_text = path.read_text(encoding="utf-8")
        current_text = original_text
        applied_bcs: list[str] = []

        # Apply BCs in canonical order
        for bc in sorted(bc_list, key=lambda b: b["id"]):
            bc_id = bc["id"]
            if bc_id == "BC-006":
                continue
            if not _bc_applies_to_file(bc_id, file_path):
                continue
            if bc_id not in _TRANSFORMS:
                continue
            # Only apply if this file has usages for this BC
            if not any(u["file"] == file_path for u in usage_map.get(bc_id, [])):
                continue

            new_text, n_changes = _TRANSFORMS[bc_id](current_text)
            if n_changes > 0:
                current_text = new_text
                applied_bcs.append(bc_id)

        if current_text != original_text:
            path.write_text(current_text, encoding="utf-8")
            for bc_id in applied_bcs:
                for usage in usage_map.get(bc_id, []):
                    if usage["file"] == file_path:
                        changes.append(
                            {
                                "bc_id": bc_id,
                                "file": file_path,
                                "line": usage["line"],
                                "description": f"Applied {bc_id} transformation",
                                "applied": True,
                            }
                        )

    # Handle requirements.txt if in assigned_files
    req_path = "requirements.txt"
    if req_path in assigned_files:
        req = Path(req_path)
        if req.exists():
            text = req.read_text(encoding="utf-8")
            new_text = re.sub(r"pydantic>=1\.10,<2", "pydantic>=2", text)
            if "pydantic-settings" not in new_text:
                new_text = new_text.rstrip() + "\npydantic-settings\n"
            if new_text != text:
                req.write_text(new_text, encoding="utf-8")
                changes.append(
                    {
                        "bc_id": "BC-001",
                        "file": req_path,
                        "line": 1,
                        "description": "Updated pydantic version constraint and added pydantic-settings",
                        "applied": True,
                    }
                )

    # BC-006 — flag as needs_human_review (verifier will fix)
    for usage in usage_map.get("BC-006", []):
        changes.append(
            {
                "bc_id": "BC-006",
                "file": usage["file"],
                "line": usage["line"],
                "reason": "Behavioral change: TypeError → ValidationError (frozen model)",
                "status": "auto-applied",
                "applied": False,
                "needs_human_review": True,
            }
        )

    return changes
