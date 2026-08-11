"""
SKILL.md frontmatter parser (Layer 1 helper for SkillScanner).

Parses the leading ``---``-delimited YAML head of a SKILL.md file. A file
that has no valid frontmatter is, by definition, not a Skill — the caller
emits SKILL-000 and skips all behavioral analysis. This is the gate that
keeps non-Skill files (poster: 23% of JA filename-matched files were game
docs, portfolios, etc.) out of the behavioral denominator.

This module is read-only: it returns parsed data; it never emits findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import yaml


_FENCE = "---"


@dataclass
class SkillFrontmatter:
    """Parsed YAML head of a SKILL.md."""

    name: Optional[str] = None
    description: Optional[str] = None
    risk: Optional[str] = None
    restricted_tools: List[str] = field(default_factory=list)
    declared_language: Optional[str] = None
    description_line: int = 1
    raw: dict = field(default_factory=dict)


def _locate_fences(source: str) -> Optional[Tuple[int, int]]:
    """Return (open_idx, close_idx) line indices of the YAML fences, 0-based.

    The opening fence must be the first non-empty line. The closing fence is
    the next ``---`` on its own line. Returns ``None`` when no well-formed
    fence pair exists.
    """
    lines = source.splitlines()
    open_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "":
            continue
        if line.strip() == _FENCE:
            open_idx = i
        break
    if open_idx is None:
        return None
    for j in range(open_idx + 1, len(lines)):
        if lines[j].strip() == _FENCE:
            return (open_idx, j)
    return None


def _description_line(source: str, open_idx: int, close_idx: int) -> int:
    """Best-effort 1-based line number where the ``description:`` key lives.

    Falls back to the line after the opening fence when the key is absent.
    """
    lines = source.splitlines()
    for k in range(open_idx + 1, close_idx):
        stripped = lines[k].lstrip()
        if stripped.startswith("description:") or stripped.startswith("description :"):
            return k + 1
    return open_idx + 2


def parse_frontmatter(source: str) -> Optional[SkillFrontmatter]:
    """Parse the YAML frontmatter at the head of a SKILL.md source string.

    Returns ``None`` when there is no fence pair or the YAML is malformed or
    does not deserialize into a mapping. A returned ``SkillFrontmatter`` is
    the green light for behavioral analysis; ``None`` means SKILL-000 and
    behavioral analysis must be disabled for this file.
    """
    fences = _locate_fences(source)
    if fences is None:
        return None
    open_idx, close_idx = fences
    yaml_text = "\n".join(source.splitlines()[open_idx + 1 : close_idx])
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None

    restricted = data.get("restricted_tools") or data.get("restricted-tools") or []
    if isinstance(restricted, str):
        restricted = [restricted]
    if not isinstance(restricted, list):
        restricted = []

    return SkillFrontmatter(
        name=_as_str(data.get("name")),
        description=_as_str(data.get("description")),
        risk=_as_str(data.get("risk")),
        restricted_tools=[str(x) for x in restricted],
        declared_language=_as_str(data.get("language") or data.get("lang")),
        description_line=_description_line(source, open_idx, close_idx),
        raw=data,
    )


def _as_str(value: object) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)
