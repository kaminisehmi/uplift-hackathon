# UpLift — agents that perform dependency upgrades, not just propose them

> Dependabot tells you you're outdated. UpLift makes you current — it reads
> the migration guide so you don't have to.

**IBM TechXchange 2026 Pre-conference Dev Day Hackathon submission.**
Built with **IBM Bob IDE** (Plan/Code modes, custom modes as subagents,
parallel tasks, custom rules, document understanding), with **watsonx.ai
(IBM Granite)** for inference and a **watsonx Orchestrate** human-approval
agent.

## 1. The problem

<!-- Fill after demo runs: quantify. Example framing:
Major-version dependency upgrades are deferred for months because breaking
changes cost days of manual work per service — which is why known-vulnerable
versions stay in production. Bots like Dependabot/Renovate only bump the
version number; the broken build is left to a human. -->

## 2. Market validation & differentiation

- Dependabot / Renovate: open the PR, don't fix the code.
- OpenRewrite / Moderne: fix code but need hand-written recipes per library.
- AWS DevOps Agent: validates the agentic-DevOps category (customers report
  75–77% faster incident resolution) but operates ops-side, post-deploy.
- **UpLift**: reads the library's own human-written migration guide,
  turns it into a structured plan, and executes it — pre-merge, in the IDE,
  repo-agnostic, no recipes required.

## 3. Architecture

<!-- mermaid diagram generated in Bob Task 6 goes here -->

## 4. How IBM Bob was used

<!-- Filled in Bob Task 6: /init, Plan->Code workflow, the four custom
modes (changelog-analyst, usage-scanner, code-migrator, verifier),
parallel migrator tasks, custom rules, built-in Review. -->

Evidence: see [`bob_sessions/`](bob_sessions/) for task session
consumption summaries, as required by the hackathon guide.

## 5. Demo script

```
python -m pytest                      # baseline: all green on pydantic v1
pip install "pydantic>=2" pydantic-settings   # the "Dependabot moment"
python -m pytest                      # everything breaks
uplift upgrade pydantic               # the agent crew takes over
python -m pytest                      # green again
cat UPGRADE_REPORT.md                 # what changed + needs-human-review
```

## 6. Measured impact

| Metric | Manual (typical) | UpLift |
|---|---|---|
| pydantic v1→v2 migration for this service | *(fill in)* | *(fill in)* |
| Breaking-change sites found / fixed | — | *(fill in)* |

## Setup

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```
