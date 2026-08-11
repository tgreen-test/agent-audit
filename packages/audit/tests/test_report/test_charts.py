"""Tests for chart generation."""

from __future__ import annotations

import pytest

from agent_audit.report.charts import (
    HAS_MATPLOTLIB,
    create_category_chart,
    create_owasp_coverage_chart,
    create_risk_gauge,
    create_severity_bar_chart,
    create_tier_donut_chart,
)

pytestmark = pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")


class TestSeverityBarChart:

    def test_returns_png_bytes(self):
        data = {"critical": 5, "high": 10, "medium": 3}
        result = create_severity_bar_chart(data)
        assert isinstance(result, bytes)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_empty_data(self):
        result = create_severity_bar_chart({})
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_single_severity(self):
        result = create_severity_bar_chart({"high": 1})
        assert isinstance(result, bytes)


class TestTierDonutChart:

    def test_returns_png_bytes(self):
        data = {"BLOCK": 5, "WARN": 10, "INFO": 2, "SUPPRESSED": 20}
        result = create_tier_donut_chart(data)
        assert isinstance(result, bytes)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_empty_data(self):
        result = create_tier_donut_chart({})
        assert isinstance(result, bytes)


class TestCategoryChart:

    def test_returns_png_bytes(self):
        data = {"command_injection": 5, "goal_hijack": 3, "tool_misuse": 8}
        result = create_category_chart(data)
        assert isinstance(result, bytes)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_many_categories(self):
        data = {f"category_{i}": i + 1 for i in range(12)}
        result = create_category_chart(data)
        assert isinstance(result, bytes)


class TestRiskGauge:

    @pytest.mark.parametrize("score", [0.0, 2.5, 5.0, 7.5, 9.8])
    def test_various_scores(self, score: float):
        result = create_risk_gauge(score)
        assert isinstance(result, bytes)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"


class TestOWASPCoverageChart:

    def test_full_coverage(self):
        data = {f"ASI-{i:02d}": i for i in range(1, 11)}
        result = create_owasp_coverage_chart(data)
        assert isinstance(result, bytes)

    def test_partial_coverage(self):
        data = {"ASI-01": 3, "ASI-02": 5}
        result = create_owasp_coverage_chart(data)
        assert isinstance(result, bytes)

    def test_no_coverage(self):
        result = create_owasp_coverage_chart({})
        assert isinstance(result, bytes)
