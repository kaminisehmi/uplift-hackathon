# UpLift — 3-minute judge pitch script

## 0:00 — The hook (say this looking at the judges, nothing on screen)

> "Every team in this room has a dependency they're afraid to upgrade.
> Dependabot opens the PR, the build explodes, and the PR rots for months —
> which is exactly why known-vulnerable versions stay in production.
> Bots bump versions. Nobody fixes the code. UpLift fixes the code."

## 0:20 — The demo (terminal, demo-v1-state branch, rehearsed)

```bash
git checkout demo-v1-state
source .venv/bin/activate
python -m pytest            # green: "a healthy service on pydantic v1"
pip install "pydantic>=2" pydantic-settings
python -m pytest            # red: "this is what Dependabot does to you"
python -m uplift upgrade pydantic --force
```

While the pipeline streams, narrate the lines as they print:

> "Watch the pipeline: the **analyst** just read pydantic's own migration
> guide — a human document — and extracted 6 breaking changes. The
> **scanner** found all 15 affected code sites. **Two migrators** patched
> different files in parallel. And the **verifier** hit exactly ONE test
> failure — a behavioral change the analyst *predicted* — fixed it under
> pre-approved authority, and went green. Under one second."

```bash
python -m pytest            # green again
cat UPGRADE_REPORT.md       # point at the needs_human_review table
```

> "And here's the trust story: it reports what it did, per breaking change,
> and tells us what a human should still look at. An agent that knows what
> it shouldn't auto-fix is one you can actually adopt."

## 1:40 — Optional dashboard flourish (if time; ./dashboard/start.sh open in a tab)

> "Same thing for the release manager who never opens a terminal —
> live streaming migration runs and reports, zero dependencies."

## 1:55 — How it was built (this is the IBM Bob slide)

> "The whole system was built *by* an agent crew in IBM Bob, in one day —
> the migration crew itself cost under six Bobcoins, and the complete
> submission used my full forty. Four custom Bob modes with file-restricted
> permissions — the migrator literally *cannot* touch the test directory.
> Plan mode designed it, subagents explored it, two migrator tasks ran in
> parallel, and every task's cost receipt is committed in the repo.
> The approval gate runs as a watsonx Orchestrate agent — the agent
> recommends, a human releases — with IBM Granite on watsonx.ai for
> document summarization."

## 2:25 — Market + scale (close)

> "AWS proved this category — their DevOps agent cuts incident time 75% on
> the ops side, after the damage. UpLift moves that intelligence to the
> cheapest point in the lifecycle: pre-merge, in the IDE. Dependabot bumps,
> OpenRewrite needs hand-written recipes — UpLift needs only the migration
> guide the library already published. That means the same crew handles
> SQLAlchemy 1-to-2, NumPy, Django — every upgrade every team defers.
> Days of dreaded migration work, down to a sub-second replay.
> That's UpLift: Dependabot tells you you're outdated. We make you current."

## Q&A ammunition

- **"Does it work on repos you didn't write?"** — The pipeline is
  pattern-generic: the analyst emits detection hints from any guide, the
  scanner greps any codebase, and anything below 90% confidence goes to
  needs_human_review instead of being guessed. This PoC proves the loop
  end-to-end; hardening the pattern coverage is engineering, not research.
- **"Why not just an LLM rewrite of the whole file?"** — Deterministic,
  auditable, per-change diffs with breaking-change IDs; sub-second replay;
  no tokens spent per repo after the pipeline is built. LLM judgment is used
  where it pays (reading the guide, deciding confidence), regex execution
  where it's safe.
- **"What about the banned models / cloud usage?"** — Granite
  (ibm/granite-3-3-8b-instruct) only; credentials from env vars; nothing
  hardcoded; hackathon account only.
- **"How much Bob did you really use?"** — bob_sessions/ has one costed
  export per task: 11 tasks totalling 40.1 Bobcoins — the entire
  allocation, itemized, including the parallel migrator pair with
  overlapping timestamps. The migration crew (tasks 0–4e) was 5.9 of those;
  the rest went to the orchestrator, dashboard and watsonx integration.
