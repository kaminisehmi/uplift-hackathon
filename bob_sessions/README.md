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
| 6 | `kamini_task06_final_readme_and_dashboard_summary.json` | Final README + self-contained live dashboard | 2.38 |
| 7 | `kamini_task07_force_flag_streaming_dashboard_summary.json` | --force live pipeline flag + streaming dashboard runner (86 tests green) | 2.13 |

**Total: ≈10.88 Bobcoins of the 40 allocated (≈27%)** — including demo-polish tasks.

Parallel-task evidence: tasks 4c and 4d carry overlapping timestamps in their
exports — both were running simultaneously in two Bob chat panels.

---

## ⚠️  REQUIRED: take PNG screenshots now (4 steps, ~5 minutes total)

The hackathon guide specifically asks for task session **screenshots** in
`bob_sessions/`. The JSON exports contain all the same data and are
machine-verifiable, but the letter of the requirement is a PNG per task.

**One-time setup (macOS):**
PNG auto-saves to the Desktop by default (`Cmd+Shift+3`), or use
`Cmd+Shift+4` to select a region.

**For each task below, open the task in Bob IDE, scroll to the
session consumption summary (Bobcoin panel at the bottom), and screenshot:**

```
Task 0  →  kamini_task00_init_summary.png
Task 1  →  kamini_task01_plan_summary.png
Task 2  →  kamini_task02_custom_modes_and_scanner_summary.png
Task 3  →  kamini_task03_orchestrator_summary.png
Task 4c →  kamini_task04c_migrator_a_models_summary.png          ← shows parallel run
Task 4d →  kamini_task04d_migrator_b_settings_service_summary.png ← shows parallel run
Task 4e →  kamini_task04e_verifier_green_summary.png
Task 5  →  kamini_task05_orchestrate_granite_summary.png
Task 6  →  kamini_task06_final_readme_and_dashboard_summary.png
Task 7  →  kamini_task07_force_flag_streaming_dashboard_summary.png
```

Move the PNGs from your Desktop into this `bob_sessions/` folder.
Note: `.bobignore` excludes `*.png` to keep Bob's context window clean —
the files are still committed to git and visible to judges.

**Highest-value screenshots** (if time is short, grab these first):
1. `kamini_task03_orchestrator_summary.png` — most Bobcoins, most capability shown
2. `kamini_task04c/4d` pair — proves parallel subagent execution
3. `kamini_task02` — proves custom mode creation
4. `kamini_task07` — proves the --force live pipeline demo feature

---

## Screenshots (add filenames here as you take them)

<!-- Update this list as you take screenshots -->
- [ ] kamini_task00_init_summary.png
- [ ] kamini_task01_plan_summary.png
- [ ] kamini_task02_custom_modes_and_scanner_summary.png
- [ ] kamini_task03_orchestrator_summary.png
- [ ] kamini_task04c_migrator_a_models_summary.png
- [ ] kamini_task04d_migrator_b_settings_service_summary.png
- [ ] kamini_task04e_verifier_green_summary.png
- [ ] kamini_task05_orchestrate_granite_summary.png
- [ ] kamini_task06_final_readme_and_dashboard_summary.png
- [ ] kamini_task07_force_flag_streaming_dashboard_summary.png
