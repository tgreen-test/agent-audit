"""Guards for the Python 3.14 `ast.NameConstant` removal (branch fix/py314-blocker).

`ast.NameConstant` was a deprecated alias for `ast.Constant` from Python 3.8 and was
REMOVED in 3.14 — `ast.NameConstant` now raises AttributeError on attribute access.

Two sites in python_scanner.py referenced it as a "Python 3.7 compat" fallback:

  * `PythonASTVisitor._has_shell_true`      (subprocess `shell=` keyword)
  * `PythonASTVisitor._check_agent_infinite_loop_no_timeout` (AGENT-115 `while True`)

Both were written as a *second* branch reached only when the preceding
`isinstance(x, ast.Constant)` check was False — i.e. exactly when the node is a Name,
Compare, Call, etc. So on 3.14 the fallback was evaluated (and blew up) precisely on
the ordinary non-literal code that real projects are full of: `shell=use_shell`,
`while running:`.

Because `ast.NameConstant is ast.Constant` on 3.8-3.13, the fallback branches were
already unreachable-by-value there; removing them is behaviour-preserving on every
supported version. These tests cover both halves of that claim:

  1. Non-literal `shell=` / `while` tests must scan without raising (the 3.14 fix).
  2. The truthiness semantics must stay strict — `shell=1` and `shell="true"` are not
     `shell=True`, and `while 0:` is not an infinite loop. This is the half that would
     catch someone "fixing" the AttributeError by relaxing the value check instead.
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path

import pytest

from agent_audit.scanners.python_scanner import PythonASTVisitor, PythonScanner


def _visitor(source: str) -> PythonASTVisitor:
    """Build a visitor over `source` the way the scanner does."""
    source = textwrap.dedent(source)
    return PythonASTVisitor(
        file_path=Path("mem.py"),
        source=source,
        tree=ast.parse(source),
    )


def _shell_kwarg_call(source: str) -> ast.Call:
    """Return the first ast.Call in `source`."""
    for node in ast.walk(ast.parse(textwrap.dedent(source))):
        if isinstance(node, ast.Call):
            return node
    raise AssertionError("no call found in source")


def test_ast_name_constant_is_gone_on_this_interpreter():
    """Documents why this file exists; informational on <3.14."""
    if sys.version_info >= (3, 14):
        assert not hasattr(ast, "NameConstant")
    else:
        # On 3.8-3.13 it is a deprecated alias, which is why removing the fallback
        # branches cannot change behaviour there.
        assert getattr(ast, "NameConstant", ast.Constant) is ast.Constant


class TestShellKeywordNonLiteral:
    """`_has_shell_true` must survive a non-literal `shell=` argument."""

    @pytest.mark.parametrize(
        "expr",
        [
            "subprocess.run(cmd, shell=use_shell)",          # ast.Name
            "subprocess.run(cmd, shell=cfg.use_shell)",      # ast.Attribute
            "subprocess.run(cmd, shell=bool(flag))",         # ast.Call
            "subprocess.run(cmd, shell=(a or b))",           # ast.BoolOp
            "subprocess.run(cmd, shell=opts['shell'])",      # ast.Subscript
        ],
    )
    def test_non_literal_shell_does_not_raise(self, expr):
        visitor = _visitor(expr)
        # Before the fix this raised:
        #   AttributeError: module 'ast' has no attribute 'NameConstant'
        assert visitor._has_shell_true(_shell_kwarg_call(expr)) is False

    def test_shell_true_still_detected(self):
        expr = "subprocess.run(cmd, shell=True)"
        assert _visitor(expr)._has_shell_true(_shell_kwarg_call(expr)) is True

    def test_shell_false_not_detected(self):
        expr = "subprocess.run(cmd, shell=False)"
        assert _visitor(expr)._has_shell_true(_shell_kwarg_call(expr)) is False

    @pytest.mark.parametrize("literal", ["1", "'true'", "'yes'", "1.0", "[1]"])
    def test_truthy_non_bool_is_not_shell_true(self, literal):
        """`shell=1` is not `shell=True`.

        The check is an identity test against the True singleton. If anyone widens it
        to a truthiness test while chasing the 3.14 AttributeError, this fails.
        """
        expr = f"subprocess.run(cmd, shell={literal})"
        assert _visitor(expr)._has_shell_true(_shell_kwarg_call(expr)) is False


class TestInfiniteLoopNonLiteral:
    """AGENT-115's `_check_agent_infinite_loop_no_timeout` must survive a non-literal while test."""

    def _check(self, body: str):
        source = textwrap.dedent(body)
        tree = ast.parse(source)
        func = tree.body[0]
        assert isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef))
        return _visitor(source)._check_agent_infinite_loop_no_timeout(func)

    @pytest.mark.parametrize(
        "test_expr",
        [
            "running",                # ast.Name
            "self.running",           # ast.Attribute
            "should_continue()",      # ast.Call
            "n < 10",                 # ast.Compare
            "a and b",                # ast.BoolOp
        ],
    )
    def test_non_literal_while_test_does_not_raise(self, test_expr):
        # Before the fix this raised:
        #   AttributeError: module 'ast' has no attribute 'NameConstant'
        result = self._check(
            f"""
            def worker():
                while {test_expr}:
                    do_work()
            """
        )
        assert result is None

    @pytest.mark.parametrize("literal", ["True", "1"])
    def test_infinite_loop_still_detected(self, literal):
        result = self._check(
            f"""
            def worker():
                while {literal}:
                    do_work()
            """
        )
        assert result is not None

    @pytest.mark.parametrize("literal", ["False", "0", "''", "None"])
    def test_falsy_literal_is_not_infinite(self, literal):
        result = self._check(
            f"""
            def worker():
                while {literal}:
                    do_work()
            """
        )
        assert result is None


def test_end_to_end_scan_of_non_literal_shell_and_loop(tmp_path):
    """Full scanner path, not just the two helpers.

    This is the shape of the failure a user would actually hit: an ordinary file with
    a variable `shell=` and a variable `while` condition.
    """
    target = tmp_path / "worker.py"
    target.write_text(
        textwrap.dedent(
            """
            import subprocess

            def run(cmd, use_shell, running):
                while running:
                    subprocess.run(cmd, shell=use_shell)
                return 0
            """
        )
    )
    # Must complete without AttributeError.
    results = PythonScanner().scan(target)
    assert results is not None
