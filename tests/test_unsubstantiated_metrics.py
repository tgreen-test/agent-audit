"""Regression guard: no metric on a user-facing surface without data behind it.

History. `README.md:147` published "validated against 18,899 ClawHub skills at 80%
precision" from v0.16.0 until 2026-09-10. Both halves of that clause were unsupported:

  * **The 18,899-skill scan is not in this repository.** No committed artifact records it,
    and nothing in the tree can reproduce it. `OUTREACH_CLAIMS.md` § 3 documents the whole
    family of figures that trace to it — 13,355 findings, 1,492 BLOCK, 18,294 rule triggers.
  * **The 80% was never a property of 18,899 skills.** It came from a 20-sample manual draw
    (16/20 true positives, 95% Wilson CI 58.4%–91.9%). The sentence attached a small-sample
    point estimate to a large-sample denominator, which is the one arrangement that makes a
    wide interval look like a precise measurement.

It was the last metric on any user-facing surface with no reproducing command — the single
exception to the standard the v0.20.0 release set. RUN10 cut the clause rather than hedging
it, per the run's decision policy: *a number that cannot be reproduced gets cut or dated,
never hedged.*

This guard is the mechanism that stops it coming back. It is the third of its shape, after
`test_published_rule_count` (one rule count) and `test_layer1_gate_singleton` (one
threshold): **one fact, several copies, and something that relates the copies to the fact.**

**Scope, and why it is drawn here.** Only surfaces a *user of the tool* reads. Deliberately
excluded, each for a stated reason:

  * `CHANGELOG.md`, `docs/blog/` and `docs/F1_REPRODUCTION.md` are **records**. Their job is
    to quote the withdrawn figures in order to withdraw them. A guard that forbade quoting a
    defect would make the defect harder to write down.
  * `NIGHT_RUN_LEDGER.md`, `DECISIONS.md`, `RUN*_REPORT.md`, `OUTREACH_CLAIMS.md`,
    `CLAIMS_RECONCILIATION.md`, `EXTERNAL_CLAIMS_CHECKLIST.md` and `docs/decisions/` are
    working notes that discuss these numbers by name.

**What this guard deliberately does NOT cover, so nobody assumes it does.**

`100% recall` is absent from the pattern list even though it is one of the four retracted
Layer 1 figures. `docs/COMPETITIVE-COMPARISON.md` legitimately reports **100.0% recall on
Agent-Vuln-Bench Sets A and B** — that figure is measured against an explicit oracle, was
re-measured at v0.20.0, and is true. A pattern matching "100% recall" would fire three times
on correct statements in a guarded file, and a guard that fails on true text is a guard that
gets switched off. Distinguishing "Layer 1 recall is 100%" (retracted) from "Set B recall is
100%" (true) needs the surrounding claim, not a regex. `scripts/scan_external_claims.sh`
carries the loose pattern instead, where a false hit costs one glance rather than a red
suite.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tests"))

# Surfaces a user of the tool reads. Kept deliberately in step with
# `test_published_rule_count.PUBLISHED_SURFACES`, plus the competitive comparison — which is
# where the v0.20.0 sweep found its last stale figure, and is the single worst place in the
# repository for one to sit.
PUBLISHED_SURFACES = (
    "README.md",
    "README_CN.md",
    "docs/index.html",
    "docs/ARCHITECTURE.md",
    "docs/README.md",
    "docs/ROADMAP.md",
    "docs/RULES.md",
    "docs/COMPETITIVE-COMPARISON.md",
    "packages/audit/pyproject.toml",
)

# Outreach drafts. Guarded only once git says they are tracked — same rule, and same
# reasoning, as `test_published_rule_count._tracked_drafts()`: a test that fails on a private
# draft in someone's working tree is a test that gets switched off.
DRAFT_SURFACES = (
    "blog_post.md",
    "twitter_thread.md",
    "chinese_summary.md",
)

# Each entry: (label, compiled pattern, why it may not appear on a user-facing surface).
#
# Two classes, and the distinction decides the remedy rather than being cosmetic:
#   UNSUB    nothing in the repository reproduces it. Commit the data or cut the claim.
#   RETRACT  never a measurement at all. Withdraw with the mechanism stated; there is no
#            corrected value to substitute, because no run produces one.
FORBIDDEN = (
    (
        "clawhub-corpus",
        re.compile(r"18[,.]?899"),
        "UNSUB: the 18,899-skill ClawHub scan is not committed anywhere in this tree. "
        "OUTREACH_CLAIMS.md section 3 has the restore conditions.",
    ),
    (
        "clawhub-findings",
        re.compile(r"13[,.]?355"),
        "UNSUB: total findings from the same uncommitted ClawHub scan.",
    ),
    (
        "clawhub-triggers",
        re.compile(r"18[,.]?294"),
        "UNSUB: rule triggers from the same uncommitted ClawHub scan. AGENT-034 alone "
        "accounted for 3,129 of them and its behaviour changed in v0.20.0, so a re-run "
        "would not return this number.",
    ),
    (
        "clawhub-block",
        re.compile(r"1[,.]?492\b[^.\n]{0,24}(?:BLOCK|critical)", re.IGNORECASE),
        "UNSUB: BLOCK-tier count from the same uncommitted ClawHub scan.",
    ),
    (
        "precision-80",
        re.compile(r"80\s*%[^.\n]{0,40}precision|precision[^.\n]{0,40}\b80\s*%", re.IGNORECASE),
        "UNSUB: the 80% is a 20-sample draw (16/20, 95% Wilson CI 58.4%-91.9%) with no "
        "committed sample data, methodology or classification rationale.",
    ),
    (
        "precision-98.51",
        re.compile(r"98[.,]51|0[.,]9851"),
        "RETRACT: never measured. False negatives were assumed to be zero rather than "
        "counted. docs/decisions/METRICS_RETRACTION.md section 4.",
    ),
    (
        "f1-99.25",
        re.compile(r"99[.,]2[45]|0[.,]992[45]"),
        "RETRACT: derived from the 98.51% and the same FN=0 assumption.",
    ),
    (
        "fpr-1.49",
        re.compile(r"1[.,]49\s*%"),
        "RETRACT: the complement of the 98.51%. Measured FP rate is 31.14%.",
    ),
)


def _tracked_drafts():
    """The draft surfaces git currently has in the index.

    Returns () rather than raising if git is unavailable or this is not a checkout: a guard
    that errored outside a working repository would be removed from CI, and an untracked
    draft is out of scope by design anyway.
    """
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--", *DRAFT_SURFACES],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode != 0:
        return ()
    return tuple(rel for rel in completed.stdout.split("\0") if rel)


def _guarded_surfaces():
    return PUBLISHED_SURFACES + _tracked_drafts()


def _violations():
    """Every forbidden figure on a guarded surface.

    Yields (surface, line number, label, line text, reason).
    """
    for rel in _guarded_surfaces():
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern, reason in FORBIDDEN:
                if pattern.search(line):
                    yield rel, lineno, label, line.strip(), reason


def test_no_unsubstantiated_metric_on_a_published_surface():
    """No user-facing surface states a figure the repository cannot produce."""
    found = list(_violations())
    if found:
        report = "\n".join(
            f"  {rel}:{lineno} [{label}]\n"
            f"      {line[:160]}\n"
            f"      -> {reason}"
            for rel, lineno, label, line, reason in found
        )
        pytest.fail(
            f"{len(found)} unsubstantiated or retracted figure(s) on user-facing "
            f"surfaces:\n{report}\n\n"
            "Either commit the data that reproduces the number, or cut the claim. "
            "Do not hedge it -- see docs/decisions/METRICS_RETRACTION.md."
        )


def test_readme_states_no_clawhub_validation_metric():
    """The specific clause this guard was written for, pinned by name.

    `test_no_unsubstantiated_metric_on_a_published_surface` would catch a reintroduction
    anywhere. This one names the original defect so a reader of a future failure sees the
    history without going to git.
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
    assert "18,899" not in readme and "18899" not in readme, (
        "README.md has regained the ClawHub corpus figure. It published 'validated against "
        "18,899 ClawHub skills at 80% precision' until 2026-09-10; the scan data is not in "
        "this repository and v0.20.0's rule changes mean a re-run would not reproduce it."
    )


