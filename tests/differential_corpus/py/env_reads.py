"""Env-read classification, the other `TreeSitterParser` consumer in
`semantic_analyzer`. `find_assignments()` classifies each of these, and the AST and
regex paths classify them by different means.
"""

from __future__ import annotations

import os
import subprocess

DIRECT_INDEX = os.environ["DATABASE_PASSWORD"]
DIRECT_GET = os.environ.get("DATABASE_PASSWORD")
GETENV = os.getenv("DATABASE_PASSWORD")
GETENV_DEFAULT = os.getenv("DATABASE_PASSWORD", "changeme")

INDIRECT = DIRECT_GET
NESTED = os.environ.get("A", os.getenv("B", "c"))


def run_tool(command: str) -> str:
    """A shell sink whose argument is a parameter."""
    return subprocess.run(command, shell=True, capture_output=True, text=True).stdout


def run_fixed() -> str:
    """A shell sink with a fixed non-shell program."""
    return subprocess.run(["git", "status"], capture_output=True, text=True).stdout


def evaluate(expression: str):
    """A code-execution sink whose argument is a parameter."""
    return eval(expression)
