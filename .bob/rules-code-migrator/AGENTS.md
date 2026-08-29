# Rules for code-migrator mode

## Role
Apply the minimal, idiomatic pydantic v2 replacements to the source files
assigned to this instance. Two instances run in parallel on non-overlapping
file sets — never edit a file outside your assigned set.

## File Ownership Split

| Instance    | Assigned Files                                                          |
|-------------|-------------------------------------------------------------------------|
| Migrator A  | `src/uplift_demo/models.py`                                             |
| Migrator B  | `src/uplift_demo/settings.py`, `src/uplift_demo/service.py`, `requirements.txt` |

Each instance receives its assigned_files list at startup.
**Never write to a file not in your assigned set.**

## Hard Constraints

- **Never touch `tests/`.** Not for any reason, not for any BC id.
  `tests/` is owned exclusively by the verifier mode.
- **Only modify your assigned files.** Reading any file is fine.
- **Reference the BC id.** Every changed line (or the immediately preceding
  comment) must include the breaking-change id it implements, e.g.:
  ```python
  # BC-002
  @field_validator("name")
  @classmethod
  def validate_name(cls, v): ...
  ```
- **Confidence threshold.** If your confidence in a transformation is below
  90%, do NOT apply the patch. Instead append the item to
  `reports/upgrade-report.json` → `needs_human_review` with the reason.
- **Minimal diffs only.** Do not rename variables, reformat surrounding code,
  add imports beyond what the new pattern requires, or make any change not
  demanded by the usage-map entry.
- **No unrelated refactoring.** If a line has a style issue unrelated to the
  migration, leave it alone.

## Per-BC Transformation Rules

Apply only the rules that have hits in your assigned files (from usage-map.json).

| BC id  | Old pattern                              | New pattern                                      |
|--------|------------------------------------------|--------------------------------------------------|
| BC-001 | `from pydantic import BaseSettings`      | `from pydantic_settings import BaseSettings, SettingsConfigDict` |
| BC-001 | `class Config: env_prefix = "..."`       | `model_config = SettingsConfigDict(env_prefix="...")` |
| BC-002 | `@validator("field")`                    | `@field_validator("field")` + `@classmethod`     |
| BC-002 | `@root_validator`                        | `@model_validator(mode="after")`                 |
| BC-003 | `class Config: allow_mutation = False`   | `model_config = ConfigDict(frozen=True)`         |
| BC-004 | `Field(regex=...)`                       | `Field(pattern=...)`                             |
| BC-004 | `Field(min_items=...)`                   | `Field(min_length=...)`                          |
| BC-005 | `.dict()`                                | `.model_dump()`                                  |
| BC-005 | `.json()`                                | `.model_dump_json()`                             |
| BC-005 | `.copy()`                                | `.model_copy()`                                  |
| BC-005 | `.schema()`                              | `.model_json_schema()`                           |
| BC-005 | `.parse_obj(...)`                        | `Model.model_validate(...)`                      |
| BC-005 | `.parse_raw(...)`                        | `Model.model_validate_json(...)`                 |
| BC-006 | (behavioral — TypeError vs ValidationError) | DO NOT PATCH. Add to needs_human_review only. |

## Report Obligation

After each file is patched, append to `reports/upgrade-report.json` →
`changes` array:
```json
{ "bc_id": "BC-XXX", "file": "src/...", "line": <int>,
  "description": "<what changed>", "applied": true }
```

## Enforcement

- Patches to `tests/` are a critical violation — stop and report.
- Patches outside assigned_files are a critical violation — stop and report.
- Any patch lacking a BC id comment must be rejected before committing.
