"""Regression guards for the Agent-Vuln-Bench agent-audit adapter.

These exist because of the failure recorded in NIGHT_RUN_LEDGER.md (W0): a broken
editable install made ``python3 -m agent_audit`` unimportable, the adapter swallowed
the resulting empty output with a bare ``return []``, and the benchmark reported
0.0% recall across all 12 KNOWN samples at 0.0s each — indistinguishable, from the
outside, from a total detection failure.

The invariant under test: the adapter must never report "the scanner found nothing"
when what actually happened is "the scanner did not run".
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_ROOT = REPO_ROOT / "tests" / "benchmark"
PACKAGE_DIR = REPO_ROOT / "packages" / "audit"


def _load_adapter_module():
    """Import the adapter through its hyphenated package path.

    ``agent-vuln-bench`` cannot be imported with an ``import`` statement because of the
    hyphen; the harness itself is run as ``python -m "agent-vuln-bench.harness.run_eval"``.
    """
    if str(BENCH_ROOT) not in sys.path:
        sys.path.insert(0, str(BENCH_ROOT))
    return importlib.import_module(
        "agent-vuln-bench.harness.adapters.agent_audit_adapter"
    )


@pytest.fixture(scope="module")
def adapter_module():
    return _load_adapter_module()


def test_agent_audit_importable_in_subprocess():
    """`python -m agent_audit --version` must work in a child process.

    The root pytest run puts the repo on sys.path itself, so an in-process
    ``import agent_audit`` proves nothing about the installed distribution. The
    benchmark adapter shells out, so the child process is what has to work.
    """
    env = _load_adapter_module()._child_env()
    result = subprocess.run(
        [sys.executable, "-m", "agent_audit", "--version"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    assert result.returncode == 0, (
        "`python -m agent_audit --version` failed in a subprocess. This is the exact "
        "condition that produced a silent 0.0% benchmark recall.\n"
        f"exit={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


def test_child_env_puts_working_tree_on_pythonpath(adapter_module):
    """The adapter must pin the subprocess to this source tree, not site-packages."""
    env = adapter_module._child_env()
    assert str(PACKAGE_DIR) in env["PYTHONPATH"].split(":")


def test_version_probe_rejects_failed_subprocess(adapter_module, monkeypatch):
    """A non-zero `--version` exit must raise, not yield a fake version string.

    Before the fix, ``output.split()[-1]`` applied to
    ``"…/python3.14: No module named agent_audit"`` produced the version
    ``"agent_audit"``, which looked plausible enough to appear in benchmark output.
    """

    class _Failed:
        returncode = 1
        stdout = ""
        stderr = "/opt/homebrew/bin/python3.14: No module named agent_audit\n"

    monkeypatch.setattr(adapter_module.subprocess, "run", lambda *a, **k: _Failed())

    adapter = adapter_module.AgentAuditAdapter()
    with pytest.raises(adapter_module.ToolNotAvailable) as exc:
        adapter.get_tool_version()
    assert "No module named agent_audit" in str(exc.value)


def test_version_probe_never_returns_module_name(adapter_module, monkeypatch):
    """Explicitly pin the original bug: the version must not become 'agent_audit'."""

    class _Failed:
        returncode = 1
        stdout = ""
        stderr = "/usr/bin/python3: No module named agent_audit\n"

    monkeypatch.setattr(adapter_module.subprocess, "run", lambda *a, **k: _Failed())
    adapter = adapter_module.AgentAuditAdapter()
    with pytest.raises(adapter_module.ToolNotAvailable):
        version = adapter.get_tool_version()
        assert version != "agent_audit"  # pragma: no cover - reached only on regression


def test_scan_raises_on_empty_output(adapter_module, monkeypatch, tmp_path):
    """Empty stdout from the scanner is a failure, not an empty result set."""

    class _Empty:
        returncode = 1
        stdout = ""
        stderr = "/usr/bin/python3: No module named agent_audit\n"

    monkeypatch.setattr(adapter_module.subprocess, "run", lambda *a, **k: _Empty())

    adapter = adapter_module.AgentAuditAdapter()
    with pytest.raises(adapter_module.ToolNotAvailable):
        adapter.scan(str(tmp_path))


def test_scan_raises_on_unparseable_output(adapter_module, monkeypatch, tmp_path):
    """Non-JSON stdout (e.g. a traceback) is a failure, not an empty result set."""

    class _Garbage:
        returncode = 1
        stdout = "Traceback (most recent call last):\n  ImportError: boom\n"
        stderr = ""

    monkeypatch.setattr(adapter_module.subprocess, "run", lambda *a, **k: _Garbage())

    adapter = adapter_module.AgentAuditAdapter()
    with pytest.raises(adapter_module.ToolNotAvailable):
        adapter.scan(str(tmp_path))


def test_scan_accepts_genuinely_empty_findings(adapter_module, monkeypatch, tmp_path):
    """A clean scan reports valid JSON with no findings — that must NOT raise."""

    class _Clean:
        returncode = 0
        stdout = '{"findings": []}'
        stderr = ""

    monkeypatch.setattr(adapter_module.subprocess, "run", lambda *a, **k: _Clean())

    adapter = adapter_module.AgentAuditAdapter()
    assert adapter.scan(str(tmp_path)) == []


def test_scan_tolerates_nonzero_exit_with_valid_json(adapter_module, monkeypatch, tmp_path):
    """The scanner exits non-zero when it finds BLOCK-tier issues; that is success."""

    class _Findings:
        returncode = 1
        stdout = (
            '{"findings": [{"rule_id": "AGENT-034", "severity": "HIGH", '
            '"location": {"file_path": "a.py", "start_line": 3}}]}'
        )
        stderr = ""

    monkeypatch.setattr(adapter_module.subprocess, "run", lambda *a, **k: _Findings())

    adapter = adapter_module.AgentAuditAdapter()
    findings = adapter.scan(str(tmp_path))
    assert len(findings) == 1
    assert findings[0].rule_id == "AGENT-034"
