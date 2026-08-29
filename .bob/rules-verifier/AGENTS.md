# Rules for verifier mode

## Role
Run `python -m pytest`, map failures to breaking-change ids, apply the one
permitted test-assertion fix (BC-006), retry up to 2 times, and write the
final `reports/upgrade-report.json` and `UPGRADE_REPORT.md`.

## Hard Constraints

- **Never touch `src/`.** Source files are owned by code-migrator instances.
  If a failure can only be fixed by changing `src/`, record it in
  `needs_human_review` and stop retrying that item.
- **Write access is limited to:** `tests/`, `reports/`, `UPGRADE_REPORT.md`.
- **Only one test-side fix is pre-approved:** replacing
  `pytest.raises(TypeError)` with `pytest.raises(pydantic.ValidationError)`
  in `tests/test_models.py` for the immutability test (BC-006).
  All other test edits require confidence >= 90%; anything below goes to
  `needs_human_review`.
- **Reference the BC id.** Every test edit must include a comment referencing
  its breaking-change id, e.g. `# BC-006`.
- **Retry budget:** maximum 2 retries after the initial run (3 total runs).

## Permitted Command

```bash
python -m pytest
```

No other commands except `pip show` or `pip list` for diagnostic purposes.

## Failure Mapping

For each test failure, identify the breaking-change id responsible:

| Failure pattern                          | BC id  |
|------------------------------------------|--------|
| `TypeError` on frozen model mutation     | BC-006 |
| Import error: `BaseSettings`             | BC-001 |
| `@validator` / `@root_validator` errors  | BC-002 |
| `class Config` attribute errors          | BC-003 |
| `regex=` / `min_items=` errors           | BC-004 |
| `.dict()` / `.json()` / `.copy()` errors | BC-005 |

## upgrade-report.json Schema

```json
{
  "target": "pydantic",
  "from_version": "1.x",
  "to_version": "2.x",
  "files_modified": ["src/uplift_demo/models.py", "..."],
  "changes": [
    { "bc_id": "BC-001", "file": "src/...", "line": 1,
      "description": "...", "applied": true }
  ],
  "needs_human_review": [
    { "bc_id": "BC-006", "file": "tests/test_models.py", "line": 58,
      "reason": "Behavioral: TypeError -> ValidationError",
      "status": "auto-applied" }
  ],
  "test_runs": [
    { "attempt": 1, "passed": false, "failure_count": 7 },
    { "attempt": 2, "passed": true,  "failure_count": 0 }
  ],
  "final_status": "green"
}
```

## UPGRADE_REPORT.md Must Include

- Files modified (with BC id references)
- All six BC ids and whether each was applied, skipped, or needs-human-review
- Test run history (attempt, pass/fail, failure count)
- `needs_human_review` items with reason and status

## Enforcement

- Any write to `src/` produced by this mode is a critical violation.
  Stop immediately and report the conflict.
- After writing both report files, validate `upgrade-report.json` is
  well-formed JSON before reporting completion.
