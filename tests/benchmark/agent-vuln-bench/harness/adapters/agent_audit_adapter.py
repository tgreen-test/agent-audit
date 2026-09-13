"""
Agent-Audit Adapter for Agent-Vuln-Bench.

Integrates agent-audit scanner with the benchmark harness.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .base_adapter import BaseAdapter, ToolFinding, ToolNotAvailable, normalize_severity

# The in-repo package directory. The adapter shells out to `-m agent_audit`, which
# normally resolves through an editable install. If that install is missing or stale
# (e.g. the repo was moved after `pip install -e`), the subprocess would fail with
# ModuleNotFoundError. Putting the working tree on the child's PYTHONPATH makes the
# benchmark runnable from a bare checkout and pins it to *this* source tree rather
# than to whatever happens to be in site-packages.
#   adapters/ -> harness/ -> agent-vuln-bench/ -> benchmark/ -> tests/ -> <repo root>
_REPO_ROOT = Path(__file__).resolve().parents[5]
_PACKAGE_DIR = _REPO_ROOT / "packages" / "audit"


def _child_env() -> Dict[str, str]:
    """Return a copy of the environment with the in-repo package on PYTHONPATH."""
    env = dict(os.environ)
    if not _PACKAGE_DIR.is_dir():
        return env
    existing = env.get("PYTHONPATH", "")
    parts = [str(_PACKAGE_DIR)] + ([existing] if existing else [])
    return {**env, "PYTHONPATH": os.pathsep.join(parts)}


def _stderr_tail(stderr: str, limit: int = 400) -> str:
    """Condense subprocess stderr for inclusion in an exception message."""
    text = (stderr or "").strip()
    if not text:
        return "<empty stderr>"
    return text[-limit:]


class AgentAuditAdapter(BaseAdapter):
    """Adapter for agent-audit SAST tool."""

    def __init__(self, rule_mapping_path: Optional[str] = None):
        """
        Initialize the adapter.

        Args:
            rule_mapping_path: Path to OWASP mapping YAML for rule-to-set mapping.
        """
        self._version: Optional[str] = None
        self._rule_to_set: Dict[str, str] = {}
        self._rule_to_type: Dict[str, str] = {}

        # Load rule mapping if available
        if rule_mapping_path and os.path.exists(rule_mapping_path):
            self._load_rule_mapping(rule_mapping_path)
        else:
            # Try default location
            default_path = Path(__file__).parent.parent.parent / "taxonomy" / "owasp_agentic_mapping.yaml"
            if default_path.exists():
                self._load_rule_mapping(str(default_path))

    def _load_rule_mapping(self, path: str) -> None:
        """Load rule-to-set mapping from YAML."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                self._rule_to_set = data.get("rule_to_set_map", {})
        except Exception:
            pass

    def get_tool_name(self) -> str:
        return "agent-audit"

    def get_tool_version(self) -> str:
        if self._version is None:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "agent_audit", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=_child_env(),
                )
                # A non-zero exit means the module could not even be imported. Do NOT
                # fall through to parsing the output: `output.split()[-1]` on
                # "... No module named agent_audit" yields the plausible-looking string
                # "agent_audit", which is how a dead tool previously reported a version.
                if result.returncode != 0:
                    raise ToolNotAvailable(
                        f"`{sys.executable} -m agent_audit --version` exited "
                        f"{result.returncode}: {_stderr_tail(result.stderr)}"
                    )
                output = result.stdout.strip() or result.stderr.strip()
                if output:
                    # Handle various version formats
                    self._version = output.split()[-1]
                else:
                    self._version = "unknown"
            except ToolNotAvailable:
                raise
            except Exception as e:
                raise ToolNotAvailable(f"agent-audit not available: {e}")
        return self._version

    def scan(self, project_path: str) -> List[ToolFinding]:
        """
        Run agent-audit scan and return findings.

        Args:
            project_path: Path to scan (file or directory).

        Returns:
            List of standardized ToolFinding objects.
        """
        # NOTE ON FAILURE SEMANTICS: this method must never convert "the scanner did not
        # run" into "the scanner found nothing". A genuinely clean scan emits valid JSON
        # with an empty findings list; anything unparseable is a harness/tool failure and
        # is raised so the harness reports ERROR instead of scoring the sample as all-FN.
        # (This silent `return []` is what produced 12/12 FN at 0.0s each — see
        # NIGHT_RUN_LEDGER.md W0.) The scanner exits non-zero when it finds BLOCK-tier
        # issues, so return code alone is NOT a failure signal — parseability is.
        try:
            # Run agent-audit with JSON output
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agent_audit",
                    "scan",
                    project_path,
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=300,
                env=_child_env(),
            )

            # Parse JSON output
            output = result.stdout
            if not output.strip():
                # Check if it's in stderr
                if result.stderr and result.stderr.strip().startswith("{"):
                    output = result.stderr
                else:
                    raise ToolNotAvailable(
                        f"agent-audit produced no output scanning {project_path} "
                        f"(exit {result.returncode}): {_stderr_tail(result.stderr)}"
                    )

            data = self._parse_json_output(output, project_path, result)

            # Handle both list and dict with 'findings' key
            if isinstance(data, list):
                raw_findings = data
            elif isinstance(data, dict):
                raw_findings = data.get("findings", [])
            else:
                raise ToolNotAvailable(
                    f"agent-audit returned unexpected JSON type {type(data).__name__} "
                    f"scanning {project_path}"
                )

            return [self._convert_finding(f) for f in raw_findings]

        except subprocess.TimeoutExpired:
            raise ToolNotAvailable("agent-audit scan timed out after 300 seconds")
        except FileNotFoundError:
            raise ToolNotAvailable("agent-audit not found in PATH")

    @staticmethod
    def _parse_json_output(
        output: str,
        project_path: str,
        result: "subprocess.CompletedProcess[str]",
    ) -> Any:
        """Parse scanner stdout as JSON, raising ToolNotAvailable if it cannot be read."""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        # Rich/CLI banners can precede the payload; look for a JSON object per line.
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        raise ToolNotAvailable(
            f"agent-audit output was not parseable JSON scanning {project_path} "
            f"(exit {result.returncode}): stdout={output[:200]!r} "
            f"stderr={_stderr_tail(result.stderr)}"
        )

    def _convert_finding(self, finding: Dict[str, Any]) -> ToolFinding:
        """Convert agent-audit finding to standardized format."""
        # Extract file path
        location = finding.get("location", {})
        file_path = location.get("file_path", finding.get("file", ""))

        # Extract line number
        line = location.get("start_line", finding.get("line", 0))
        if isinstance(line, str):
            line = int(line) if line.isdigit() else 0

        # Extract rule ID
        rule_id = finding.get("rule_id", finding.get("id", "unknown"))

        # Normalize severity
        severity = normalize_severity(finding.get("severity", "MEDIUM"))

        # Get confidence
        confidence = finding.get("confidence", 1.0)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 1.0

        # Get tier (v2: BLOCK | WARN | INFO | SUPPRESSED)
        tier = finding.get("tier", "WARN")
        if not isinstance(tier, str):
            tier = "WARN"

        # Map to benchmark categories
        mapped_set = self._rule_to_set.get(rule_id, "")
        mapped_type = self._map_rule_to_type(rule_id)

        # v0.13.0: Extract taint analysis data for benchmark evaluation
        tool_specific: Dict[str, Any] = {
            "owasp_id": finding.get("owasp_id", ""),
            "cwe_id": finding.get("cwe_id", ""),
            "needs_review": finding.get("needs_review", False),
        }

        # Check for taint_analysis in metadata
        metadata = finding.get("metadata", {})
        taint_analysis = metadata.get("taint_analysis", {})

        if taint_analysis:
            dangerous_flows = taint_analysis.get("dangerous_flows", [])
            if dangerous_flows:
                # Extract taint source and sink from first flow
                first_flow = dangerous_flows[0]
                # Map sink_type to benchmark-compatible format
                sink_type = first_flow.get("sink_type", "")
                source_var = first_flow.get("var", "")

                # Map internal types to oracle-compatible types
                # Oracle source types: user_input, llm_output, config, variable, literal
                source_type_map = {
                    "function_param": "user_input",
                    "env_var": "config",
                    "user_input": "user_input",
                    "network": "user_input",
                    "file_read": "user_input",
                    "llm_output": "llm_output",
                }

                # Oracle sink types: eval, code_execution, shell_execution, sql_execution
                # Don't remap - pass through the type from the finding
                sink_type_map = {
                    "shell_exec": "shell_execution",
                    "code_exec": "code_execution",
                    "sql_exec": "sql_execution",
                    "file_write": "file_write",
                    "network_req": "http_request",
                    # Pass through for already-correct types
                    "shell_execution": "shell_execution",
                    "code_execution": "code_execution",
                    "eval": "eval",
                    "sql_execution": "sql_execution",
                }

                # Add taint info in format expected by oracle_eval.validates_taint_flow
                tool_specific["taint_source"] = source_type_map.get(
                    first_flow.get("source", "function_param"), "user_input"
                )
                tool_specific["taint_sink"] = sink_type_map.get(sink_type, sink_type)
                tool_specific["source"] = source_var
                tool_specific["sink"] = first_flow.get("sink", "")
                tool_specific["taint_path"] = first_flow.get("path", [])
                tool_specific["taint_confidence"] = first_flow.get("confidence", 0.0)

        return ToolFinding(
            file=file_path,
            line=line,
            rule_id=rule_id,
            severity=severity,
            message=finding.get("message", finding.get("title", "")),
            confidence=confidence,
            tier=tier,
            mapped_vuln_type=mapped_type,
            mapped_set=mapped_set,
            end_line=location.get("end_line"),
            snippet=location.get("snippet", ""),
            tool_specific=tool_specific,
        )

    def _map_rule_to_type(self, rule_id: str) -> str:
        """Map rule ID to vulnerability type."""
        type_map = {
            "AGENT-004": "hardcoded_credential",
            "AGENT-010": "unsanitized_tool_args",
            "AGENT-011": "prompt_injection",
            "AGENT-026": "tool_input_unsanitized",
            "AGENT-027": "system_prompt_injectable",
            "AGENT-029": "mcp_overpermissive",
            "AGENT-030": "mcp_no_confirm",
            "AGENT-031": "mcp_wide_access",
            "AGENT-032": "mcp_no_tls",
            "AGENT-033": "mcp_env_exposed",
            "AGENT-034": "eval_exec",
            "AGENT-035": "unrestricted_file",
            "AGENT-036": "shell_injection",
            "AGENT-037": "ssrf",
            "AGENT-043": "daemon_privilege",
        }
        return type_map.get(rule_id, "other")
