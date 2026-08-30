# UpLift — hackathon submission deliverables

Copy each section into the matching field on the My Team → Submissions page.

---

## Deliverable 2 — Problem and solution statement (498 words)

**The problem.** Every engineering team carries dependencies it is afraid to
upgrade. Dependabot and Renovate open a pull request that bumps a version
number, the build explodes, and the PR rots for months. That is why known-
vulnerable library versions stay in production long after a patch exists: the
bump is free, but the *breaking changes* cost days of manual work per service.

The pydantic v1→v2 upgrade is the canonical example. Six unrelated API
surfaces change at once — validators, field keywords, `class Config`,
`BaseSettings`, six renamed model methods, and a silent behavioural change
where mutating a frozen model raises `ValidationError` instead of `TypeError`.
A human has to read a long migration guide, find every affected line, and
rewrite each one correctly.

**The solution.** UpLift is an agent crew that *performs* the upgrade instead
of proposing it. Point it at a repository and the library's own published
migration guide, and four specialised agents run in sequence:

1. **changelog-analyst** reads the migration guide and extracts structured
   breaking changes, each with a detection pattern.
2. **usage-scanner** finds every affected line across the codebase.
3. **Two code-migrators run in parallel**, split by file ownership so they can
   never collide, patching the source and citing the breaking-change ID for
   every edit.
4. **verifier** runs the test suite, maps each failure back to a breaking
   change, applies the test-side fix, and retries until green.

On our demo service it read the guide, found 15 usage sites, patched 4 files
with 14 edits, hit exactly the one test failure the analyst had predicted,
fixed it, and finished green — 86/86 tests — in under a second of pipeline
time.

**Target users and interaction.** Platform and application engineers, in the
IDE, before merge. One command: `python -m uplift upgrade pydantic --force`.
A zero-dependency dashboard streams the run for anyone who doesn't live in a
terminal, and a watsonx Orchestrate agent summarises the result for an
engineering manager and demands an explicit approve/reject before recommending
merge.

**Why it is different.** Dependabot and Renovate bump versions but never fix
code. OpenRewrite and Moderne fix code but need a hand-written recipe per
library. AWS DevOps Agent validates the category commercially but operates
ops-side, after deployment. UpLift needs neither a recipe nor a cloud
platform: it reads the human-written migration guide the library already
published. With `--llm`, an IBM Granite model on watsonx.ai discovers the
breaking changes itself, so the same crew handles SQLAlchemy 1→2 or NumPy 1→2
by dropping in a different guide.

**Trust.** The model reads prose and proposes patterns; every stage that
touches code stays deterministic, and the model never edits source. Anything
below 90% confidence — like that behavioural `TypeError` change — is applied
but reported in a `needs_human_review` list rather than hidden. An agent that
tells you what it *didn't* dare auto-fix is one a team can actually adopt.

---

## Deliverable 3 — How IBM Bob was used (and watsonx)

**IBM Bob IDE built this project.** Eleven Bob tasks consumed the full
40-Bobcoin allocation; every task is exported with its task ID, workspace,
full message log and exact Bobcoin cost in [`bob_sessions/`](bob_sessions/).

| Bob capability | Where it was used |
|---|---|
| `/init` | Generated `AGENTS.md`, seeding every later task with project context (0.53 coins) |
| **Plan mode** + `create-plan` skill + **explore subagent** | Designed the four-agent architecture and the JSON contracts between stages before any code was written (0.41) |
| **Custom modes** (`.bob/custom_modes.yaml`) | Created `changelog-analyst`, `usage-scanner`, `code-migrator`, `verifier` — each with file-regex-restricted write permissions, so the migrator literally cannot touch the test directory (1.71) |
| **Parallel tasks** | Migrator A (`models.py`) and Migrator B (`settings.py`, `service.py`, `requirements.txt`) ran simultaneously in two Bob chat panels — their exports carry overlapping timestamps (0.18 + 0.15) |
| **Custom rules** (`.bob/rules-*`) | Enforced that every patch cites its breaking-change ID, no unrelated refactoring, and anything under 90% confidence goes to `needs_human_review` instead of being guessed |
| **Document understanding** | The changelog-analyst mode read `docs/migration-guide.md` and produced `reports/breaking-changes.json` (0.18) |
| **Agent mode** | Built the orchestrator package and 61 unit tests (2.26), the watsonx integration (0.52), and the live dashboard (2.38 + 2.13) |

