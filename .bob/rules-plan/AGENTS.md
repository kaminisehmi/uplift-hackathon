# Project Architecture Rules (Non-Obvious Only)

- Four custom Bob modes are the architectural units: changelog-analyst → usage-scanner → code-migrator (×2, parallel) → verifier. They are sequential except 4c/4d which run in parallel.
- JSON contracts between modes are the strict interface: `reports/breaking-changes.json` (analyst output), `reports/usage-map.json` (scanner output), `reports/upgrade-report.json` + `UPGRADE_REPORT.md` (final output).
- `code-migrator` is stateless per breaking-change group — the orchestrator drives retry (up to 2 retries per group) by re-running pytest and re-invoking the migrator.
- Mode permissions are intentionally restrictive: changelog-analyst is read-only; usage-scanner is read-only; code-migrator cannot touch `tests/`; verifier cannot touch `src/` source files.
- `src/uplift_demo/` is v1 pydantic by design — the migration is the demo. `src/uplift/` (the orchestrator) must be written in v2 style from the start.
- watsonx Orchestrate integration lives in `orchestrate/` (Task 5); it is a separate concern from the Bob-based agent crew (Tasks 2–4).
- `Optional[X]` fields without a default become required in pydantic v2 — relevant when adding new fields to `uplift_demo` models.