def test_guard_can_actually_fail():
    """The guard's own smoke test: the patterns match the text they were written for.

    Without this, a typo in a pattern turns the guard green and silent -- which is the exact
    failure mode the v0.20.0 release spent nine runs finding elsewhere. Checking that a
    mechanism still fires is cheaper than discovering it stopped.
    """
    specimens = {
        "clawhub-corpus": "validated against 18,899 ClawHub skills",
        "clawhub-findings": "identified 13,355 security findings",
        "clawhub-triggers": "these 18,294 total rule triggers map to",
        "clawhub-block": "1,492 were BLOCK-tier critical vulnerabilities",
        "precision-80": "BLOCK-tier precision: 80%",
        "precision-98.51": "this system achieves 98.51% precision",
        "f1-99.25": "F1 | 99.25% |",
        "fpr-1.49": "FP Rate | 1.49% |",
    }
    by_label = {label: pattern for label, pattern, _ in FORBIDDEN}
    assert set(specimens) == set(by_label), (
        "every FORBIDDEN pattern needs a specimen here, and vice versa"
    )
    for label, specimen in specimens.items():
        assert by_label[label].search(specimen), (
            f"pattern {label!r} no longer matches the text it was written for: {specimen!r}"
        )


def test_true_avb_recall_is_not_flagged():
    """The guard must not fire on correct statements.

    `docs/COMPETITIVE-COMPARISON.md` reports 100.0% recall on Agent-Vuln-Bench Sets A and B.
    That is measured against an explicit oracle and is true. This test pins the decision
    recorded in the module docstring: a `100% recall` pattern is deliberately absent, because
    a guard that fails on true text gets switched off rather than fixed.
    """
    true_statements = (
        "| **A** | Injection & RCE (19 labels) | **100.0%** (19/19) | 57.9% (11/19) |",
        "agent-audit achieves 100% recall on Set B (MCP & Component)",
        "AVB knowns: R 100.0% / P 88.0% / F1 0.9362",
    )
    for statement in true_statements:
        for label, pattern, _ in FORBIDDEN:
            assert not pattern.search(statement), (
                f"pattern {label!r} fires on a true statement: {statement!r}. "
                "A guard that flags correct text will be disabled, not repaired."
            )