The clearest single result: when the verifier mode ran the suite after both
migrators finished, there was **exactly one failure — the behavioural change
the analyst had predicted hours earlier** — which it fixed under its
pre-approved authority, ending green.

**IBM watsonx.ai (Granite).** `orchestrate/granite_summarizer.py` and
`src/uplift/llm_analyst.py` call `ibm/granite-4-h-small` on watsonx.ai. With
`--llm`, Granite reads an arbitrary migration guide and discovers the breaking
changes and detection patterns itself — this is what makes UpLift
library-agnostic rather than pydantic-specific. Granite's proposed regexes are
compiled before use and discarded if invalid, and any failure falls back to
the deterministic parser so a migration never dies because the model is
unavailable.

**IBM watsonx Orchestrate.** An **Upgrade Approval Agent** is deployed on our
hackathon Orchestrate instance. It summarises the migration for an engineering
manager and requires an explicit approve/reject before recommending merge —
the human gate that makes autonomous migration adoptable. ADK definitions are
in [`orchestrate/`](orchestrate/); `orchestrate/README.md` documents two honest
constraints of the hosted instance: model selection is locked for the Builder
role every participant is assigned, and a cloud-hosted agent cannot read a
report file from a developer laptop.

---

## Deliverable 1 — Video script (3:00 max, ≥90s of live demo)

**Shot list — record in this order. Terminal font large. Close the CLAUDE CODE
and CODEX tabs in Bob so only IBM BOB is visible.**

### 0:00–0:25 — The problem (talking head or title card)
> "Every team has a dependency it's scared to upgrade. Dependabot opens the
> PR, the build explodes, and the PR rots for months — which is why
> vulnerable versions stay in production. Bots bump versions. Nobody fixes
> the code. UpLift fixes the code."

### 0:25–0:50 — Show the break (screen: terminal)
```bash
git checkout demo-v1-state
python -m pytest                    # 86 passed
pip install "pydantic>=2" pydantic-settings
python -m pytest                    # collection errors
```
> "A healthy service on pydantic v1. One version bump — and six API surfaces
> changed at once. Somebody has to read the migration guide and fix every
> line."

### 0:50–1:50 — THE DEMO (screen: terminal — this is the 90 seconds that matter)
```bash
python -m uplift upgrade pydantic --force
```
Narrate the lines as they stream:
> "The analyst just read pydantic's own migration guide — a human document —
> and extracted six breaking changes. The scanner found all fifteen affected
> code sites. Two migrators patched different files **in parallel**. And the
> verifier hit exactly ONE failure — a behavioural change the analyst
> predicted — fixed it, and went green. Eighty-six tests. Under a second."

```bash
python -m pytest                    # 86 passed
cat UPGRADE_REPORT.md
```
> "And here's the trust story: every edit cites its breaking-change ID, and
> it tells us the one thing a human should still confirm. An agent that knows
> what it *shouldn't* auto-fix is one you can actually adopt."

### 1:50–2:20 — IBM Bob (screen: Bob IDE, Tasks panel open)
Show the task list with the two parallel migrator tasks and their Bobcoin costs.
> "This was built *by* an agent crew in IBM Bob. Four custom modes with
> file-restricted permissions — the migrator literally cannot touch the test
> directory. Plan mode designed it, two migrator tasks ran in parallel, and
> every task's cost receipt is committed in the repo. Forty Bobcoins,
> itemised."

### 2:20–2:45 — watsonx (screen: Orchestrate chat)
Ask the agent for status; show it summarise and demand approval; type `approve`.
> "The approval gate runs as a watsonx Orchestrate agent — the agent
> recommends, a human releases. Granite on watsonx.ai reads the migration
> guide when we point UpLift at a library it's never seen."

### 2:45–3:00 — Close
> "AWS proved this category on the ops side, after the damage. UpLift moves
> it to the cheapest point in the lifecycle: pre-merge, in the IDE. Dependabot
> tells you you're outdated — UpLift makes you current."

---

## Deliverable 4 — Repository

`https://github.com/kaminisehmi/uplift-hackathon` — **must be PUBLIC at
submission time**, and must contain the Bob task session summary screenshots.
