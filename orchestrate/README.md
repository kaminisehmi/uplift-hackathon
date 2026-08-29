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

## Prerequisites

```bash
# 1. Install the Orchestrate optional dependencies
pip install -r requirements-orchestrate.txt

# 2. Install the Orchestrate CLI (once, globally)
pip install ibm-watsonx-orchestrate

# 3. Set credentials
cp orchestrate/.env.example .env
# Edit .env with your real values, then:
source .env
```

> **Note**: `.env` is already listed in `.gitignore`. Never commit it.

---

## Importing the tool into watsonx Orchestrate

```bash
# Authenticate to your Orchestrate instance
orchestrate env activate <your-env-name>

# Import the Python tool
orchestrate tools import \
  --file orchestrate/upgrade_status_tool.py \
  --name upgrade_status

# Verify the tool is registered
orchestrate tools list
```

---

## Importing the Upgrade Approval Agent

```bash
# Import the agent YAML
orchestrate agents import \
  --file orchestrate/upgrade_approval_agent.yaml

# Verify the agent is registered
orchestrate agents list
```

---

## Running the Upgrade Approval Agent

Once both the tool and agent are imported:

```bash
# Start a chat session with the agent in the CLI
orchestrate agents chat --name upgrade_approval_agent
```

Or open the **watsonx Orchestrate** web UI, navigate to **My Agents**, and
select **Upgrade Approval Agent** to start an interactive session.

The agent will:
1. Call `upgrade_status` to fetch `reports/upgrade-report.json`.
2. Present a human-readable summary of all breaking-change results and
   any items flagged for human review.
3. Prompt the engineering manager for an explicit **approve** or **reject**
   decision before recommending a merge.

---

## Running the Granite summarizer (optional)

`granite_summarizer.py` calls watsonx.ai with the `ibm/granite-3-3-8b-instruct`
model to summarize `docs/migration-guide.md` into a breaking-changes list.
This is a standalone helper; it does **not** affect the main migration pipeline.

```bash
# Ensure credentials are exported
source .env

# Run from the repo root
python orchestrate/granite_summarizer.py
```

Expected output:

```
[granite_summarizer] Reading .../docs/migration-guide.md …
[granite_summarizer] Calling model ibm/granite-3-3-8b-instruct on watsonx.ai …

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
