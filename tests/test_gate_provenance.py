"""Regression guard: the quality gate may not pass on numbers it cannot account for.

History — the eighth instance of this repository's recurring defect shape, measured on
2026-08-11 and recorded in `NIGHT_RUN_LEDGER.md` § W38.

`quality_gate_check.py` decided the build by reading `results/layer1.json`, and read
nothing else. Two ways it exited 0 while proving nothing:

  A. **A stale file.** `results/layer1.json` is committed, so every checkout has one
     whether or not anything measured it. The copy from the previous commit — TP 196 /
     FP 93 / FN 40, F1 0.746667, describing a corpus three labels out of date — passed
     the freshly raised ratchet and reported success. `gates.yaml`'s own header records
     the historical version of this: the `results/layer1.json` committed at `a65b341`
     reported R 0.4746 and sat in the tree for six months.

  B. **No file at all.** An empty results directory produced two SKIP lines for two
     layers declared `enabled: true, blocking: true`, and SKIP is not counted as a
     failure. Exit 0.

Both are `CAPABILITY_BOUNDARIES.md` § 3 with the gate in the detector's place: a gate
that evaluated the wrong corpus, a gate that evaluated nothing, and a gate that evaluated
a passing build all print the same exit code, so nothing watching the exit code can tell
them apart.

These tests assert the *mechanism* rather than any one instance of it, and they use
synthetic results directories only: no scan, no fixture write, no ground-truth read
beyond fingerprinting.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = REPO_ROOT / "tests" / "benchmark"
GATE_CHECKER = BENCHMARK_DIR / "quality_gate_check.py"
GATES_YAML = BENCHMARK_DIR / "gates.yaml"
PROVENANCE = BENCHMARK_DIR / "provenance.py"


def _provenance_module():
    spec = importlib.util.spec_from_file_location("_gate_provenance", PROVENANCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _passing_metrics() -> dict:
    """Metrics that clear every floor in gates.yaml, so only provenance can block."""
    layer1 = yaml.safe_load(GATES_YAML.read_text())["layer1"]
    return {
        "true_positives": 1,
        "false_positives": 0,
        "false_negatives": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1_score": 1.0,
        "false_positive_rate": 0.0,
        "per_asi": {
            asi: {"recall": 1.0, "expected": 1, "tp": 1}
            for asi in layer1.get("per_asi_recall_min", {})
        },
    }


def _run_gate(results_dir: Path, layers: str = "layer1") -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable, str(GATE_CHECKER),
            "--config", str(GATES_YAML),
            "--results", str(results_dir),
            "--layers", layers,
        ],
        capture_output=True,
        text=True,
    )


def _results_dir(tmp_path: Path, payload: dict | None) -> Path:
    results = tmp_path / "results"
    results.mkdir()
    if payload is not None:
        (results / "layer1.json").write_text(json.dumps(payload))
    return results


class TestTheGateRefusesToGuess:
    """Defect A — a results file that does not describe the tree being checked."""

    def test_unstamped_results_block(self, tmp_path):
        """The exact shape of every layer1.json written before 2026-08-11."""
        proc = _run_gate(_results_dir(tmp_path, _passing_metrics()))
        assert proc.returncode == 1, (
            "a results file with no provenance passed the gate. Its numbers clear every "
            f"floor, but nothing in it says which corpus or scanner produced them.\n{proc.stdout}"
        )
        assert "provenance" in proc.stdout

    def test_stale_corpus_fingerprint_blocks(self, tmp_path):
        """A file measured before the corpus changed must not gate the build."""
        stamp = dict(_provenance_module().current_stamp(), corpus_fingerprint="0" * 64)
        proc = _run_gate(_results_dir(tmp_path, {**_passing_metrics(), "provenance": stamp}))
        assert proc.returncode == 1, proc.stdout
        assert "corpus" in proc.stdout

    def test_stale_source_fingerprint_blocks(self, tmp_path):
        """Nor may a file measured against a different scanner."""
        stamp = dict(_provenance_module().current_stamp(), source_fingerprint="0" * 64)
        proc = _run_gate(_results_dir(tmp_path, {**_passing_metrics(), "provenance": stamp}))
        assert proc.returncode == 1, proc.stdout
        assert "scanner source" in proc.stdout

    def test_measurement_from_another_install_blocks(self, tmp_path):
        """`python -m agent_audit` resolving outside the checkout is a different build.

        This is the failure that has no other symptom: the corpus is right, the scanner
        source is right, and the numbers describe a wheel installed somewhere else.
        """
        stamp = dict(
            _provenance_module().current_stamp(),
            runtime_package={
                "path": "/somewhere/else/site-packages/agent_audit",
                "version": "0.18.2",
                "error": None,
                "is_this_checkout": False,
            },
        )
        proc = _run_gate(_results_dir(tmp_path, {**_passing_metrics(), "provenance": stamp}))
        assert proc.returncode == 1, proc.stdout
        assert "outside this checkout" in proc.stdout

    def test_a_current_stamp_passes(self, tmp_path):
        """And the honest case must still exit 0, or the guard is just a blocker."""
        stamp = _provenance_module().current_stamp()
        proc = _run_gate(_results_dir(tmp_path, {**_passing_metrics(), "provenance": stamp}))
        assert proc.returncode == 0, proc.stdout

    def test_stale_results_are_not_also_scored(self, tmp_path):
        """A number that describes another tree must not be printed as if it were one.

        Reporting `precision 68.9% >= 66%` beneath a staleness failure is how a figure
        with no referent ends up quoted in a release note.
        """
        stamp = dict(_provenance_module().current_stamp(), corpus_fingerprint="0" * 64)
        proc = _run_gate(_results_dir(tmp_path, {**_passing_metrics(), "provenance": stamp}))
        scored = [line for line in proc.stdout.splitlines() if "[INFO] Layer 1" in line]
        assert not scored, (
            "the gate blocked on staleness and then reported the stale metrics anyway:\n"
            + "\n".join(scored)
        )


class TestSilenceIsNotSuccess:
    """Defect B — an enabled, blocking layer that nothing measured."""

    def test_missing_blocking_results_block(self, tmp_path):
        proc = _run_gate(_results_dir(tmp_path, None))
        assert proc.returncode == 1, (
            "an empty results directory passed the gate. Layer 1 is enabled and "
            f"blocking, and nothing measured it.\n{proc.stdout}"
        )
        assert "missing" in proc.stdout

    def test_every_enabled_blocking_layer_is_covered(self, tmp_path):
        """Not only Layer 1 — the rule is about the declaration, not the layer."""
        config = yaml.safe_load(GATES_YAML.read_text())
        blocking = [
            name
            for name in ("layer1", "layer2", "agent_vuln_bench")
            if config.get(name, {}).get("enabled", True)
            and config.get(name, {}).get("blocking", False)
        ]
        assert blocking, "no layer is enabled and blocking; this guard would be vacuous"

        proc = _run_gate(_results_dir(tmp_path, None), layers="all")
        assert proc.returncode == 1, proc.stdout
        failures = [line for line in proc.stdout.splitlines() if "[FAIL]" in line]
        assert len(failures) == len(blocking), (
            f"expected one blocking failure per unmeasured blocking layer {blocking}, "
            f"got {len(failures)}:\n{proc.stdout}"
        )

    def test_a_layer_not_named_is_not_checked(self, tmp_path):
        """--layers is the escape hatch, and it has to be explicit to be honest.

        A job that measured only Layer 1 says so. It does not get to stay green because
        the file it never produced reported SKIP.
        """
        stamp = _provenance_module().current_stamp()
        results = _results_dir(tmp_path, {**_passing_metrics(), "provenance": stamp})
        assert _run_gate(results, layers="layer1").returncode == 0
        assert _run_gate(results, layers="all").returncode == 1

    def test_an_unknown_layer_name_is_rejected(self, tmp_path):
        """A typo in --layers must not silently check nothing."""
        proc = _run_gate(_results_dir(tmp_path, None), layers="layer1,layerOne")
        assert proc.returncode == 1
        assert "Unknown layer" in proc.stderr


class TestTheMeasurementWritesAStamp:
    """The other half: a gate that demands a stamp needs a producer that writes one."""

    def test_committed_layer1_results_carry_a_current_stamp(self):
        """The file in the tree must itself survive the check it is gated by."""
        committed = REPO_ROOT / "results" / "layer1.json"
        if not committed.exists():
            pytest.skip("results/layer1.json is not present in this checkout")
        payload = json.loads(committed.read_text())
        problems = _provenance_module().verify_stamp(payload.get("provenance"))
        assert not problems, (
            "the committed results/layer1.json does not describe this tree, so CI would "
            "block on it. Regenerate:\n  cd packages/audit && python3 "
            "../../tests/benchmark/precision_recall.py --output-json ../../results/layer1.json\n"
            + "\n".join(problems)
        )

    def test_the_evaluator_stamps_what_it_writes(self, tmp_path):
        """Measured end to end, because a stamp written by nobody is the same defect."""
        ground_truth = tmp_path / "gt.yaml"
        ground_truth.write_text(
            yaml.safe_dump(
                {
                    "samples": [
                        {
                            "file": "synthetic.py",
                            "vulnerabilities": [
                                {"line": 10, "rule_id": "AGENT-001", "owasp_id": "ASI-01"}
                            ],
                        }
                    ]
                }
            )
        )
        scan = tmp_path / "scan.json"
        scan.write_text(
            json.dumps({"findings": [{"file": "synthetic.py", "line": 10, "rule_id": "AGENT-001"}]})
        )
        out = tmp_path / "layer1.json"
        proc = subprocess.run(
            [
                sys.executable, str(BENCHMARK_DIR / "precision_recall.py"),
                "--ground-truth", str(ground_truth),
                "--scan-results", str(scan),
                "--output-json", str(out),
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        stamp = json.loads(out.read_text()).get("provenance")
        assert stamp, "precision_recall.py --output-json wrote no provenance stamp"

        # And it must be a stamp of the corpus that was actually measured, not of the
        # repository default. A synthetic run producing the real fingerprint would let a
        # toy measurement gate a real build.
        assert _provenance_module().verify_stamp(stamp), (
            "a measurement against a synthetic ground-truth file carries the real "
            "corpus fingerprint, so it would pass the gate for the wrong tree"
        )
