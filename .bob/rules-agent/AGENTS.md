# Project Coding Rules (Non-Obvious Only)

- `src/uplift_demo/` is **intentionally v1** — do not migrate it unless the current task is a migration task (code-migrator mode or Task 4).
- Every code patch to `uplift_demo/` must include the breaking-change id (from `reports/breaking-changes.json`) in a comment or commit message.
- Put anything under 90% confidence in a `needs-human-review` list instead of guessing.
- `code-migrator` mode may only write to `src/` and `requirements.txt`; `verifier` mode may only write to `tests/`.
- `settings.py` uses `UPLIFT_` env prefix — new settings fields get the same prefix automatically.
- The `test_order_items_are_immutable` test asserts `TypeError`; after v2 migration this must change to `pydantic.ValidationError` (frozen model raises `ValidationError`, not `TypeError`).
- `pytest.ini` sets `pythonpath = src` — test imports use bare package names (`from uplift_demo.models import ...`), not relative paths.
- No linter/formatter is configured — follow 4-space indent, type hints on all public functions, relative imports within `uplift_demo`.
- watsonx credentials come only from env vars `WATSONX_APIKEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`.
