# UpLift — watsonx Orchestrate Integration

This directory contains the watsonx Orchestrate ADK artefacts for the **UpLift**
pydantic migration system.

```
orchestrate/
├── upgrade_status_tool.py      # ADK @tool — reads reports/upgrade-report.json
├── upgrade_approval_agent.yaml # ADK Agent YAML — Upgrade Approval Agent
├── granite_summarizer.py       # Optional: summarize migration-guide.md via Granite
└── .env.example                # Credential template (copy → .env, never commit)
```

---

## Hackathon demo: end-to-end import in ~20 minutes

> **This section turns "claimed IBM tech" into "shown IBM tech."**
> Complete it before presenting to judges.

### A. Set up credentials

```bash
# 1. Clone the repo and enter it
git clone <your-repo-url> && cd IBM-Hackthon

# 2. Copy the credential template
cp orchestrate/.env.example .env

# 3. Fill in .env with values from your hackathon IBM Cloud account:
#    WATSONX_APIKEY      → IBM Cloud → Manage → Access → API keys → Create
#    WATSONX_PROJECT_ID  → watsonx.ai → Your project → Manage tab → Project ID
#    WATSONX_URL         → https://us-south.ml.cloud.ibm.com  (us-east: us-east.ml.cloud.ibm.com)

# 4. Load them
source .env

# 5. Install the Orchestrate CLI and optional deps
pip install ibm-watsonx-orchestrate
pip install -r requirements-orchestrate.txt
```

### B. Authenticate to your hackathon Orchestrate instance

```bash
# List available environments (your hackathon instance will appear here)
orchestrate env list

# Activate your hackathon environment by name
orchestrate env activate <your-hackathon-env-name>
# e.g.: orchestrate env activate ibm-coding-challenge-uat

# Confirm you're connected
orchestrate env current
```

### C. Import the tool

```bash
# Import the upgrade_status Python tool
orchestrate tools import \
  --file orchestrate/upgrade_status_tool.py \
  --name upgrade_status

# Verify it's registered (should show upgrade_status in the list)
orchestrate tools list
```

### D. Import the Upgrade Approval Agent

```bash
# Import the agent YAML
orchestrate agents import \
  --file orchestrate/upgrade_approval_agent.yaml

# Verify it's registered
orchestrate agents list
# Expected: upgrade_approval_agent  Upgrade Approval Agent
```

### E. Run the agent (CLI chat — takes 2 minutes)

```bash
orchestrate agents chat --name upgrade_approval_agent
```

Expected conversation:
```
Agent: I'll retrieve the current upgrade status…
       [calls upgrade_status tool]

       **Upgrade**: pydantic 1.x → 2.x
       **Result**: ✅ GREEN — 77/77 tests passed in 2 attempts

       **Breaking changes applied**:
       ✅ BC-001  BaseSettings moved to pydantic-settings   settings.py
       ✅ BC-002  Validators renamed (@field_validator)     models.py
       ✅ BC-003  class Config → ConfigDict                 models.py
       ✅ BC-004  Field keyword renames (regex→pattern)     models.py
       ✅ BC-005  Method renames (.dict → .model_dump)      service.py
       ⚠️  BC-006  TypeError → ValidationError (flagged for human review)

       **Human review items**: 1 item — BC-006, tests/test_models.py, auto-fixed

       Do you **approve** or **reject** merging this migration branch?

You: approve

Agent: ✅ Migration approved for merge. Note: BC-006 was auto-fixed in the
       test suite; verify the behavioral change is intentional post-merge.
```

**Screenshot this conversation** → `bob_sessions/kamini_orchestrate_approval_demo.png`

### F. Run the Granite summarizer (shows watsonx.ai inference)

```bash
# Run from the repo root
python orchestrate/granite_summarizer.py
```

This calls `ibm/granite-4-h-small` on your watsonx.ai project to
re-summarize `docs/migration-guide.md` into a structured breaking-changes list.
It demonstrates the same document-understanding step the pipeline performs,
but with a live Granite inference call visible on screen.

**Screenshot the output** → `bob_sessions/kamini_granite_summarizer_demo.png`

---

## Standard setup (CI / local without hackathon cloud)

### Prerequisites

```bash
# Install the Orchestrate optional dependencies
pip install -r requirements-orchestrate.txt

# Install the Orchestrate CLI (once, globally)
pip install ibm-watsonx-orchestrate

# Set credentials
cp orchestrate/.env.example .env
# Edit .env with your real values, then:
source .env
```

> **Note**: `.env` is already listed in `.gitignore`. Never commit it.

### Importing the tool

```bash
orchestrate env activate <your-env-name>
orchestrate tools import \
  --file orchestrate/upgrade_status_tool.py \
  --name upgrade_status
orchestrate tools list
```

### Importing the agent

```bash
orchestrate agents import \
  --file orchestrate/upgrade_approval_agent.yaml
orchestrate agents list
```

### Running the agent

```bash
orchestrate agents chat --name upgrade_approval_agent
```

Or open the **watsonx Orchestrate** web UI → **My Agents** → **Upgrade Approval Agent**.

The agent will:
1. Call `upgrade_status` to fetch `reports/upgrade-report.json`.
2. Summarize all breaking-change results and human-review items.
3. Ask for an explicit **approve** or **reject** before recommending merge.

---

## Running the Granite summarizer (optional)

`granite_summarizer.py` calls watsonx.ai with the `ibm/granite-4-h-small`
model to summarize `docs/migration-guide.md` into a breaking-changes list.

```bash
source .env
python orchestrate/granite_summarizer.py
```

Expected output:

```
[granite_summarizer] Reading .../docs/migration-guide.md …
[granite_summarizer] Calling model ibm/granite-4-h-small on watsonx.ai …

======================================================================
Breaking changes summary from Granite:
======================================================================
1. BaseSettings moved …
   Old: from pydantic import BaseSettings
   New: from pydantic_settings import BaseSettings, SettingsConfigDict
   Confidence: high
...
======================================================================
```

If credentials are missing the script exits with a clear message:

```
[granite_summarizer] ERROR: environment variable 'WATSONX_APIKEY' is not set.
Please export WATSONX_APIKEY, WATSONX_PROJECT_ID, and WATSONX_URL …
```

---

## Credential environment variables

| Variable              | Description                                           |
|-----------------------|-------------------------------------------------------|
| `WATSONX_APIKEY`      | IBM Cloud IAM API key                                 |
| `WATSONX_PROJECT_ID`  | watsonx.ai project ID (from project Manage tab)       |
| `WATSONX_URL`         | watsonx.ai endpoint, e.g. `https://us-south.ml.cloud.ibm.com` |

Credentials are **never** hardcoded. They are read exclusively from environment
variables as required by the UpLift project conventions.
