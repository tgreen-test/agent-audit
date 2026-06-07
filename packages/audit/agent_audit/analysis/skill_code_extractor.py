"""
Fenced code-block extractor (Layer 2 helper for SkillScanner).

Walks a SKILL.md source string and yields ``SkillCodeBlock`` records, one
per fenced block, with the 1-based line number of the **first code line
inside the block** (not the opening fence). That offset is what the
SkillScanner uses to remap downstream PythonScanner / PrivilegeScanner
findings back to the SKILL.md.

The classifier maps fence info-strings to {``python``, ``shell``,
``unknown``}. ``unknown`` blocks are extracted but the scanner does not
route them to any code scanner (PLAN §2.2: route *real* code only).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Literal


_FENCE_RE = re.compile(r"^(?P<fence>```+|~~~+)(?P<info>[^\n]*)$")

_PYTHON_INFO_STRINGS = {"python", "py", "python3"}
_SHELL_INFO_STRINGS = {"bash", "sh", "shell", "zsh"}


CodeKind = Literal["python", "shell", "unknown"]


@dataclass
class SkillCodeBlock:
    """One fenced code block lifted out of a SKILL.md."""

    kind: CodeKind
    info_string: str
    source: str
    start_line: int  # 1-based; line of the first code line inside the fence


def _classify(info_string: str) -> CodeKind:
    token = info_string.strip().split()[0].lower() if info_string.strip() else ""
    if token in _PYTHON_INFO_STRINGS:
        return "python"
    if token in _SHELL_INFO_STRINGS:
        return "shell"
    return "unknown"


def extract_code_blocks(source: str) -> List[SkillCodeBlock]:
    """Extract fenced code blocks from a SKILL.md source string.

    Only well-formed fenced blocks (matching opening + closing fence) are
    returned. Mismatched / unterminated fences are dropped silently — they
    are not code we can route safely.
    """
    blocks: List[SkillCodeBlock] = []
    lines = source.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        m = _FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group("fence")
        info = m.group("info").strip()
        # walk to closing fence of equal-or-longer length, same char
        j = i + 1
        body_lines: List[str] = []
        while j < n:
            stripped = lines[j].rstrip("\r")
            if stripped.startswith(fence[0]) and stripped[: len(fence)] == fence and stripped.strip() == fence:
                break
            body_lines.append(lines[j])
            j += 1
        if j >= n:
            # unterminated fence — bail out of this block
            i += 1
            continue
        blocks.append(
            SkillCodeBlock(
                kind=_classify(info),
                info_string=info,
                source="\n".join(body_lines),
                start_line=i + 2,  # 1-based: opening fence is i+1, first code line is i+2
            )
        )
        i = j + 1
    return blocks
