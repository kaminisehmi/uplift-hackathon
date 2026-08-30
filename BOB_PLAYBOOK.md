# BOB_PLAYBOOK — exact prompts to paste into IBM Bob IDE (Bobcoin-optimized)

Everything in this repo was pre-scaffolded so that **every Bobcoin is spent on
work that (a) produces a `bob_sessions/` screenshot or (b) showcases an
agentic feature judges score**. Do not chat with Bob — paste one prompt,
let it finish, screenshot the task summary, move on.

## Token-saving rules (read once, follow always)

1. **One prompt per task, no follow-up chat.** Refine wording BEFORE pasting.
2. **New context window / new task for each numbered step below.** Never
   continue a long conversation — context resends cost coins.
3. `.bobignore` is already set up (venv, caches, screenshots excluded).
4. Point Bob at files with `@` mentions instead of letting it explore.
5. Check Bobcoin usage in Settings → General after each task. If a task ate
   more than ~15%, shrink the next one's scope.
6. Screenshot the task session summary IMMEDIATELY after each task:
   `bob_sessions/<team>_task0N_<short-desc>_summary.png`.
7. Make sure the selected instance is **ibm-coding-challenge-uat (us-east)**.
8. If working as a team: each member runs a different block below on their
   own 40-coin allocation (and gets their own screenshots).

## Budget map (solo, ~40 coins)

| Task | What | Budget |
|---|---|---|
| 0 | `/init` | ~2% |
| 1 | Plan mode: architecture | ~13% |
| 2 | Custom modes + rules | ~10% |
| 3 | Orchestrator (Code mode) | ~25% |
| 4a–4e | Parallel subagent runs | ~25% |
| 5 | Orchestrate/ADK + Granite | ~10% |
| 6 | Review + README polish | ~5% |
| — | Reserve for one retry | ~10% |

If coins run low: Tasks 0–4 are the must-haves. Task 5 can be done in the
Orchestrate no-code UI (spends cloud credit, not Bobcoins). Task 6 by hand.

---

## Task 0 — project context (cheap, do first)

Type in Bob chat:

    /init

## Task 1 — PLAN MODE (switch Bob to Plan mode first)

    I'm building "UpLift", an agentic system that performs major-version
    dependency upgrades end-to-end. Given a target upgrade (pydantic v1 -> v2
    in this repo), it must: (1) read @docs/migration-guide.md and extract a
    structured list of breaking changes; (2) scan src/ and tests/ for every
    usage site affected by each breaking change; (3) patch the affected files
    in parallel; (4) run `python -m pytest` and iterate until green; (5)
    produce an upgrade report (what changed, what was risky, what needs human
    review). Produce an implementation plan only: files to create, which
    steps become separate custom modes/subagents with restricted permissions,
    and the JSON contracts between them (reports/breaking-changes.json,
    reports/usage-map.json, reports/upgrade-report.json). Do not write code
    yet.

Screenshot, then switch to Code mode for the rest.

## Task 2 — custom modes + rules (new task)

    Create four project-level custom modes with tailored role definitions and
    restricted tool access, following the plan in @AGENTS.md:
    1. "changelog-analyst" - reads docs/ only; converts
       @docs/migration-guide.md into reports/breaking-changes.json: for each
       breaking change an id, description, old API pattern, new API pattern,
       and a detection hint (regex or import signature). No source write
       access.
    2. "usage-scanner" - read-only on src/ and tests/; for each breaking
       change, finds every affected file:line and writes
       reports/usage-map.json.
    3. "code-migrator" - may edit src/ and requirements.txt only; applies the
       new API pattern at each usage site, one breaking-change id at a time,
       minimal idiomatic diffs.
    4. "verifier" - may run commands and edit tests/ only; runs
       `python -m pytest`, maps failures back to breaking-change ids, and
       reports which migrations are incomplete.
    Also create a project rules file enforcing: every patch references the
    breaking-change id it implements; no unrelated refactoring; anything the
    migrator is less than 90% confident about goes into a
    "needs-human-review" list instead of being guessed.

## Task 3 — orchestrator (new task, Code mode)

    Implement the UpLift orchestrator per @AGENTS.md: a CLI
    `python -m uplift upgrade pydantic` (new package src/uplift/) that:
    (1) updates requirements.txt to pydantic>=2 plus pydantic-settings,
    (2) loads reports/breaking-changes.json and reports/usage-map.json,
    (3) coordinates patching grouped by breaking-change id,
    (4) runs `python -m pytest` after each group, retrying failed groups up
        to 2 times,
    (5) writes reports/upgrade-report.json plus a human-readable
        UPGRADE_REPORT.md containing: changes applied, files touched, test
        status timeline (failure count -> green), and the
        needs-human-review list.
    Write unit tests for the orchestration and report logic in tests/.
    Do not modify src/uplift_demo/ in this task.

## Task 4 — the agent crew (SEPARATE tasks; run 4c and 4d AT THE SAME TIME)

4a (mode: changelog-analyst):

    Using the changelog-analyst mode: read @docs/migration-guide.md and
    produce reports/breaking-changes.json per the project rules.

