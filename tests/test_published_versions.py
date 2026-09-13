"""Regression guard: a version a published surface names must be a release that exists.

History. On 2026-09-12 (RUN 11) eight in-repo surfaces told the reader that six advertised
rules were **"withdrawn in v0.19.3"**. There is no 0.19.3. It was never uploaded to PyPI,
never tagged, and has no CHANGELOG section. A user on 0.19.2 reading that sentence was being
told the withdrawal had already shipped in a release they could have installed; it ships in
0.20.0. Five of those references were on surfaces a *user* reads — `docs/RULES.md` twice,
`CAPABILITY_BOUNDARIES.md`, and the correction note at the head of both blog posts.

That is `test_published_rule_count.py` again with a different fact. One thing is true — which
releases exist — several documents assert it, and nothing related the assertions to the
thing. So the same shape of check: find the fact, find the copies, relate them.

**The fact, and why it is these three records.** A release exists if you can get it:

  * a **git tag**, read from the repository, for anything installable from GitHub;
  * the **PyPI release history**, which is the only record for three published versions that
    were never tagged (0.17.1, 0.18.0, 0.18.1) — a network call cannot be part of a unit
    test, so the list is written down in `PYPI_PUBLISHED` below *with the command that
    produces it*, the same rule this project applies to every other copied fact;
  * the version this tree is about to release, from `packages/audit/agent_audit/version.py`.
    Without it, every correct reference to the release being prepared would fail.

`CHANGELOG.md` is deliberately **not** one of them, and the reason is the defect itself: it
carries `## [0.19.1]`, `## [0.5.0]`, `## [0.4.1]`, `## [0.4.0]`, `## [0.3.2]` and
`## [0.3.1]` sections for versions that were never tagged and never published. If a document
counted as proof that a release happened, then writing the wrong sentence twice would make it
true, and adding a `## [0.19.3]` section would have turned this guard green while leaving the
claim as false as it was.

**Scope, and the 190 references this guard deliberately does not read.** Only surfaces a user
of the tool reads. The package sources are excluded, measured rather than assumed: they carry
**190** references to 0.x versions with no tag and no PyPI release — `# v0.5.1: Reduced from
0.85`, `# v0.9.0: Mask/Redaction Detection`, and 188 more. Those are internal provenance
comments on development series, addressed to whoever next edits the line, and rewriting them
would destroy the only record of when a behaviour changed while telling no user anything. The
one exception corrected by hand in RUN 12 — `rules/engine.py:22`, the withdrawal block, which
is where `docs/RULES.md` gets its story from — is therefore *not* protected by this guard, and
that is a known gap rather than an oversight. Reproduce the 190:

    python3 -c "import re,subprocess,pathlib; ..."   # see NIGHT_RUN_LEDGER.md § W58

**Two ways a reference is allowed to name something unreleased**, because forbidding it
outright would make honest sentences unwriteable:

  * an explicit marker beside it (`_UNRELEASED_MARKERS`) — "0.3.0 development series (never
    released)" is a true statement and must stay sayable. This is `_SUPERSESSION_MARKERS` in
    `test_published_metrics.py`, the same idea: a claim earns its exemption by telling the
    reader, not by appearing on a list in a test file.
  * a document that declares itself historical in its first lines
    (`_HISTORICAL_BANNERS`) — `docs/BENCHMARK-RESULTS.md` compares against a "v0.4.1
    Baseline" under a banner reading **HISTORICAL DOCUMENT — DO NOT CITE AS CURRENT**.
    Rewriting that column would falsify a record of a comparison that really was run against
    that build. `test_a_banner_exempted_document_still_carries_its_banner` is what keeps this
    from becoming a silent per-file allow-list: delete the banner and the file re-enters the
    guard.

**Known limitation, written down rather than papered over.** A version pinned with an
operator is not read as a release claim — `tree-sitter = "^0.22.0"` is a dependency, not a
version of this project — so `pip install agent-audit==0.19.3` would pass. `agent-audit==`
is therefore matched separately, with no operator exclusion. And a two-component reference
("shipped in v0.19") is invisible to the pattern: this guard reads `0.X.Y`, and
`test_the_pattern_reads_the_version_this_tree_declares` is what will say so out loud on the
day the project releases 1.0.0.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_PY = REPO_ROOT / "packages" / "audit" / "agent_audit" / "version.py"

# The PyPI release history, 2026-09-13. Three of these have no git tag, which is why the
# list cannot be derived from the repository alone. Reproduce:
#
#   curl -sS https://pypi.org/pypi/agent-audit/json \
#     | python3 -c "import json,sys; d=json.load(sys.stdin); print(', '.join(sorted(
#         d['releases'], key=lambda v:[int(x) for x in v.split('.')])))"
#
# A version published after this list was written and then referenced in a document would
# fail here. That is the right failure: it asks whoever added the reference to refresh the
# record beside it, which is how the list stays honest.
PYPI_PUBLISHED = frozenset({
    "0.1.0", "0.2.0", "0.5.2", "0.7.0", "0.8.0", "0.12.0", "0.15.1", "0.16.0",
    "0.17.0", "0.17.1", "0.18.0", "0.18.1", "0.18.2", "0.19.2",
})

# Surfaces a user of the tool reads. Same scope rule as test_published_rule_count.py, with
# one deliberate addition: the two blog posts. That guard excludes them as records, correctly
# — "72 rules" in a dated post was true when written. But the *correction note* at the head of
# each post is not a record, it is a live statement about the release a reader is about to
# install, and it is where two of the five user-facing v0.19.3 claims were.
GUARDED_SURFACES = (
    "README.md",
    "README_CN.md",
    "CLAUDE.md",
    "CAPABILITY_BOUNDARIES.md",
    "RELEASE_NOTES_v0.20.0.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "action.yml",
    "docs/RULES.md",
    "docs/index.html",
    "docs/ARCHITECTURE.md",
    "docs/README.md",
    "docs/ROADMAP.md",
    "docs/F1_REPRODUCTION.md",
    "docs/COMPETITIVE-COMPARISON.md",
    "docs/BENCHMARK-RESULTS.md",
    "docs/blog/launch-post.md",
    "docs/blog/hackernews-post.md",
    "packages/audit/README.md",
    "packages/audit/pyproject.toml",
)

# Surfaces that must yield at least one readable version reference. If one stops matching,
# this guard has gone inert over it and the suite says so rather than going quiet — the
# vacuity trap that let RUN 11's defect survive a scanner built to catch it.
MUST_NAME_A_VERSION = (
    "README.md",
    "README_CN.md",
    "CLAUDE.md",
    "RELEASE_NOTES_v0.20.0.md",
    "docs/RULES.md",
    "docs/index.html",
    "packages/audit/pyproject.toml",
)

# A 0.x version of *this* project, not a dependency pin. The lookbehind drops `^0.21.0`,
# `>=0.40`, `<0.23.0` and `,0.24.0`; the lookahead drops the third dot of an IP address.
# `v` is optional because half the references are written without it.
_VERSION = re.compile(r"(?<![\w.^~=<>,])v?(0\.\d{1,2}\.\d{1,2})(?!\.?\d)")

# Checked with no operator exclusion: this one *is* a release claim, and a wrong one sends
# the reader to an index that will refuse them.
_PIP_PIN = re.compile(r"agent[-_]audit\s*==\s*v?(\d+\.\d+\.\d+)")

# A reference that says out loud that the thing it names was never a release.
_UNRELEASED_MARKERS = (
    "never released",
    "never published",
    "not released",
    "unreleased",
    "no such release",
    "development series",
    "dev series",
    "planned",
    "pending version bump",
)

# A document that tells the reader, in its first lines, that it is a record. Checked by
# test_a_banner_exempted_document_still_carries_its_banner, so removing the banner re-arms
# the guard rather than silently keeping the exemption.
_HISTORICAL_BANNERS = (
    "historical document",
    "do not cite as current",
)
_BANNER_LINES = 10

# How far above a line to look for a marker. Three lines covers a table caption or the
# sentence introducing a list; further away and the marker is not about this reference.
_MARKER_CONTEXT = 3

BANNER_EXEMPT = ("docs/BENCHMARK-RESULTS.md",)


def _git_tag_versions():
    """Versions that exist as a git tag.

    Returns an empty set rather than raising when git is unavailable or this is not a
    checkout: a guard that errors outside a working repository gets deleted from CI. The
    cost is that the tag half goes quiet there, which is why PYPI_PUBLISHED is a literal.
    """
    try:
        completed = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short)", "refs/tags"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if completed.returncode != 0:
        return set()
    return {
        tag.lstrip("v")
        for tag in completed.stdout.split()
        if re.fullmatch(r"v?\d+\.\d+\.\d+", tag)
    }


def declared_version():
    """The version this tree is about to release."""
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', VERSION_PY.read_text(encoding="utf-8"))
    assert match, f"no __version__ in {VERSION_PY}"
    return match.group(1)


def real_releases():
    """Every version that exists as a release, by any of the three records."""
    return (PYPI_PUBLISHED | _git_tag_versions()) | {declared_version()}


def _has_banner(text):
    head = "\n".join(text.splitlines()[:_BANNER_LINES]).lower()
    return any(banner in head for banner in _HISTORICAL_BANNERS)


def _claims():
    """Every version a guarded surface presents as a release.

    Yields (surface, line number, version, line text).
    """
    for rel in GUARDED_SURFACES:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if _has_banner(text):
            continue
        lines = text.splitlines()
        for index, line in enumerate(lines):
            context = "\n".join(lines[max(0, index - _MARKER_CONTEXT) : index + 1]).lower()
            if any(marker in context for marker in _UNRELEASED_MARKERS):
                continue
            for match in _VERSION.finditer(line):
                yield rel, index + 1, match.group(1), line.strip()
        # The pip pin is checked whatever the markers say: "install 0.19.3, which was never
        # released" is not an honest sentence, it is a broken command.
        for index, line in enumerate(lines):
            for match in _PIP_PIN.finditer(line):
                yield rel, index + 1, match.group(1), line.strip()


def test_the_release_set_is_not_empty():
    """A vacuous guard is worse than none — see the differential of RUN7."""
    releases = real_releases()
    assert len(releases) >= len(PYPI_PUBLISHED)
    assert declared_version() in releases


def test_the_pattern_reads_the_version_this_tree_declares():
    """The trap this catches: `0\\.` stops matching on the day 1.0.0 is released.

    At that point every reference to 1.0.0 becomes invisible to the guard and the suite
    stays green while the check does nothing. This test fails instead, which is the alarm.
    """
    version = declared_version()
    assert _VERSION.search(f"v{version} "), (
        f"the version pattern does not read the declared version {version}. If the project "
        "has left 0.x, widen _VERSION to the new major and re-measure the dependency-pin "
        "exclusions — several pins in packages/audit/pyproject.toml are 1.x and 2.x."
    )


def test_every_published_version_reference_is_a_real_release():
    releases = real_releases()
    wrong = [
        (rel, lineno, version, text)
        for rel, lineno, version, text in _claims()
        if version not in releases
    ]
    assert not wrong, (
        f"{len(wrong)} published reference(s) name a version that was never released "
        "(no git tag, not on PyPI, and not the version this tree declares):\n\n"
        + "\n".join(
            f"  {rel}:{lineno}  says {version}\n      {text[:110]}"
            for rel, lineno, version, text in wrong
        )
        + "\n\nThe releases that exist:\n  "
        + ", ".join(sorted(releases, key=lambda v: [int(x) for x in v.split(".")]))
        + "\n\nIf the sentence is about a development series that was never cut, say so on "
        "the line — see _UNRELEASED_MARKERS — rather than leaving a reader to look for a "
        "release they cannot install."
    )


@pytest.mark.parametrize("rel", MUST_NAME_A_VERSION)
def test_the_version_bearing_surfaces_still_name_one(rel):
    """Otherwise the test above passes by finding nothing.

    Per surface, not "at least one somewhere": a reformat that took one page out of the
    guard would leave the suite green while that page drifted, which is exactly how
    `docs/index.html` came to publish a rule count of 49 while the README published 72.
    """
    if not (REPO_ROOT / rel).exists():
        pytest.skip(f"{rel} does not exist on this checkout")
    seen = [claim for claim in _claims() if claim[0] == rel]
    assert seen, (
        f"{rel} no longer names any 0.x version this guard can read.\n"
        "Either the version was removed from it, or the phrasing changed and the guard has "
        "gone inert over that page."
    )


@pytest.mark.parametrize("rel", BANNER_EXEMPT)
def test_a_banner_exempted_document_still_carries_its_banner(rel):
    """The exemption is the banner, not the filename.

    `docs/BENCHMARK-RESULTS.md` is out of the guard because it opens by telling the reader
    it is historical. If that banner is ever removed, the document starts reading as current
    and must be checked like any other — so this test fails and the exemption has to be
    removed with it.
    """
    path = REPO_ROOT / rel
    if not path.exists():
        pytest.skip(f"{rel} does not exist on this checkout")
    assert _has_banner(path.read_text(encoding="utf-8")), (
        f"{rel} is exempt from the version guard because it declares itself historical in "
        f"its first {_BANNER_LINES} lines, and it no longer does. Either restore the banner "
        "or remove the file from BANNER_EXEMPT and correct the version references in it."
    )


@pytest.mark.parametrize("phantom", ["0.3.0", "0.4.1", "0.5.0", "0.19.1", "0.19.3"])
def test_the_phantom_versions_are_gone(phantom):
    """Named individually so a regression says which one came back.

    0.19.3 is RUN 11's finding: the version eight surfaces said the withdrawal shipped in.
    The other four were found by checking the class rather than the instance (RUN 12) — each
    has a CHANGELOG section and no release anywhere.
    """
    assert phantom not in real_releases(), (
        f"{phantom} is now a real release, so remove it from this list — the parametrize "
        "case is asserting the opposite of the truth."
    )
    offenders = [
        f"  {rel}:{lineno}  {text[:110]}"
        for rel, lineno, version, text in _claims()
        if version == phantom
    ]
    assert not offenders, (
        f"the never-released version {phantom} is named on a user-facing surface:\n"
        + "\n".join(offenders)
    )


def test_dependency_pins_are_not_read_as_release_claims():
    """The exclusion that keeps this guard usable, pinned to the lines that motivated it.

    Without it, `packages/audit/pyproject.toml` alone reports six failures for pins on
    pytest-asyncio and three tree-sitter packages, and a guard that fires on correct lines
    is a guard somebody switches off.
    """
    for pin in (
        'pytest-asyncio = "^0.21.0"',
        'tree-sitter = {version = "^0.22.0", optional = true}',
        'tree-sitter-python = {version = "^0.23.0", optional = true}',
        "anthropic = {version = \">=0.40,<1.0\", optional = true}",
    ):
        assert not _VERSION.search(pin), f"a dependency pin was read as a release claim: {pin}"


def test_the_guard_can_actually_fail():
    """The cheapest test in the file, and the worst failure mode if absent.

    A silent regex is indistinguishable from a clean repository — the defect this module
    exists to catch, applied to this module. Feed it the sentence that was on five surfaces.
    """
    line = "six advertised rules were withdrawn in v0.19.3"
    found = [match.group(1) for match in _VERSION.finditer(line)]
    assert found == ["0.19.3"], f"the pattern did not read the sentence it was built for: {found}"
    assert "0.19.3" not in real_releases(), (
        "0.19.3 is being treated as a real release, which would make the whole module inert"
    )
    assert _PIP_PIN.search("pip install agent-audit==0.19.3"), (
        "the pip-pin pattern does not read a pinned install command"
    )
