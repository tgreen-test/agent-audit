"""
Language-aware description judge (Layer 3 core; PLAN §2.3, §2.3.1).

The judge is the **single contribution** of SkillScanner: it replaces
surface-statistic heuristics (word count, keyword density, length) with a
semantic call that judges description clarity *in the target language*.

This module deliberately contains NO surface-statistic code path. The only
way to obtain a behavioral verdict here is through ``SemanticJudge`` (real
LLM judge) or ``NullJudge`` (fail-closed-to-silent). There is no third
backend, no fallback, no heuristic.

Judge Freeze (PLAN §2.3.1, do not change without bumping JUDGE_PROMPT_VERSION):

- ``JUDGE_MODEL``          = "claude-sonnet-4-6" (pinned id; never the
                              "sonnet" alias and never the retired
                              "claude-sonnet-4-20250514").
- ``JUDGE_TEMPERATURE``    = 0
- ``JUDGE_MAX_TOKENS``     = 300
- ``JUDGE_PROMPT_VERSION`` = "v2" (provisional until the Phase 1 freeze gate)
- ``JUDGE_PROMPT_V2``      = the literal prompt template below, hashed by the
                              test suite. Any edit without a version bump
                              fails CI.

Pre-judge deterministic short-circuit (v2; PROTOCOL §3.2.1):

An empty or whitespace-only description never reaches the LLM. It is
language-agnostic and certain → verdict "vague" with backend
``SemanticJudge`` (the short-circuit IS part of the SemanticJudge contract,
not a separate heuristic). The short-circuit is documented in PROTOCOL so
the "every behavioral verdict has known provenance" guarantee remains
honest: provenance for empty descriptions is the pre-judge rule, not the
LLM. Unreadable / ambiguous content (non-empty but undecidable) goes to
the LLM and may return ``cannot_judge``.

The Anthropic API key is read from the ``ANTHROPIC_API_KEY`` env var on
construction. The key is never hardcoded and never logged.

Verdict cache: a process-local dict keyed on
``sha256(description) + "|" + language + "|" + JUDGE_MODEL + "|" + JUDGE_PROMPT_VERSION``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Protocol


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Judge Freeze constants (PLAN §2.3.1). Treat as load-bearing.
# ---------------------------------------------------------------------------

JUDGE_MODEL: str = "claude-sonnet-4-6"
JUDGE_TEMPERATURE: int = 0
JUDGE_MAX_TOKENS: int = 300
JUDGE_PROMPT_VERSION: str = "v2"

# The prompt text and its version tag are physically bound here. Do not
# load this string from another file, do not assemble it from fragments,
# and do not edit it without bumping JUDGE_PROMPT_VERSION (which also
# lifts the version → model schema pin in finding.schema.json).
#
# The test suite asserts sha256(JUDGE_PROMPT_V2) matches a recorded hash so
# silent edits fail CI (PROMPT step 1.3 final note).
#
# v1 → v2: the empty / whitespace case was lifted out of the prompt and
# made a deterministic non-LLM short-circuit in SemanticJudge.judge.
# Reaching this prompt therefore guarantees a non-empty description.
JUDGE_PROMPT_V2: str = """You are auditing one Agent Skill (a packaged tool consumed by an AI agent).

The Skill's primary language is "{language}". You are given only the Skill's free-text description, between the <description> tags below. You do not see the Skill's code, name, or other fields. The description is guaranteed to contain at least one non-whitespace character.

Decide a single binary question, in the Skill's own language:

  Does this description contain AT LEAST ONE sentence that communicates
  the Skill's functionality — what it does, what input it expects, or
  what output it produces — written in {language}?

Rules for your decision:
- Judge meaning, not surface features. Do NOT count words, characters, or keywords.
- A single complete functional sentence in {language} is sufficient for "clear".
- Marketing slogans, hashtags, single tokens, placeholder text ("TODO", "build"), or text written in a language other than {language} are NOT functional sentences and are "vague".
- If you genuinely cannot tell (ambiguous script, mixed languages with no clear primary sentence, content you do not understand), reply "cannot_judge".

Respond with strict JSON on a single line, no surrounding prose, no code fences, no trailing text. The JSON has exactly two keys:

  {{"verdict": "<clear|vague|cannot_judge>", "reason": "<one short English sentence>"}}

<description>
{description}
</description>"""


# ---------------------------------------------------------------------------
# Verdict and judge protocol
# ---------------------------------------------------------------------------


VerdictLiteral = Literal["clear", "vague", "cannot_judge"]


@dataclass(frozen=True)
class JudgeVerdict:
    """One verdict from a DescriptionJudge backend.

    Only ``verdict == "vague"`` may produce a SKILL-010 finding. ``clear``
    and ``cannot_judge`` MUST be silent (PLAN §0 constraint #4,
    fail-closed-to-silent).
    """

    verdict: VerdictLiteral
    reason: str


class DescriptionJudge(Protocol):
    """Backend that judges a Skill description's functional clarity."""

    backend_name: str

    def judge(self, description: str, language: str) -> JudgeVerdict:  # pragma: no cover - protocol
        ...


