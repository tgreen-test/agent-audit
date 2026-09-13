"""AGENT-041 may not call every `.execute()` a SQL sink — issue #10.

The reported case, verbatim:

    return target_agent.execute(task)   ->  AGENT-041, tier BLOCK, confidence 1.0

Every other branch of the SQL check requires the argument to look like SQL. The
KNOWN-008 branch (`_check_sql_tainted_param`, added v0.15.1) deliberately cannot: its
purpose is the statement built upstream, where this file sees only a parameter name. With
no evidence from the argument and none from the receiver, it accused any `x.execute(p)`
of SQL injection at full confidence — and `.execute()` is a common non-SQL idiom in agent
code: an agent, a task runner, a `concurrent.futures.Executor`, an ORM query builder.

`CAPABILITY_BOUNDARIES.md` § 1 names the general shape — no type resolution, so a method
name stands in for a receiver type. The `.eval`-on-a-Redis-client and
`.fetch`-on-a-request-handler families were the same bug, and each got its own receiver
heuristic. This is the third, and these tests pin both directions of it so the next
change has to keep the true positives as well as the suppression.

The evidence is positive by design: a receiver must *look like* a database handle for the
finding to fire. An unrecognised receiver is silence rather than a BLOCK-tier accusation,
which is the direction that makes an incomplete vocabulary a missed detection rather than
a confident wrong one.
"""

from __future__ import annotations

import textwrap

import pytest

from agent_audit.scanners.python_scanner import PythonScanner


def _sql_findings(tmp_path, source: str, name: str = "sample.py"):
    """Scan one file and return only the SQL-sink patterns from the KNOWN-008 branch."""
    path = tmp_path / name
    path.write_text(textwrap.dedent(source))
    results = PythonScanner().scan(path)
    return [
        pattern
        for result in results
        for pattern in result.dangerous_patterns
        if pattern.get("type") == "sql_tainted_param"
    ]


class TestTheReportedFalsePositive:
    def test_agent_execute_is_not_sql(self, tmp_path):
        """Issue #10's `fp_case.py`, unchanged."""
        assert not _sql_findings(
            tmp_path,
            """
            from typing import Any


            class AgentRunner:
                def dispatch(self, target_agent: Any, task: str) -> Any:
                    return target_agent.execute(task)
            """,
        )

    @pytest.mark.parametrize(
        "receiver",
        [
            "target_agent",          # the reported case
            "executor",              # concurrent.futures
            "runner",
            "workflow",
            "chain",                 # LangChain
            "graph",                 # LangGraph
            "self.tool",
            "pipeline",
        ],
    )
    def test_non_database_receivers_do_not_fire(self, tmp_path, receiver):
        assert not _sql_findings(
            tmp_path,
            f"""
            def dispatch({receiver.split('.')[0]}, task):
                return {receiver}.execute(task)
            """,
        )


class TestTheDetectionThatMustSurvive:
    """KNOWN-008 is the reason this branch exists; suppressing it would be a regression."""

    def test_cursor_parameter_still_fires(self, tmp_path):
        """SQL built upstream and handed in — the v0.15.1 case, receiver named `cursor`."""
        found = _sql_findings(
            tmp_path,
            """
            def find_user_upstream(cursor, query: str):
                cursor.execute(query)
                return cursor.fetchall()
            """,
        )
        assert len(found) == 1
        assert found[0]["note"].endswith('"query"')

    @pytest.mark.parametrize(
        "receiver",
        ["cursor", "cur", "conn", "connection", "db", "db_conn", "read_cursor",
         "self.session", "engine", "tx"],
    )
    def test_database_receiver_names_fire(self, tmp_path, receiver):
        assert _sql_findings(
            tmp_path,
            f"""
            def run({receiver.split('.')[0]}, query):
                {receiver}.execute(query)
            """,
        )

    def test_receiver_assigned_from_a_factory_fires(self, tmp_path):
        """A handle whose *name* says nothing, whose assignment says everything.

        `handle = conn.cursor()` is the case a name-only heuristic would miss, and it is
        why the gate reads assignments as well as identifiers.
        """
        assert _sql_findings(
            tmp_path,
            """
            import sqlite3


            def run(query):
                connection = sqlite3.connect("app.db")
                handle = connection.cursor()
                handle.execute(query)
            """,
        )

    def test_receiver_from_a_with_statement_fires(self, tmp_path):
        assert _sql_findings(
            tmp_path,
            """
            import sqlite3


            def run(query):
                with sqlite3.connect("app.db") as handle:
                    handle.execute(query)
            """,
        )

    def test_sqlalchemy_engine_factory_fires(self, tmp_path):
        assert _sql_findings(
            tmp_path,
            """
            from sqlalchemy import create_engine


            def run(query):
                bound = create_engine("postgresql://localhost/app")
                bound.execute(query)
            """,
        )


class TestTheGateIsAboutTheReceiverOnly:
    """It must not become a second, quieter way to lose the other SQL branches."""

    def test_a_bare_execute_call_is_not_judged(self, tmp_path):
        """`execute(query)` with no receiver: nothing to read, so nothing is claimed."""
        assert not _sql_findings(
            tmp_path,
            """
            def run(query):
                execute(query)
            """,
        )

    def test_fstring_sql_is_unaffected_by_this_gate(self, tmp_path):
        """The f-string branch has its own `looks_like_sql` test and is not touched here.

        Asserted through the scanner rather than by reading the source, so a refactor
        that routed the f-string case through the receiver gate would fail here.
        """
        path = tmp_path / "fstring.py"
        path.write_text(
            textwrap.dedent(
                """
                def find_user(cursor, name):
                    cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
                """
            )
        )
        results = PythonScanner().scan(path)
        kinds = {
            pattern.get("type")
            for result in results
            for pattern in result.dangerous_patterns
        }
        assert "sql_fstring_injection" in kinds
