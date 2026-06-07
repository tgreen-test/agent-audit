"""
SkillScanner rule-tier ceilings (Layer 4; PLAN §2.4).

Existing AGENT-* code-level rules surfaced via Layer 2 keep their existing
tiering logic untouched. The Skill-namespaced rules need an additional
clamp so that:

- ``SKILL-010`` (behavioral) can never reach ``BLOCK`` regardless of
  confidence — behavioral judgments require a human in the loop and must
  not gate CI (PLAN §0 constraint #5).
- ``SKILL-020`` (policy) is INFO only.
- ``SKILL-000`` (frontmatter / not-a-Skill) is INFO only.

The clamp is applied by ``apply_skill_tier_ceiling`` *after* the existing
``confidence_to_tier`` produces its baseline tier. Doing the clamp in code
keeps the existing tier machinery untouched while guaranteeing the
ceiling in every emit path.
"""

from __future__ import annotations

from typing import Set

from agent_audit.models.finding import confidence_to_tier


BEHAVIORAL_SKILL_RULES: Set[str] = {"SKILL-010"}
POLICY_SKILL_RULES: Set[str] = {"SKILL-020"}
FRONTMATTER_SKILL_RULES: Set[str] = {"SKILL-000"}

_TIER_RANK = {"SUPPRESSED": 0, "INFO": 1, "WARN": 2, "BLOCK": 3}
_RANK_TIER = {v: k for k, v in _TIER_RANK.items()}


def _clamp(base: str, ceiling: str) -> str:
    return _RANK_TIER[min(_TIER_RANK[base], _TIER_RANK[ceiling])]


def apply_skill_tier_ceiling(rule_id: str, confidence: float) -> str:
    """Return the reporting tier for a Skill-namespaced rule.

    Behavioral rules are ceiling-capped at WARN; policy and frontmatter at
    INFO. AGENT-* code-level rules are out of scope here — the caller does
    not pass them in.
    """
    base = confidence_to_tier(confidence)
    if rule_id in BEHAVIORAL_SKILL_RULES:
        return _clamp(base, "WARN")
    if rule_id in POLICY_SKILL_RULES or rule_id in FRONTMATTER_SKILL_RULES:
        return _clamp(base, "INFO")
    return base
