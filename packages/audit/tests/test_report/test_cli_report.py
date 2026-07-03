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
