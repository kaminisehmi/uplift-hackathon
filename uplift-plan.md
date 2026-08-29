# UpLift — Agentic Pydantic v1→v2 Migration System: Implementation Plan

## Top-Level Overview

**Goal:** Build an end-to-end agentic upgrade system that, given a target library bump (pydantic v1→v2), autonomously reads migration docs, detects every affected usage site, patches the source, iterates until tests are green, and produces a human-readable report.

**Scope:**
- Four custom Bob modes as sequential subagents with restricted permissions
- One orchestrator CLI (`python -m uplift upgrade pydantic`) that drives them
- Three JSON contract files (`reports/breaking-changes.json`, `reports/usage-map.json`, `reports/upgrade-report.json`) as the strict inter-mode interface
- Demo payload lives in `src/uplift_demo/` (pydantic v1 intentionally); orchestrator lives in `src/uplift/` (pydantic v2 from the start)

**Non-goals:** No watsonx Orchestrate integration in this plan (Task 5 is separate). No changes to `tests/` except by the `verifier` mode. No style cleanup unrelated to migration.

---

## Architecture Overview

```
docs/migration-guide.md
        │
        ▼
┌─────────────────────┐
│  changelog-analyst  │  read-only; writes breaking-changes.json
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│   usage-scanner     │  read-only; writes usage-map.json
└─────────────────────┘
        │
   ┌────┴────┐
   │         │  (parallel)
   ▼         ▼
┌──────┐  ┌──────┐
│ code │  │ code │  edits src/ + requirements.txt only
│  -   │  │  -   │
│migr. │  │migr. │
└──────┘  └──────┘
   │         │
   └────┬────┘
        ▼
┌─────────────────────┐
│      verifier       │  runs pytest; edits tests/ only
└─────────────────────┘
        │
        ▼
 reports/upgrade-report.json
 UPGRADE_REPORT.md
```

---

## JSON Contract Schemas

### `reports/breaking-changes.json`

Produced by `changelog-analyst`. Consumed by `usage-scanner` and `code-migrator`.

```jsonc
[
  {
    "id": "BC-001",                        // stable short identifier
    "title": "BaseSettings moved",         // human label
    "description": "...",                  // prose from migration guide
    "detection_hint": "from pydantic import BaseSettings",  // regex / AST pattern
    "old_pattern": "from pydantic import BaseSettings",
    "new_pattern": "from pydantic_settings import BaseSettings, SettingsConfigDict",
    "confidence_required": 0.9             // threshold below which → needs-human-review
  }
]
```

Known IDs (one per breaking-change category in `docs/migration-guide.md`):
- `BC-001` BaseSettings moved
- `BC-002` @validator / @root_validator renamed
- `BC-003` class Config → model_config / ConfigDict
- `BC-004` Field keyword renames (regex→pattern, min_items→min_length)
- `BC-005` Renamed model methods (.dict, .json, .copy, .schema, .parse_obj, .parse_raw)
- `BC-006` Behavioral changes (frozen raises ValidationError not TypeError; Optional without default)

### `reports/usage-map.json`

Produced by `usage-scanner`. Consumed by `code-migrator` (both instances).

```jsonc
{
  "BC-001": [
    { "file": "src/uplift_demo/settings.py", "line": 1, "snippet": "from pydantic import BaseSettings" }
  ],
  "BC-002": [
    { "file": "src/uplift_demo/models.py", "line": 8, "snippet": "@validator(\"name\")" },
    { "file": "src/uplift_demo/models.py", "line": 30, "snippet": "@root_validator" }
  ]
  // ... one key per BC id
}
```

### `reports/upgrade-report.json`

Produced by `verifier` (populated incrementally). Consumed by the README generator.

```jsonc
{
  "target": "pydantic",
  "from_version": "1.x",
  "to_version": "2.x",
  "files_modified": ["src/uplift_demo/models.py", "src/uplift_demo/service.py", "..."],
  "changes": [
    {
      "bc_id": "BC-001",
      "file": "src/uplift_demo/settings.py",
      "line": 1,
      "description": "Replaced BaseSettings import",
      "applied": true
    }
  ],
  "needs_human_review": [
    { "bc_id": "BC-006", "file": "tests/test_models.py", "line": 58, "reason": "Behavioral change: TypeError → ValidationError", "status": "auto-applied" }
  ],
  "test_runs": [
    { "attempt": 1, "passed": false, "failure_count": 7 },
    { "attempt": 2, "passed": true,  "failure_count": 0 }
  ],
  "final_status": "green"
}
```

