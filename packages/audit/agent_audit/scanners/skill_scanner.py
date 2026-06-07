"""
SkillScanner — cross-lingual SKILL.md security scanner.

Four layers, in dependency order:

1. Frontmatter / Skill validation — emit SKILL-000 and disable behavioral
   analysis on any file that lacks valid YAML frontmatter (PLAN §2.1).
2. Code-block extraction — call existing PythonScanner / PrivilegeScanner
   public scan interfaces on extracted blocks (PLAN §2.2). No edits to
   either scanner's internals.
3. Language-aware description judge — route through SemanticJudge or
   NullJudge per language support; emit SKILL-010 only on a 'vague'
   semantic verdict (PLAN §2.3 / §2.3.1).
4. Tiering — clamp Skill-namespaced rule tiers via
   ``apply_skill_tier_ceiling`` (PLAN §2.4).

This file consumes existing scanners; it does not modify them. The
contribution is fairness/calibration, not detection.
"""

from __future__ import annotations

import hashlib
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from agent_audit.analysis.skill_code_extractor import SkillCodeBlock, extract_code_blocks
from agent_audit.analysis.skill_description_judge import (
    JUDGE_MODEL,
    JUDGE_PROMPT_VERSION,
    DescriptionJudge,
    JudgeVerdict,
    NullJudge,
    get_default_judge,
)
from agent_audit.analysis.skill_frontmatter import SkillFrontmatter, parse_frontmatter
from agent_audit.analysis.skill_language_router import SUPPORTED_LANGUAGES, detect_language
from agent_audit.models.finding import Finding, Remediation
from agent_audit.models.risk import Category, Location, Severity
from agent_audit.rules.skill_rule_context import apply_skill_tier_ceiling
from agent_audit.scanners.base import BaseScanner, ScanResult

logger = logging.getLogger(__name__)


@dataclass
class SkillScanResult(ScanResult):
    """Per-SKILL.md scan result."""

    findings: List[Finding] = field(default_factory=list)
    language: str = "unsupported"
    behavioral_disabled: bool = False


