"""Regression guard: one rule count, and every published surface must agree with it.

History. On 2026-08-11 this repository published **four different rule counts for one set
of rules** — 40, 49, 53 and 72 — across twenty locations, while the set contained 66. The
PyPI description said 53 and was the only rule count on a distribution surface. None of
the four was checked against anything, because nothing checked them.

That is the same defect as the duplicate Layer 1 thresholds (`test_layer1_gate_singleton`)
and the stale gate results (`test_gate_provenance`): one fact, several copies, no
mechanism relating the copies to the fact. Documents drift silently because a wrong
sentence and a right one look identical to every test in the suite.

This test relates them. `tests/test_rule_producers.advertised_rules()` is the fact — the
rules the tool can actually emit — and any number written next to the word "rules" on a
surface a user reads must equal it.

**Scope, and why it is drawn here.** Only surfaces a *user of the tool* reads: the two
READMEs, the docs site, the architecture and roadmap pages, and the packaging metadata.
Deliberately excluded, each for a stated reason:

  * `CHANGELOG.md` and the `docs/blog/` posts are **records**. "72 rules" in a v0.18 entry
    was true when written; rewriting history to make a test pass is the opposite of what
    this guard is for. The blog posts carry a dated correction note instead.
  * `NIGHT_RUN_LEDGER.md`, `DECISIONS.md`, `RUN*_REPORT.md`, `CLAIMS_RECONCILIATION.md`
    and `docs/decisions/` are working notes that *quote* wrong numbers in order to discuss
    them. A guard that forbade quoting the defect would make the defect harder to write
    down.

**The outreach drafts, added 2026-08-11 (RUN9).** `blog_post.md`, `twitter_thread.md` and
`chinese_summary.md` sat untracked in the working tree publishing a *fifth* count, 56, in
the two files most likely to go out next (`DECISIONS.md` item 44). They are guarded here,
but **only once git says they are tracked** — see `_guarded_surfaces()`.

The original objection to guarding them was sound: a test that failed on a draft in
someone's working tree is a test that gets switched off, and a switched-off guard is worse
than none. Tracking is what answers it. An untracked file is a private draft and the suite
says nothing about it; the moment it is `git add`ed it stops being someone's working tree
and becomes the repository, which is exactly the point at which "one release away from
being the sixth wrong surface" becomes "is the sixth wrong surface".
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_rule_producers import advertised_rules  # noqa: E402

# Surfaces a user of the tool reads. Adding a new one is a one-line change here.
PUBLISHED_SURFACES = (
    "README.md",
    "README_CN.md",
    "docs/index.html",
    "docs/ARCHITECTURE.md",
    "docs/README.md",
    "docs/ROADMAP.md",
    "docs/RULES.md",
    "packages/audit/pyproject.toml",
)

# Outreach drafts. Guarded only once tracked — see the module docstring and
# `_guarded_surfaces()`. Listed here while untracked so that adding one to the index is
# all it takes; nobody has to remember to come back and edit this file.
DRAFT_SURFACES = (
    "blog_post.md",
    "twitter_thread.md",
    "chinese_summary.md",
)

# "66 rules", "66 detection rules", "66 Rules x OWASP", "66 条规则", "66 条检测规则".
# The `\+?` matters: "40+ rules" is how three of the four wrong numbers were written, and
# a vague count that happens to be satisfied by the truth is still a count nobody checked.
COUNT_NEAR_RULES = re.compile(
    r"(?<![\d.])(\d{1,4})\s*\+?\s*(?:detection\s+|Detection\s+)?(?:rules|Rules|条检测规则|条规则)",
)

# A count is only checked when its line also claims to describe the *whole* set. Without
# this, `docs/index.html` alone yields nine per-category counts ("4 rules · prompt
# injection via f-string") that are correct and are not the total.
#
# The cost of the approach is that a count phrased in none of these ways goes unguarded —
# `docs/ARCHITECTURE.md:134` is a bare `(66 rules)` inside an ASCII diagram, and this
# guard does not see it. `test_every_published_surface_states_the_count` limits the
# damage: if a surface stops matching entirely, the suite fails rather than going quiet.
TOTALITY_MARKERS = (
    "mapped to", "映射到",
    "covering all", "覆盖",
    "coverage",
    "rule reference", "rules x owasp",
    "complete list",
    "dedup",
    "total",
    "asi categories",
    "as of v",
)


def _tracked_drafts():
    """The draft surfaces git currently has in the index.

    Returns () rather than raising if git is unavailable or this is not a checkout: a
    guard that errors outside a working repository would be removed from CI, and an
    untracked draft is out of scope by design anyway.
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


