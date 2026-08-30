"""Tests for the Granite-backed changelog analyst.

These never touch the network: the watsonx call is the only part that needs
credentials, and it is mocked out. What is verified here is the contract
around it — response parsing, validation, and the fallback behaviour the
pipeline depends on.
"""

from __future__ import annotations

import json
from unittest import mock

import pytest

from uplift import llm_analyst
from uplift.llm_analyst import (
    GraniteUnavailable,
    _extract_json_array,
    _validate,
    missing_credentials,
)


def _entry(**overrides):
    base = {
        "id": "BC-001",
        "title": "BaseSettings moved",
        "description": "Settings live in pydantic-settings now.",
        "detection_hint": r"from pydantic import BaseSettings",
        "old_pattern": "from pydantic import BaseSettings",
        "new_pattern": "from pydantic_settings import BaseSettings",
        "confidence_required": 0.95,
    }
    base.update(overrides)
    return base


class TestExtractJsonArray:
    def test_plain_array(self):
        assert _extract_json_array('[{"id": "BC-001"}]') == [{"id": "BC-001"}]

    def test_strips_markdown_fence(self):
        raw = '```json\n[{"id": "BC-001"}]\n```'
        assert _extract_json_array(raw) == [{"id": "BC-001"}]

    def test_ignores_prose_around_array(self):
        raw = 'Here you go:\n[{"id": "BC-002"}]\nHope that helps.'
        assert _extract_json_array(raw) == [{"id": "BC-002"}]

    def test_no_array_raises(self):
        with pytest.raises(GraniteUnavailable):
            _extract_json_array("I could not find any breaking changes.")

    def test_invalid_json_raises(self):
        with pytest.raises(GraniteUnavailable):
            _extract_json_array('[{"id": "BC-001",}]')


class TestValidate:
    def test_keeps_well_formed_entry(self):
        out = _validate([_entry()])
        assert len(out) == 1
        assert out[0]["id"] == "BC-001"
        assert out[0]["confidence_required"] == 0.95

    def test_drops_entry_without_id_or_title(self):
        with pytest.raises(GraniteUnavailable):
            _validate([_entry(id=""), _entry(title="")])

    def test_blanks_an_uncompilable_regex(self):
        """A broken pattern must not reach the scanner and explode there."""
        out = _validate([_entry(detection_hint="(unclosed[")])
        assert out[0]["detection_hint"] == ""

    def test_coerces_bad_confidence_to_default(self):
        out = _validate([_entry(confidence_required="not-a-number")])
        assert out[0]["confidence_required"] == 0.95

    def test_ignores_non_dict_items(self):
        out = _validate(["nonsense", _entry()])
        assert len(out) == 1

    def test_all_required_fields_present(self):
        out = _validate([{"id": "BC-009", "title": "Sparse entry"}])
        for field in (
            "description",
            "detection_hint",
            "old_pattern",
            "new_pattern",
            "confidence_required",
        ):
            assert field in out[0]

    def test_empty_input_raises(self):
        with pytest.raises(GraniteUnavailable):
            _validate([])


class TestCredentialGate:
    def test_missing_credentials_listed(self, monkeypatch):
        for name in ("WATSONX_APIKEY", "WATSONX_PROJECT_ID", "WATSONX_URL"):
            monkeypatch.delenv(name, raising=False)
        assert set(missing_credentials()) == {
            "WATSONX_APIKEY",
            "WATSONX_PROJECT_ID",
            "WATSONX_URL",
        }

    def test_extraction_refuses_without_credentials(self, monkeypatch, tmp_path):
        for name in ("WATSONX_APIKEY", "WATSONX_PROJECT_ID", "WATSONX_URL"):
            monkeypatch.delenv(name, raising=False)
        guide = tmp_path / "guide.md"
        guide.write_text("# Guide")
        with pytest.raises(GraniteUnavailable) as exc:
            llm_analyst.extract_breaking_changes_llm(guide)
        assert "WATSONX_APIKEY" in str(exc.value)


class TestOrchestratorFallback:
    """The migration must proceed on the built-in parser when Granite fails."""

    def test_falls_back_when_granite_unavailable(self, tmp_path, monkeypatch, capsys):
        from uplift import orchestrator

        guide = tmp_path / "migration-guide.md"
        guide.write_text("## 1. Something changed\n\nProse.\n")
        reports = tmp_path / "reports"
        monkeypatch.setattr(orchestrator, "MIGRATION_GUIDE_PATH", guide)
        monkeypatch.setattr(orchestrator, "REPORTS_DIR", reports)
        monkeypatch.setattr(
            orchestrator, "BREAKING_CHANGES_PATH", reports / "breaking-changes.json"
        )
        monkeypatch.setattr(
            orchestrator.sys.modules["uplift.llm_analyst"],
            "extract_breaking_changes_llm",
            mock.Mock(side_effect=GraniteUnavailable("no credentials")),
        )

        result = orchestrator.run_changelog_analyst(force=True, llm=True)

        assert result, "fallback must still produce breaking changes"
        assert "Granite unavailable" in capsys.readouterr().out

    def test_uses_granite_result_when_available(self, tmp_path, monkeypatch):
        from uplift import orchestrator

        guide = tmp_path / "migration-guide.md"
        guide.write_text("## 1. Something changed\n")
        reports = tmp_path / "reports"
        monkeypatch.setattr(orchestrator, "MIGRATION_GUIDE_PATH", guide)
        monkeypatch.setattr(orchestrator, "REPORTS_DIR", reports)
        monkeypatch.setattr(
            orchestrator, "BREAKING_CHANGES_PATH", reports / "breaking-changes.json"
        )
        granite_out = [_entry(id="BC-042", title="Discovered by Granite")]
        monkeypatch.setattr(
            orchestrator.sys.modules["uplift.llm_analyst"],
            "extract_breaking_changes_llm",
            mock.Mock(return_value=granite_out),
        )

        result = orchestrator.run_changelog_analyst(force=True, llm=True)

        assert [b["id"] for b in result] == ["BC-042"]
        written = json.loads((reports / "breaking-changes.json").read_text())
        assert written[0]["title"] == "Discovered by Granite"
