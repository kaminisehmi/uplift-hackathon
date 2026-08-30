"""
UpLift — optional Granite summarizer helper.

Reads docs/migration-guide.md and asks an IBM Granite model on watsonx.ai
to extract a structured breaking-changes list from the document.

Credentials are read ONLY from environment variables:
    WATSONX_APIKEY      – IBM Cloud IAM API key
    WATSONX_PROJECT_ID  – watsonx.ai project ID
    WATSONX_URL         – watsonx.ai endpoint URL
                          (e.g. https://us-south.ml.cloud.ibm.com)

If any required variable is unset, the script prints a clear message and exits.

Usage:
    python orchestrate/granite_summarizer.py
    # or from the repo root:
    python -m orchestrate.granite_summarizer
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_MIGRATION_GUIDE = _REPO_ROOT / "docs" / "migration-guide.md"
_MODEL_ID = "ibm/granite-4-h-small"

# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    """Return the value of *name* from the environment or exit with a message."""
    value = os.environ.get(name, "").strip()
    if not value:
        print(
            f"[granite_summarizer] ERROR: environment variable '{name}' is not set.\n"
            "Please export WATSONX_APIKEY, WATSONX_PROJECT_ID, and WATSONX_URL "
            "before running this script.\n"
            "Copy orchestrate/.env.example to .env, fill in the values, "
            "then run:  source .env"
        )
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

def summarize_migration_guide() -> str:
    """Call watsonx.ai (Granite) to summarize docs/migration-guide.md.

    Returns the model's text response as a string.
    """
    api_key = _require_env("WATSONX_APIKEY")
    project_id = _require_env("WATSONX_PROJECT_ID")
    url = _require_env("WATSONX_URL")

    # Late import — only needed when credentials are present.
    try:
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params
    except ImportError:
        print(
            "[granite_summarizer] ERROR: ibm-watsonx-ai is not installed.\n"
            "Run:  pip install -r requirements-orchestrate.txt"
        )
        sys.exit(1)

    if not _MIGRATION_GUIDE.exists():
        print(f"[granite_summarizer] ERROR: Migration guide not found at {_MIGRATION_GUIDE}")
        sys.exit(1)

    guide_text = _MIGRATION_GUIDE.read_text(encoding="utf-8")

    prompt = (
        "You are a senior Python engineer. "
        "Read the pydantic migration guide below and extract a concise, "
        "numbered list of breaking changes. "
        "For each breaking change include:\n"
        "  - a short title\n"
        "  - the old API pattern (v1)\n"
        "  - the new API pattern (v2)\n"
        "  - the confidence level (high / medium / low) that automated migration is safe\n\n"
        "Migration guide:\n"
        "---\n"
        f"{guide_text}\n"
        "---\n\n"
        "Breaking changes list:"
    )

    credentials = Credentials(url=url, api_key=api_key)
    client = APIClient(credentials=credentials)

    model = ModelInference(
        model_id=_MODEL_ID,
        api_client=client,
        project_id=project_id,
        params={
            Params.MAX_NEW_TOKENS: 1024,
            Params.TEMPERATURE: 0.0,
            Params.STOP_SEQUENCES: [],
        },
    )

    response = model.generate_text(prompt=prompt)
    return response


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"[granite_summarizer] Reading {_MIGRATION_GUIDE} …")
    print(f"[granite_summarizer] Calling model {_MODEL_ID} on watsonx.ai …\n")

    result = summarize_migration_guide()

    print("=" * 70)
    print("Breaking changes summary from Granite:")
    print("=" * 70)
    print(result)
    print("=" * 70)


if __name__ == "__main__":
    main()