def _published_counts():
    """Every whole-set rule count on a guarded surface.

    Yields (surface, line number, number, line text).
    """
    for rel in _guarded_surfaces():
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            lowered = line.lower()
            if not any(marker in lowered for marker in TOTALITY_MARKERS):
                continue
            for match in COUNT_NEAR_RULES.finditer(line):
                yield rel, lineno, int(match.group(1)), line.strip()


def test_the_rule_set_is_not_empty():
    """A vacuous guard is worse than none — see the differential of RUN7."""
    assert len(advertised_rules()) > 0


def test_every_published_rule_count_equals_the_rule_set():
    actual = len(advertised_rules())
    wrong = [
        (rel, lineno, found, text)
        for rel, lineno, found, text in _published_counts()
        if found != actual
    ]
    assert not wrong, (
        f"{len(wrong)} published rule count(s) disagree with the {actual} rules the tool "
        "can actually emit.\n\n"
        + "\n".join(f"  {rel}:{lineno}  says {found}\n      {text[:110]}" for rel, lineno, found, text in wrong)
        + "\n\nThe count is checkable:\n"
        "  python3 -c \"import sys;sys.path.insert(0,'tests');"
        "from test_rule_producers import advertised_rules;print(len(advertised_rules()))\""
    )


def test_every_published_surface_states_the_count():
    """Otherwise the test above passes by finding nothing, which is the vacuity trap.

    Per surface, not merely "at least one somewhere": a phrasing change on one page would
    otherwise take that page out of the guard while the suite stayed green — which is
    precisely how `docs/index.html` came to publish 49 while the README published 72.
    """
    seen = {rel for rel, _, _, _ in _published_counts()}
    missing = [rel for rel in PUBLISHED_SURFACES if (REPO_ROOT / rel).exists() and rel not in seen]
    assert not missing, (
        "no whole-set rule count was found on these published surfaces:\n  "
        + "\n  ".join(missing)
        + "\n\nEither the count was removed from them, or the phrasing changed and "
        "TOTALITY_MARKERS no longer matches — in which case this guard has gone inert "
        "for those files and is now the thing that needs fixing."
    )


def test_tracked_outreach_drafts_are_guarded():
    """Coverage of the drafts is conditional, so say out loud which condition holds.

    This test never fails on an untracked draft. It exists so that `-v` output records
    whether the drafts are inside the guard on this checkout, rather than leaving that to
    be inferred from the absence of a failure — an inert guard and a satisfied one are
    otherwise indistinguishable, which is the defect this whole file is about.
    """
    tracked = _tracked_drafts()
    if not tracked:
        pytest.skip(
            "no outreach draft is tracked; they are private working-tree files and the "
            "guard is correctly silent. See DECISIONS.md item 45."
        )
    actual = len(advertised_rules())
    wrong = [
        (rel, lineno, found, text)
        for rel, lineno, found, text in _published_counts()
        if rel in tracked and found != actual
    ]
    assert not wrong, (
        "a tracked outreach draft publishes a rule count that is not the "
        f"{actual} rules the tool can emit:\n"
        + "\n".join(f"  {rel}:{lineno}  says {found}\n      {text[:110]}" for rel, lineno, found, text in wrong)
    )


@pytest.mark.parametrize("stale", [40, 49, 53, 56, 72])
def test_the_historical_counts_are_gone(stale):
    """Named individually so a regression says which one came back.

    56 joined the list in RUN9: it was never on a tracked surface, only in the three
    outreach drafts, which is why nothing caught it for as long as it sat there.
    """
    actual = len(advertised_rules())
    if stale == actual:
        pytest.skip(f"{stale} is the current count")
    offenders = [
        f"{rel}:{lineno}  {text[:110]}"
        for rel, lineno, found, text in _published_counts()
        if found == stale
    ]
    assert not offenders, (
        f"the published count {stale} is back on a user-facing surface:\n"
        + "\n".join(offenders)
    )