---

## Sub-Tasks

---

### Sub-Task 1 — Create the Four Custom Bob Modes

**Intent:** Define the four agent personas with their permission sets and role instructions. Each mode is a distinct Bob custom mode saved in the project's `.bob/custom_modes.yaml`.

**Expected Outcomes:**
- `.bob/custom_modes.yaml` contains four mode entries: `changelog-analyst`, `usage-scanner`, `code-migrator`, `verifier`
- Each mode has: correct `roleDefinition`, the right `allowedTools` restricted to its permission tier, and project rules referencing `AGENTS.md`
- Modes are selectable from the Bob mode switcher

**Todo List:**
1. Read `.bob/` directory to understand any existing custom mode configuration
2. Define `changelog-analyst`: read-only tools only; role = parse migration guide and emit `reports/breaking-changes.json`; cannot write source files
3. Define `usage-scanner`: read-only tools only; role = scan `src/` and `tests/` for usage patterns and emit `reports/usage-map.json`; cannot write source files
4. Define `code-migrator`: read + write tools for `src/` and `requirements.txt` only; explicitly prohibited from touching `tests/`; receives a `bc_ids` split so two instances can work on non-overlapping IDs; references `reports/breaking-changes.json` and `reports/usage-map.json`
5. Define `verifier`: read + write tools for `tests/` only; can run `python -m pytest`; cannot touch `src/`; writes `reports/upgrade-report.json` and `UPGRADE_REPORT.md`
6. Write the complete `.bob/custom_modes.yaml`

**Relevant Context:**
- `AGENTS.md` — permission matrix and mode descriptions
- `.bob/` — existing Bob configuration directory
- Bob custom modes schema: `roleDefinition`, `allowedTools` (groups), `customInstructions`

**Status:** `[ ] pending`

---

### Sub-Task 2 — Scaffold the Orchestrator Package (`src/uplift/`)

**Intent:** Create the `src/uplift/` Python package with a `__main__.py` entry point so `python -m uplift upgrade pydantic` is a valid command. This is the driver that sequences the four modes, passes context between them, and controls retry logic.

**Expected Outcomes:**
- `src/uplift/__init__.py` exists
- `src/uplift/__main__.py` parses `upgrade <library>` subcommand
- `src/uplift/orchestrator.py` contains the sequencing logic (calls modes in order, manages retry loop)
- Running `python -m uplift upgrade pydantic --help` prints usage without error
- No watsonx integration yet (that is Task 5); mode invocations are stubs in this sub-task

**Todo List:**
1. Create `src/uplift/__init__.py` with package docstring
2. Create `src/uplift/__main__.py` using `argparse` with subcommand `upgrade <library>`; validate that the library arg is supported
3. Create `src/uplift/orchestrator.py` with:
   - `run_changelog_analyst()` — stub that checks for `reports/breaking-changes.json`
   - `run_usage_scanner()` — stub that checks for `reports/usage-map.json`
   - `run_code_migrators(bc_ids_split)` — stub for parallel execution of two migrator instances
   - `run_verifier(attempt, max_retries=2)` — stub that invokes `python -m pytest` and reads result; loops up to `max_retries`
   - `upgrade(library)` — top-level coordinator calling the above in sequence
4. Write `tests/test_orchestrator.py` with minimal unit tests: argument parsing, retry counter logic, `needs_human_review` passthrough

**Relevant Context:**
- `pytest.ini` — `pythonpath = src`, `testpaths = tests`
- `AGENTS.md` — orchestrator must be written in pydantic v2 style
- `requirements.txt` — may add `pydantic>=2`, `pydantic-settings` here for the orchestrator package only (the demo payload stays on v1 until migration)

**Status:** `[ ] pending`

---

### Sub-Task 3 — Implement `changelog-analyst` Logic

**Intent:** Implement the actual `run_changelog_analyst()` function that reads `docs/migration-guide.md` and writes a well-structured `reports/breaking-changes.json` covering all six breaking-change categories.

