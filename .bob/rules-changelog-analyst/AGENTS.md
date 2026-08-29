# Rules for changelog-analyst mode

## Role
Parse `docs/migration-guide.md` and emit `reports/breaking-changes.json`.
Do nothing else.

## Hard Constraints

- **Read only.** You may read `docs/`, `reports/`, and root-level planning
  files (e.g., `uplift-plan.md`, `AGENTS.md`). You must not open or stat any
  file under `src/` or `tests/`.
- **Single output.** Write exactly one file: `reports/breaking-changes.json`.
  Do not create, modify, or delete any other file.
- **No speculation.** Every field you write must be directly grounded in text
  you read from `docs/migration-guide.md`. If the guide does not mention
  something, do not invent it.

## Output Schema (strictly enforced)

```json
[
  {
    "id": "BC-001",
    "title": "<short label>",
    "description": "<prose from migration guide>",
    "old_pattern": "<v1 import or usage>",
    "new_pattern": "<v2 replacement>",
    "detection_hint": "<regex or import signature for scanner>",
    "confidence_required": 0.95
  }
]
```

- Exactly six entries: BC-001 through BC-006.
- `confidence_required` = 0.95 for BC-001 through BC-005.
- `confidence_required` = 0.70 for BC-006 (behavioral change).

## Known ID Assignment

| ID     | Category                                      |
|--------|-----------------------------------------------|
| BC-001 | BaseSettings moved to pydantic-settings       |
| BC-002 | @validator / @root_validator renamed          |
| BC-003 | class Config removed (model_config/ConfigDict)|
| BC-004 | Field keyword renames (regex, min_items)      |
| BC-005 | Renamed model methods (.dict, .json, etc.)    |
| BC-006 | Behavioral: frozen raises ValidationError     |

## Enforcement

- Any patch to `src/` or `tests/` produced by this mode is a critical
  violation. Stop immediately and report the conflict.
- Every breaking-change id must reference the exact section of
  `docs/migration-guide.md` it was derived from (use `description`).
