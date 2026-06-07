"""
SkillScanner unit tests (Phase 1.5).

Covers each layer of the new SkillScanner and locks in:

- the four decisive Layer-3 cases from the PLAN (clear JA, vague EN,
  unsupported language, simulated API error);
- the behavioral-tier BLOCK ceiling assertion;
- the SKILL-000 emit-and-suppress-behavioral contract on non-Skill files;
- the Layer-2 reuse of existing AGENT-* rules via PythonScanner and
  PrivilegeScanner;
- the JUDGE_PROMPT_V1 sha256 fence so silent prompt edits without a
  version bump fail CI.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List

import pytest

from agent_audit.analysis import skill_description_judge as judge_mod
from agent_audit.analysis.skill_code_extractor import extract_code_blocks
from agent_audit.analysis.skill_description_judge import (
    JUDGE_MODEL,
    JUDGE_PROMPT_V2,
    JUDGE_PROMPT_VERSION,
    JudgeVerdict,
    NullJudge,
    SemanticJudge,
    _parse_verdict_json,
)
from agent_audit.analysis.skill_frontmatter import parse_frontmatter
from agent_audit.analysis.skill_language_router import detect_language
from agent_audit.models.finding import Finding
from agent_audit.rules.skill_rule_context import apply_skill_tier_ceiling
from agent_audit.scanners.skill_scanner import SkillScanner


FIXTURES = Path(__file__).parent / "fixtures" / "skills"


# ---------------------------------------------------------------------------
# Helpers: programmable judge backends for deterministic tests.
# ---------------------------------------------------------------------------


class _StubJudge:
    """Test judge that returns a pre-canned verdict. Stands in for SemanticJudge."""

    backend_name = "SemanticJudge"

    def __init__(self, verdict: str, reason: str = "stub") -> None:
        self._verdict = JudgeVerdict(verdict=verdict, reason=reason)

    def judge(self, description: str, language: str) -> JudgeVerdict:
        return self._verdict


def _findings_by_rule(findings: List[Finding], rule_id: str) -> List[Finding]:
    return [f for f in findings if f.rule_id == rule_id]


# ---------------------------------------------------------------------------
# Layer 1: frontmatter / SKILL-000.
# ---------------------------------------------------------------------------


class TestLayer1Frontmatter:
    def test_missing_frontmatter_emits_only_skill_000(self):
        scanner = SkillScanner(judge=_StubJudge("vague"))
        findings = scanner.scan_and_convert(FIXTURES / "no_frontmatter")
        assert len(findings) >= 1
        assert {f.rule_id for f in findings} == {"SKILL-000"}, (
            "Non-Skill file must emit SKILL-000 only and suppress every "
            "behavioral / code-level finding from this file."
        )

    def test_clear_ja_skill_has_frontmatter(self):
        source = (FIXTURES / "clear_ja" / "SKILL.md").read_text(encoding="utf-8")
        fm = parse_frontmatter(source)
        assert fm is not None
        assert fm.declared_language == "ja"


# ---------------------------------------------------------------------------
# Layer 2: code-block extraction + reuse of existing scanners.
# ---------------------------------------------------------------------------


class TestLayer2CodeBlocks:
    def test_extractor_classifies_python_and_shell(self):
        source = (FIXTURES / "curl_pipe_sh" / "SKILL.md").read_text(encoding="utf-8")
        blocks = extract_code_blocks(source)
        assert any(b.kind == "shell" for b in blocks)

    def test_curl_pipe_sh_existing_skill_body_finding_unchanged(self):
        """The existing pipeline-taint detection for 'curl | sh' lives in
        SkillBodyScanner (rule AGENT-058 skill_obfuscated_shell). PLAN
        constraint #1: SkillScanner must not edit or duplicate that — it
        runs alongside. This test is a regression guard that the existing
        sibling scanner still surfaces the finding, and that SkillScanner
        does not invent a new rule_id for the same line."""
        from agent_audit.scanners.skill_body_scanner import SkillBodyScanner

        body_scanner = SkillBodyScanner()
        body_results = body_scanner.scan(FIXTURES / "curl_pipe_sh")
        rule_ids = {bf.rule_id for r in body_results for bf in r.security_findings}
        assert "AGENT-058" in rule_ids, (
            "Existing SkillBodyScanner must still detect curl|sh as "
            "AGENT-058; SkillScanner must not suppress it."
        )

        scanner = SkillScanner(judge=NullJudge())
        skill_findings = scanner.scan_and_convert(FIXTURES / "curl_pipe_sh")
        # SkillScanner itself may emit SKILL-000/010/020 + remapped AGENT-*
        # from PythonScanner/PrivilegeScanner on extracted blocks. PrivilegeScanner
        # has no curl|sh pattern, so SkillScanner should not emit AGENT-058 here
        # (that's the sibling's job; deduping it would be inventing detection).
        skill_rule_ids = {f.rule_id for f in skill_findings}
        assert "AGENT-058" not in skill_rule_ids, (
            "SkillScanner must not duplicate SkillBodyScanner's AGENT-058 emit; "
            "that would inflate the finding count for the same root cause."
        )

    def test_eval_python_block_triggers_existing_agent_rule(self):
        scanner = SkillScanner(judge=NullJudge())
        findings = scanner.scan_and_convert(FIXTURES / "eval_python")
        agent_findings = [f for f in findings if f.rule_id.startswith("AGENT-")]
        assert agent_findings, (
            "Python-block `eval(arg)` must surface an existing AGENT-* finding "
            "via PythonScanner."
        )


# ---------------------------------------------------------------------------
# Layer 3: language router + judge routing (the four decisive cases).
# ---------------------------------------------------------------------------


class TestLayer3LanguageRouter:
    def test_japanese_text_routes_to_ja(self):
        assert detect_language("東京の現在の気温と湿度を取得します。") == "ja"

    def test_english_text_routes_to_en(self):
        assert detect_language("Fetches the current weather for a city.") == "en"

    def test_declared_thai_routes_to_unsupported(self):
        assert detect_language("สวัสดีครับ", declared="th") == "unsupported"

    def test_short_or_empty_routes_to_unsupported(self):
        assert detect_language("") == "unsupported"
        assert detect_language("x") == "unsupported"


class TestLayer3Judge:
    def test_decisive_clear_ja_emits_no_skill010(self):
        """Decisive case: clear Japanese description → no SKILL-010 (the
        exact false positive the AgentSkills '26 poster documented)."""
        scanner = SkillScanner(judge=_StubJudge("clear"))
        findings = scanner.scan_and_convert(FIXTURES / "clear_ja")
        assert _findings_by_rule(findings, "SKILL-010") == []

    def test_decisive_vague_en_emits_skill010(self):
        """Decisive case: EN description 'build' → SKILL-010 (poster's
        canonical genuine TP)."""
        scanner = SkillScanner(judge=_StubJudge("vague"))
        findings = scanner.scan_and_convert(FIXTURES / "vague_en")
        s10 = _findings_by_rule(findings, "SKILL-010")
        assert len(s10) == 1
        f = s10[0]
        assert f.metadata["layer"] == "behavioral"
        assert f.metadata["judge_verdict"] == "vague"
        assert f.metadata["judge_backend"] == "SemanticJudge"
        assert f.metadata["judge_model"] == JUDGE_MODEL
        assert f.metadata["judge_prompt_version"] == JUDGE_PROMPT_VERSION

    def test_decisive_unsupported_language_emits_no_skill010(self):
        """Decisive case: unsupported language → NullJudge path → no SKILL-010."""
        scanner = SkillScanner(judge=_StubJudge("vague"))  # would say vague if asked
        findings = scanner.scan_and_convert(FIXTURES / "unsupported_language")
        # Router gates the judge — stub never gets called for unsupported.
        assert _findings_by_rule(findings, "SKILL-010") == []

    def test_decisive_judge_api_error_emits_no_skill010(self):
        """Decisive case: simulated judge API error → cannot_judge → no SKILL-010
        (fail-closed-to-silent, PLAN §0 constraint #4)."""

        class _BoomClient:
            class _Messages:
                def create(self, **_kwargs):
                    raise RuntimeError("simulated API error")

            messages = _Messages()

        sj = SemanticJudge(client=_BoomClient())
        scanner = SkillScanner(judge=sj)
        findings = scanner.scan_and_convert(FIXTURES / "vague_en")
        assert _findings_by_rule(findings, "SKILL-010") == [], (
            "Judge API error must produce cannot_judge → no behavioral finding."
        )


# ---------------------------------------------------------------------------
# Layer 4: behavioral tier ceiling.
# ---------------------------------------------------------------------------


class TestLayer4TierCeiling:
    def test_skill010_can_never_be_block(self):
        """Exhaustive ceiling check across the full [0.0, 1.0] confidence range:
        SKILL-010 must never resolve to BLOCK, regardless of confidence."""
        for i in range(0, 101):
            conf = i / 100.0
            tier = apply_skill_tier_ceiling("SKILL-010", conf)
            assert tier in {"WARN", "INFO", "SUPPRESSED"}, (
                f"SKILL-010 produced {tier} at confidence={conf}; behavioral ceiling breached."
            )

    def test_skill010_actual_emit_is_clamped_to_warn(self):
        scanner = SkillScanner(judge=_StubJudge("vague"))
        findings = scanner.scan_and_convert(FIXTURES / "vague_en")
        s10 = _findings_by_rule(findings, "SKILL-010")
        assert s10 and s10[0].tier in {"WARN", "INFO", "SUPPRESSED"}

    def test_policy_ceiling_is_info(self):
        for i in range(0, 101):
            conf = i / 100.0
            tier = apply_skill_tier_ceiling("SKILL-020", conf)
            assert tier in {"INFO", "SUPPRESSED"}


# ---------------------------------------------------------------------------
# Schema conformance: every SKILL-010 emit carries judge provenance.
# ---------------------------------------------------------------------------


class TestSchemaCompliance:
    def test_skill010_finding_has_judge_provenance(self):
        scanner = SkillScanner(judge=_StubJudge("vague"))
        findings = scanner.scan_and_convert(FIXTURES / "vague_en")
        s10 = _findings_by_rule(findings, "SKILL-010")
        assert s10, "expected SKILL-010 emission"
        md = s10[0].metadata
        # The two provenance fields the user named as freeze-required.
        assert md["judge_model"] == "claude-sonnet-4-6"
        assert md["judge_prompt_version"] == "v2"


# ---------------------------------------------------------------------------
# Judge Freeze: prompt sha256 lockfile.
# ---------------------------------------------------------------------------


# Recorded sha256 of JUDGE_PROMPT_V2. If the prompt text changes without
# bumping JUDGE_PROMPT_VERSION, this assertion fails — the intent of the
# lock (PROMPT §1.3 final note). Updating the prompt requires updating
# BOTH this hash AND JUDGE_PROMPT_VERSION in the same commit.
JUDGE_PROMPT_V2_SHA256 = "a40bc2194c409eecdf7af43c884ef1ffc1adea85f655b9c4660550087816e56f"


class TestJudgeFreeze:
    def test_prompt_text_sha256_locked(self):
        # The recorded hash is bound to this commit. Bumping the prompt text
        # without bumping JUDGE_PROMPT_VERSION will produce a different
        # sha256 and this test will fail in CI.
        assert hashlib.sha256(JUDGE_PROMPT_V2.encode("utf-8")).hexdigest() == JUDGE_PROMPT_V2_SHA256

    def test_judge_constants_match_freeze(self):
        assert judge_mod.JUDGE_MODEL == "claude-sonnet-4-6"
        assert judge_mod.JUDGE_TEMPERATURE == 0
        assert judge_mod.JUDGE_MAX_TOKENS == 300
        assert judge_mod.JUDGE_PROMPT_VERSION == "v2"

    def test_prompt_carries_language_and_description_slots(self):
        assert "{language}" in JUDGE_PROMPT_V2
        assert "{description}" in JUDGE_PROMPT_V2

    def test_v2_prompt_does_not_mention_empty_case(self):
        """v2 lifted the empty-description rule out of the prompt and into
        a deterministic pre-judge short-circuit. The prompt must NOT still
        instruct the LLM on the empty case, otherwise the two paths could
        disagree."""
        lowered = JUDGE_PROMPT_V2.lower()
        assert "empty" not in lowered, (
            "v2 prompt must not mention 'empty' — that case is handled by "
            "the SemanticJudge pre-judge short-circuit, not by the LLM."
        )
        assert "whitespace-only" not in lowered


# ---------------------------------------------------------------------------
# SemanticJudge cache + verdict parsing.
# ---------------------------------------------------------------------------


class _MockTextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _MockResponse:
    def __init__(self, payload: str) -> None:
        self.content = [_MockTextBlock(payload)]


class _ScriptedClient:
    """Anthropic client double that returns scripted responses and counts calls."""

    def __init__(self, payloads: List[str]) -> None:
        self._payloads = list(payloads)
        self.calls = 0

        class _Messages:
            def __init__(self, parent: "_ScriptedClient") -> None:
                self._parent = parent

            def create(self, **_kwargs):
                self._parent.calls += 1
                return _MockResponse(self._parent._payloads.pop(0))

        self.messages = _Messages(self)


class TestSemanticJudgeCacheAndParse:
    def test_parse_verdict_strict_json(self):
        v = _parse_verdict_json('{"verdict": "vague", "reason": "single token"}')
        assert v is not None and v.verdict == "vague" and v.reason == "single token"

    def test_parse_verdict_rejects_unknown(self):
        assert _parse_verdict_json('{"verdict": "unsure", "reason": ""}') is None
        assert _parse_verdict_json("not json") is None

    def test_cache_returns_same_verdict_without_extra_call(self):
        client = _ScriptedClient([
            '{"verdict": "vague", "reason": "single token"}',
        ])
        sj = SemanticJudge(client=client)
        v1 = sj.judge("build", "en")
        v2 = sj.judge("build", "en")
        assert v1 == v2
        assert client.calls == 1, "second call must hit cache, not API"

    def test_cache_keys_differ_by_language(self):
        client = _ScriptedClient([
            '{"verdict": "vague", "reason": "en"}',
            '{"verdict": "clear", "reason": "ja"}',
        ])
        sj = SemanticJudge(client=client)
        assert sj.judge("build", "en").verdict == "vague"
        assert sj.judge("build", "ja").verdict == "clear"
        assert client.calls == 2

    def test_v2_empty_description_short_circuits_without_api_call(self):
        """v2 deterministic pre-judge (PROTOCOL §3.2.1): an empty or
        whitespace-only description is language-agnostic and certain →
        verdict 'vague' WITHOUT an API call. The short-circuit is part of
        SemanticJudge's contract and is documented in PROTOCOL; provenance
        is the version tag, not the LLM. This is NOT a surface-stat
        quality heuristic (PLAN §4 anti-pattern #1) — it does not infer
        anything about *content* quality, it only handles the absence of
        content."""
        client = _ScriptedClient([])  # no payload queued
        sj = SemanticJudge(client=client)
        v_blank = sj.judge("   ", "en")
        v_empty = sj.judge("", "ja")
        assert v_blank.verdict == "vague"
        assert v_empty.verdict == "vague"
        assert "v2 pre-judge" in v_blank.reason, (
            "Short-circuit emits must be self-identifying so an annotator "
            "can tell pre-judge from LLM provenance."
        )
        assert client.calls == 0, (
            "Empty/whitespace must NOT reach the API in v2."
        )

    def test_unparseable_output_is_cannot_judge(self):
        client = _ScriptedClient(["not json at all"])
        sj = SemanticJudge(client=client)
        v = sj.judge("Fetches the weather for a city.", "en")
        assert v.verdict == "cannot_judge"


# ---------------------------------------------------------------------------
# NullJudge contract.
# ---------------------------------------------------------------------------


class TestNullJudge:
    def test_null_judge_always_cannot_judge(self):
        nj = NullJudge()
        assert nj.judge("anything", "en").verdict == "cannot_judge"
        assert nj.judge("", "ja").verdict == "cannot_judge"
        assert nj.backend_name == "NullJudge"