**Expected Outcomes:**
- `reports/breaking-changes.json` is written with exactly six entries (BC-001 through BC-006) matching the schema above
- Each entry has `id`, `title`, `description`, `detection_hint`, `old_pattern`, `new_pattern`, `confidence_required`
- A unit test verifies the schema of the output

**Todo List:**
1. Create `src/uplift/analyst.py` with `extract_breaking_changes(guide_path) -> list[dict]`
2. Implement parsing of `docs/migration-guide.md`: iterate over H2 sections, extract code fences as old/new patterns, derive `detection_hint` from the old pattern
3. Hardcode `confidence_required` per category: BC-006 (behavioral) = 0.7; all others = 0.95
4. Write the result to `reports/breaking-changes.json`
5. Wire `run_changelog_analyst()` in `orchestrator.py` to call `analyst.extract_breaking_changes()`
6. Add tests for `extract_breaking_changes()` covering schema validity and all six IDs being present

**Relevant Context:**
- `docs/migration-guide.md` — the input; six H2 sections, each with before/after code fences
- `reports/breaking-changes.json` — target output path
- `src/uplift/orchestrator.py` — caller

**Status:** `[ ] pending`

---

### Sub-Task 4 — Implement `usage-scanner` Logic

**Intent:** Implement `run_usage_scanner()` that reads `reports/breaking-changes.json` and scans `src/` and `tests/` for every line matching each breaking change's `detection_hint`, writing `reports/usage-map.json`.

**Expected Outcomes:**
- `reports/usage-map.json` written with at least one entry per BC id that has known usages
- Known usages captured: all six patterns in `models.py`/`service.py`/`settings.py` plus the `TypeError` assertion in `tests/test_models.py`
- A unit test verifies the map contains expected file:line pairs for a fixture input

**Todo List:**
1. Create `src/uplift/scanner.py` with `scan_usages(bc_list, root_dirs) -> dict`
2. Implement: for each breaking change, compile `detection_hint` as a regex; walk `root_dirs`; record `{file, line, snippet}` for each match
3. Handle multi-line patterns (e.g., `@root_validator` may appear with `@validator` nearby): emit one entry per matched line
4. Write result to `reports/usage-map.json`
5. Wire `run_usage_scanner()` in `orchestrator.py`
6. Add tests with a temporary source tree fixture confirming all expected hits are found

**Relevant Context:**
- `reports/breaking-changes.json` — source of detection hints
- `src/uplift_demo/models.py`, `src/uplift_demo/service.py`, `src/uplift_demo/settings.py`, `tests/test_models.py` — the files that will be scanned
- BC-006 behavioral change: `detection_hint` should target the `TypeError` assertion in `tests/test_models.py` line 58

**Status:** `[ ] pending`

---

### Sub-Task 5 — Implement `code-migrator` Logic (Two Parallel Instances)

**Intent:** Implement the actual patching logic that reads `reports/usage-map.json`, applies the correct v2 replacement for each usage site, and records each change. Two instances run in parallel, each owning a disjoint set of **files** — ensuring no two migrators ever write the same file simultaneously.

**File ownership split:**
- **Migrator A** — owns `src/uplift_demo/models.py` only (BC-002, BC-003, BC-004 apply here)
- **Migrator B** — owns `src/uplift_demo/settings.py` + `src/uplift_demo/service.py` + `requirements.txt` (BC-001, BC-003, BC-005 apply here)

No BC id is split across migrators — each migrator applies whichever BCs have hits in its assigned files.

**Expected Outcomes:**
- `src/uplift_demo/models.py`, `service.py`, `settings.py` are patched to pydantic v2 syntax
- `requirements.txt` is updated from `pydantic>=1.10,<2` to `pydantic>=2` and adds `pydantic-settings`
- Each patch is annotated with its `bc_id` in the report
- Running `python -m pytest` after patching has only the one known remaining failure (`TypeError` → `ValidationError` in `tests/test_models.py`)
- `reports/upgrade-report.json` `changes` array is populated

