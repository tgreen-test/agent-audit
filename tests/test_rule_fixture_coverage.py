"""Every advertised rule must have an input in this repository that makes it fire.

`tests/test_rule_producers.py` asks whether a rule *can* be constructed by some code
path. This asks the next question, and it is the one that determines whether a rule
is measured: **is there a file in the repository that actually produces it?**

A rule with a producer but no input is invisible to every quality gate in the
project. It cannot regress, because nothing observes it.

**Sixteen** advertised rules were in that state. Twelve had been catalogued —
AGENT-002, 027, 037, 038, 039, 040, 042, 048, 052, 055, 056, 057 — each demonstrated
working only by a hand-built trigger recorded in a ledger, which is not a test. The
audit that produced that list classified a rule as covered if it fired on *any* of
its probes, and some of its probes were synthetic files it built itself rather than
repository fixtures. Running the check against the repository alone adds four more:
**AGENT-049, 083, 084 and 085.** The graded corpus contains only `.py`, `.json`,
`.md` and `.sh` files, so the Solidity and Go scanners had no input in it at all.

Two of the sixteen, AGENT-056 and AGENT-057, had additionally been recorded as
structurally unreachable on the strength of a producer method with no callers; the
real producer was a differently-named method that runs on every config scan, and
nothing in the repository was exercising either.

The two trees are kept separate on purpose, and the reason is measured rather than
asserted — see `tests/rule_fixtures/README.md`. `tests/fixtures/` is the graded
corpus: an unlabelled file there costs published precision, which is exactly what
happened to `vulnerable_hooks` and AGENT-120. `tests/rule_fixtures/` is not graded by
anything except this module.

There is no allow-list. The single exception, AGENT-054, is not listed here at all —
it is pinned with its reason in `tests/test_rule_producers.py`, and this module reads
that pin rather than keeping a second copy of it.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Dict, Set

import pytest

from agent_audit.cli.commands.scan import run_scan

from tests.test_rule_producers import SCAN_UNREACHABLE_BY_DESIGN, advertised_rules

REPO_ROOT = Path(__file__).resolve().parent.parent
GRADED_CORPUS = REPO_ROOT / "tests" / "fixtures"
RULE_TRIGGERS = REPO_ROOT / "tests" / "rule_fixtures"

# The twelve this module was written for. Named so that a failure says which of them
# regressed rather than only that the count changed. Not an allow-list: every one of
# them is required to fire, and a rule outside this set is required to fire too.
TRIGGER_ONLY_RULES = (
    "AGENT-002", "AGENT-027", "AGENT-037", "AGENT-038", "AGENT-039", "AGENT-040",
    "AGENT-042", "AGENT-048", "AGENT-052", "AGENT-055", "AGENT-056", "AGENT-057",
    "AGENT-083", "AGENT-084", "AGENT-085",
)

# The sixteenth rule, and it is a different defect from the other fifteen. AGENT-049
# has a working detector: `python_scanner._check_unsafe_deserialization` emits an
# `unsafe_deserialization` pattern on `pickle.load` at confidence 0.85, and
# `PATTERN_TYPE_TO_RULE_MAP` maps it to AGENT-049. The finding is then thrown away,
# because `_create_finding_from_pattern` looks the rule up in the YAML-loaded rule
# table and AGENT-049 is not one of the 52 rules with a YAML definition. So the rule
# is advertised, detected, and silently discarded — including on
# `tests/fixtures/asi-06-memory-poisoning/direct/pickle_memory.py:14`, which the
# corpus does label, just under AGENT-018.
#
# It is not fixed here. Supplying the missing YAML metadata would make the rule fire
# and add an unlabelled finding to the graded corpus, which is a rule-set and corpus
# decision rather than a fixture one. DECISIONS.md item 36.
#
# The trigger fixture at tests/rule_fixtures/agent-049/ is kept: it is the input this
# rule needs the moment the decision is taken. The pin below is self-invalidating —
# it asserts the mechanism is still exactly as described, so fixing the rule fails
# the test and forces the pin to be removed.
DETECTED_BUT_DISCARDED = {
    "AGENT-049": "detector emits `unsafe_deserialization`; no YAML definition, so the "
                 "engine's rule lookup returns None and the finding is dropped",
}


def _scan(path: Path) -> Dict[str, Set[str]]:
    """rule_id -> set of relative paths that produced it."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "findings.json"
        run_scan(
            path=path,
            output_format="json",
            output_path=out,
            min_severity="info",
            additional_rules=[],
            fail_on_severity="none",
            quiet=True,
        )
        if not out.exists():
            return {}
        data = json.loads(out.read_text(encoding="utf-8"))

    produced: Dict[str, Set[str]] = {}
    for finding in data.get("findings", []):
        rule_id = finding.get("rule_id")
        if not rule_id:
            continue
        location = finding.get("location", {}) or {}
        produced.setdefault(rule_id, set()).add(str(location.get("file_path", "?")))
    return produced


@pytest.fixture(scope="module")
def graded_corpus_rules() -> Dict[str, Set[str]]:
    return _scan(GRADED_CORPUS)


@pytest.fixture(scope="module")
def trigger_rules() -> Dict[str, Set[str]]:
    return _scan(RULE_TRIGGERS)


