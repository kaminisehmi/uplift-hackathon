# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project

**UpLift** — agentic pydantic v1→v2 migration system. IBM TechXchange 2026 Hackathon submission built with IBM Bob IDE + watsonx.ai (Granite).

The demo payload in `src/uplift_demo/` is intentionally written in **pydantic v1** style. It is the migration target — do not "fix" it unless running a migration task.

## Commands

```bash
# Setup
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run all tests (pytest.ini sets pythonpath=src, testpaths=tests)
python -m pytest

# Run a single test
python -m pytest tests/test_models.py::test_discount_cannot_exceed_subtotal

# Demo flow (in order)
python -m pytest                               # green on pydantic v1
pip install "pydantic>=2" pydantic-settings    # simulate Dependabot bump
python -m pytest                               # expected failures
python -m uplift upgrade pydantic             # agent crew migrates
python -m pytest                               # green again
cat UPGRADE_REPORT.md
```

## Stack

- Python 3.12, pydantic `>=1.10,<2` (v1 pinned; upgrading to v2 is the demo)
- `pytest>=8` — only test framework; no extra plugins
- No linter/formatter configured — follow existing style (4-space indent, type hints on all public functions, relative imports within `uplift_demo`)

## Architecture

Four custom Bob modes act as subagents in sequence (4c and 4d run in parallel):

1. **changelog-analyst** — reads `docs/migration-guide.md` → writes `reports/breaking-changes.json`
2. **usage-scanner** — reads `src/` and `tests/` → writes `reports/usage-map.json`
3. **code-migrator** (×2, parallel) — patches `src/uplift_demo/` only; each handles half the breaking-change IDs
4. **verifier** — runs `python -m pytest`; fixes test-side assertions only; reports status

Orchestrator CLI: `python -m uplift upgrade pydantic` (to be built in `src/uplift/`).

JSON contracts between modes:
- `reports/breaking-changes.json` — id, description, old/new API pattern, detection hint
- `reports/usage-map.json` — file:line entries per breaking-change id
- `reports/upgrade-report.json` + `UPGRADE_REPORT.md` — final human-readable output

## Critical Conventions

- **Every patch must reference its breaking-change id** (from `reports/breaking-changes.json`).
- **< 90% confidence → `needs-human-review` list**, never guess.
- `code-migrator` may only edit `src/` and `requirements.txt`; `verifier` may only edit `tests/`.
- No unrelated refactoring — minimal idiomatic diffs only.
- `settings.py` uses `class Config: env_prefix = "UPLIFT_"` (v1); all env vars are prefixed `UPLIFT_`.
- watsonx credentials come **only** from env vars `WATSONX_APIKEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL` — never hardcode.

## Pydantic v1 patterns in use (migration targets)

| File | v1 pattern | v2 replacement |
|------|-----------|----------------|
| `models.py` | `@validator`, `@root_validator` | `@field_validator`, `@model_validator` |
| `models.py` | `Field(regex=...)`, `Field(min_items=...)` | `Field(pattern=...)`, `Field(min_length=...)` |
| `models.py` | `class Config: allow_mutation = False` | `model_config = ConfigDict(frozen=True)` |
| `service.py` | `.parse_obj()`, `.parse_raw()`, `.dict()`, `.json()`, `.copy()`, `.schema()` | `model_validate()`, `model_validate_json()`, `model_dump()`, `model_dump_json()`, `model_copy()`, `model_json_schema()` |
| `settings.py` | `from pydantic import BaseSettings` | `from pydantic_settings import BaseSettings, SettingsConfigDict` |

**Behavioral gotcha (v2):** `frozen=True` raises `pydantic.ValidationError` on mutation; v1 `allow_mutation=False` raised `TypeError`. `test_order_items_are_immutable` asserts `TypeError` — this assertion must be updated to `ValidationError` when migrating.

## Bob-specific

- Bob instance: **ibm-coding-challenge-uat (us-east)**
- `.bobignore` excludes `.venv/`, `__pycache__/`, `.pytest_cache/`, `.git/`, `bob_sessions/`, `*.png`, `*.zip`
- `bob_sessions/` holds task summary screenshots for hackathon evidence — do not delete
- Full task prompts and Bobcoin budget map are in `BOB_PLAYBOOK.md`
