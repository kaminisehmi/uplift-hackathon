"""
Unit tests for the UpLift orchestrator package.

All tests use temporary directories and fixtures — the live demo files are
never touched here.  pytest.ini already sets pythonpath=src so imports work.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bc_list() -> list[dict[str, Any]]:
    return [
        {
            "id": "BC-001",
            "title": "BaseSettings moved",
            "description": "from pydantic import BaseSettings raises error in v2",
            "detection_hint": r"from pydantic import BaseSettings",
            "old_pattern": "from pydantic import BaseSettings",
            "new_pattern": "from pydantic_settings import BaseSettings, SettingsConfigDict",
            "confidence_required": 0.95,
        },
        {
            "id": "BC-002",
            "title": "Validators renamed",
            "description": "@validator renamed",
            "detection_hint": r"@validator|@root_validator",
            "old_pattern": "@validator",
            "new_pattern": "@field_validator",
            "confidence_required": 0.95,
        },
        {
            "id": "BC-003",
            "title": "class Config → model_config",
            "description": "class Config replaced",
            "detection_hint": r"class Config:",
            "old_pattern": "class Config:",
            "new_pattern": "model_config = ConfigDict(...)",
            "confidence_required": 0.95,
        },
        {
            "id": "BC-004",
            "title": "Field keyword renames",
            "description": "regex= → pattern=",
            "detection_hint": r"regex=|min_items=",
            "old_pattern": "regex=",
            "new_pattern": "pattern=",
            "confidence_required": 0.95,
        },
        {
            "id": "BC-005",
            "title": "Renamed model methods",
            "description": ".dict() → .model_dump()",
            "detection_hint": r"\.(dict|json)\(\)|\.parse_obj\(",
            "old_pattern": ".dict()",
            "new_pattern": ".model_dump()",
            "confidence_required": 0.95,
        },
        {
            "id": "BC-006",
            "title": "Behavioral changes",
            "description": "frozen raises ValidationError",
            "detection_hint": r"pytest\.raises\(TypeError\)",
            "old_pattern": "TypeError",
            "new_pattern": "ValidationError",
            "confidence_required": 0.70,
        },
    ]


# ---------------------------------------------------------------------------
# 1. CLI argument parsing
# ---------------------------------------------------------------------------

class TestCLI:
    def test_help_exits_zero(self):
        from uplift.__main__ import build_parser
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_upgrade_pydantic_parsed(self):
        from uplift.__main__ import build_parser
        parser = build_parser()
        args = parser.parse_args(["upgrade", "pydantic"])
        assert args.command == "upgrade"
        assert args.library == "pydantic"

    def test_unsupported_library_returns_2(self):
        from uplift.__main__ import main
        rc = main(["upgrade", "requests"])
        assert rc == 2

    def test_no_command_returns_1(self):
        from uplift.__main__ import main
        rc = main([])
        assert rc == 1

    def test_upgrade_pydantic_calls_upgrade(self):
        from uplift.__main__ import main
        with patch("uplift.__main__.upgrade", return_value=True) as mock_up:
            rc = main(["upgrade", "pydantic"])
        mock_up.assert_called_once_with("pydantic", force=False)
        assert rc == 0

    def test_upgrade_failure_returns_1(self):
        from uplift.__main__ import main
        with patch("uplift.__main__.upgrade", return_value=False):
            rc = main(["upgrade", "pydantic"])
        assert rc == 1


# ---------------------------------------------------------------------------
# 2. Orchestrator stage functions
# ---------------------------------------------------------------------------

class TestRunChangelogAnalyst:
    def test_reads_existing_json(self, tmp_path):
        """If breaking-changes.json already exists, it is read without re-parsing."""
        reports = tmp_path / "reports"
        reports.mkdir()
        bc_data = _make_bc_list()
        (reports / "breaking-changes.json").write_text(json.dumps(bc_data), encoding="utf-8")

        from uplift import orchestrator
        orig_bc_path = orchestrator.BREAKING_CHANGES_PATH
        orig_guide_path = orchestrator.MIGRATION_GUIDE_PATH
        orchestrator.BREAKING_CHANGES_PATH = reports / "breaking-changes.json"
        orchestrator.MIGRATION_GUIDE_PATH = tmp_path / "does-not-exist.md"
        try:
            result = orchestrator.run_changelog_analyst()
        finally:
            orchestrator.BREAKING_CHANGES_PATH = orig_bc_path
            orchestrator.MIGRATION_GUIDE_PATH = orig_guide_path

        assert len(result) == 6
        assert result[0]["id"] == "BC-001"

    def test_raises_if_guide_missing_and_no_json(self, tmp_path):
        from uplift import orchestrator
        orig_bc_path = orchestrator.BREAKING_CHANGES_PATH
        orig_guide_path = orchestrator.MIGRATION_GUIDE_PATH
        orchestrator.BREAKING_CHANGES_PATH = tmp_path / "breaking-changes.json"
        orchestrator.MIGRATION_GUIDE_PATH = tmp_path / "nonexistent.md"
        try:
            with pytest.raises(FileNotFoundError, match="Migration guide not found"):
                orchestrator.run_changelog_analyst()
        finally:
            orchestrator.BREAKING_CHANGES_PATH = orig_bc_path
            orchestrator.MIGRATION_GUIDE_PATH = orig_guide_path

    def test_generates_from_guide(self, tmp_path):
        """When no json exists but guide is present, analyst generates the file."""
        reports = tmp_path / "reports"
        reports.mkdir()
        docs = tmp_path / "docs"
        docs.mkdir()
        guide = docs / "migration-guide.md"
        # Minimal guide with 6 H2 sections
        guide.write_text(
            "\n".join(
                f"## {i}. Section {i}\n\nDesc {i}.\n\n```python\n# v1\nold_{i}()\n```\n\n"
                f"```python\n# v2\nnew_{i}()\n```\n"
                for i in range(1, 7)
            ),
            encoding="utf-8",
        )

        from uplift import orchestrator, analyst
        orig_bc_path = orchestrator.BREAKING_CHANGES_PATH
        orig_guide_path = orchestrator.MIGRATION_GUIDE_PATH
        orig_reports_dir = orchestrator.REPORTS_DIR
        orchestrator.BREAKING_CHANGES_PATH = reports / "breaking-changes.json"
        orchestrator.MIGRATION_GUIDE_PATH = guide
        orchestrator.REPORTS_DIR = reports
        try:
            result = orchestrator.run_changelog_analyst()
        finally:
            orchestrator.BREAKING_CHANGES_PATH = orig_bc_path
            orchestrator.MIGRATION_GUIDE_PATH = orig_guide_path
            orchestrator.REPORTS_DIR = orig_reports_dir

        assert len(result) == 6
        assert (reports / "breaking-changes.json").exists()


class TestRunUsageScanner:
    def test_reads_existing_usage_map(self, tmp_path):
        reports = tmp_path / "reports"
        reports.mkdir()
        usage_data = {"BC-001": [{"file": "foo.py", "line": 1, "snippet": "x"}]}
        (reports / "usage-map.json").write_text(json.dumps(usage_data), encoding="utf-8")

        from uplift import orchestrator
        orig = orchestrator.USAGE_MAP_PATH
        orchestrator.USAGE_MAP_PATH = reports / "usage-map.json"
        try:
            result = orchestrator.run_usage_scanner([])
        finally:
            orchestrator.USAGE_MAP_PATH = orig

        assert result == usage_data

    def test_scans_and_writes(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "foo.py").write_text("from pydantic import BaseSettings\n", encoding="utf-8")
        reports = tmp_path / "reports"
        reports.mkdir()

        from uplift import orchestrator
        orig_usage = orchestrator.USAGE_MAP_PATH
        orig_src = orchestrator.SRC_ROOT
        orig_test = orchestrator.TEST_ROOT
        orig_reports = orchestrator.REPORTS_DIR
        orchestrator.USAGE_MAP_PATH = reports / "usage-map.json"
        orchestrator.SRC_ROOT = src
        orchestrator.TEST_ROOT = tmp_path / "nonexistent_tests"
        orchestrator.REPORTS_DIR = reports
        try:
            result = orchestrator.run_usage_scanner(_make_bc_list())
        finally:
            orchestrator.USAGE_MAP_PATH = orig_usage
            orchestrator.SRC_ROOT = orig_src
            orchestrator.TEST_ROOT = orig_test
            orchestrator.REPORTS_DIR = orig_reports

        assert "BC-001" in result
        assert any("foo.py" in u["file"] for u in result["BC-001"])


# ---------------------------------------------------------------------------
# 3. Retry logic in run_verifier
# ---------------------------------------------------------------------------

class TestRunVerifier:
    def _make_changes_and_review(self) -> tuple[list, list]:
        changes: list[dict] = []
        nhr: list[dict] = [
            {
                "bc_id": "BC-006",
                "file": "tests/test_models.py",
                "line": 58,
                "reason": "TypeError → ValidationError",
                "status": "pending",
            }
        ]
        return changes, nhr

    def test_passes_on_first_attempt(self):
        from uplift.orchestrator import run_verifier
        with patch("uplift.orchestrator.run_pytest", return_value=(True, 0)) as mock_pytest, \
             patch("uplift.orchestrator.fix_test_assertions") as mock_fix:
            passed, test_runs = run_verifier([], [], max_retries=2)

        assert passed is True
        assert len(test_runs) == 1
        assert test_runs[0]["passed"] is True
        assert test_runs[0]["failure_count"] == 0
        mock_fix.assert_not_called()

    def test_retries_on_failure_then_passes(self):
        from uplift.orchestrator import run_verifier
        results = [(False, 5), (True, 0)]
        with patch("uplift.orchestrator.run_pytest", side_effect=results), \
             patch("uplift.orchestrator.fix_test_assertions") as mock_fix:
            changes, nhr = self._make_changes_and_review()
            passed, test_runs = run_verifier(changes, nhr, max_retries=2)

        assert passed is True
        assert len(test_runs) == 2
        assert test_runs[0] == {"attempt": 1, "passed": False, "failure_count": 5}
        assert test_runs[1] == {"attempt": 2, "passed": True, "failure_count": 0}
        mock_fix.assert_called_once_with(nhr)

    def test_fails_after_max_retries(self):
        from uplift.orchestrator import run_verifier
        # Always fails
        with patch("uplift.orchestrator.run_pytest", return_value=(False, 3)):
            with patch("uplift.orchestrator.fix_test_assertions"):
                passed, test_runs = run_verifier([], [], max_retries=2)

        assert passed is False
        # Attempts: 1, 2, 3 (initial + 2 retries)
        assert len(test_runs) == 3

    def test_failure_count_recorded(self):
        from uplift.orchestrator import run_verifier
        with patch("uplift.orchestrator.run_pytest", side_effect=[(False, 7), (True, 0)]):
            with patch("uplift.orchestrator.fix_test_assertions"):
                passed, test_runs = run_verifier([], [], max_retries=2)

        assert test_runs[0]["failure_count"] == 7
        assert test_runs[1]["failure_count"] == 0


# ---------------------------------------------------------------------------
# 4. run_pytest parsing
# ---------------------------------------------------------------------------

class TestRunPytest:
    def _make_completed_process(self, returncode: int, stdout: str) -> subprocess.CompletedProcess:
        proc = MagicMock(spec=subprocess.CompletedProcess)
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = ""
        return proc

    def test_passes_on_exit_zero(self):
        from uplift.verifier import run_pytest
        with patch("subprocess.run", return_value=self._make_completed_process(0, "5 passed")):
            passed, count = run_pytest()
        assert passed is True
        assert count == 0

    def test_parses_failure_count(self):
        from uplift.verifier import run_pytest
        output = "3 failed, 2 passed"
        with patch("subprocess.run", return_value=self._make_completed_process(1, output)):
            passed, count = run_pytest()
        assert passed is False
        assert count == 3

    def test_no_failed_text_defaults_to_one(self):
        from uplift.verifier import run_pytest
        with patch("subprocess.run", return_value=self._make_completed_process(1, "ERROR")):
            passed, count = run_pytest()
        assert passed is False
        assert count == 1


# ---------------------------------------------------------------------------
# 5. fix_test_assertions (BC-006)
# ---------------------------------------------------------------------------

class TestFixTestAssertions:
    def test_replaces_typeerror_with_validationerror(self, tmp_path):
        from uplift.verifier import fix_test_assertions

        test_file = tmp_path / "test_models.py"
        test_file.write_text(
            "import pytest\nfrom pydantic import ValidationError\n\n"
            "def test_immutable():\n"
            "    with pytest.raises(TypeError):\n"
            "        obj.field = 1\n",
            encoding="utf-8",
        )

        nhr = [
            {
                "bc_id": "BC-006",
                "file": str(test_file),
                "line": 5,
                "reason": "frozen raises ValidationError",
                "status": "pending",
            }
        ]
        fix_test_assertions(nhr)

        result = test_file.read_text(encoding="utf-8")
        assert "pytest.raises(ValidationError)" in result
        assert "pytest.raises(TypeError)" not in result
        assert nhr[0]["status"] == "auto-applied"

    def test_ignores_non_bc006(self, tmp_path):
        from uplift.verifier import fix_test_assertions

        test_file = tmp_path / "test_models.py"
        original = "with pytest.raises(TypeError):\n    pass\n"
        test_file.write_text(original, encoding="utf-8")

        nhr = [{"bc_id": "BC-005", "file": str(test_file), "line": 1}]
        fix_test_assertions(nhr)

        # File should be unchanged
        assert test_file.read_text(encoding="utf-8") == original

    def test_skips_missing_file(self, tmp_path):
        from uplift.verifier import fix_test_assertions
        # Should not raise
        nhr = [{"bc_id": "BC-006", "file": str(tmp_path / "nonexistent.py"), "line": 1}]
        fix_test_assertions(nhr)


# ---------------------------------------------------------------------------
# 6. write_upgrade_report
# ---------------------------------------------------------------------------

class TestWriteUpgradeReport:
    def _make_report_data(self) -> dict[str, Any]:
        return {
            "target": "pydantic",
            "from_version": "1.x",
            "to_version": "2.x",
            "files_modified": ["src/uplift_demo/models.py"],
            "changes": [
                {
                    "bc_id": "BC-002",
                    "file": "src/uplift_demo/models.py",
                    "line": 12,
                    "description": "Applied BC-002 transformation",
                    "applied": True,
                }
            ],
            "needs_human_review": [
                {
                    "bc_id": "BC-006",
                    "file": "tests/test_models.py",
                    "line": 58,
                    "reason": "TypeError → ValidationError",
                    "status": "auto-applied",
                }
            ],
            "test_runs": [
                {"attempt": 1, "passed": False, "failure_count": 7},
                {"attempt": 2, "passed": True, "failure_count": 0},
            ],
            "final_status": "green",
        }

    def test_writes_json(self, tmp_path):
        from uplift.verifier import write_upgrade_report

        report_path = tmp_path / "reports" / "upgrade-report.json"
        write_upgrade_report(self._make_report_data(), report_path)

        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["final_status"] == "green"
        assert data["target"] == "pydantic"
        assert len(data["changes"]) == 1
        assert data["changes"][0]["bc_id"] == "BC-002"

    def test_writes_markdown(self, tmp_path):
        from uplift.verifier import write_upgrade_report

        report_path = tmp_path / "reports" / "upgrade-report.json"
        write_upgrade_report(self._make_report_data(), report_path)

        md_path = tmp_path / "UPGRADE_REPORT.md"
        assert md_path.exists()
        md = md_path.read_text(encoding="utf-8")
        assert "pydantic" in md
        assert "BC-002" in md
        assert "BC-006" in md
        assert "green" in md

    def test_markdown_contains_test_run_history(self, tmp_path):
        from uplift.verifier import write_upgrade_report

        report_path = tmp_path / "reports" / "upgrade-report.json"
        write_upgrade_report(self._make_report_data(), report_path)

        md = (tmp_path / "UPGRADE_REPORT.md").read_text(encoding="utf-8")
        assert "Test Run History" in md
        assert "7" in md   # failure count
        assert "0" in md   # green

    def test_markdown_has_needs_human_review(self, tmp_path):
        from uplift.verifier import write_upgrade_report

        report_path = tmp_path / "reports" / "upgrade-report.json"
        write_upgrade_report(self._make_report_data(), report_path)

        md = (tmp_path / "UPGRADE_REPORT.md").read_text(encoding="utf-8")
        assert "Needs Human Review" in md
        assert "auto-applied" in md

    def test_json_schema_has_required_keys(self, tmp_path):
        from uplift.verifier import write_upgrade_report

        report_path = tmp_path / "reports" / "upgrade-report.json"
        write_upgrade_report(self._make_report_data(), report_path)

        data = json.loads(report_path.read_text(encoding="utf-8"))
        required_keys = {
            "target", "from_version", "to_version", "files_modified",
            "changes", "needs_human_review", "test_runs", "final_status",
        }
        assert required_keys.issubset(data.keys())


# ---------------------------------------------------------------------------
# 7. Analyst — extract_breaking_changes
# ---------------------------------------------------------------------------

class TestExtractBreakingChanges:
    def _write_minimal_guide(self, path: Path) -> None:
        sections = []
        bc_bodies = [
            ("1. `BaseSettings` moved", "from pydantic import BaseSettings",
             "from pydantic_settings import BaseSettings, SettingsConfigDict"),
            ("2. Validators renamed", "@validator(\"field\")", "@field_validator(\"field\")"),
            ("3. `class Config` → `model_config`", "class Config:", "model_config = ConfigDict(...)"),
            ("4. `Field` keyword changes", "regex=r\"pattern\"", "pattern=r\"pattern\""),
            ("5. Renamed model methods", ".dict()", ".model_dump()"),
            ("6. Behavioral changes", "TypeError", "ValidationError"),
        ]
        for heading, old, new in bc_bodies:
            sections.append(
                f"## {heading}\n\nDescription text here.\n\n"
                f"```python\n# v1\n{old}\n```\n\n"
                f"```python\n# v2\n{new}\n```\n"
            )
        path.write_text("\n".join(sections), encoding="utf-8")

    def test_returns_six_entries(self, tmp_path):
        from uplift.analyst import extract_breaking_changes

        guide = tmp_path / "migration-guide.md"
        self._write_minimal_guide(guide)
        result = extract_breaking_changes(guide)
        assert len(result) == 6

    def test_all_six_ids_present(self, tmp_path):
        from uplift.analyst import extract_breaking_changes

        guide = tmp_path / "migration-guide.md"
        self._write_minimal_guide(guide)
        result = extract_breaking_changes(guide)
        ids = [entry["id"] for entry in result]
        assert ids == ["BC-001", "BC-002", "BC-003", "BC-004", "BC-005", "BC-006"]

    def test_schema_keys_present(self, tmp_path):
        from uplift.analyst import extract_breaking_changes

        guide = tmp_path / "migration-guide.md"
        self._write_minimal_guide(guide)
        result = extract_breaking_changes(guide)
        required = {"id", "title", "description", "detection_hint", "old_pattern", "new_pattern", "confidence_required"}
        for entry in result:
            assert required.issubset(entry.keys()), f"{entry['id']} missing keys"

    def test_bc006_has_low_confidence(self, tmp_path):
        from uplift.analyst import extract_breaking_changes

        guide = tmp_path / "migration-guide.md"
        self._write_minimal_guide(guide)
        result = extract_breaking_changes(guide)
        bc006 = next(e for e in result if e["id"] == "BC-006")
        assert bc006["confidence_required"] == pytest.approx(0.70)

    def test_other_bcs_have_high_confidence(self, tmp_path):
        from uplift.analyst import extract_breaking_changes

        guide = tmp_path / "migration-guide.md"
        self._write_minimal_guide(guide)
        result = extract_breaking_changes(guide)
        for entry in result:
            if entry["id"] != "BC-006":
                assert entry["confidence_required"] >= 0.9, f"{entry['id']} confidence too low"

    def test_reads_real_guide(self):
        """Smoke test: extract from the real docs/migration-guide.md if it exists."""
        guide = Path("docs/migration-guide.md")
        if not guide.exists():
            pytest.skip("docs/migration-guide.md not found")
        from uplift.analyst import extract_breaking_changes
        result = extract_breaking_changes(guide)
        assert len(result) == 6
        ids = [e["id"] for e in result]
        assert ids == ["BC-001", "BC-002", "BC-003", "BC-004", "BC-005", "BC-006"]


# ---------------------------------------------------------------------------
# 8. Scanner — scan_usages
# ---------------------------------------------------------------------------

class TestScanUsages:
    def _write_fixture_src(self, src_dir: Path) -> None:
        (src_dir / "settings.py").write_text(
            "from pydantic import BaseSettings\n\nclass AppSettings(BaseSettings):\n    pass\n",
            encoding="utf-8",
        )
        (src_dir / "models.py").write_text(
            "from pydantic import BaseModel, validator, root_validator\n\n"
            "@validator('name')\ndef check_name(cls, v): return v\n\n"
            "@root_validator\ndef check_all(cls, values): return values\n\n"
            "class Config:\n    allow_mutation = False\n",
            encoding="utf-8",
        )
        (src_dir / "service.py").write_text(
            "def export(order):\n    return order.dict()\n",
            encoding="utf-8",
        )

    def _write_fixture_tests(self, tests_dir: Path) -> None:
        (tests_dir / "test_models.py").write_text(
            "def test_immutable():\n    with pytest.raises(TypeError):\n        obj.x = 1\n",
            encoding="utf-8",
        )

    def test_finds_bc001_in_settings(self, tmp_path):
        from uplift.scanner import scan_usages

        src = tmp_path / "src"
        src.mkdir()
        self._write_fixture_src(src)
        tests = tmp_path / "tests"
        tests.mkdir()

        bc_list = _make_bc_list()
        result = scan_usages(bc_list, root_dirs=[src, tests])

        assert any("settings.py" in u["file"] for u in result["BC-001"])

    def test_finds_bc002_validators(self, tmp_path):
        from uplift.scanner import scan_usages

        src = tmp_path / "src"
        src.mkdir()
        self._write_fixture_src(src)

        bc_list = _make_bc_list()
        result = scan_usages(bc_list, root_dirs=[src])

        # Should find @validator and @root_validator lines
        bc002_files = {u["file"] for u in result["BC-002"]}
        assert any("models.py" in f for f in bc002_files)

    def test_finds_bc006_in_tests(self, tmp_path):
        from uplift.scanner import scan_usages

        src = tmp_path / "src"
        src.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()
        self._write_fixture_tests(tests)

        bc_list = _make_bc_list()
        result = scan_usages(bc_list, root_dirs=[src, tests])

        assert any("test_models.py" in u["file"] for u in result["BC-006"])

    def test_empty_dir_returns_empty_lists(self, tmp_path):
        from uplift.scanner import scan_usages

        empty = tmp_path / "empty"
        empty.mkdir()
        bc_list = _make_bc_list()
        result = scan_usages(bc_list, root_dirs=[empty])
        for bc in bc_list:
            assert result[bc["id"]] == []

    def test_nonexistent_dir_ignored(self, tmp_path):
        from uplift.scanner import scan_usages

        bc_list = _make_bc_list()
        result = scan_usages(bc_list, root_dirs=[tmp_path / "no-such-dir"])
        for bc in bc_list:
            assert result[bc["id"]] == []

    def test_snippet_preserved(self, tmp_path):
        from uplift.scanner import scan_usages

        src = tmp_path / "src"
        src.mkdir()
        code = "from pydantic import BaseSettings  # used here\n"
        (src / "settings.py").write_text(code, encoding="utf-8")

        bc_list = [_make_bc_list()[0]]  # BC-001 only
        result = scan_usages(bc_list, root_dirs=[src])
        assert result["BC-001"][0]["snippet"] == code.rstrip()
        assert result["BC-001"][0]["line"] == 1


# ---------------------------------------------------------------------------
# 9. Migrator — apply_migrations + file_split
# ---------------------------------------------------------------------------

class TestFileSplit:
    def test_sets_are_disjoint(self):
        from uplift.migrator import file_split
        a, b = file_split()
        assert a.isdisjoint(b)

    def test_models_in_a(self):
        from uplift.migrator import file_split
        a, _ = file_split()
        assert "src/uplift_demo/models.py" in a

    def test_service_and_settings_in_b(self):
        from uplift.migrator import file_split
        _, b = file_split()
        assert "src/uplift_demo/service.py" in b
        assert "src/uplift_demo/settings.py" in b

    def test_requirements_in_b(self):
        from uplift.migrator import file_split
        _, b = file_split()
        assert "requirements.txt" in b


class TestTransformations:
    """Test each BC transformation rule in isolation."""

    # BC-001
    def test_bc001_replaces_basesettings_import(self):
        from uplift.migrator import _transform_bc001
        src = "from pydantic import BaseSettings\n\nclass AppSettings(BaseSettings):\n    pass\n"
        result, count = _transform_bc001(src)
        assert "from pydantic_settings import BaseSettings, SettingsConfigDict" in result
        assert "from pydantic import BaseSettings" not in result
        assert count >= 1

    def test_bc001_replaces_class_config_env_prefix(self):
        from uplift.migrator import _transform_bc001
        src = (
            "from pydantic import BaseSettings\n\n"
            "class App(BaseSettings):\n"
            "    x: str = 'a'\n\n"
            "    class Config:\n"
            "        env_prefix = 'UPLIFT_'\n"
        )
        result, count = _transform_bc001(src)
        assert "model_config = SettingsConfigDict(env_prefix=" in result
        assert "class Config:" not in result

    # BC-002
    def test_bc002_renames_validator(self):
        from uplift.migrator import _transform_bc002
        src = (
            "from pydantic import BaseModel, validator\n\n"
            "class M(BaseModel):\n"
            "    @validator('name')\n"
            "    def check_name(cls, v):\n"
            "        return v\n"
        )
        result, count = _transform_bc002(src)
        assert "@field_validator('name')" in result
        assert "@classmethod" in result
        assert "@validator" not in result

    def test_bc002_renames_root_validator(self):
        from uplift.migrator import _transform_bc002
        src = (
            "from pydantic import BaseModel, root_validator\n\n"
            "class M(BaseModel):\n"
            "    @root_validator\n"
            "    def check_all(cls, values):\n"
            "        return values\n"
        )
        result, count = _transform_bc002(src)
        assert '@model_validator(mode="after")' in result
        assert "@root_validator" not in result

    def test_bc002_updates_import(self):
        from uplift.migrator import _transform_bc002
        src = "from pydantic import BaseModel, validator, root_validator\n"
        result, count = _transform_bc002(src)
        assert "field_validator" in result
        assert "model_validator" in result
        assert "validator" not in result.split("field_validator")[0]

    # BC-003
    def test_bc003_replaces_allow_mutation(self):
        from uplift.migrator import _transform_bc003_models
        src = (
            "from pydantic import BaseModel\n\n"
            "class Item(BaseModel):\n"
            "    x: int\n\n"
            "    class Config:\n"
            "        allow_mutation = False\n"
        )
        result, count = _transform_bc003_models(src)
        assert "model_config = ConfigDict(frozen=True)" in result
        assert "class Config:" not in result
        assert count >= 1

    def test_bc003_adds_configdict_import(self):
        from uplift.migrator import _transform_bc003_models
        src = "from pydantic import BaseModel\n\nclass M(BaseModel):\n    class Config:\n        allow_mutation = False\n"
        result, _ = _transform_bc003_models(src)
        assert "ConfigDict" in result

    # BC-004
    def test_bc004_renames_regex(self):
        from uplift.migrator import _transform_bc004
        src = "email: str = Field(..., regex=r'^[^@]+@[^@]+$')\n"
        result, count = _transform_bc004(src)
        assert "pattern=" in result
        assert "regex=" not in result
        assert count >= 1

    def test_bc004_renames_min_items(self):
        from uplift.migrator import _transform_bc004
        src = "items: List[Item] = Field(..., min_items=1)\n"
        result, count = _transform_bc004(src)
        assert "min_length=" in result
        assert "min_items=" not in result

    # BC-005
    def test_bc005_renames_dict(self):
        from uplift.migrator import _transform_bc005
        src = "data = order.dict()\n"
        result, count = _transform_bc005(src)
        assert "model_dump()" in result
        assert ".dict()" not in result
        assert count >= 1

    def test_bc005_renames_parse_obj(self):
        from uplift.migrator import _transform_bc005
        src = "order = Order.parse_obj(payload)\n"
        result, count = _transform_bc005(src)
        assert ".model_validate(" in result
        assert ".parse_obj(" not in result

    def test_bc005_renames_json(self):
        from uplift.migrator import _transform_bc005
        src = "return order.json()\n"
        result, count = _transform_bc005(src)
        assert ".model_dump_json()" in result

    def test_bc005_renames_copy(self):
        from uplift.migrator import _transform_bc005
        src = "new_order = order.copy(update={'discount': 5})\n"
        result, count = _transform_bc005(src)
        assert ".model_copy(" in result
        assert ".copy(" not in result

    def test_bc005_renames_schema(self):
        from uplift.migrator import _transform_bc005
        src = "schema = Order.schema()\n"
        result, count = _transform_bc005(src)
        assert ".model_json_schema()" in result


class TestApplyMigrations:
    def _make_usage_map(self, file_path: str) -> dict[str, list[dict]]:
        return {
            "BC-001": [{"file": file_path, "line": 1, "snippet": "from pydantic import BaseSettings"}],
            "BC-002": [],
            "BC-003": [],
            "BC-004": [],
            "BC-005": [],
            "BC-006": [],
        }

    def test_patches_file_in_assigned_set(self, tmp_path):
        from uplift.migrator import apply_migrations

        settings_file = tmp_path / "settings.py"
        settings_file.write_text(
            "from pydantic import BaseSettings\n\nclass App(BaseSettings):\n"
            "    x: str = 'a'\n\n    class Config:\n        env_prefix = 'X_'\n",
            encoding="utf-8",
        )

        file_path = str(settings_file)
        usage_map = self._make_usage_map(file_path)
        bc_list = _make_bc_list()

        changes = apply_migrations(usage_map, bc_list, assigned_files={file_path})

        result = settings_file.read_text(encoding="utf-8")
        assert "pydantic_settings" in result
        applied = [c for c in changes if c.get("applied")]
        assert len(applied) >= 1

    def test_does_not_patch_file_outside_assigned(self, tmp_path):
        from uplift.migrator import apply_migrations

        settings_file = tmp_path / "settings.py"
        original = "from pydantic import BaseSettings\n"
        settings_file.write_text(original, encoding="utf-8")

        file_path = str(settings_file)
        usage_map = self._make_usage_map(file_path)
        bc_list = _make_bc_list()

        # assigned_files does NOT include settings_file
        changes = apply_migrations(usage_map, bc_list, assigned_files={"other_file.py"})

        # File should be unchanged
        assert settings_file.read_text(encoding="utf-8") == original

    def test_bc006_goes_to_needs_human_review(self, tmp_path):
        from uplift.migrator import apply_migrations

        test_file = tmp_path / "test_models.py"
        test_file.write_text("with pytest.raises(TypeError):\n    pass\n", encoding="utf-8")

        file_path = str(test_file)
        usage_map = {bc_id: [] for bc_id in ["BC-001","BC-002","BC-003","BC-004","BC-005"]}
        usage_map["BC-006"] = [{"file": file_path, "line": 1, "snippet": "pytest.raises(TypeError)"}]

        bc_list = _make_bc_list()
        changes = apply_migrations(usage_map, bc_list, assigned_files=set())

        # BC-006 must be flagged as needs_human_review and NOT applied
        bc006_changes = [c for c in changes if c["bc_id"] == "BC-006"]
        assert len(bc006_changes) >= 1
        for c in bc006_changes:
            assert c["needs_human_review"] is True
            assert c["applied"] is False

        # Test file should NOT be modified by migrator
        assert test_file.read_text(encoding="utf-8") == "with pytest.raises(TypeError):\n    pass\n"

    def test_requirements_updated_when_in_assigned(self, tmp_path):
        from uplift.migrator import apply_migrations

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("pydantic>=1.10,<2\npytest>=8\n", encoding="utf-8")

        # Patch the path the migrator uses
        import uplift.migrator as mig_module
        orig_req = None

        # We pass requirements.txt as a path — migrator uses Path("requirements.txt")
        # We need to temporarily chdir to tmp_path
        import os
        orig_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            usage_map = {bc_id: [] for bc_id in ["BC-001","BC-002","BC-003","BC-004","BC-005","BC-006"]}
            bc_list = _make_bc_list()
            changes = apply_migrations(usage_map, bc_list, assigned_files={"requirements.txt"})
        finally:
            os.chdir(orig_cwd)

        result = req_file.read_text(encoding="utf-8")
        assert "pydantic>=2" in result
        assert "pydantic-settings" in result
        assert "pydantic>=1.10,<2" not in result


# ---------------------------------------------------------------------------
# 10. needs_human_review passthrough in upgrade()
# ---------------------------------------------------------------------------

class TestUpgradeNeedsHumanReviewPassthrough:
    def test_needs_human_review_in_report(self, tmp_path):
        """Verify that BC-006 needs_human_review items make it into the report."""
        from uplift import orchestrator

        # Patch all stage functions
        bc_list = _make_bc_list()
        usage_map = {"BC-006": [{"file": "tests/test_models.py", "line": 58, "snippet": "TypeError"}]}
        for bc in bc_list:
            if bc["id"] != "BC-006":
                usage_map[bc["id"]] = []

        nhr_item = {
            "bc_id": "BC-006",
            "file": "tests/test_models.py",
            "line": 58,
            "reason": "Behavioral change: TypeError → ValidationError (frozen model)",
            "status": "auto-applied",
            "applied": False,
            "needs_human_review": True,
        }

        reports = tmp_path / "reports"
        reports.mkdir()
        report_path = reports / "upgrade-report.json"
        md_path = tmp_path / "UPGRADE_REPORT.md"

        orig_paths = {
            "BREAKING_CHANGES_PATH": orchestrator.BREAKING_CHANGES_PATH,
            "USAGE_MAP_PATH": orchestrator.USAGE_MAP_PATH,
            "UPGRADE_REPORT_PATH": orchestrator.UPGRADE_REPORT_PATH,
            "REPORTS_DIR": orchestrator.REPORTS_DIR,
        }
        orchestrator.BREAKING_CHANGES_PATH = reports / "breaking-changes.json"
        orchestrator.USAGE_MAP_PATH = reports / "usage-map.json"
        orchestrator.UPGRADE_REPORT_PATH = report_path
        orchestrator.REPORTS_DIR = reports

        try:
            with patch("uplift.orchestrator.run_changelog_analyst", return_value=bc_list), \
                 patch("uplift.orchestrator.run_usage_scanner", return_value=usage_map), \
                 patch("uplift.orchestrator.run_code_migrators", return_value=[nhr_item]), \
                 patch("uplift.orchestrator.run_verifier", return_value=(True, [{"attempt": 1, "passed": True, "failure_count": 0}])), \
                 patch("uplift.orchestrator.write_upgrade_report") as mock_write:
                orchestrator.upgrade("pydantic")

            # Capture what was passed to write_upgrade_report
            call_args = mock_write.call_args
            report_data = call_args[0][0]

            assert len(report_data["needs_human_review"]) == 1
            assert report_data["needs_human_review"][0]["bc_id"] == "BC-006"
            assert report_data["final_status"] == "green"
        finally:
            for k, v in orig_paths.items():
                setattr(orchestrator, k, v)


# ---------------------------------------------------------------------------
# --force flag tests
# ---------------------------------------------------------------------------

class TestForceFlag:
    """Tests for the --force CLI flag and its effect on the pipeline."""

    def test_force_flag_parsed(self):
        from uplift.__main__ import build_parser
        parser = build_parser()
        args = parser.parse_args(["upgrade", "pydantic", "--force"])
        assert args.force is True

    def test_force_flag_default_false(self):
        from uplift.__main__ import build_parser
        parser = build_parser()
        args = parser.parse_args(["upgrade", "pydantic"])
        assert args.force is False

    def test_force_flag_in_help(self):
        from uplift.__main__ import build_parser
        import io
        parser = build_parser()
        buf = io.StringIO()
        try:
            parser.parse_args(["upgrade", "--help"])
        except SystemExit:
            pass
        # Capture help via format_help on the upgrade sub-parser
        for action in parser._subparsers._group_actions:
            for name, subparser in action.choices.items():
                if name == "upgrade":
                    help_text = subparser.format_help()
                    assert "--force" in help_text

    def test_force_flag_calls_upgrade_with_force_true(self):
        from uplift.__main__ import main
        with patch("uplift.__main__.upgrade", return_value=True) as mock_up:
            rc = main(["upgrade", "pydantic", "--force"])
        mock_up.assert_called_once_with("pydantic", force=True)
        assert rc == 0

    def test_no_force_flag_calls_upgrade_with_force_false(self):
        from uplift.__main__ import main
        with patch("uplift.__main__.upgrade", return_value=True) as mock_up:
            rc = main(["upgrade", "pydantic"])
        mock_up.assert_called_once_with("pydantic", force=False)
        assert rc == 0

    def test_force_bypasses_cached_breaking_changes(self, tmp_path):
        """With force=True, existing breaking-changes.json is ignored and regenerated."""
        reports = tmp_path / "reports"
        reports.mkdir()
        docs = tmp_path / "docs"
        docs.mkdir()
        guide = docs / "migration-guide.md"
        guide.write_text(
            "\n".join(
                f"## {i}. Section {i}\n\nDesc {i}.\n\n```python\n# v1\nold_{i}()\n```\n\n"
                f"```python\n# v2\nnew_{i}()\n```\n"
                for i in range(1, 7)
            ),
            encoding="utf-8",
        )
        # Pre-populate the cache with a sentinel that would signal a cache hit
        stale_data = [{"id": "STALE", "title": "stale"}]
        (reports / "breaking-changes.json").write_text(json.dumps(stale_data), encoding="utf-8")

        from uplift import orchestrator
        orig_bc_path = orchestrator.BREAKING_CHANGES_PATH
        orig_guide_path = orchestrator.MIGRATION_GUIDE_PATH
        orig_reports_dir = orchestrator.REPORTS_DIR
        orchestrator.BREAKING_CHANGES_PATH = reports / "breaking-changes.json"
        orchestrator.MIGRATION_GUIDE_PATH = guide
        orchestrator.REPORTS_DIR = reports
        try:
            result = orchestrator.run_changelog_analyst(force=True)
        finally:
            orchestrator.BREAKING_CHANGES_PATH = orig_bc_path
            orchestrator.MIGRATION_GUIDE_PATH = orig_guide_path
            orchestrator.REPORTS_DIR = orig_reports_dir

        # Must NOT return the stale sentinel; must return fresh 6-entry list
        assert len(result) == 6
        assert result[0]["id"] == "BC-001"

    def test_force_bypasses_cached_usage_map(self, tmp_path):
        """With force=True, existing usage-map.json is ignored and re-scanned."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "settings.py").write_text("from pydantic import BaseSettings\n", encoding="utf-8")
        reports = tmp_path / "reports"
        reports.mkdir()
        # Pre-populate with stale/empty map
        stale = {"BC-001": [], "BC-002": [], "BC-003": [], "BC-004": [], "BC-005": [], "BC-006": []}
        (reports / "usage-map.json").write_text(json.dumps(stale), encoding="utf-8")

        from uplift import orchestrator
        orig_usage = orchestrator.USAGE_MAP_PATH
        orig_src = orchestrator.SRC_ROOT
        orig_test = orchestrator.TEST_ROOT
        orig_reports = orchestrator.REPORTS_DIR
        orchestrator.USAGE_MAP_PATH = reports / "usage-map.json"
        orchestrator.SRC_ROOT = src
        orchestrator.TEST_ROOT = tmp_path / "nonexistent_tests"
        orchestrator.REPORTS_DIR = reports
        try:
            result = orchestrator.run_usage_scanner(_make_bc_list(), force=True)
        finally:
            orchestrator.USAGE_MAP_PATH = orig_usage
            orchestrator.SRC_ROOT = orig_src
            orchestrator.TEST_ROOT = orig_test
            orchestrator.REPORTS_DIR = orig_reports

        # Must have found the real usage in settings.py
        assert any("settings.py" in u["file"] for u in result["BC-001"])

    def test_force_output_lines(self, tmp_path, capsys):
        """force=True prints the canonical '[analyst] extracted N ...' lines."""
        reports = tmp_path / "reports"
        reports.mkdir()
        docs = tmp_path / "docs"
        docs.mkdir()
        guide = docs / "migration-guide.md"
        guide.write_text(
            "\n".join(
                f"## {i}. Section {i}\n\nDesc {i}.\n\n```python\n# v1\nold_{i}()\n```\n\n"
                f"```python\n# v2\nnew_{i}()\n```\n"
                for i in range(1, 7)
            ),
            encoding="utf-8",
        )

        from uplift import orchestrator
        orig_bc_path = orchestrator.BREAKING_CHANGES_PATH
        orig_guide_path = orchestrator.MIGRATION_GUIDE_PATH
        orig_reports_dir = orchestrator.REPORTS_DIR
        orchestrator.BREAKING_CHANGES_PATH = reports / "breaking-changes.json"
        orchestrator.MIGRATION_GUIDE_PATH = guide
        orchestrator.REPORTS_DIR = reports
        try:
            bc_list = orchestrator.run_changelog_analyst(force=True)
        finally:
            orchestrator.BREAKING_CHANGES_PATH = orig_bc_path
            orchestrator.MIGRATION_GUIDE_PATH = orig_guide_path
            orchestrator.REPORTS_DIR = orig_reports_dir

        captured = capsys.readouterr()
        assert "[analyst] extracted" in captured.out
        assert "6" in captured.out

    def test_force_scanner_output_lines(self, tmp_path, capsys):
        """force=True on scanner prints '[scanner] found N usage sites'."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "s.py").write_text("from pydantic import BaseSettings\n", encoding="utf-8")
        reports = tmp_path / "reports"
        reports.mkdir()

        from uplift import orchestrator
        orig_usage = orchestrator.USAGE_MAP_PATH
        orig_src = orchestrator.SRC_ROOT
        orig_test = orchestrator.TEST_ROOT
        orig_reports = orchestrator.REPORTS_DIR
        orchestrator.USAGE_MAP_PATH = reports / "usage-map.json"
        orchestrator.SRC_ROOT = src
        orchestrator.TEST_ROOT = tmp_path / "nonexistent_tests"
        orchestrator.REPORTS_DIR = reports
        try:
            orchestrator.run_usage_scanner(_make_bc_list(), force=True)
        finally:
            orchestrator.USAGE_MAP_PATH = orig_usage
            orchestrator.SRC_ROOT = orig_src
            orchestrator.TEST_ROOT = orig_test
            orchestrator.REPORTS_DIR = orig_reports

        captured = capsys.readouterr()
        assert "[scanner] found" in captured.out
        assert "usage sites" in captured.out