**Todo List:**
1. Create `src/uplift/migrator.py` with `apply_migrations(usage_map, bc_list, assigned_files) -> list[dict]`; the `assigned_files` parameter is a set of file paths this instance is permitted to modify
2. Implement per-BC transformation rules (one function per BC id):
   - BC-001: replace `from pydantic import BaseSettings` + `class Config: env_prefix` → `SettingsConfigDict` (applies in `settings.py`)
   - BC-002: rewrite `@validator(...)` → `@field_validator(...)` with `@classmethod`; `@root_validator` → `@model_validator(mode="after")` (applies in `models.py`)
   - BC-003: rewrite `class Config: allow_mutation = False` → `model_config = ConfigDict(frozen=True)` in `models.py`; `class Config: env_prefix` → `SettingsConfigDict` already covered by BC-001 in `settings.py`
   - BC-004: rename `regex=` → `pattern=`, `min_items=` → `min_length=` (applies in `models.py`)
   - BC-005: rename all six method calls (`.dict()`, `.json()`, `.copy()`, `.schema()`, `.parse_obj()`, `.parse_raw()`) (applies in `service.py`)
   - BC-006: flag `TypeError` assertion in `tests/test_models.py` as `needs_human_review`; migrator does NOT touch `tests/`; verifier handles it
3. Implement `file_split() -> (set_a, set_b)` returning the two disjoint file-ownership sets described above
4. Wire `run_code_migrators()` in `orchestrator.py` to call both instances with their respective `assigned_files`; use `concurrent.futures.ThreadPoolExecutor` for parallelism
5. After patching, append to `reports/upgrade-report.json`
6. Add unit tests for each transformation rule against a string fixture

**Relevant Context:**
- `src/uplift_demo/models.py` — lines 1–45 (BC-002, BC-003, BC-004 targets; Migrator A)
- `src/uplift_demo/service.py` — lines 1–38 (BC-005 targets; Migrator B)
- `src/uplift_demo/settings.py` — lines 1–13 (BC-001, BC-003 targets; Migrator B)
- `requirements.txt` — version constraint update; owned by Migrator B
- BC-006 is flagged but NOT patched by either migrator; it goes to `needs_human_review`

**Status:** `[ ] pending`

---

### Sub-Task 6 — Implement `verifier` Logic and Report Generation

**Intent:** Implement `run_verifier()` which runs `python -m pytest`, parses the result, applies any test-side assertion fixes (only `tests/test_models.py` line 58: `TypeError` → `ValidationError`), retries up to 2 times, and writes the final `reports/upgrade-report.json` + `UPGRADE_REPORT.md`.

**Expected Outcomes:**
- After verifier completes, `python -m pytest` exits 0
- `reports/upgrade-report.json` contains complete `test_runs`, `changes`, `needs_human_review`, `final_status: "green"`
- `UPGRADE_REPORT.md` is written with: files changed, breaking changes applied, test run history, needs-human-review items
- `run_verifier()` returns `True` on green, `False` (or raises) if still red after max retries

**Todo List:**
1. Create `src/uplift/verifier.py` with `run_pytest() -> (bool, int)` that calls `subprocess.run(["python", "-m", "pytest"])` and parses exit code + failure count
2. Implement `fix_test_assertions(needs_human_review_list)`: for each flagged item in `tests/`, apply the known behavioral fix (BC-006: replace `pytest.raises(TypeError)` with `pytest.raises(ValidationError)` at the flagged line)
3. Implement `run_verifier(max_retries=2)` retry loop: run pytest → if failing and retries remain → attempt test fix → retry
4. Implement `write_upgrade_report(report_data)` that writes both `reports/upgrade-report.json` and `UPGRADE_REPORT.md`
5. Wire into `orchestrator.py`
6. Add tests: mock `subprocess.run`; verify retry logic; verify report schema

**Relevant Context:**
- `tests/test_models.py` line 58 — the one test assertion that must change (`TypeError` → `ValidationError`) — this is the only `tests/` edit in the entire migration
- BC-006 fix is **auto-applied** by the verifier AND recorded in `needs_human_review` with `"status": "auto-applied"` so it remains visible in the report
- `reports/upgrade-report.json` schema — defined in the JSON Contracts section above
- `AGENTS.md` — verifier may only edit `tests/`; cannot touch `src/`

**Status:** `[ ] pending`

---

### Sub-Task 7 — End-to-End Integration and Demo Validation

**Intent:** Wire all sub-tasks together, validate the full demo script runs green, and confirm all output artifacts are correct.

