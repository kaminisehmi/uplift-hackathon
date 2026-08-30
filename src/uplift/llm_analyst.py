"""
Granite-backed changelog analyst.

The deterministic analyst in :mod:`uplift.analyst` knows the six pydantic
breaking changes up front. That is fast and repeatable, but it only works for
a guide whose changes are already known.

This module asks an IBM Granite model on watsonx.ai to *discover* the breaking
changes in an arbitrary migration guide and emit the same JSON contract the
rest of the pipeline consumes — so UpLift can be pointed at a library it has
never seen.

Division of labour: the model reads prose and proposes patterns; every
downstream step (scanning, patching, verifying) stays deterministic. The model
never edits code.

Credentials come only from the environment:
    WATSONX_APIKEY, WATSONX_PROJECT_ID, WATSONX_URL
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

MODEL_ID = "ibm/granite-4-h-small"
_REQUIRED_ENV = ("WATSONX_APIKEY", "WATSONX_PROJECT_ID", "WATSONX_URL")
_REQUIRED_FIELDS = (
    "id",
    "title",
    "description",
    "detection_hint",
    "old_pattern",
    "new_pattern",
    "confidence_required",
)

_PROMPT = """You are a senior Python engineer preparing an automated dependency upgrade.

Read the migration guide below and identify every breaking change that requires
a source-code edit. Return ONLY a JSON array — no prose, no markdown fence.

Each array element must be an object with exactly these keys:
  "id"                  : "BC-001", "BC-002", ... in guide order
  "title"               : short human title
  "description"         : one or two sentences explaining the change
  "detection_hint"      : a Python regular expression that finds affected
                          source lines. It must match the OLD API only, and
                          must not match the new API.
  "old_pattern"         : the v1 / old form
  "new_pattern"         : the v2 / new form
  "confidence_required" : 0.95 for mechanical renames, 0.70 for behavioural
                          changes that need a human to confirm

Rules:
- A behavioural change with no direct code substitution still gets an entry,
  with empty old_pattern and new_pattern and confidence_required 0.70.
- Escape backslashes properly so the JSON parses.

Migration guide:
---
{guide}
---

JSON array:"""


class GraniteUnavailable(RuntimeError):
    """Raised when watsonx.ai cannot be reached or is not configured."""


def _concise_reason(exc: Exception) -> str:
    """Turn a verbose SDK error into one readable line.

    watsonx errors embed a JSON blob with request ids and timestamps; the only
    part worth printing during a migration is the message itself.
    """
    text = str(exc)
    match = re.search(r'"errorMessage"\s*:\s*"([^"]+)"', text)
    if match:
        return f"watsonx.ai: {match.group(1)}"
    text = " ".join(text.split())
    return f"watsonx.ai call failed: {text[:120]}" + ("…" if len(text) > 120 else "")


def missing_credentials() -> list[str]:
    """Return the names of any required environment variables that are unset."""
    return [name for name in _REQUIRED_ENV if not os.environ.get(name)]


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """Pull the first JSON array out of a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise GraniteUnavailable("model response contained no JSON array")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise GraniteUnavailable(f"model returned invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise GraniteUnavailable("model response was not a JSON array")
    return data


def _validate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only well-formed entries whose detection_hint is a usable regex.

    A model can hallucinate a field or emit a broken pattern; anything that
    would poison the deterministic stages downstream is dropped here rather
    than allowed to reach the scanner.
    """
    clean: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        entry = {field: raw.get(field, "") for field in _REQUIRED_FIELDS}
        if not entry["id"] or not entry["title"]:
            continue
        hint = entry["detection_hint"]
        if hint:
            try:
                re.compile(hint)
            except re.error:
                entry["detection_hint"] = ""
        try:
            entry["confidence_required"] = float(entry["confidence_required"] or 0.95)
        except (TypeError, ValueError):
            entry["confidence_required"] = 0.95
        clean.append(entry)
    if not clean:
        raise GraniteUnavailable("model returned no usable breaking changes")
    return clean


def extract_breaking_changes_llm(
    guide_path: Path,
    model_id: str = MODEL_ID,
    max_new_tokens: int = 4096,
) -> list[dict[str, Any]]:
    """Ask Granite to extract breaking changes from *guide_path*.

    Raises :class:`GraniteUnavailable` if credentials, the SDK, or the model
    response are not usable — callers fall back to the deterministic analyst.
    """
    missing = missing_credentials()
    if missing:
        raise GraniteUnavailable(
            "missing environment variables: " + ", ".join(missing)
        )

    try:
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise GraniteUnavailable(
            "ibm-watsonx-ai is not installed (pip install -r requirements-orchestrate.txt)"
        ) from exc

    guide_text = Path(guide_path).read_text(encoding="utf-8")

    # APIClient authenticates inside its constructor, so client creation is as
    # much a failure point as the call itself (a disabled or rotated key raises
    # here). Both must degrade to the deterministic analyst, never crash the
    # migration.
    try:
        client = APIClient(
            Credentials(
                url=os.environ["WATSONX_URL"],
                api_key=os.environ["WATSONX_APIKEY"],
            )
        )
        model = ModelInference(
            model_id=model_id,
            api_client=client,
            project_id=os.environ["WATSONX_PROJECT_ID"],
            params={
                Params.MAX_NEW_TOKENS: max_new_tokens,
                Params.TEMPERATURE: 0.0,
                Params.DECODING_METHOD: "greedy",
            },
        )
        response = model.generate_text(prompt=_PROMPT.format(guide=guide_text))
    except GraniteUnavailable:
        raise
    except Exception as exc:
        raise GraniteUnavailable(_concise_reason(exc)) from exc

    return _validate(_extract_json_array(response))
