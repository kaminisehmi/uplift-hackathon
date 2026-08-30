# Bob task session evidence

This folder contains the IBM Bob task session evidence for the UpLift
submission, as required by the hackathon guide.

## JSON exports (machine-verifiable)

One file per Bob task, exported directly from Bob IDE (Tasks → task header →
Export → JSON). Each export contains the task id, workspace, prompt, todo
states, full message log, and the `costs` block (Bobcoins consumed and
context-token breakdown) — the same data shown in the task session
consumption summary panel.

| # | File | Task | Bobcoins |
|---|------|------|----------|
| 0 | `kamini_task00_init_summary.json` | `/init` — AGENTS.md context | 0.527 |
| 1 | `kamini_task01_plan_summary.json` | Plan mode — architecture (create-plan skill + explore subagent) | 0.412 |
| 2 | `kamini_task02_custom_modes_and_scanner_summary.json` | Four custom modes + rules; usage scan (15 sites) | 1.709 |
| 3 | `kamini_task03_orchestrator_summary.json` | UpLift orchestrator + 61 unit tests | 2.262 |
| 4a | `kamini_task04a_changelog_analyst_summary.json` | Changelog Analyst mode → breaking-changes.json | 0.183 |
| 4c | `kamini_task04c_migrator_a_models_summary.json` | Code Migrator A (models.py) — ran in parallel with 4d | 0.180 |
| 4d | `kamini_task04d_migrator_b_settings_service_summary.json` | Code Migrator B (settings.py + service.py + requirements.txt) — ran in parallel with 4c | 0.146 |
| 4e | `kamini_task04e_verifier_green_summary.json` | Verifier mode — BC-006 fix, 77/77 green | 0.431 |
| 5 | `kamini_task05_orchestrate_granite_summary.json` | watsonx Orchestrate ADK + Granite integration | 0.519 |
| 6 | `kamini_task06_final_readme_summary.json` | Final README with measured impact | 0.265 |

**Total: ≈6.63 Bobcoins of the 40 allocated (≈17%).**

Parallel-task evidence: tasks 4c and 4d carry overlapping timestamps in their
exports — both were running simultaneously in two Bob chat panels.

## Screenshots

PNG screenshots of the task session consumption summaries (same panels the
JSON was exported from) accompany these files per the submission guide.
