"""Issue #8 — three of four claims, and the shape of the one that is left.

The report (deer-flow, agent-audit 0.18.2, ~70% false positives on 136 findings) makes
four separate claims. Claim 1 — everything under `tests/` reported CRITICAL — was fixed
before v0.20.0 and is pinned elsewhere. These are the other three, each reproduced from
the reporter's own shape.

What changed here, and what did not:

  * **Claim 2, credential half — fixed.** `f"password={password}"` was AGENT-004,
    Hardcoded Credentials, at WARN/0.70. A hardcoded credential is by definition a
    literal in the source, and that value is entirely interpolation.

  * **Claim 2, SQL half — NOT fixed.** `conn.execute(f'CREATE DATABASE "{db_name}"')`
    where `db_name` comes from `urlparse(config_url)` still fires at BLOCK/1.0. There is
    no provenance model separating configuration from untrusted input, and `config_url`
    genuinely is a parameter of that function. Pinned below so the state is measured
    rather than remembered.

  * **Claim 3 — downgraded, not fixed.** A prompt f-string interpolating a local rather
    than one of the function's own inputs drops from BLOCK/1.0 to a lower tier. One step
    of distance is all this pass can see; `skills_list` is still parameter-derived
    transitively.

  * **Claim 4 — improved, not fixed.** `subprocess.run(["docker", "run", ..., image])`
    no longer carries a taint flow asserting a `shell_execution` sink reached from
    `user_input`, and no longer reports AGENT-034, *Tool Function Without Input
    Validation*, on a function that is not a tool. A finding remains on the line under
    AGENT-047, unsandboxed subprocess, which is at least a true statement.

That last one is the finding worth keeping from this work: **three separate producers
report that one line**, and gating two of them relocated the finding to the third rather
than removing it. Suppressing per-producer cannot answer a per-line complaint.
"""

from __future__ import annotations

import textwrap

import pytest

from agent_audit.scanners.python_scanner import PythonASTVisitor, PythonScanner


def _patterns(tmp_path, source: str, name: str = "sample.py"):
    path = tmp_path / name
    path.write_text(textwrap.dedent(source))
    return [
        pattern
        for result in PythonScanner().scan(path)
        for pattern in result.dangerous_patterns
    ]


def _of_type(patterns, kind):
    return [p for p in patterns if p.get("type") == kind]


class TestClaim2Credentials:
    """`f"password={password}"` is a format string, not a hardcoded credential."""

    def test_interpolated_credential_value_is_not_a_literal(self):
        from agent_audit.analysis.placeholder_detector import is_interpolated_value

        for value in ("{password}\\n", "${TOKEN}", "{{ secret }}", "%(password)s", "%s"):
            assert is_interpolated_value(value).is_placeholder, value

    def test_a_real_key_with_an_interpolated_tail_is_still_a_key(self):
        """`sk-{suffix}` keeps its literal prefix and must stay under analysis."""
        from agent_audit.analysis.placeholder_detector import is_interpolated_value

        for value in ("sk-{suffix}", "ghp_{token}", "AKIA{rest}"):
            assert not is_interpolated_value(value).is_placeholder, value

    def test_a_plain_literal_is_untouched(self):
        from agent_audit.analysis.placeholder_detector import is_interpolated_value

        assert not is_interpolated_value("sk-proj-abc123def456ghi789").is_placeholder


class TestClaim3PromptProvenance:
    def test_direct_parameter_interpolation_keeps_full_confidence(self, tmp_path):
        """The genuine injection vector: an inbound value straight into the prompt."""
        found = _of_type(
            _patterns(
                tmp_path,
                """
                def build_prompt(user_input: str) -> str:
                    return f"You are a helpful agent. User request: {user_input}"
                """,
            ),
            "prompt_return_fstring",
        )
        assert len(found) == 1
        assert "confidence" not in found[0], (
            "a directly-interpolated parameter was downgraded; the reported case and the "
            "real one would then be indistinguishable in the other direction"
        )

    def test_local_interpolation_is_downgraded(self, tmp_path):
        """The reporter's `<skill_system>` shape."""
        found = _of_type(
            _patterns(
                tmp_path,
                """
                def get_enabled_skills_for_config(config) -> str:
                    return "\\n".join(sorted(config.enabled_skills))


                def build_system_prompt(config) -> str:
                    skills_list = get_enabled_skills_for_config(config)
                    return f"<skill_system>{skills_list}</skill_system>"
                """,
            ),
            "prompt_return_fstring",
        )
        assert len(found) == 1
        assert found[0]["confidence"] == PythonASTVisitor.INDIRECT_PROMPT_CONFIDENCE

    def test_an_unresolvable_interpolation_is_not_downgraded(self, tmp_path):
        """`f"{fetch()}"` — nothing to resolve, so it must fail towards reporting."""
        found = _of_type(
            _patterns(
                tmp_path,
                """
                def build_prompt() -> str:
                    return f"System: {fetch_untrusted()}"
                """,
            ),
            "prompt_return_fstring",
        )
        assert len(found) == 1
        assert "confidence" not in found[0]

    def test_assigned_system_prompt_follows_the_same_rule(self, tmp_path):
        """The corpus fixture's shape: assignment rather than return, param interpolated."""
        found = _of_type(
            _patterns(
                tmp_path,
                """
                def create_agent(user_input: str):
                    system_prompt = f"You are a helpful agent. User request: {user_input}"
                    return system_prompt
                """,
            ),
            "system_prompt_fstring",
        )
        assert len(found) == 1
        assert "confidence" not in found[0]