4b (mode: usage-scanner):

    Using the usage-scanner mode: using @reports/breaking-changes.json, scan
    src/uplift_demo/ and tests/ and produce reports/usage-map.json with
    file:line entries for every affected usage site.

4c (mode: code-migrator) — run in parallel with 4d:

    Using the code-migrator mode: apply the migrations for the FIRST HALF of
    the breaking-change ids in @reports/usage-map.json to src/uplift_demo/.
    Reference each id in your changes. Put anything under 90% confidence in
    the needs-human-review list instead of guessing.

4d (mode: code-migrator) — run in parallel with 4c:

    Using the code-migrator mode: apply the migrations for the SECOND HALF of
    the breaking-change ids in @reports/usage-map.json to src/uplift_demo/.
    Reference each id in your changes. Put anything under 90% confidence in
    the needs-human-review list instead of guessing.

4e (mode: verifier):

    Using the verifier mode: run `python -m pytest`, map any failures to
    breaking-change ids from @reports/breaking-changes.json, fix test-side
    issues only (e.g. error-type assertions that legitimately changed in v2,
    per @docs/migration-guide.md section 6), and report which migrations are
    complete and which need another pass.

Screenshot the task LIST while 4c and 4d run simultaneously — that image is
your "parallel tasks" evidence.

## Task 5 — watsonx integration (new task)

    Create a watsonx Orchestrate integration using the ADK under orchestrate/:
    (1) a Python tool that reads reports/upgrade-report.json and returns
        upgrade status, risk items, and the needs-human-review list;
    (2) an agent YAML for an "Upgrade Approval Agent" that summarizes the
        upgrade for an engineering manager and requires an explicit human
        approve/reject before recommending merge;
    (3) where our code needs inference (summarizing a migration guide into
        breaking changes), call watsonx.ai via the ibm-watsonx-ai Python SDK
        with an IBM Granite model; credentials come ONLY from environment
        variables WATSONX_APIKEY, WATSONX_PROJECT_ID, WATSONX_URL; .env is
        gitignored.
    Add README setup steps for importing the tool and agent into Orchestrate.

## Task 6 — review + polish

First run Bob's built-in **Review** workflow on the working-tree changes.
Then, as the final task:

    Complete @README.md for the hackathon submission: fill the problem
    section with our measured numbers, add a mermaid architecture diagram
    showing the four custom modes, the orchestrator, Granite inference, and
    the Orchestrate approval gate; complete the "How IBM Bob was used"
    section (/init, Plan->Code workflow, four custom modes, parallel tasks,
    custom rules, built-in Review); verify the demo script commands work as
    written; and fill the measured impact table from reports/
    upgrade-report.json.

---

## Demo script (rehearse this — 90 seconds)

1. `python -m pytest` -> all green ("a healthy service").
2. `pip install "pydantic>=2" pydantic-settings` -> "this is what Dependabot
   does to you" -> `python -m pytest` -> show the failure count.
3. `python -m uplift upgrade pydantic` -> narrate: "the analyst read the
   migration guide; the scanner found N affected sites; two migrators
   patched different change categories in parallel."
4. `python -m pytest` -> green. Open UPGRADE_REPORT.md, point at the
   needs-human-review list: "it did N-2 of N and told us which 2 need a
   human — that's the trust story."

## Submission checklist

### Must-do before presenting (highest-priority first)

**PNG screenshots** — the letter of the requirement; 4 keypresses each:
- [ ] Open each completed task in Bob IDE → scroll to session summary panel → `Cmd+Shift+3`
- [ ] Save as `bob_sessions/kamini_task0N_<desc>_summary.png`
- [ ] Minimum set: task03 (orchestrator), task04c+4d (parallel tasks), task02 (custom modes), task07 (--force demo)
- [ ] See `bob_sessions/README.md` for the full ordered list

**watsonx live demo** (turns "claimed" into "shown"):
- [ ] `source .env` with hackathon cloud credentials
- [ ] `orchestrate env activate <hackathon-env>` + `orchestrate tools import` + `orchestrate agents import`
- [ ] `orchestrate agents chat --name upgrade_approval_agent` → approve the migration → screenshot
- [ ] `python orchestrate/granite_summarizer.py` → screenshot Granite output
- [ ] See `orchestrate/README.md` sections A–F for exact commands (~20 min)

**Rehearse the 90-second demo once** (see demo script in `README.md §5`):
- [ ] `python -m uplift upgrade pydantic --force` — confirm `[analyst] extracted 6` and `[scanner] found 15` lines print
- [ ] `python dashboard/server.py` → click "⚡ Run migration" → confirm terminal panel streams

### Already done ✅
- [x] `bob_sessions/` has JSON exports for all 11 tasks (machine-verifiable, Bobcoin data included)
- [x] 86/86 tests green (`python -m pytest`)
- [x] Repo has README.md, UPGRADE_REPORT.md, reports/*.json, UPGRADE_REPORT.md
- [x] No IBM Cloud API keys in repo (`.env` in `.gitignore`, credentials env-var only)
- [x] Bob instance: ibm-coding-challenge-uat (us-east)
- [x] `--force` live pipeline + streaming dashboard runner implemented and tested
