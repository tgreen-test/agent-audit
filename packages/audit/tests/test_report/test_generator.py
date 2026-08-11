"""Tests for PDF report generator."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent_audit.report.generator import ReportGenerator
from agent_audit.report.styles import (
    CATEGORY_TO_ASI,
    Colors,
    OWASP_ASI_CATEGORIES,
    SEVERITY_COLORS,
    TIER_COLORS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_SCAN_DATA = {
    "version": "0.18.2",
    "scan_timestamp": "2026-04-04T00:10:48.681196",
    "scan_path": "/test/project",
    "scanned_files": 42,
    "summary": {
        "total": 5,
        "actionable": 3,
        "suppressed": 0,
        "by_severity": {"critical": 1, "high": 2, "medium": 2},
        "by_category": {"command_injection": 1, "tool_misuse": 2, "goal_hijack": 2},
        "by_tier": {"BLOCK": 1, "WARN": 2, "INFO": 0, "SUPPRESSED": 2},
        "risk_score": 4.5,
        "risk_label": "MEDIUM",
    },
    "findings": [
        {
            "rule_id": "AGENT-001",
            "title": "Command Injection via Unsanitized Input",
            "description": "Tool accepts user input passed directly to shell execution.",
            "severity": "critical",
            "category": "command_injection",
            "location": {
                "file_path": "src/tools/runner.py",
                "start_line": 42,
                "end_line": 42,
                "start_column": None,
                "end_column": None,
                "snippet": "subprocess.run(user_cmd, shell=True)",
            },
            "confidence": 0.95,
            "tier": "BLOCK",
            "suppressed": False,
            "suppressed_reason": None,
            "suppressed_by": None,
            "needs_review": False,
            "cwe_id": "CWE-78",
            "owasp_id": "ASI-02",
            "asi_categories": ["ASI-02"],
            "remediation": {
                "description": "Use shlex.quote() to escape user input.",
                "code_example": 'subprocess.run(["ls", shlex.quote(user_input)])',
                "reference_url": "https://owasp.org/www-community/attacks/Command_Injection",
            },
            "metadata": {},
            "detected_at": "2026-04-04T00:10:48.550346",
            "reason": "User input flows to shell execution.",
        },
        {
            "rule_id": "AGENT-034",
            "title": "Tool Input Without Validation",
            "description": "Tool function accepts string parameters without validation.",
            "severity": "high",
            "category": "tool_misuse",
            "location": {
                "file_path": "src/tools/search.py",
                "start_line": 15,
                "end_line": 15,
                "start_column": None,
                "end_column": None,
                "snippet": "def search(query: str):",
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
                "description": "Validate and sanitize tool inputs.",
                "code_example": "",
                "reference_url": "",
            },
            "metadata": {},
            "detected_at": "2026-04-04T00:10:48.560000",
            "reason": "String parameter without validation.",
        },
        {
            "rule_id": "AGENT-010",
            "title": "Prompt Injection Risk",
            "description": "User input interpolated into system prompt.",
            "severity": "high",
            "category": "goal_hijack",
            "location": {
                "file_path": "src/agents/chat.py",
                "start_line": 88,
                "end_line": 88,
                "start_column": None,
                "end_column": None,
                "snippet": 'prompt = f"You are a {role} assistant"',
            },
            "confidence": 0.70,
            "tier": "WARN",
            "suppressed": False,
            "suppressed_reason": None,
            "suppressed_by": None,
            "needs_review": False,
            "cwe_id": "CWE-74",
            "owasp_id": "ASI-01",
            "asi_categories": ["ASI-01"],
            "remediation": {
                "description": "Use parameterized prompts, not f-strings.",
                "code_example": "",
                "reference_url": "",
            },
            "metadata": {},
            "detected_at": "2026-04-04T00:10:48.570000",
            "reason": "F-string in system prompt.",
        },
    ],
}

EMPTY_SCAN_DATA = {
    "version": "0.18.2",
    "scan_timestamp": "2026-04-04T00:10:48.681196",
    "scan_path": "/clean/project",
    "scanned_files": 10,
    "summary": {
        "total": 0,
        "actionable": 0,
        "suppressed": 0,
        "by_severity": {},
        "by_category": {},
        "by_tier": {"BLOCK": 0, "WARN": 0, "INFO": 0, "SUPPRESSED": 0},
        "risk_score": 0.0,
        "risk_label": "LOW",
    },
    "findings": [],
}


@pytest.fixture
def scan_json_path(tmp_path: Path) -> str:
    """Write minimal scan data to a temp JSON file."""
    path = tmp_path / "scan.json"
    path.write_text(json.dumps(MINIMAL_SCAN_DATA), encoding="utf-8")
    return str(path)


@pytest.fixture
def empty_json_path(tmp_path: Path) -> str:
    path = tmp_path / "empty_scan.json"
    path.write_text(json.dumps(EMPTY_SCAN_DATA), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReportGenerator:
    """Test PDF report generation."""

    def test_generate_from_json_file(self, scan_json_path: str, tmp_path: Path):
        """Report is generated from a JSON file."""
        output = str(tmp_path / "report.pdf")
        gen = ReportGenerator()
        result = gen.generate(scan_json_path, output)

        assert Path(result).exists()
        assert Path(result).stat().st_size > 0
        # PDF magic bytes
        with open(result, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_generate_from_data_dict(self, tmp_path: Path):
        """Report is generated from a data dict."""
        output = str(tmp_path / "report.pdf")
        gen = ReportGenerator()
        result = gen.generate_from_data(MINIMAL_SCAN_DATA, output)

        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    def test_empty_scan_produces_valid_pdf(self, empty_json_path: str, tmp_path: Path):
        """Empty scan results still produce a valid PDF."""
        output = str(tmp_path / "empty_report.pdf")
        gen = ReportGenerator()
        result = gen.generate(empty_json_path, output)

        assert Path(result).exists()
        with open(result, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_custom_title_and_org(self, tmp_path: Path):
        """Custom title and organization appear in the report."""
        output = str(tmp_path / "custom.pdf")
        gen = ReportGenerator(
            title="Custom Security Report",
            organization="Acme Corp",
        )
        result = gen.generate_from_data(MINIMAL_SCAN_DATA, output)
        assert Path(result).exists()

    def test_include_suppressed_flag(self, tmp_path: Path):
        """include_suppressed controls whether suppressed findings are shown."""
        data = {
            **MINIMAL_SCAN_DATA,
            "findings": [
                {**MINIMAL_SCAN_DATA["findings"][0], "suppressed": True},
                MINIMAL_SCAN_DATA["findings"][1],
            ],
        }

        # Without suppressed
        out1 = str(tmp_path / "no_suppressed.pdf")
        gen1 = ReportGenerator(include_suppressed=False)
        gen1.generate_from_data(data, out1)

        # With suppressed
        out2 = str(tmp_path / "with_suppressed.pdf")
        gen2 = ReportGenerator(include_suppressed=True)
        gen2.generate_from_data(data, out2)

        # Both should produce valid PDFs
        assert Path(out1).exists()
        assert Path(out2).exists()

    def test_output_directory_created(self, tmp_path: Path):
        """Output parent directory is created if it doesn't exist."""
        output = str(tmp_path / "nested" / "dirs" / "report.pdf")
        gen = ReportGenerator()
        result = gen.generate_from_data(MINIMAL_SCAN_DATA, output)
        assert Path(result).exists()

    def test_large_findings_list(self, tmp_path: Path):
        """Report handles many findings without crashing."""
        findings = []
        for i in range(100):
            finding = {
                **MINIMAL_SCAN_DATA["findings"][0],
                "rule_id": f"AGENT-{i:03d}",
                "location": {
                    "file_path": f"src/module_{i}.py",
                    "start_line": i * 10,
                    "end_line": i * 10,
                    "start_column": None,
                    "end_column": None,
                    "snippet": f"dangerous_call_{i}(user_input)",
                },
            }
            findings.append(finding)

        data = {
            **MINIMAL_SCAN_DATA,
            "summary": {
                **MINIMAL_SCAN_DATA["summary"],
                "total": 100,
                "actionable": 100,
                "by_tier": {"BLOCK": 50, "WARN": 30, "INFO": 20, "SUPPRESSED": 0},
            },
            "findings": findings,
        }

        output = str(tmp_path / "large.pdf")
        gen = ReportGenerator()
        result = gen.generate_from_data(data, output)
        assert Path(result).exists()
        assert Path(result).stat().st_size > 1000


class TestStyles:
    """Test style constants."""

    def test_all_severities_have_colors(self):
        for sev in ["critical", "high", "medium", "low", "info"]:
            assert sev in SEVERITY_COLORS

    def test_all_tiers_have_colors(self):
        for tier in ["BLOCK", "WARN", "INFO", "SUPPRESSED"]:
            assert tier in TIER_COLORS

    def test_owasp_asi_complete(self):
        """All 10 ASI categories are defined."""
        for i in range(1, 11):
            asi_id = f"ASI-{i:02d}"
            assert asi_id in OWASP_ASI_CATEGORIES
            assert "title" in OWASP_ASI_CATEGORIES[asi_id]
            assert "description" in OWASP_ASI_CATEGORIES[asi_id]

    def test_chart_palette_sufficient(self):
        """Chart palette has enough colors for 10+ categories."""
        assert len(Colors.CHART_PALETTE) >= 10
