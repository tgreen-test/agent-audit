"""Every corpus label must cite a rule the tool can actually emit.

Layer 1 matches a detection to a label on `file:line:rule_id` — the rule ID is part
of the key (`tests/benchmark/precision_recall.py`, `VulnerabilityLabel.key`). So a
label citing a rule ID that no code path can construct is not merely mislabelled: it
is **unmatchable by construction**. It scores as a false negative on every input, at
every commit, forever, and no amount of detection work can ever clear it.

AGENT-015 is why this file exists. Three documents gave that identifier three
different meanings at once:

* **published** as "Untrusted MCP Server Source";
* **implemented** as nothing at all — no producer at any commit, withdrawn in v0.20.0
  as a duplicate of AGENT-030;
* **labelled**, five times, on `npm install`, `curl | bash`, `git clone` + exec,
  install-from-remote-requirements and PyPI typosquatting — not one of which involves
  an MCP server.

The mechanism is worth stating plainly, because it generalises: **a rule that never
fires can be labelled to mean anything, because no output ever contradicts the
label.** Nothing was ever emitted under AGENT-015 to anchor its meaning, so the
corpus drifted to a different vulnerability class and nobody noticed for four minor
versions — while the identifier went on corrupting the published rule list, the
corpus and the ASI-04 coverage figure simultaneously.

This test is the check that would have caught it before it reached a published
number. There is deliberately no allow-list: pinning the known-bad set is what made
"advertised and unproducible" a permanently acceptable state for six rules, and
`tests/test_rule_producers.py` removed that allowance on the rule side. This removes
it on the corpus side.

Run standalone for the report without the assertion:

    python3 tests/test_corpus_label_rules.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_rule_producers import advertised_rules, producers_for  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
GROUND_TRUTH = REPO_ROOT / "tests" / "ground_truth" / "labeled_samples.yaml"


class Label:
    """One corpus label, with the line of the YAML file that declares its rule."""

    __slots__ = ("file", "line", "rule_id", "owasp_id", "notes", "yaml_line")

    def __init__(self, file: str, line: int, rule_id: str, owasp_id, notes, yaml_line):
        self.file = file
        self.line = line
        self.rule_id = rule_id
        self.owasp_id = owasp_id
        self.notes = notes
        self.yaml_line = yaml_line

    def __str__(self) -> str:
        where = f"labeled_samples.yaml:{self.yaml_line}" if self.yaml_line else "labeled_samples.yaml"
        return f"{self.rule_id}  {self.file}:{self.line}  ({where})  {self.notes!r}"


def _rule_declaration_lines() -> Dict[str, List[int]]:
    """rule_id -> the YAML line numbers that declare it, so a failure is actionable."""
    lines: Dict[str, List[int]] = defaultdict(list)
    for number, text in enumerate(GROUND_TRUTH.read_text(encoding="utf-8").splitlines(), 1):
        stripped = text.strip()
        if stripped.startswith("rule_id:"):
            lines[stripped.split(":", 1)[1].strip().strip("\"'")].append(number)
    return lines


def corpus_labels() -> List[Label]:
    data = yaml.safe_load(GROUND_TRUTH.read_text(encoding="utf-8"))
    declarations = _rule_declaration_lines()
    consumed: Dict[str, int] = defaultdict(int)

    labels: List[Label] = []
    for sample in data.get("samples", []) or []:
        for vuln in sample.get("vulnerabilities", []) or []:
            rule_id = vuln["rule_id"]
            candidates = declarations.get(rule_id, [])
            index = consumed[rule_id]
            consumed[rule_id] += 1
            labels.append(
                Label(
                    file=sample["file"],
                    line=vuln["line"],
                    rule_id=rule_id,
                    owasp_id=vuln.get("owasp_id"),
                    notes=vuln.get("notes", ""),
                    yaml_line=candidates[index] if index < len(candidates) else None,
                )
            )
    return labels


def unmatchable_labels() -> Tuple[List[Label], List[Label]]:
    """(labels citing a rule with no producer, labels citing an unadvertised rule).

    The first list is the fatal one: no producer means no detection can ever carry
    that rule ID, so the label can never be matched. The second is the same defect
    seen from the product side — the corpus grades against a rule the tool does not
    offer — and in practice the two overlap, because a withdrawn rule is withdrawn
    precisely for having no producer.
    """
    advertised = advertised_rules()
    producer_cache: Dict[str, bool] = {}

    no_producer: List[Label] = []
    not_advertised: List[Label] = []
    for label in corpus_labels():
        if label.rule_id not in producer_cache:
            producer_cache[label.rule_id] = bool(producers_for(label.rule_id))
        if not producer_cache[label.rule_id]:
            no_producer.append(label)
        if label.rule_id not in advertised:
            not_advertised.append(label)
    return no_producer, not_advertised


def test_no_corpus_label_cites_a_rule_that_cannot_be_emitted() -> None:
    """A label whose rule ID has no producer is a permanent false negative.

    This currently FAILS, and the failure is the point: six labels across two
    withdrawn rule IDs are unmatchable at every commit. Fixing them means editing
    ground truth, which is not a change a scanner author may make — see
    `docs/decisions/AGENT-015_RESOLUTION.md` for what each one should become and
    what the arithmetic does when it does.
    """
    no_producer, not_advertised = unmatchable_labels()

    by_rule: Dict[str, List[Label]] = defaultdict(list)
    for label in no_producer:
        by_rule[label.rule_id].append(label)

    report = []
    for rule_id in sorted(by_rule):
        report.append(f"  {rule_id} — {len(by_rule[rule_id])} label(s), no producer anywhere:")
        report.extend(f"      {label}" for label in by_rule[rule_id])

    only_unadvertised = [l for l in not_advertised if l not in no_producer]
    if only_unadvertised:
        report.append("  additionally, citing a rule that is not in the advertised set:")
        report.extend(f"      {label}" for label in only_unadvertised)

    assert not no_producer, (
        f"{len(no_producer)} corpus label(s) cite a rule ID that no code path in the "
        "package can construct. Layer 1 keys on file:line:rule_id, so each of these is "
        "an unmatchable label — a false negative on every input at every commit, and "
        "where the tool does detect the defect under a different ID, a false positive "
        "at the same time.\n" + "\n".join(report) + "\n\n"
        "This is not fixable by improving detection. Either the label is retargeted to "
        "the rule that fires (an accounting correction) or a rule is introduced that "
        "matches what the label describes (a capability change). "
        "docs/decisions/AGENT-015_RESOLUTION.md sets out both with the measured "
        "arithmetic. Ground truth is not the scanner author's to edit."
    )


def test_every_advertised_rule_id_in_the_corpus_is_spelled_consistently() -> None:
    """Cheap companion check: no label may cite a malformed identifier.

    A typo'd ID is the same defect with a shorter story — unmatchable, and silently
    counted as a miss rather than reported as a corpus error.
    """
    malformed = [
        label for label in corpus_labels() if not re.fullmatch(r"AGENT-\d{3}", label.rule_id)
    ]
    assert not malformed, "corpus labels with a malformed rule ID: " + ", ".join(
        str(label) for label in malformed
    )


if __name__ == "__main__":
    no_producer, not_advertised = unmatchable_labels()
    total = len(corpus_labels())
    print(f"corpus labels: {total}")
    print(f"labels citing a rule with NO producer: {len(no_producer)}")
    for label in no_producer:
        print(f"    {label}")
    print(f"labels citing a rule not in the advertised set: {len(not_advertised)}")
    for label in not_advertised:
        print(f"    {label}")
    sys.exit(1 if no_producer else 0)