class SkillScanner(BaseScanner):
    """Scanner for SKILL.md files (Anthropic-style packaged Skills).

    Disjoint from ``SkillBodyScanner`` / ``SkillMetaScanner``: those emit
    AGENT-058..AGENT-064 against the existing tiering rules; this scanner
    emits the new ``SKILL-000 / 010 / 020`` namespace and reuses AGENT-*
    only for Layer-2 code-level findings.
    """

    name = "Skill Scanner"

    def __init__(self, judge: Optional[DescriptionJudge] = None) -> None:
        self._judge: DescriptionJudge = judge if judge is not None else get_default_judge()

    # -- BaseScanner contract --------------------------------------------

    def scan(self, path: Path) -> Sequence[SkillScanResult]:
        results: List[SkillScanResult] = []
        for skill_path in self._find_skill_files(path):
            try:
                result = self._scan_file(skill_path)
            except Exception as exc:  # pragma: no cover - safety net
                logger.warning("SkillScanner error on %s: %s", skill_path, exc)
                continue
            if result is not None:
                results.append(result)
        return results

    def scan_and_convert(self, path: Path) -> List[Finding]:
        findings: List[Finding] = []
        for result in self.scan(path):
            findings.extend(result.findings)
        return findings

    # -- File discovery ---------------------------------------------------

    def _find_skill_files(self, path: Path) -> List[Path]:
        if path.is_file():
            return [path] if _is_skill_filename(path) else []
        skill_files: List[Path] = []
        skip_dirs = {".git", "venv", ".venv", "__pycache__", "dist", "build", "node_modules"}
        for candidate in path.rglob("*"):
            if not candidate.is_file():
                continue
            if any(part in skip_dirs for part in candidate.parts):
                continue
            if _is_skill_filename(candidate):
                skill_files.append(candidate)
        return skill_files

    # -- Per-file pipeline -----------------------------------------------

    def _scan_file(self, skill_path: Path) -> Optional[SkillScanResult]:
        try:
            source = skill_path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - I/O guard
            logger.warning("Cannot read %s: %s", skill_path, exc)
            return None

        result = SkillScanResult(source_file=str(skill_path))

        # ---- Layer 1: frontmatter ---------------------------------------
        fm = parse_frontmatter(source)
        if fm is None:
            result.behavioral_disabled = True
            result.findings.append(_make_skill_000(skill_path))
            return result

        # ---- Layer 2: code-block extraction ----------------------------
        blocks = extract_code_blocks(source)
        result.findings.extend(_scan_code_blocks(skill_path, blocks))

        # ---- Language detection (used by Layers 3 + reporting) ---------
        result.language = detect_language(fm.description or "", fm.declared_language)

        # ---- Layer 3: language-aware description judge -----------------
        skill010 = self._maybe_emit_skill010(skill_path, fm, result.language)
        if skill010 is not None:
            result.findings.append(skill010)

        return result

    def _maybe_emit_skill010(
        self,
        skill_path: Path,
        fm: SkillFrontmatter,
        language: str,
    ) -> Optional[Finding]:
        """Run the description judge and emit SKILL-010 iff verdict='vague'."""
        if language not in SUPPORTED_LANGUAGES:
            return None
        judge = self._judge if language in SUPPORTED_LANGUAGES else NullJudge()
        description = fm.description or ""
        verdict: JudgeVerdict = judge.judge(description, language)
        if verdict.verdict != "vague":
            return None
        # NullJudge must never produce 'vague' (defensive — schema enforces this too).
        if judge.backend_name == "NullJudge":  # pragma: no cover - defensive
            return None

        confidence = 0.72  # Behavioral confidence; clamped to WARN ceiling below.
        tier = apply_skill_tier_ceiling("SKILL-010", confidence)
        # Defensive: assert ceiling holds.
        assert tier in {"WARN", "INFO", "SUPPRESSED"}, "behavioral tier ceiling breach"

        metadata: Dict[str, Any] = {
            "layer": "behavioral",
            "language": language,
            "judge_verdict": verdict.verdict,
            "judge_backend": judge.backend_name,
            "judge_reason": verdict.reason,
            "judge_model": JUDGE_MODEL,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
        }

        return Finding(
            rule_id="SKILL-010",
            title="Skill description does not communicate functionality",
            description=(
                f"DescriptionJudge ({judge.backend_name}, model={JUDGE_MODEL}, "
                f"prompt={JUDGE_PROMPT_VERSION}) verdict='vague' for language='{language}'. "
                f"Reason: {verdict.reason}"
            ),
            severity=Severity.LOW,
            category=Category.TRUST_EXPLOITATION,
            location=Location(
                file_path=str(skill_path),
                start_line=fm.description_line,
                end_line=fm.description_line,
                snippet=(description.splitlines() or [""])[0][:200],
            ),
            confidence=confidence,
            tier=tier,
            owasp_id="ASI-09",
            remediation=Remediation(
                description=(
                    "Rewrite the Skill description so it contains at least one sentence, "
                    "in the Skill's own language, that says what the Skill does, what input "
                    "it expects, or what output it produces."
                )
            ),
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# SKILL-000 emit (Layer 1).
# ---------------------------------------------------------------------------


def _make_skill_000(skill_path: Path) -> Finding:
    return Finding(
        rule_id="SKILL-000",
        title="File lacks valid YAML frontmatter; not a Skill",
        description=(
            "This file is named like a Skill but has no parsable YAML frontmatter. "
            "It is treated as 'not a Skill': behavioral analysis is suppressed and "
            "the file does not enter the behavioral evaluation denominator."
        ),
        severity=Severity.INFO,
        category=Category.SUPPLY_CHAIN_AGENTIC,
        location=Location(file_path=str(skill_path), start_line=1, end_line=1),
        confidence=0.99,
        tier=apply_skill_tier_ceiling("SKILL-000", 0.99),
        owasp_id="ASI-04",
        metadata={"layer": "frontmatter", "language": "unsupported"},
    )


# ---------------------------------------------------------------------------
# Layer 2: route extracted code blocks through existing scanners.
# ---------------------------------------------------------------------------


def _scan_code_blocks(skill_path: Path, blocks: List[SkillCodeBlock]) -> List[Finding]:
    findings: List[Finding] = []
    if not blocks:
        return findings

    # Lazy imports to keep test isolation simple and to avoid circulars.
    import agent_audit
    from agent_audit.rules.engine import RuleEngine
    from agent_audit.scanners.privilege_scanner import PrivilegeScanner
    from agent_audit.scanners.python_scanner import PythonScanner

    py_scanner = PythonScanner()
    rule_engine = RuleEngine()
    builtin_dir = Path(agent_audit.__file__).parent / "rules" / "builtin"
    if builtin_dir.exists():
        rule_engine.add_builtin_rules_dir(builtin_dir)
    rule_engine.load_rules()
    priv_scanner = PrivilegeScanner()

    skill_str = str(skill_path)

    with tempfile.TemporaryDirectory(prefix="skillscanner-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        for idx, block in enumerate(blocks):
            if block.kind == "python":
                findings.extend(
                    _route_python_block(block, idx, tmpdir, py_scanner, rule_engine, skill_str)
                )
            elif block.kind == "shell":
                findings.extend(
                    _route_shell_block(block, idx, tmpdir, priv_scanner, skill_str)
                )
            # 'unknown' blocks intentionally drop through — PLAN §2.2 routes
            # real code only.
    return findings


def _route_python_block(
    block: SkillCodeBlock,
    idx: int,
    tmpdir: Path,
    py_scanner: Any,
    rule_engine: Any,
    skill_str: str,
) -> List[Finding]:
    """Run PythonScanner public scan() on the block; remap findings to SKILL.md."""
    tmp_file = tmpdir / f"block_{idx}.py"
    tmp_file.write_text(block.source, encoding="utf-8")
    scan_results = py_scanner.scan(tmp_file)
    findings: List[Finding] = []
    for sr in scan_results:
        try:
            block_source = tmp_file.read_text(encoding="utf-8")
        except Exception:  # pragma: no cover - defensive
            block_source = block.source
        emitted = rule_engine.evaluate_dangerous_patterns(
            sr.dangerous_patterns,
            sr.source_file,
            source_code=block_source,
        )
        for f in emitted:
            findings.append(_remap_finding(f, block, skill_str))
    return findings


def _route_shell_block(
    block: SkillCodeBlock,
    idx: int,
    tmpdir: Path,
    priv_scanner: Any,
    skill_str: str,
) -> List[Finding]:
    """Run PrivilegeScanner public scan_and_convert() on the block; remap findings."""
    tmp_file = tmpdir / f"block_{idx}.sh"
    tmp_file.write_text(block.source, encoding="utf-8")
    emitted = priv_scanner.scan_and_convert(tmp_file)
    return [_remap_finding(f, block, skill_str) for f in emitted]


def _remap_finding(finding: Finding, block: SkillCodeBlock, skill_str: str) -> Finding:
    """Rewrite an existing-scanner finding so it points back into the SKILL.md.

    Mutates the finding in place (it is freshly constructed and not shared)
    and stamps the SkillScanner-specific metadata.
    """
    offset = block.start_line - 1
    finding.location = Location(
        file_path=skill_str,
        start_line=finding.location.start_line + offset,
        end_line=finding.location.end_line + offset,
        start_column=finding.location.start_column,
        end_column=finding.location.end_column,
        snippet=finding.location.snippet,
    )
    md = dict(finding.metadata) if finding.metadata else {}
    md.setdefault("layer", "code")
    md.setdefault("source_block_kind", block.kind)
    finding.metadata = md
    return finding


# ---------------------------------------------------------------------------
# Filename gate.
# ---------------------------------------------------------------------------


def _is_skill_filename(path: Path) -> bool:
    name = path.name
    # PLAN §2.1: we treat files named SKILL.md as candidate Skills. The
    # poster's contamination came from filename-only matching; the
    # frontmatter check in _scan_file is what actually rejects non-Skills.
    if name == "SKILL.md":
        return True
    if name.lower() == "skill.md":
        return True
    return False


def _hash_block(block: SkillCodeBlock) -> str:  # pragma: no cover - reserved
    """Stable hash of a code block (reserved for future caching)."""
    return hashlib.sha256(block.source.encode("utf-8")).hexdigest()[:16]
