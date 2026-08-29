# Project Documentation Context (Non-Obvious Only)

- `src/uplift_demo/` is a **demo target service** written in pydantic v1 on purpose — it exists to be broken and then repaired by the UpLift agents. It is not the UpLift system itself.
- The UpLift orchestrator/CLI (`src/uplift/`) does not exist yet — it is Task 3 in `BOB_PLAYBOOK.md`.
- `docs/migration-guide.md` is the canonical reference for pydantic v1→v2 breaking changes; it is the changelog-analyst's sole input.
- `reports/` is intentionally empty (only `.gitkeep`) until the agent crew runs — don't assume the JSON files exist.
- `bob_sessions/` stores hackathon evidence screenshots; `BOB_PLAYBOOK.md` has the exact Bob prompts and Bobcoin budget for all six tasks.
- There is no linter, formatter, or CI config — code style is enforced by convention only.
