"""TestPythonStringLiterals and TestValueTypeClassification shapes.

Two of the 42 regressions a live tree-sitter path caused were on the Python side, not
the TypeScript side — `test_detect_fstring` and the `os.environ["KEY"] -> ENV_READ`
classification. Both go through `TreeSitterParser`, which is why this file exists.
"""

from __future__ import annotations

import os

NAME = "world"

PLAIN = "hello"
FSTRING = f"hello {NAME}"
FSTRING_NESTED = f"hello {NAME.upper()} and {NAME!r}"
CONCAT = "hello " + NAME
PERCENT = "hello %s" % NAME
FORMAT = "hello {}".format(NAME)

ENV_INDEX = os.environ["KEY"]
ENV_GET = os.environ.get("KEY")
ENV_GETENV = os.getenv("KEY")

NUMERIC = 42
BOOLEAN = True
NONE_VALUE = None
LISTV = [1, 2, 3]
DICTV = {"a": 1}
CALL = os.getcwd()
REF = PLAIN
