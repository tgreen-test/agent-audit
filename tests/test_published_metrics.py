"""Regression guard: one Layer 1 measurement, and every block that prints it must agree.

History. On 2026-09-12 (RUN 11) the three documents that *define* the correct Layer 1
figures for every other surface were themselves stale:

  * `docs/decisions/METRICS_RETRACTION.md` § 3, under the heading **"The correct current
    values, measured now"**, printed a verbatim transcript reading TP 196 / FP 93 / FN 40,
    P 67.82% / R 83.05% / F1 74.67%. The command in the transcript produces TP 199 /
    FP 90 / FN 37, P 68.86% / R 84.32% / F1 75.81%.
  * `CAPABILITY_BOUNDARIES.md` § 6, directly under the sentence "Reproduce with
    `python3 tests/benchmark/precision_recall.py`", printed the same superseded set.
  * `docs/F1_REPRODUCTION.md` — the document whose entire purpose is to prove the headline
    reproduces — attributed the v0.20.0 output to "2026-05-31 (agent-audit 0.19.0)" and
    did its adjustment arithmetic on a 70-false-positive run that no longer exists.

The figures went stale at `fda9f06`, which corrected three ground-truth labels and moved
the measurement from F1 0.746667 to 0.758095. Every surface a *user* reads was updated in
that pass. The documents those surfaces cite as the authority were not, because nothing
related them to the measurement.

**Why no existing guard saw it.** `scripts/scan_external_claims.sh` carries patterns for
exactly these numbers (`F1-0.7467`, `P-67.82`, `R-83.05`). It reported nothing, because
`scripts/external_claims_allowlist.txt` exempts `CAPABILITY_BOUNDARIES.md`,
`docs/decisions/` and the working notes — correctly, since those documents quote wrong
numbers in order to discuss them. The allowlist was drawn around *documents*, and the
documents it exempted contain both kinds of block: quotations of withdrawn figures, which
must stay, and statements of the current figure, which must move. So the scanner's blind
spot fell precisely over the definition of the value it was scanning for.

That is `CAPABILITY_BOUNDARIES.md` § 3 again, one level up: a checker that cannot see a
surface and a surface with nothing wrong on it produce identical output.

**The invariant, and why it is drawn this narrowly.** A fenced code block is a claim about
a machine: it says "this is what came out". So —

    a fenced block that names `precision_recall.py` as its producer must print what
    `precision_recall.py` actually produces.

Not "the numbers must not appear" — they must, in the retraction tables, the causal notes
and the run logs, or the defect becomes unwriteable. Prose and markdown tables are left
alone for that reason, and so are blocks quoting some *other* producer: § 1 of the
retraction document displays the withdrawn 98.51% / 100% / 99.25% four times, as the output
of `git show`, of a `python3 -c` arithmetic demonstration, and as quoted CHANGELOG lines.
Those are evidence that the figure was never measured. A guard that failed on them would be
failing on true text, and a guard that fails on true text gets switched off rather than
repaired.

Requiring the producer to be *named* is the load-bearing half. It is RUN 9's rule turned
into a check — *where a fact has copies, give every copy the command that produces it* —
and it is self-reinforcing: a block earns the guard's attention by saying what made it, and
`test_the_authority_documents_still_print_a_checked_block` then requires the three
documents that define the number to keep saying it. A block that is deliberately historical
says so in its heading instead (`_SUPERSESSION_MARKERS`).

The fact is `results/layer1.json`, whose own freshness is guarded by
`tests/test_gate_provenance.py` — a stale results file cannot pass the gate, so it cannot
silently become the baseline here either.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYER1_JSON = REPO_ROOT / "results" / "layer1.json"

# Documents that present the Layer 1 measurement as the current one. Records that only
# quote it historically (NIGHT_RUN_LEDGER.md, RUN*_REPORT.md, CLAIMS_RECONCILIATION.md)
# are deliberately absent: they are stamped with the commit they describe.
GUARDED_SURFACES = (
    "CLAUDE.md",
    "README.md",
    "README_CN.md",
    "CAPABILITY_BOUNDARIES.md",
    "docs/index.html",
    "docs/F1_REPRODUCTION.md",
    "docs/COMPETITIVE-COMPARISON.md",
    "docs/BENCHMARK-RESULTS.md",
    "docs/decisions/METRICS_RETRACTION.md",
)

# Surfaces that must yield at least one checked block. If one stops matching, this guard
# has gone inert over it and the suite says so rather than going quiet — the failure mode
# that let the defect above survive a scanner built to catch it.
MUST_PRINT_A_BLOCK = (
    "CAPABILITY_BOUNDARIES.md",
    "docs/F1_REPRODUCTION.md",
    "docs/decisions/METRICS_RETRACTION.md",
)

# What ties a block to the Layer 1 measurement. The block body, or the few lines above the
# opening fence, must name the script — otherwise the block is quoting some other producer
# and is none of this guard's business.
_PRODUCER = "precision_recall.py"

# How far above the opening fence to look for the producer's name. Six lines covers a
# heading plus a sentence; beyond that the attribution is too far away to be a claim about
# this block, which is itself the defect `docs/F1_REPRODUCTION.md` had.
_CONTEXT_LINES = 6

# A block whose heading or body says it is historical. Kept short and explicit: a marker
# list that grows loose turns the guard off one document at a time.
_SUPERSESSION_MARKERS = (
    "before",
    "previously",
    "used to print",
    "superseded",
    "historical",
    "no longer",
    "as published",
    "prior to",
    "withdrawn",
)

_COUNTS = {
    "TP": re.compile(r"(?:\bTP\b|True Positives)\s*[:=]?\s*(\d+)"),
    "FP": re.compile(r"(?:\bFP\b|False Positives)\s*[:=]?\s*(\d+)"),
    "FN": re.compile(r"(?:\bFN\b|False Negatives)\s*[:=]?\s*(\d+)"),
}
_RATIOS = {
    "precision": re.compile(r"\bPrecision\b\s*[:=]?\s*([0-9]*\.?[0-9]+)\s*(%?)"),
    "recall": re.compile(r"\bRecall\b\s*[:=]?\s*([0-9]*\.?[0-9]+)\s*(%?)"),
    "f1": re.compile(r"\bF1(?:[-\s]?Score)?\b\s*[:=]?\s*([0-9]*\.?[0-9]+)\s*(%?)"),
}


def measured():
    """The fact. Raises rather than defaulting — a guard with no baseline is not a guard."""
    data = json.loads(LAYER1_JSON.read_text(encoding="utf-8"))
    return {
        "TP": data["true_positives"],
        "FP": data["false_positives"],
        "FN": data["false_negatives"],
        "precision": data["precision"],
        "recall": data["recall"],
        "f1": data["f1_score"],
    }


def _fenced_blocks(text):
    """Yield (start line number, heading context, block body) for each fenced block."""
    lines = text.splitlines()
    in_block = False
    start = 0
    body = []
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            if in_block:
                context = "\n".join(lines[max(0, start - 1 - _CONTEXT_LINES) : start - 1])
                yield start, context, "\n".join(body)
                in_block = False
                body = []
            else:
                in_block = True
                start = lineno
            continue
        if in_block:
            body.append(line)


def _ratio_matches(found, raw_is_percent, actual):
    """Compare a written ratio to the measurement at the precision it was written to."""
    if raw_is_percent:
        return round(found, 2) == round(actual * 100, 2)
    return abs(found - actual) < 5e-4


def _claims():
    """Every Layer 1 figure printed inside a fenced block on a guarded surface.

    Yields (surface, line number, label, written value, ok).
    """
    fact = measured()
    for rel in GUARDED_SURFACES:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for start, context, body in _fenced_blocks(text):
            haystack = (context + "\n" + body).lower()
            if _PRODUCER not in haystack:
                continue
            if any(marker in haystack for marker in _SUPERSESSION_MARKERS):
                continue
            for label, pattern in _COUNTS.items():
                for match in pattern.finditer(body):
                    written = int(match.group(1))
                    yield rel, start, label, written, written == fact[label]
            for label, pattern in _RATIOS.items():
                for match in pattern.finditer(body):
                    written = float(match.group(1))
                    ok = _ratio_matches(written, match.group(2) == "%", fact[label])
                    yield rel, start, label, written, ok


def test_the_measurement_exists():
    """A vacuous guard is worse than none."""
    fact = measured()
    assert fact["TP"] > 0 and fact["FP"] >= 0 and fact["FN"] >= 0
    assert 0.0 < fact["f1"] <= 1.0


def test_every_printed_layer1_block_states_the_measurement():
    fact = measured()
    wrong = [(rel, start, label, written) for rel, start, label, written, ok in _claims() if not ok]
    assert not wrong, (
        f"{len(wrong)} figure(s) printed as command output disagree with the measurement "
        f"in results/layer1.json (TP {fact['TP']} / FP {fact['FP']} / FN {fact['FN']}, "
        f"P {fact['precision']:.4f} / R {fact['recall']:.4f} / F1 {fact['f1']:.4f}):\n\n"
        + "\n".join(
            f"  {rel}: block opening at line {start} prints {label} = {written}"
            for rel, start, label, written in wrong
        )
        + "\n\nReproduce the measurement with:\n"
        "  cd packages/audit && python3 ../../tests/benchmark/precision_recall.py\n\n"
        "If a block is meant to be historical, say so in its heading — see "
        "_SUPERSESSION_MARKERS — rather than leaving it to read as current."
    )


@pytest.mark.parametrize("rel", MUST_PRINT_A_BLOCK)
def test_the_authority_documents_still_print_a_checked_block(rel):
    """Otherwise the test above passes by finding nothing.

    These three are what every other surface cites. A reformat that took one of them out
    of the guard would restore the exact condition of RUN 11: the definition of the value
    drifting while everything quoting it stayed green.
    """
    seen = [claim for claim in _claims() if claim[0] == rel]
    assert seen, (
        f"{rel} no longer prints any Layer 1 figure this guard can read.\n"
        "Either the block was removed, or its formatting changed and the guard has gone "
        "inert over the one document that defines the number."
    )


@pytest.mark.parametrize("stale", [0.7467, 0.778, 0.9925])
def test_the_superseded_f1_values_are_not_printed_as_current(stale):
    """Named individually so a regression says which one came back.

    0.7467 is the pre-`fda9f06` measurement, 0.778 the v0.19.0 one, 0.9925 the withdrawn
    figure that was never a measurement at all.
    """
    offenders = [
        f"  {rel}: block opening at line {start} prints F1 = {written}"
        for rel, start, label, written, _ in _claims()
        if label == "f1" and abs(written - stale) < 5e-4
    ]
    assert not offenders, (
        f"the superseded F1 {stale} is printed as current command output:\n"
        + "\n".join(offenders)
    )


def test_the_guard_can_actually_fail():
    """The cheapest test in the file, and the one with the worst failure mode if absent.

    A silent regex is indistinguishable from a clean repository — the defect this module
    exists to catch, applied to this module. Feed it a block that is wrong on purpose.
    """
    fact = measured()
    bogus = f"TP {fact['TP'] + 7}   FP {fact['FP'] + 7}   FN {fact['FN'] + 7}"
    found = {label: int(m.group(1)) for label, p in _COUNTS.items() if (m := p.search(bogus))}
    assert found == {"TP": fact["TP"] + 7, "FP": fact["FP"] + 7, "FN": fact["FN"] + 7}, (
        "the count patterns did not read a block they must be able to read"
    )
    assert not _ratio_matches(74.67, True, fact["f1"]), (
        "the ratio comparison accepted the superseded F1 74.67% as matching the "
        "measurement — the comparison, not the documents, is what is broken"
    )
