"""Regression guard: the Layer 1 evaluator must score deterministically.

`precision_recall.evaluate` matched findings to labels while iterating over two
`set` objects. Set iteration order for these tuples varies with PYTHONHASHSEED,
so when one detection fell within `line_tolerance` of two labels, whichever
label the loop reached first claimed the match. The identical command therefore
returned different scores on different runs:

    PYTHONHASHSEED=0 -> TP 196, F1 74.95%
    PYTHONHASHSEED=1 -> TP 197, F1 75.19%

That is fatal for the quality gate, which ratchets a floor against these
numbers: a build could fail on a rerun of a commit that had just passed, and a
genuine one-finding regression is indistinguishable from the flap.

These tests use synthetic labels and findings — no fixture and no ground-truth
file is read — so they stay valid as the corpus evolves.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = REPO_ROOT / "tests" / "benchmark" / "precision_recall.py"


def _load_evaluator():
    """Import precision_recall.py by path; tests/benchmark is not a package."""
    spec = importlib.util.spec_from_file_location("_layer1_evaluator", EVALUATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def evaluator():
    return _load_evaluator()


def _ambiguous_case(evaluator):
    """One finding sitting within tolerance of two labels of the same rule.

    This is the exact shape that made the score flap: line 11 is 1 away from
    label line 10 and 2 away from label line 13, so both are eligible and the
    tie had to be broken by iteration order.
    """
    Label = evaluator.VulnerabilityLabel
    Finding = evaluator.Finding
    ground_truth = {
        "a.py": [
            Label(file="a.py", line=10, rule_id="AGENT-001"),
            Label(file="a.py", line=13, rule_id="AGENT-001"),
        ]
    }
    findings = [Finding(file="a.py", line=11, rule_id="AGENT-001")]
    return ground_truth, findings


def test_ambiguous_match_is_stable_across_orderings(evaluator):
    """Repeated evaluation of the same inputs gives the same score.

    In-process only: PYTHONHASHSEED is fixed for the life of an interpreter, so
    this alone does NOT reproduce the original defect. See the subprocess test
    below, which is the one that actually catches it.
    """
    ground_truth, findings = _ambiguous_case(evaluator)

    scores = set()
    for _ in range(25):
        result, _per_asi = evaluator.evaluate(ground_truth, findings, line_tolerance=3)
        scores.add((result.true_positives, result.false_positives, result.false_negatives))

    assert len(scores) == 1, f"evaluate() is not deterministic: {scores}"


# The probe below is what makes this file a real guard. Set iteration order is
# fixed for the life of an interpreter, so the flap is only visible when the
# same inputs are scored by several processes started with different hash seeds.
_PROBE = textwrap.dedent(
    """
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("_ev", sys.argv[1])
    ev = importlib.util.module_from_spec(spec)
    sys.modules["_ev"] = ev
    spec.loader.exec_module(ev)

    # Several ambiguous files, to raise the chance that at least one ordering
    # differs. Each finding sits within tolerance of two same-rule labels.
    gt, fs = {}, []
    for i in range(12):
        name = "f%02d.py" % i
        gt[name] = [
            ev.VulnerabilityLabel(file=name, line=10, rule_id="AGENT-001"),
            ev.VulnerabilityLabel(file=name, line=13, rule_id="AGENT-001"),
        ]
        fs.append(ev.Finding(file=name, line=11, rule_id="AGENT-001"))

    r, _ = ev.evaluate(gt, fs, line_tolerance=3)
    print("%d,%d,%d|%s" % (r.true_positives, r.false_positives,
                           r.false_negatives, ";".join(r.fn_details)))
    """
)


@pytest.mark.parametrize("seeds", [("0", "1", "2", "3", "4", "5", "6", "7")])
def test_score_is_identical_across_hash_seeds(tmp_path, seeds):
    """The defect proper: identical inputs, different PYTHONHASHSEED, one score."""
    probe = tmp_path / "probe.py"
    probe.write_text(_PROBE)

    outputs = {}
    for seed in seeds:
        proc = subprocess.run(
            [sys.executable, str(probe), str(EVALUATOR)],
            capture_output=True,
            text=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
            timeout=120,
        )
        assert proc.returncode == 0, f"probe failed at seed {seed}: {proc.stderr}"
        outputs[seed] = proc.stdout.strip()

    distinct = set(outputs.values())
    assert len(distinct) == 1, (
        "evaluate() scores differ by PYTHONHASHSEED — the quality gate would "
        f"ratchet against a flapping number:\n"
        + "\n".join(f"  seed {s}: {o}" for s, o in sorted(outputs.items()))
    )


def test_ambiguous_match_credits_the_nearest_label(evaluator):
    """The tie is broken by line distance, not by iteration accident."""
    ground_truth, findings = _ambiguous_case(evaluator)

    result, _per_asi = evaluator.evaluate(ground_truth, findings, line_tolerance=3)

    assert result.true_positives == 1
    assert result.false_negatives == 1
    # Line 10 is 1 away, line 13 is 2 away: the match must go to line 10, so the
    # surviving false negative is line 13.
    assert result.fn_details == ["a.py:13 AGENT-001"]


def test_detail_lists_are_ordered(evaluator):
    """Report bodies are stable too, so diffing two runs is meaningful."""
    Label = evaluator.VulnerabilityLabel
    Finding = evaluator.Finding
    ground_truth = {
        "z.py": [Label(file="z.py", line=5, rule_id="AGENT-002")],
        "a.py": [Label(file="a.py", line=5, rule_id="AGENT-001")],
        "m.py": [Label(file="m.py", line=5, rule_id="AGENT-003")],
    }
    findings = [Finding(file="q.py", line=1, rule_id="AGENT-009")]

    runs = set()
    for _ in range(25):
        result, _per_asi = evaluator.evaluate(ground_truth, findings, line_tolerance=3)
        runs.add(tuple(result.fn_details))

    assert len(runs) == 1, f"fn_details ordering is unstable: {runs}"
    assert list(runs)[0] == (
        "a.py:5 AGENT-001",
        "m.py:5 AGENT-003",
        "z.py:5 AGENT-002",
    )


def test_exact_match_still_preferred_over_fuzzy(evaluator):
    """Control: pinning the order must not disturb exact matching."""
    Label = evaluator.VulnerabilityLabel
    Finding = evaluator.Finding
    ground_truth = {
        "a.py": [
            Label(file="a.py", line=10, rule_id="AGENT-001"),
            Label(file="a.py", line=12, rule_id="AGENT-001"),
        ]
    }
    findings = [
        Finding(file="a.py", line=12, rule_id="AGENT-001"),
        Finding(file="a.py", line=10, rule_id="AGENT-001"),
    ]

    result, _per_asi = evaluator.evaluate(ground_truth, findings, line_tolerance=3)

    assert (result.true_positives, result.false_positives, result.false_negatives) == (2, 0, 0)


def test_rule_id_mismatch_still_counts_twice(evaluator):
    """Control: this guard must not paper over the W11 double-count.

    A detection whose rule id disagrees with the label is deliberately scored as
    both a false positive and a false negative. That is the behaviour W11
    characterises; determinism must not quietly change it.
    """
    Label = evaluator.VulnerabilityLabel
    Finding = evaluator.Finding
    ground_truth = {"a.py": [Label(file="a.py", line=10, rule_id="AGENT-015")]}
    findings = [Finding(file="a.py", line=10, rule_id="AGENT-001")]

    result, _per_asi = evaluator.evaluate(ground_truth, findings, line_tolerance=3)

    assert (result.true_positives, result.false_positives, result.false_negatives) == (0, 1, 1)
