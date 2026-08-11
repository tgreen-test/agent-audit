"""Regression guard: exactly one thing may decide whether Layer 1 passes.

History. `tests/benchmark/gates.yaml` opens by calling itself THE SINGLE SOURCE OF
TRUTH, and its header describes deleting an inline gate in
`.github/workflows/benchmark.yml` because two gates on one layer hid a contradiction
for six months. That consolidation missed one: `precision_recall.py` ended with its
own

    if result.f1_score < 0.75:
        sys.exit(1)

while gates.yaml carried `f1_min: 0.72`. On 2026-08-11 the measurement was F1 0.7467,
so the same build passed the documented gate and failed the undocumented one. Before
that it read 0.7510 — one thousandth above the hard-coded floor, which is the only
reason the contradiction had not yet fired. It was the seventh instance in this
repository of two places defining the same thing.

These tests make the *shape* of that defect fail the suite rather than any one
instance of it, so the next copy cannot be added quietly. They read source text and
synthetic inputs only: no fixture, no ground-truth file and no scan.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = REPO_ROOT / "tests" / "benchmark"
EVALUATOR = BENCHMARK_DIR / "precision_recall.py"
GATE_CHECKER = BENCHMARK_DIR / "quality_gate_check.py"
GATES_YAML = BENCHMARK_DIR / "gates.yaml"
BENCHMARK_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "benchmark.yml"

# Metric names a Layer 1 floor could be expressed against.
METRIC_NAMES = ("f1_score", "f1", "precision", "recall", "false_positive_rate", "fp_rate")

# `metric <op> 0.87` / `metric <op> 87` — a literal floor written in code.
_LITERAL_COMPARISON = re.compile(
    r"\b(?:" + "|".join(METRIC_NAMES) + r")\b\s*(?:<=|>=|<|>)\s*(?:0\.\d+|\d+(?:\.\d+)?%?)",
    re.IGNORECASE,
)


def _current_stamp():
    """The real provenance stamp for this checkout.

    Tests in this file invent metrics but must not invent provenance: since W38 the gate
    refuses to evaluate a results file that cannot name the corpus and scanner behind it,
    so a synthetic file that omits the stamp fails for a reason the test is not about.
    """
    spec = importlib.util.spec_from_file_location(
        "_layer1_provenance", BENCHMARK_DIR / "provenance.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.current_stamp()


def _load_evaluator():
    """Import precision_recall.py by path; tests/benchmark is not a package."""
    spec = importlib.util.spec_from_file_location("_layer1_gate_evaluator", EVALUATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _code_lines(path: Path) -> list[tuple[int, str]]:
    """Source lines with whole-line comments dropped.

    A comment describing a deleted gate is documentation, not a second definition —
    this file's own docstring quotes one. Only executable text is inspected.
    """
    out = []
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("#") or not stripped:
            continue
        out.append((number, raw.split("#", 1)[0]))
    return out


class TestSingleSourceOfTruth:
    def test_the_measurement_script_defines_no_layer1_floor(self):
        """precision_recall.py measures. It must not also decide.

        This is the exact line that was deleted; the test fails if any equivalent
        returns, whichever metric it is written against.
        """
        offenders = [
            f"{EVALUATOR.name}:{n}: {line.strip()}"
            for n, line in _code_lines(EVALUATOR)
            if _LITERAL_COMPARISON.search(line)
        ]
        assert not offenders, (
            "precision_recall.py compares a metric against a literal threshold. "
            "Layer 1 floors live in tests/benchmark/gates.yaml and are evaluated by "
            "quality_gate_check.py, which owns the exit code:\n  "
            + "\n  ".join(offenders)
        )

    def test_the_measurement_script_never_exits_on_a_metric(self):
        """No `sys.exit` may sit downstream of a metric value.

        Weaker than the test above and deliberately so: it catches a floor written
        as `if not ok: sys.exit(1)` where `ok` was computed elsewhere.
        """
        # Everything after the call to evaluate() is the post-measurement tail, which
        # is where the deleted gate lived. Comments are excluded: the replacement
        # comment quotes the line it replaced, and so does this file's docstring.
        code = _code_lines(EVALUATOR)
        anchor = next(
            n for n, line in code if "evaluate(ground_truth, findings)" in line
        )
        tail = "\n".join(line for n, line in code if n > anchor)
        assert "sys.exit" not in tail, (
            "precision_recall.py exits after computing the measurement. The only "
            "legitimate non-zero exit from this script is a failure to produce a "
            "measurement at all (missing ground truth, unparseable scan output), "
            "and those all precede evaluate()."
        )

    def test_the_gate_checker_reads_every_floor_from_config(self):
        """quality_gate_check.py may hold no floor of its own.

        `.get(key, 0)` defaults are fine — a missing floor must not silently become
        a passing one — but a non-zero literal would be a second definition.
        """
        offenders = []
        for n, line in _code_lines(GATE_CHECKER):
            for match in _LITERAL_COMPARISON.finditer(line):
                text = match.group(0)
                value = re.split(r"<=|>=|<|>", text)[-1].strip().rstrip("%")
                if float(value) != 0.0:
                    offenders.append(f"{GATE_CHECKER.name}:{n}: {line.strip()}")
        assert not offenders, (
            "quality_gate_check.py compares against a literal floor instead of one "
            "read from gates.yaml:\n  " + "\n  ".join(offenders)
        )

    def test_the_workflow_gates_layer1_exactly_once(self):
        """One step in benchmark.yml may decide Layer 1, and it must use gates.yaml."""
        workflow = BENCHMARK_WORKFLOW.read_text()

        gating_steps = re.findall(r"quality_gate_check\.py[^\n]*(?:\n[^\n]*)*?--config\s+(\S+)", workflow)
        assert gating_steps, "benchmark.yml no longer runs quality_gate_check.py at all"
        for config in gating_steps:
            assert config.endswith("tests/benchmark/gates.yaml"), (
                f"a workflow step gates against {config}, not tests/benchmark/gates.yaml. "
                "There is one Layer 1 config; quality_gates.yaml and quality_gates_v2.yaml "
                "are superseded and are referenced by nothing."
            )

        # An inline floor written into the workflow body is the original defect.
        for n, raw in enumerate(workflow.splitlines(), 1):
            line = raw.split("#", 1)[0]
            assert not _LITERAL_COMPARISON.search(line), (
                f"benchmark.yml:{n} carries an inline metric threshold: {raw.strip()}"
            )


class TestGatesYamlIsWellFormed:
    def test_layer1_ratchet_and_target_are_both_declared(self):
        config = yaml.safe_load(GATES_YAML.read_text())
        layer1 = config["layer1"]
        for key in ("precision_min", "recall_min", "f1_min"):
            assert key in layer1["thresholds"], f"gates.yaml layer1.thresholds lacks {key}"
            assert key in layer1["target"], f"gates.yaml layer1.target lacks {key}"

    def test_the_ratchet_is_not_above_the_target(self):
        """The ratchet is a floor under the measurement; the target is the ambition.

        A ratchet above its target would mean CI blocks on a number the project does
        not even claim to be aiming for, which is how an aspiration gets mistaken for
        a standard.
        """
        layer1 = yaml.safe_load(GATES_YAML.read_text())["layer1"]
        for key in ("precision_min", "recall_min", "f1_min"):
            assert layer1["thresholds"][key] <= layer1["target"][key], (
                f"gates.yaml layer1 ratchet {key}={layer1['thresholds'][key]} exceeds "
                f"target {key}={layer1['target'][key]}"
            )


class TestExitContract:
    """End to end, with synthetic inputs — no scan, no fixture, no ground truth file."""

    @staticmethod
    def _synthetic_inputs(tmp_path: Path) -> tuple[Path, Path]:
        ground_truth = tmp_path / "labels.yaml"
        ground_truth.write_text(
            yaml.safe_dump(
                {
                    "samples": [
                        {
                            "file": "synthetic.py",
                            "vulnerabilities": [
                                {"line": 10, "rule_id": "AGENT-001", "owasp_id": "ASI-01"},
                                {"line": 20, "rule_id": "AGENT-004", "owasp_id": "ASI-02"},
                            ],
                        }
                    ]
                }
            )
        )
        scan = tmp_path / "scan.json"
        # One hit, one miss, one spurious: P 0.5 / R 0.5 / F1 0.5, well under any floor.
        scan.write_text(
            json.dumps(
                {
                    "findings": [
                        {"file": "synthetic.py", "line": 10, "rule_id": "AGENT-001"},
                        {"file": "synthetic.py", "line": 90, "rule_id": "AGENT-099"},
                    ]
                }
            )
        )
        return ground_truth, scan

    def test_measurement_script_exits_zero_even_on_a_terrible_score(self, tmp_path):
        """A bad measurement is still a successful measurement."""
        ground_truth, scan = self._synthetic_inputs(tmp_path)
        out = tmp_path / "layer1.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(EVALUATOR),
                "--ground-truth", str(ground_truth),
                "--scan-results", str(scan),
                "--output-json", str(out),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, (
            f"precision_recall.py exited {proc.returncode} on a valid measurement.\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
        measured = json.loads(out.read_text())
        assert measured["f1_score"] == pytest.approx(0.5)

    def test_measurement_script_exits_nonzero_when_it_cannot_measure(self, tmp_path):
        """The one legitimate failure mode: no input to measure."""
        proc = subprocess.run(
            [sys.executable, str(EVALUATOR), "--ground-truth", str(tmp_path / "absent.yaml")],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0

    def test_gate_checker_blocks_below_the_ratchet(self, tmp_path):
        """A result one point under gates.yaml's f1_min must exit 1."""
        f1_min = yaml.safe_load(GATES_YAML.read_text())["layer1"]["thresholds"]["f1_min"]
        results = tmp_path / "results"
        results.mkdir()
        (results / "layer1.json").write_text(
            json.dumps(
                {
                    # Real stamp, so this blocks for the reason the test names — see
                    # _current_stamp. Without it the gate would block on provenance and
                    # the assertion below would pass while testing nothing.
                    "provenance": _current_stamp(),
                    "true_positives": 1,
                    "false_positives": 0,
                    "false_negatives": 0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1_score": round(f1_min - 0.01, 4),
                    "false_positive_rate": 0.0,
                    "per_asi": {},
                }
            )
        )
        proc = subprocess.run(
            [
                sys.executable, str(GATE_CHECKER),
                "--config", str(GATES_YAML),
                "--results", str(results),
                "--layers", "layer1",
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1, (
            f"quality_gate_check.py exited {proc.returncode} on F1 one point below the "
            f"ratchet ({f1_min}).\n{proc.stdout}"
        )
        assert "F1" in proc.stdout and "provenance" not in proc.stdout, (
            "it blocked, but not on the ratchet — the assertion above would pass on any "
            f"blocking reason at all.\n{proc.stdout}"
        )

    def test_gate_checker_passes_on_the_ratchet(self, tmp_path):
        """And exactly at the floor it must pass, so the ratchet is inclusive."""
        layer1 = yaml.safe_load(GATES_YAML.read_text())["layer1"]
        thresholds = layer1["thresholds"]
        results = tmp_path / "results"
        results.mkdir()
        (results / "layer1.json").write_text(
            json.dumps(
                {
                    # Synthetic metrics, real stamp. The numbers below are invented to sit
                    # exactly on the ratchet; the stamp is the true one for this checkout,
                    # because since W38 the gate refuses to evaluate a file that cannot say
                    # which corpus and which scanner produced it.
                    "provenance": _current_stamp(),
                    "true_positives": 1,
                    "false_positives": 0,
                    "false_negatives": 0,
                    "precision": thresholds["precision_min"],
                    "recall": thresholds["recall_min"],
                    "f1_score": thresholds["f1_min"],
                    "false_positive_rate": 0.0,
                    "per_asi": {
                        asi: {"recall": floor, "expected": 1, "tp": 1}
                        for asi, floor in layer1.get("per_asi_recall_min", {}).items()
                    },
                }
            )
        )
        proc = subprocess.run(
            [
                sys.executable, str(GATE_CHECKER),
                "--config", str(GATES_YAML),
                "--results", str(results),
                "--layers", "layer1",
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stdout


def test_report_thresholds_come_from_gates_yaml(tmp_path):
    """The printed report must not carry its own copy of the floors either.

    It used to print `Precision >= 90%` / `Recall >= 85%` / `F1 >= 0.87` from literals
    that happened to duplicate gates.yaml `layer1.target`, and then announce
    "QUALITY GATE FAILED" for missing an aspiration that blocks nothing — while the
    gate that does block was passing.
    """
    evaluator = _load_evaluator()
    ratchet, target = evaluator.load_layer1_gates()
    config = yaml.safe_load(GATES_YAML.read_text())["layer1"]
    assert ratchet == config["thresholds"]
    assert target == config["target"]

    # And a missing config yields no floors rather than invented ones.
    empty_ratchet, empty_target = evaluator.load_layer1_gates(tmp_path / "absent.yaml")
    assert empty_ratchet == {} and empty_target == {}
