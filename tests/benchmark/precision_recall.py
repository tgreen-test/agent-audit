#!/usr/bin/env python3
"""
Precision/Recall/F1 Evaluator for agent-audit.

Usage:
    python tests/benchmark/precision_recall.py [--ground-truth PATH] [--scan-results PATH]

This script compares scanner output against ground truth labels to calculate:
- True Positives (TP): Correctly detected vulnerabilities
- False Positives (FP): Incorrectly flagged safe code
- False Negatives (FN): Missed vulnerabilities
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 * P * R / (P + R)
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class VulnerabilityLabel:
    """Ground truth label for a vulnerability."""

    file: str
    line: int
    rule_id: str
    owasp_id: Optional[str] = None
    is_true_positive: bool = True
    confidence: float = 1.0
    notes: str = ""

    def key(self) -> str:
        """Unique identifier for matching."""
        return f"{self.file}:{self.line}:{self.rule_id}"


@dataclass
class Finding:
    """Scanner finding."""

    file: str
    line: int
    rule_id: str
    severity: str = ""
    owasp_id: Optional[str] = None

    def key(self) -> str:
        """Unique identifier for matching."""
        return f"{self.file}:{self.line}:{self.rule_id}"


@dataclass
class EvaluationResult:
    """Evaluation metrics."""

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    tp_details: List[str] = field(default_factory=list)
    fp_details: List[str] = field(default_factory=list)
    fn_details: List[str] = field(default_factory=list)

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        total = self.true_positives + self.false_positives
        return self.false_positives / total if total > 0 else 0.0


def load_ground_truth(path: Path) -> Dict[str, List[VulnerabilityLabel]]:
    """Load ground truth labels from YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    labels: Dict[str, List[VulnerabilityLabel]] = {}

    for sample in data.get("samples", []):
        file_path = sample["file"]
        vulns = sample.get("vulnerabilities", [])

        labels[file_path] = []
        for v in vulns:
            labels[file_path].append(
                VulnerabilityLabel(
                    file=file_path,
                    line=v["line"],
                    rule_id=v["rule_id"],
                    owasp_id=v.get("owasp_id"),
                    is_true_positive=v.get("is_true_positive", True),
                    confidence=v.get("confidence", 1.0),
                    notes=v.get("notes", ""),
                )
            )

    return labels


