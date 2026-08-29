# Rules for usage-scanner mode

## Role
Read `reports/breaking-changes.json`, scan `src/` and `tests/` for every line
matching each `detection_hint`, and write `reports/usage-map.json`.

## Hard Constraints

- **Read only on source.** You may read any file under `src/`, `tests/`,
  `reports/`, and `docs/`. You must not modify any source file.
- **Single output.** Write exactly one file: `reports/usage-map.json`.
- **No fabrication.** If a `detection_hint` regex matches nothing, emit an
  empty list for that id — never fabricate a hit.
- **One entry per matched line.** Do not collapse multiple matching lines into
  a single entry.

## Output Schema (strictly enforced)

```json
{
  "BC-001": [
    { "file": "src/uplift_demo/settings.py", "line": 1,
      "snippet": "from pydantic import BaseSettings" }
  ],
  "BC-002": []
}
```

- Top-level keys are BC ids exactly as they appear in `breaking-changes.json`.
- All six ids must be present as keys (empty list if no match).
- `file` paths are relative to the workspace root.
- `line` is 1-based.

## Scan Scope

- Include all `.py` files under `src/` and `tests/`.
- Do not scan `.venv/`, `__pycache__/`, `.git/`, or `bob_sessions/`.

## Enforcement

- Any modification to `src/` or `tests/` produced by this mode is a critical
  violation. Stop immediately and report the conflict.
- After writing `usage-map.json`, verify the file is valid JSON before
  reporting completion.