**Expected Outcomes:**
- `python -m pytest` is green on pydantic v1 (baseline)
- After `pip install "pydantic>=2" pydantic-settings`, `python -m pytest` fails (expected)
- `python -m uplift upgrade pydantic` runs without error, produces all three report files + `UPGRADE_REPORT.md`
- `python -m pytest` is green on pydantic v2 after the migration
- `cat UPGRADE_REPORT.md` shows a well-formatted summary

**Todo List:**
1. Run baseline `python -m pytest` and confirm all 10 tests pass on pydantic v1
2. Bump pydantic to v2 in a scratch `requirements.txt` and confirm test failures appear
3. Run `python -m uplift upgrade pydantic` end-to-end
4. Confirm `reports/breaking-changes.json`, `reports/usage-map.json`, `reports/upgrade-report.json` all exist and are schema-valid
5. Run `python -m pytest` and confirm green
6. Review `UPGRADE_REPORT.md` for completeness: all six BC ids, correct file:line references, `needs_human_review` list containing at least BC-006

**Relevant Context:**
- `BOB_PLAYBOOK.md` — demo script and evidence requirements
- All `src/uplift_demo/` files — the migration targets
- `pytest.ini` — test configuration

**Status:** `[ ] pending`

---

## File Manifest (Files to Create)

| File | Created By | Purpose |
|------|------------|---------|
| `.bob/custom_modes.yaml` | Sub-Task 1 | Four custom Bob mode definitions |
| `src/uplift/__init__.py` | Sub-Task 2 | Package marker |
| `src/uplift/__main__.py` | Sub-Task 2 | CLI entry point (`python -m uplift`) |
| `src/uplift/orchestrator.py` | Sub-Task 2 | Top-level sequencer + retry loop |
| `src/uplift/analyst.py` | Sub-Task 3 | Parse migration-guide.md → breaking-changes.json |
| `src/uplift/scanner.py` | Sub-Task 4 | Scan src/ + tests/ → usage-map.json |
| `src/uplift/migrator.py` | Sub-Task 5 | Apply per-BC patches to src/uplift_demo/ |
| `src/uplift/verifier.py` | Sub-Task 6 | Run pytest, fix test assertions, write reports |
| `tests/test_orchestrator.py` | Sub-Task 2 | Unit tests: CLI parsing, retry logic |
| `tests/test_analyst.py` | Sub-Task 3 | Unit tests: schema validity, all 6 IDs |
| `tests/test_scanner.py` | Sub-Task 4 | Unit tests: expected file:line hits |
| `tests/test_migrator.py` | Sub-Task 5 | Unit tests: per-BC transformation rules |
| `tests/test_verifier.py` | Sub-Task 6 | Unit tests: retry logic, report schema |
| `reports/breaking-changes.json` | Sub-Task 3 | Analyst output (BC-001..BC-006) |
| `reports/usage-map.json` | Sub-Task 4 | Scanner output (file:line per BC id) |
| `reports/upgrade-report.json` | Sub-Task 6 | Verifier output (full run summary) |
| `UPGRADE_REPORT.md` | Sub-Task 6 | Human-readable upgrade summary |

## Files Modified (Existing)

| File | Modified By | Migrator | Change |
|------|-------------|----------|--------|
| `requirements.txt` | Sub-Task 5 | Migrator B | `pydantic>=1.10,<2` → `pydantic>=2`; add `pydantic-settings` |
| `src/uplift_demo/models.py` | Sub-Task 5 | Migrator A | Apply BC-002, BC-003, BC-004 patches |
| `src/uplift_demo/service.py` | Sub-Task 5 | Migrator B | Apply BC-005 patches |
| `src/uplift_demo/settings.py` | Sub-Task 5 | Migrator B | Apply BC-001, BC-003 patches |
| `tests/test_models.py` | Sub-Task 6 | verifier | BC-006: `TypeError` → `ValidationError` on line 58 (auto-applied + listed in needs_human_review) |

---

## Permission Matrix (Enforced by Mode Restrictions)

| Mode | Read src/ | Write src/ | Read tests/ | Write tests/ | Run pytest | Write reports/ |
|------|-----------|------------|-------------|--------------|------------|----------------|
| changelog-analyst | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| usage-scanner | ✓ | ✗ | ✓ | ✗ | ✗ | ✓ |
| code-migrator | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ |
| verifier | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