class TestClaim4ArgvShape:
    def test_fixed_program_argv_is_not_a_shell_sink(self, tmp_path):
        """No taint flow may claim `cmd` reached a shell from user input."""
        found = _of_type(
            _patterns(
                tmp_path,
                """
                import subprocess


                def run_in_container(image: str, workdir: str):
                    cmd = ["docker", "run", "--rm", "-v", f"{workdir}:/work", image]
                    return subprocess.run(cmd, capture_output=True, check=False)
                """,
            ),
            "subprocess_expanded",
        )
        for pattern in found:
            flows = pattern.get("taint_analysis", {}).get("dangerous_flows", [])
            assert not [f for f in flows if f.get("sink_type") == "shell_execution"], (
                "a fixed argv with a named program is still reported as reaching a shell"
            )

    @pytest.mark.parametrize(
        "argv",
        [
            '["sh", "-c", cmd]',
            '["bash", "-lc", cmd]',
            '["python3", "-c", cmd]',
            '["env", cmd]',
            '["sudo", cmd]',
        ],
    )
    def test_an_interpreter_in_position_zero_is_not_a_fixed_program(self, tmp_path, argv):
        """Naming `sh` fixes nothing — the argument is still a command."""
        import ast

        from agent_audit.analysis.argv_shape import is_fixed_program_argv

        source = f"subprocess.run({argv})"
        call = ast.parse(source).body[0].value
        assert not is_fixed_program_argv(call, "subprocess.run", None)

    def test_shell_true_is_never_a_fixed_program(self, tmp_path):
        import ast

        from agent_audit.analysis.argv_shape import is_fixed_program_argv

        call = ast.parse('subprocess.run(["docker", "run"], shell=True)').body[0].value
        assert not is_fixed_program_argv(call, "subprocess.run", None)

    def test_a_reassigned_argv_is_not_resolved(self, tmp_path):
        """Two literals for one name: which one reaches the call is not decidable here."""
        import ast

        from agent_audit.analysis.argv_shape import is_fixed_program_argv

        module = ast.parse(
            textwrap.dedent(
                """
                def go(flag, cmd):
                    argv = ["docker", "run"]
                    if flag:
                        argv = ["sh", "-c", cmd]
                    subprocess.run(argv)
                """
            )
        )
        func = module.body[0]
        call = [n for n in ast.walk(func) if isinstance(n, ast.Call)][0]
        assert not is_fixed_program_argv(call, "subprocess.run", func)

    def test_a_non_literal_argv_is_not_resolved(self, tmp_path):
        import ast

        from agent_audit.analysis.argv_shape import is_fixed_program_argv

        call = ast.parse("subprocess.run(user_supplied_command)").body[0].value
        assert not is_fixed_program_argv(call, "subprocess.run", None)


class TestWhatIsStillOpen:
    """Pinned so the remaining state is measured rather than remembered.

    These assert the *defect*. Each one fails the moment it is fixed, which is the point:
    a note in a document decays, and an allow-list entry would let the fix pass unnoticed.
    """

    def test_config_derived_sql_still_fires(self, tmp_path):
        """Claim 2's SQL half. Needs a provenance model, not a receiver heuristic.

        `db_name` comes from `urlparse(config_url)`, and `config_url` is a parameter.
        Nothing in a single-file pass distinguishes a deployment's own database URL from
        an inbound request, so this stays reported. Recorded in ISSUE_TRIAGE.md.
        """
        found = _of_type(
            _patterns(
                tmp_path,
                """
                from urllib.parse import urlparse


                def provision(config_url: str, conn) -> None:
                    db_name = urlparse(config_url).path.lstrip("/")
                    conn.execute(f'CREATE DATABASE "{db_name}"')
                """,
            ),
            "sql_fstring_injection",
        )
        assert found, (
            "config-derived SQL no longer fires — if that was deliberate, this pin and "
            "ISSUE_TRIAGE.md #8 claim 2 both need updating, and the provenance model "
            "that made it possible needs its own tests"
        )

    def test_a_fixed_argv_still_produces_a_finding_under_another_rule(self, tmp_path):
        """Claim 4's residue: three producers see this line, and gating two moved it.

        AGENT-047 (unsandboxed subprocess) is a different and defensible claim from
        AGENT-034 (tool function without input validation), but the reporter's line still
        carries a finding, so the issue is improved rather than closed.
        """
        patterns = _patterns(
            tmp_path,
            """
            import subprocess


            def run_in_container(image: str, workdir: str):
                cmd = ["docker", "run", "--rm", "-v", f"{workdir}:/work", image]
                return subprocess.run(cmd, capture_output=True, check=False)
            """,
        )
        assert _of_type(patterns, "dangerous_function_call"), (
            "the third producer stopped firing — claim 4 may now be closeable; re-run "
            "the reporter's case and update ISSUE_TRIAGE.md before closing anything"
        )