def test_every_advertised_rule_is_produced_by_some_input_in_the_repository(
    graded_corpus_rules, trigger_rules
) -> None:
    """The guard. A published rule that nothing in the repo can trigger fails here.

    Deliberately no allow-list. Either an input exists that reaches the rule, or the
    rule comes out of `RULE_CWE_MAPPING` and `docs/RULES.md` — the same contract
    `test_no_advertised_rule_is_without_a_producer` applies one level up.
    """
    covered = (
        set(graded_corpus_rules)
        | set(trigger_rules)
        | set(SCAN_UNREACHABLE_BY_DESIGN)
        | set(DETECTED_BUT_DISCARDED)
    )
    uncovered = sorted(advertised_rules() - covered)

    assert not uncovered, (
        f"{len(uncovered)} advertised rule(s) are produced by no input anywhere in "
        f"this repository: {uncovered}\n"
        "A rule nothing triggers is invisible to every quality gate — it cannot "
        "regress, because nothing measures it. Add the smallest input that satisfies "
        "the rule's own producer condition under tests/rule_fixtures/<rule-id>/ "
        "(see that directory's README for why not tests/fixtures/), or withdraw the "
        "rule and record the gap."
    )


@pytest.mark.parametrize("rule_id", TRIGGER_ONLY_RULES)
def test_each_trigger_fixture_still_fires(rule_id: str, trigger_rules) -> None:
    """Per-rule, so a regression names the rule instead of shrinking a set."""
    assert rule_id in trigger_rules, (
        f"{rule_id} no longer fires on tests/rule_fixtures/{rule_id.lower()}/. Either "
        "the rule regressed or its producer condition changed and the trigger needs "
        "rebuilding from the new condition."
    )


@pytest.mark.parametrize("rule_id", TRIGGER_ONLY_RULES)
def test_each_trigger_fixture_fires_from_its_own_directory(rule_id: str) -> None:
    """A trigger must work in isolation, not only as part of a whole-tree scan.

    Without this, a directory could be credited for a finding that another
    directory's file actually produced — which is real: cross-server tool shadowing
    (AGENT-055) is computed across every config in the scanned tree, so in a
    whole-tree scan it is reported against whichever config the analysis reaches
    first.
    """
    directory = RULE_TRIGGERS / rule_id.lower()
    assert directory.is_dir(), f"no trigger directory at {directory}"
    assert rule_id in _scan(directory), (
        f"{rule_id} does not fire when {directory.name}/ is scanned on its own"
    )


@pytest.mark.parametrize("rule_id", sorted(DETECTED_BUT_DISCARDED))
def test_discarded_rules_are_still_discarded_for_the_stated_reason(rule_id: str) -> None:
    """Self-invalidating pin: assert the mechanism, not the outcome.

    Three things must all still hold, or the entry is stale and must be removed:
      1. a trigger fixture exists for the rule;
      2. that fixture does NOT produce the rule on a real scan;
      3. the reason is the one recorded — the rule has no YAML definition, so the
         engine's rule-table lookup fails and the finding is dropped.

    Checking (3) is what stops this becoming an allow-list. If someone adds the YAML
    and the rule starts firing, (2) fails; if someone adds the YAML and it still does
    not fire, (3) fails and the real cause has to be found.
    """
    directory = RULE_TRIGGERS / rule_id.lower()
    assert directory.is_dir(), (
        f"{rule_id} is pinned as detected-but-discarded with no trigger fixture at "
        f"{directory}. The fixture is what proves the claim."
    )

    assert rule_id not in _scan(directory), (
        f"{rule_id} now fires on its trigger fixture. Remove it from "
        "DETECTED_BUT_DISCARDED, add it to TRIGGER_ONLY_RULES, and record what "
        "wired it up."
    )

    builtin = REPO_ROOT / "packages" / "audit" / "agent_audit" / "rules" / "builtin"
    defined_in_yaml = any(
        re.search(rf'^\s*-\s+id:\s*["\']?{rule_id}\b', path.read_text(encoding="utf-8"), re.M)
        for path in builtin.glob("*.yaml")
    )
    assert not defined_in_yaml, (
        f"{rule_id} now has a YAML definition but still does not fire — the recorded "
        "reason (missing rule-table entry) is no longer the cause. Find the real one."
    )


def test_trigger_fixtures_are_not_graded_by_layer_1() -> None:
    """The trees must stay disjoint, or an unlabelled trigger becomes a false positive.

    Layer 1 scans `tests/fixtures` and grades every finding against
    `tests/ground_truth/labeled_samples.yaml`. A trigger fixture has no label by
    design, so if this tree ever moved inside the graded corpus every file in it
    would depress published precision for rules working exactly as intended. That is
    precisely what happened to `vulnerable_hooks` and AGENT-120.
    """
    assert RULE_TRIGGERS.is_dir()
    assert GRADED_CORPUS.is_dir()
    assert GRADED_CORPUS not in RULE_TRIGGERS.parents, (
        "tests/rule_fixtures/ has moved inside the graded corpus; every trigger in it "
        "now counts as an unlabelled false positive against published precision"
    )
    assert RULE_TRIGGERS not in GRADED_CORPUS.parents


def test_no_trigger_fixture_is_referenced_by_ground_truth() -> None:
    """A label pointing into this tree would move it into the benchmark by stealth."""
    ground_truth = (
        REPO_ROOT / "tests" / "ground_truth" / "labeled_samples.yaml"
    ).read_text(encoding="utf-8")
    assert "rule_fixtures" not in ground_truth, (
        "tests/ground_truth/labeled_samples.yaml references tests/rule_fixtures/. "
        "Trigger fixtures are not graded inputs; a label pointing at one puts it in "
        "the benchmark corpus without moving the file."
    )