# ---------------------------------------------------------------------------
# NullJudge — the fail-closed backend. Always cannot_judge.
# ---------------------------------------------------------------------------


class NullJudge:
    """Backend that abstains. Used when no LLM judge is available or when
    the detected language is ``unsupported``. Always returns
    ``cannot_judge`` so the scanner emits nothing."""

    backend_name = "NullJudge"

    def judge(self, description: str, language: str) -> JudgeVerdict:
        return JudgeVerdict(verdict="cannot_judge", reason="NullJudge: no semantic backend available")


# ---------------------------------------------------------------------------
# SemanticJudge — the real LLM-backed judge (Claude API).
# ---------------------------------------------------------------------------


def _cache_key(description: str, language: str) -> str:
    """Stable cache key per Judge Freeze: sha256(description) | language | model | prompt_version."""
    h = hashlib.sha256(description.encode("utf-8")).hexdigest()
    return f"{h}|{language}|{JUDGE_MODEL}|{JUDGE_PROMPT_VERSION}"


def _parse_verdict_json(raw: str) -> Optional[JudgeVerdict]:
    """Parse the strict JSON the prompt asks for. Tolerant of trailing whitespace
    or a stray newline only — anything else returns None and the caller maps to
    ``cannot_judge``."""
    if not raw:
        return None
    text = raw.strip()
    # Strip an accidental code fence if the model adds one.
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]) if lines[-1].strip().startswith("```") else "\n".join(lines[1:])
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    verdict = data.get("verdict") if isinstance(data, dict) else None
    reason = data.get("reason") if isinstance(data, dict) else None
    if verdict not in ("clear", "vague", "cannot_judge"):
        return None
    if not isinstance(reason, str):
        reason = ""
    return JudgeVerdict(verdict=verdict, reason=reason)


class SemanticJudge:
    """Claude-API-backed description judge using the frozen v1 prompt.

    Construction reads ``ANTHROPIC_API_KEY`` from the environment and
    imports the ``anthropic`` SDK lazily. Construction raises
    ``RuntimeError`` when either is missing; callers (see
    :func:`get_default_judge`) should swallow that and fall back to
    ``NullJudge``.
    """

    backend_name = "SemanticJudge"

    def __init__(self, client: Optional[object] = None) -> None:
        self._cache: Dict[str, JudgeVerdict] = {}
        if client is not None:
            self._client = client
            return
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; SemanticJudge unavailable")
        try:
            from anthropic import Anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise RuntimeError("anthropic SDK not installed; SemanticJudge unavailable") from exc
        self._client = Anthropic(api_key=api_key)

    def judge(self, description: str, language: str) -> JudgeVerdict:
        # v2 deterministic pre-judge (PROTOCOL §3.2.1): empty or whitespace-
        # only descriptions are language-agnostic, certain, and require no
        # semantic call. The short-circuit is part of the SemanticJudge
        # contract and is documented in PROTOCOL; it is NOT a surface-stat
        # heuristic for *content* quality. Provenance for these emits is
        # "v2 pre-judge", not the LLM — recorded in the verdict reason so
        # an annotator can tell the two paths apart.
        if not description or not description.strip():
            return JudgeVerdict(
                verdict="vague",
                reason="v2 pre-judge: empty or whitespace-only description (no LLM call)",
            )
        key = _cache_key(description, language)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        prompt = JUDGE_PROMPT_V2.format(language=language, description=description)
        try:
            response = self._client.messages.create(
                model=JUDGE_MODEL,
                max_tokens=JUDGE_MAX_TOKENS,
                temperature=JUDGE_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            logger.warning("SemanticJudge API error: %s", exc.__class__.__name__)
            verdict = JudgeVerdict(verdict="cannot_judge", reason="judge_error")
            self._cache[key] = verdict
            return verdict

        raw = _extract_text(response)
        parsed = _parse_verdict_json(raw)
        if parsed is None:
            verdict = JudgeVerdict(verdict="cannot_judge", reason="unparseable_judge_output")
        else:
            verdict = parsed
        self._cache[key] = verdict
        return verdict


def _extract_text(response: object) -> str:
    """Pull the text content out of an Anthropic Messages response.

    Robust to the SDK returning either a typed ``Message`` or a dict-like
    object during tests. Returns the concatenated text of all text blocks.
    """
    content = getattr(response, "content", None)
    if content is None and isinstance(response, dict):
        content = response.get("content")
    if content is None:
        return ""
    parts = []
    for block in content:
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Default judge selection (PLAN §2.3 routing rule).
# ---------------------------------------------------------------------------


def get_default_judge() -> DescriptionJudge:
    """Return ``SemanticJudge`` if it can be constructed, else ``NullJudge``.

    The routing rule from PLAN §2.3: a behavioral verdict requires both a
    supported language *and* an available judge. This function is the
    "available judge" half; the language router is the "supported language"
    half. Either failure path lands on ``NullJudge``.
    """
    try:
        return SemanticJudge()
    except RuntimeError:
        return NullJudge()
