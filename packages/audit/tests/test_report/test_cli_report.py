"""Tests for the report CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from agent_audit.cli.main import cli


SCAN_DATA = {
    "version": "0.18.2",
    "scan_timestamp": "2026-04-04T00:10:48.681196",
    "scan_path": "/test/project",
    "scanned_files": 10,
    "summary": {
        "total": 2,
        "actionable": 2,
        "suppressed": 0,
        "by_severity": {"high": 2},
        "by_category": {"tool_misuse": 2},
        "by_tier": {"BLOCK": 0, "WARN": 2, "INFO": 0, "SUPPRESSED": 0},
        "risk_score": 3.2,
        "risk_label": "LOW-MEDIUM",
    },
    "findings": [
        {
            "rule_id": "AGENT-034",
            "title": "Tool Input Without Validation",
            "description": "String parameter without validation.",
            "severity": "high",
            "category": "tool_misuse",
            "location": {
                "file_path": "src/tool.py",
                "start_line": 10,
                "end_line": 10,
                "start_column": None,
                "end_column": None,
                "snippet": "def run(cmd: str):",
            },
            "confidence": 0.75,
            "tier": "WARN",
            "suppressed": False,
            "suppressed_reason": None,
            "suppressed_by": None,
            "needs_review": False,
            "cwe_id": "CWE-20",
            "owasp_id": "ASI-02",
            "asi_categories": ["ASI-02"],
            "remediation": {
                "description": "Validate inputs.",
                "code_example": "",
                "reference_url": "",
            },
            "metadata": {},
            "detected_at": "2026-04-04T00:10:48.550346",
            "reason": "No validation.",
        },
    ],
}


@pytest.fixture
def scan_json(tmp_path: Path) -> str:
    path = tmp_path / "scan.json"
    path.write_text(json.dumps(SCAN_DATA), encoding="utf-8")
    return str(path)


class TestReportCommand:

    def test_basic_report_generation(self, scan_json: str, tmp_path: Path):
        output = str(tmp_path / "report.pdf")
        runner = CliRunner()
        result = runner.invoke(cli, ["report", scan_json, "-o", output])
        assert result.exit_code == 0
        assert Path(output).exists()
        assert "Report generated" in result.output

    def test_default_output_name(self, scan_json: str, tmp_path: Path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["report", scan_json])
            assert result.exit_code == 0
            assert "Report generated" in result.output

    def test_custom_title(self, scan_json: str, tmp_path: Path):
        output = str(tmp_path / "custom.pdf")
        runner = CliRunner()
        result = runner.invoke(
            cli, ["report", scan_json, "-o", output, "--title", "My Report"]
        )
        assert result.exit_code == 0
        assert Path(output).exists()

    def test_nonexistent_input(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "/nonexistent/file.json"])
        assert result.exit_code != 0

    def test_verbose_output(self, scan_json: str, tmp_path: Path):
        output = str(tmp_path / "verbose.pdf")
        runner = CliRunner()
        result = runner.invoke(cli, ["-v", "report", scan_json, "-o", output])
        assert result.exit_code == 0
        assert "Input:" in result.output

    def test_help_text(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "--help"])
        assert result.exit_code == 0
        assert "PDF audit report" in result.output

    def test_missing_reportlab_names_the_extra(self, scan_json: str, monkeypatch):
        """The install instruction must survive Rich, not be eaten as a style tag.

        `reportlab` is only needed at generate time, so the `except ImportError` guard around
        the `ReportGenerator` import never runs and the message the user actually sees is
        `generator.py`'s "Install with: pip install agent-audit[report]", interpolated into a
        `console.print`. Rich parsed `[report]` as markup and rendered nothing for it, so the
        instruction read `pip install agent-audit` — which does not install reportlab. The
        extra is the entire content of the instruction, so it is what this asserts.

        RUN 11 checked this path by reading the code and recorded it as handled. It was not.
        """
        import sys

        class _BlockReportlab:
            def find_spec(self, name, path=None, target=None):
                if name == "reportlab" or name.startswith("reportlab."):
                    raise ImportError("reportlab is not installed (simulated)")
                return None

        monkeypatch.setattr(sys, "meta_path", [_BlockReportlab(), *sys.meta_path])
        # Both, and in this order. `generator.HAS_REPORTLAB` is decided once at import time,
        # so blocking the finder alone changes nothing for a module another test in this file
        # has already imported — the reason this test passed alone and failed in the file.
        for mod in [
            m for m in list(sys.modules)
            if m.startswith("reportlab") or m.startswith("agent_audit.report")
        ]:
            monkeypatch.delitem(sys.modules, mod)

        result = CliRunner().invoke(cli, ["report", scan_json])

        assert result.exit_code == 1
        assert "agent-audit[report]" in result.output, (
            "the extra was dropped from the install instruction: " + repr(result.output)
        )