def run_scan(fixtures_path: Path) -> List[Finding]:
    """Run agent-audit scan and parse results.
    
    Temporarily disables .agent-audit.yaml ignore rules by renaming the file,
    since benchmark needs to evaluate all findings in test fixtures.
    """
    # Try multiple Python commands for cross-platform compatibility
    python_cmds = [sys.executable, "python3", "python"]
    
    # Find and temporarily disable config file
    project_root = fixtures_path
    while project_root.parent != project_root:
        config_file = project_root / ".agent-audit.yaml"
        if config_file.exists():
            break
        project_root = project_root.parent
    else:
        config_file = None
    
    backup_file = None
    if config_file and config_file.exists():
        backup_file = config_file.with_suffix(".yaml.bak")
        config_file.rename(backup_file)
        logger.info("Temporarily disabled .agent-audit.yaml for benchmark scan")
    
    try:
        for python_cmd in python_cmds:
            try:
                result = subprocess.run(
                    [python_cmd, "-m", "agent_audit", "scan", str(fixtures_path), "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0 or result.stdout.strip():
                    break
            except subprocess.TimeoutExpired:
                logger.error("Scan timed out")
                return []
            except FileNotFoundError:
                continue
        else:
            logger.error("agent-audit not found - tried: " + ", ".join(python_cmds))
            return []
    finally:
        # Restore config file
        if backup_file and backup_file.exists():
            backup_file.rename(config_file)
            logger.info("Restored .agent-audit.yaml")

    if not result.stdout.strip():
        logger.warning("Empty scan output")
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        # Try to find JSON in output
        for line in result.stdout.split("\n"):
            if line.strip().startswith("{") or line.strip().startswith("["):
                try:
                    data = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        else:
            logger.error(f"Could not parse JSON: {result.stdout[:200]}")
            return []

    findings = []
    items = data.get("findings", data) if isinstance(data, dict) else data

    for item in items:
        if not isinstance(item, dict):
            continue
        
        # Skip suppressed findings - these are intentionally ignored
        if item.get("suppressed", False):
            continue

        location = item.get("location", {})
        file_path = location.get("file_path", item.get("file", ""))

        # Normalize path to be relative to fixtures
        if "fixtures/" in file_path:
            file_path = file_path.split("fixtures/", 1)[-1]

        findings.append(
            Finding(
                file=file_path,
                line=location.get("start_line", item.get("line", 0)),
                rule_id=item.get("rule_id", ""),
                severity=item.get("severity", ""),
                owasp_id=item.get("owasp_id"),
            )
        )

    return findings


@dataclass
class PerASIMetrics:
    """Per-ASI evaluation metrics."""

    recall: float
    expected: int
    tp: int


def evaluate(
    ground_truth: Dict[str, List[VulnerabilityLabel]],
    findings: List[Finding],
    line_tolerance: int = 3,
) -> Tuple[EvaluationResult, Dict[str, PerASIMetrics]]:
    """
    Evaluate scanner accuracy against ground truth.

    Args:
        ground_truth: Labeled vulnerabilities by file
        findings: Scanner findings
        line_tolerance: Allow line number mismatch within this range

    Returns:
        Tuple of (EvaluationResult with overall metrics, Dict of per-ASI metrics)
    """
    result = EvaluationResult()

    # Build sets for matching with owasp_id tracking
    expected_vulns: Set[Tuple[str, int, str]] = set()
    expected_by_asi: Dict[str, Set[Tuple[str, int, str]]] = {}
    label_owasp_map: Dict[Tuple[str, int, str], str] = {}

    for file_path, labels in ground_truth.items():
        for label in labels:
            if label.is_true_positive:
                key = (file_path, label.line, label.rule_id)
                expected_vulns.add(key)
                # Track owasp_id for per-ASI metrics
                owasp_id = label.owasp_id or "unknown"
                label_owasp_map[key] = owasp_id
                if owasp_id not in expected_by_asi:
                    expected_by_asi[owasp_id] = set()
                expected_by_asi[owasp_id].add(key)

    detected_vulns: Set[Tuple[str, int, str]] = set()
    for f in findings:
        detected_vulns.add((f.file, f.line, f.rule_id))

    # Safe files (should have no findings)
    safe_files = {fp for fp, labels in ground_truth.items() if not labels}

    # Calculate TP, FP, FN
    matched: Set[Tuple[str, int, str]] = set()
    # Track which expected vulns were matched for per-ASI
    matched_expected: Set[Tuple[str, int, str]] = set()

    # Iterate in sorted order, not set order. Both `detected_vulns` and
    # `expected_vulns` are sets, and set iteration order for these tuples varies
    # with PYTHONHASHSEED. When one detection is within tolerance of two labels,
    # whichever label the fuzzy loop reached first claimed the match, so the
    # score moved between runs of the identical command:
    #     PYTHONHASHSEED=0 -> TP 196, F1 74.95%
    #     PYTHONHASHSEED=1 -> TP 197, F1 75.19%
    # A quality gate cannot ratchet against a number that flaps, so the order is
    # pinned here. See TestEvaluateDeterminism.
    for d_file, d_line, d_rule in sorted(detected_vulns):
        found_match = False

        # Try exact match first
        if (d_file, d_line, d_rule) in expected_vulns:
            result.true_positives += 1
            result.tp_details.append(f"{d_file}:{d_line} {d_rule}")
            matched.add((d_file, d_line, d_rule))
            matched_expected.add((d_file, d_line, d_rule))
            found_match = True
        else:
            # Fuzzy line match. Credit the detection to the *nearest* unmatched
            # label rather than to whichever one iteration happened to reach
            # first; ties break toward the lower line number.
            candidates = sorted(
                (
                    (abs(e_line - d_line), e_file, e_line, e_rule)
                    for (e_file, e_line, e_rule) in expected_vulns
                    if e_file == d_file
                    and e_rule == d_rule
                    and abs(e_line - d_line) <= line_tolerance
                    and (e_file, e_line, e_rule) not in matched
                )
            )
            if candidates:
                _, e_file, e_line, e_rule = candidates[0]
                result.true_positives += 1
                result.tp_details.append(f"{d_file}:{d_line}~{e_line} {d_rule}")
                matched.add((e_file, e_line, e_rule))
                matched_expected.add((e_file, e_line, e_rule))
                found_match = True

        if not found_match:
            # Check if this is a finding in a safe file
            if d_file in safe_files:
                result.false_positives += 1
                result.fp_details.append(f"{d_file}:{d_line} {d_rule} (safe file)")
            elif (d_file, d_line, d_rule) not in expected_vulns:
                # Finding not in ground truth - could be FP or unlabeled
                result.false_positives += 1
                result.fp_details.append(f"{d_file}:{d_line} {d_rule} (not labeled)")

    # False negatives: expected but not detected
    for e_file, e_line, e_rule in sorted(expected_vulns):
        if (e_file, e_line, e_rule) not in matched:
            result.false_negatives += 1
            result.fn_details.append(f"{e_file}:{e_line} {e_rule}")

    # Calculate per-ASI metrics
    per_asi_metrics: Dict[str, PerASIMetrics] = {}
    for asi, expected_set in expected_by_asi.items():
        if asi == "unknown":
            continue  # Skip unknown ASI
        expected_count = len(expected_set)
        tp_count = len(expected_set & matched_expected)
        recall = tp_count / expected_count if expected_count > 0 else 0.0
        per_asi_metrics[asi] = PerASIMetrics(
            recall=recall,
            expected=expected_count,
            tp=tp_count,
        )

    return result, per_asi_metrics


GATES_PATH = Path(__file__).parent / "gates.yaml"


def load_layer1_gates(path: Path = GATES_PATH) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Read the Layer 1 ratchet and target from gates.yaml.

    There is deliberately no fallback set of numbers here. This report used to carry
    its own copy of 0.90 / 0.85 / 0.87 / 0.05, which is a second definition of the
    figures in gates.yaml `layer1.target` — the same defect this file's exit gate was.
    If gates.yaml cannot be read, the report says so rather than inventing floors.
    """
    try:
        with open(path) as f:
            config = yaml.safe_load(f) or {}
    except OSError as e:
        logger.warning(f"Could not read {path}: {e}; thresholds will not be reported")
        return {}, {}

    layer1 = config.get("layer1", {}) or {}
    return layer1.get("thresholds", {}) or {}, layer1.get("target", {}) or {}


def _threshold_lines(
    result: EvaluationResult, floors: Dict[str, float]
) -> List[Tuple[str, bool]]:
    """Build (label, passed) rows for whichever floors the config actually defines."""
    metrics = (
        ("precision_min", "Precision", result.precision, False),
        ("recall_min", "Recall", result.recall, False),
        ("f1_min", "F1", result.f1_score, False),
        ("fp_rate_max", "FP Rate", result.false_positive_rate, True),
    )
    rows: List[Tuple[str, bool]] = []
    for key, label, value, is_max in metrics:
        if key not in floors:
            continue
        bound = floors[key]
        if is_max:
            rows.append((f"{label} <= {bound:.0%}", value <= bound))
        else:
            rows.append((f"{label} >= {bound:.0%}", value >= bound))
    return rows


def print_report(result: EvaluationResult, verbose: bool = False) -> None:
    """Print evaluation report."""
    print("\n" + "=" * 60)
    print("PRECISION/RECALL EVALUATION REPORT")
    print("=" * 60)

    print(f"\nSummary Metrics:")
    print(f"  True Positives:  {result.true_positives}")
    print(f"  False Positives: {result.false_positives}")
    print(f"  False Negatives: {result.false_negatives}")
    print()
    print(f"  Precision: {result.precision:.2%}")
    print(f"  Recall:    {result.recall:.2%}")
    print(f"  F1-Score:  {result.f1_score:.2%}")
    print(f"  FP Rate:   {result.false_positive_rate:.2%}")

    # Threshold REPORT, read from gates.yaml. Nothing here decides an exit code:
    # quality_gate_check.py is the only thing that gates Layer 1.
    ratchet, target = load_layer1_gates()

    if not ratchet and not target:
        print(f"\nThresholds: unavailable ({GATES_PATH} could not be read)")
    else:
        ratchet_rows = _threshold_lines(result, ratchet)
        if ratchet_rows:
            print("\nRatchet (tests/benchmark/gates.yaml layer1.thresholds — blocks CI")
            print("via quality_gate_check.py, which is what decides the build):")
            for name, passed in ratchet_rows:
                print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            verdict = "WOULD PASS" if all(p for _, p in ratchet_rows) else "WOULD FAIL"
            print(f"\n  -> against the ratchet, Layer 1 {verdict}")

        target_rows = _threshold_lines(result, target)
        if target_rows:
            print("\nTarget (gates.yaml layer1.target — aspirational, never blocks):")
            for name, passed in target_rows:
                print(f"  [{'MET' if passed else 'not met'}] {name}")

    if verbose:
        if result.tp_details:
            print("\nTrue Positives:")
            for d in result.tp_details[:10]:
                print(f"  + {d}")
            if len(result.tp_details) > 10:
                print(f"  ... and {len(result.tp_details) - 10} more")

        if result.fp_details:
            print("\nFalse Positives:")
            for d in result.fp_details[:10]:
                print(f"  - {d}")

        if result.fn_details:
            print("\nFalse Negatives (Missed):")
            for d in result.fn_details[:10]:
                print(f"  ! {d}")

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate agent-audit accuracy")
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=Path(__file__).parent.parent / "ground_truth" / "labeled_samples.yaml",
        help="Path to ground truth YAML file",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path(__file__).parent.parent / "fixtures",
        help="Path to fixtures directory to scan",
    )
    parser.add_argument(
        "--scan-results",
        type=Path,
        help="Use existing scan results JSON instead of running scan",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed findings",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Output results to JSON file",
    )
    args = parser.parse_args()

    # Load ground truth
    logger.info(f"Loading ground truth from {args.ground_truth}")
    if not args.ground_truth.exists():
        logger.error(f"Ground truth file not found: {args.ground_truth}")
        sys.exit(1)

    ground_truth = load_ground_truth(args.ground_truth)
    total_labels = sum(len(v) for v in ground_truth.values())
    logger.info(f"Loaded {total_labels} labels for {len(ground_truth)} files")

    # Get findings
    if args.scan_results:
        logger.info(f"Loading scan results from {args.scan_results}")
        with open(args.scan_results) as f:
            data = json.load(f)
        findings = [Finding(**f) for f in data.get("findings", data)]
    else:
        logger.info(f"Running scan on {args.fixtures}")
        findings = run_scan(args.fixtures)

    logger.info(f"Got {len(findings)} findings")

    # Evaluate
    result, per_asi_metrics = evaluate(ground_truth, findings)

    # Output
    print_report(result, verbose=args.verbose)

    if args.output_json:
        # Build per_asi output structure
        per_asi_output = {}
        for asi, metrics in sorted(per_asi_metrics.items()):
            per_asi_output[asi] = {
                "recall": round(metrics.recall, 4),
                "expected": metrics.expected,
                "tp": metrics.tp,
            }

        output = {
            "true_positives": result.true_positives,
            "false_positives": result.false_positives,
            "false_negatives": result.false_negatives,
            "precision": result.precision,
            "recall": result.recall,
            "f1_score": result.f1_score,
            "false_positive_rate": result.false_positive_rate,
            "tp_details": result.tp_details,
            "fp_details": result.fp_details,
            "fn_details": result.fn_details,
            "per_asi": per_asi_output,
        }
        with open(args.output_json, "w") as f:
            json.dump(output, f, indent=2)
        logger.info(f"Results written to {args.output_json}")

    # This script MEASURES. It does not gate.
    #
    # It used to end with its own `if result.f1_score < 0.75: sys.exit(1)`, a second
    # blocking Layer 1 floor living alongside `tests/benchmark/gates.yaml`, whose header
    # calls itself the single source of truth and carries f1_min there. The two never
    # knew about each other: on 2026-08-11 F1 measured 0.7467, so gates.yaml passed and
    # this line failed the same build. Before that it was 0.7510 — one thousandth above
    # the floor, which is the only reason the contradiction had not yet fired.
    #
    # The floor now lives in exactly one place. `quality_gate_check.py --config
    # tests/benchmark/gates.yaml` reads the JSON this script writes and owns the exit
    # code; .github/workflows/benchmark.yml runs it as a separate step. Do not
    # reintroduce a threshold here. See DECISIONS.md item 31 and
    # NIGHT_RUN_LEDGER.md § W24.


if __name__ == "__main__":
    main()
