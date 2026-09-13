# RUN 11 — the pre-release audit, and the release staged

**Branch `fix/py314-blocker`, from `a7854bd`. 2026-09-12.** Nothing pushed, merged, tagged or
published. W52 landed as `7ddf826`, `0e5dfcf`, `a7854bd`; W53–W55 are in the working tree.

---

## 1. Should v0.20.0 ship?

**Yes — the tree is verified, the artifacts in `dist/` are the ones that were audited, and
nothing found in this run is a defect in the tool.** Two things stand in front of it: `twine`
is not installed, which is mechanical, and **the push publishes 7 commits of unreleased
SkillScanner and PDF-report work that no release note mentions**, whose merge commit calls
itself WIP — that code is already inside the branch and inside the wheel, so the question is
not whether 0.20.0 includes it but whether 0.20.0 ships it undocumented, and that one is
yours.

Five things that would have shipped wrong were found and fixed this run, and two of them were
on the page that announces the release: `CHANGELOG.md` told the reporter of issue #10 that
their fix had not happened, and it published a test count from three sessions ago.

---

## 2. The audit

### 2.1 The verification set, re-measured rather than trusted

| command | result |
|---|---|
| `python3 -m pytest tests/ packages/audit/tests/ -q` | **1 failed, 1905 passed, 4 skipped**. It was 1,904 for the four runs described in finding 6 — one of which gave 2 failed / 1903 — and 1,905 after finding 12 added one guard case |
| `precision_recall.py` | **TP 199 / FP 90 / FN 37**, P 68.86% / R 84.32% / **F1 75.81%**, FP rate 31.14% |
| `quality_gate_check.py --config tests/benchmark/gates.yaml` | **exit 0** — 0 failures, 0 warnings, 0 skipped, 4 below target (non-blocking) |
| AVB, `--tool agent-audit --dataset knowns` | **recall 100.0%, precision 88.0%, F1 0.9362**; Sets A / B / C all 100.0% |
| `bash .claude/hooks/test-guard.sh` | **passed=11 failed=0** |
| `advertised_rules()` | **66** |
| version files ×3 + both distribution surfaces | **0.20.0**, and both say **66 rules** |
| `dist/` artifacts | both sha256s match `RELEASE_CHECKLIST.md` § 5; **99 package files** in each, wheel and sdist identical; **0** forbidden path components |
| `pypi.org` / `test.pypi.org` | **0.20.0 absent from both**; latest published is 0.19.2 |
| `./run_eval.sh --commit HEAD` | **UNVERIFIED — the file does not exist.** Unchanged since RUN10; `DECISIONS.md` item 52 |

The signal-to-noise 2.2:1 figure is not restated. Its producer (`run_eval.sh`) and its corpus
both live outside this repository, so it cannot be reproduced here; the provenance and an
available cross-check are in `NIGHT_RUN_LEDGER.md` § W55 rather than a number repeated from
memory.

### 2.2 What would have embarrassed the project after release, ranked

**Fixed this run:**

1. **`CHANGELOG.md` contradicted its own fix, on the page that closes issue #10.** The
   *Known limitations* section said `AGENT-041` *"over-triggers on any `.execute()` receiver —
   agent invocation, task dispatch and `concurrent.futures.Executor` are all reported as SQL
   sinks"*, thirty lines below the *Fixed* bullet saying it no longer does. Measured on all
   three shapes it names: **0 findings**. The limitation predates `9b366fc` and is false;
   replaced with the one that is true (an unrecognised receiver still fires when the SQL is at
   the call site) and the real cost (an unknown-named cursor with upstream SQL is now silence).
2. **The same entry published `1796 passed / 1 failed / 3 skipped`** for a release containing
   **1,905 passed / 1 failed / 4 skipped**. Fifth consecutive session with a stale test count,
   first time in the release notes themselves.
3. **`RELEASE_CHECKLIST.md` § 4a told a reader to write `1,796 tests` onto a surface that
   was already current** — the same defect as `METRICS_RETRACTION.md` § 3a, found in § 2 of
   this same run: a table of replacement values that went stale while the surfaces it
   described were corrected. § 4a now says it is a record, not a work list.
4. **§ 6's commit count drifted inside its own correction, for the third time** (9 at
   `7ddf826`, 10 at `0e5dfcf`, 11 at `a7854bd`). Replaced with the range and the command.
5. **§ 7 said issue #10 stays open, four lines under a header saying it closes as fixed.**
   Re-measured at HEAD on the reporter's shapes — `target_agent.execute(task)` silent, both
   true positives still firing — and corrected, with a note that `ISSUE_REPLIES.md` supersedes
   both that table and `ISSUE_TRIAGE.md`.

**Found and left for you** (each is in § 4 with what it would take):

6. **A flaky test in the suite that gates the release.**
   `performance_test.py::TestThroughput::test_consistent_performance` asserts three wall-clock
   timings stay within 50% of their average, on a scan taking 0.06s. **1 of 4 whole-suite runs
   failed today; 10 of 10 isolated runs passed.** It will go red in CI on a busy runner for no
   reason connected to the code. Not touched — a tolerance is a threshold.
7. **The push publishes 7 commits that predate the branch**, `ab6f0ee`..`78e1337`: SkillScanner
   Phase 1–2A and the PDF report generator, 48 files, 8,899 insertions, merge titled
   *(WIP, pre-0.20.0)*.
8. **Those features ship undocumented.** `agent-audit report` is one of four commands in
   `--help` in the built wheel and appears in no README, no CHANGELOG entry and no docs page;
   `skill_scanner.py` likewise; and **`langdetect` is a new *required* runtime dependency**
   that 0.19.2 did not have, unmentioned anywhere. This is the mirror of the defect the release
   is about — code with no document. (The optional PDF dependency is handled: a missing
   `reportlab` gives *"Install with: pip install agent-audit[report]"* rather than a traceback,
   by code inspection; not executed here, because reportlab 4.4.10 is installed in this
   environment.)
9. **`"withdrawn in v0.19.3"` appears on eight surfaces** including `docs/RULES.md`,
   `CAPABILITY_BOUNDARIES.md` and both blog posts. **0.19.3 was never published** — PyPI's
   latest is 0.19.2, there is no tag and no CHANGELOG entry. A user on 0.19.2 is being told the
   withdrawal shipped in a release they could have had; it ships in 0.20.0.
10. **`CAPABILITY_BOUNDARIES.md` § 3 counts seven instances of the defect shape.** RUN8 named
    the quality gate the eighth and RUN10's scanner finding is the same shape again, but
    neither was added to the table — so the document the release notes point users to is two
    behind, and "nine" is a count no document supports.
11. **`twine` is not installed.** Stages 5 and 6 cannot run until it is.

**Two more, from doing the work:**

12. **The release notes were unguarded, and adding the guard moved the test count.**
    `RELEASE_NOTES_v0.20.0.md` prints the Layer 1 measurement under the command that produces
    it, on the page an upgrading user reads first, and neither
    `tests/test_published_metrics.py` nor `tests/test_published_rule_count.py` knew the file
    existed. Both now list it. The first attempt is the interesting part: adding it to
    `GUARDED_SURFACES` alone reported green while checking **nothing**, because the six lines
    above the fenced block contained the word *withdrawn* and `_SUPERSESSION_MARKERS`
    classified the live measurement as historical. Only the `MUST_PRINT_A_BLOCK` vacuity
    entry caught that — the same shape as W52's finding, a guard pointed at a document and
    reading none of it. Keeping that entry costs one parametrized case, which moved the suite
    **1,904 → 1,905** and, with it, fifteen surfaces. All fifteen are updated in this change
    rather than in the next one, and `1,904` is now in the claims scanner's stale-count
    pattern. **This is the sixth consecutive session in which the count moved inside the work
    on the count**, and the first in which it moved because a guard was extended to a
    genuinely unguarded surface.
13. **A recursive `grep` over this repository silently skips `CLAUDE.md`.** `.gitignore:22`
    lists it, the file is nonetheless tracked, and the interactive grep here honours
    `.gitignore`, so `grep -rn "1,904" .` returns no hit in a file that contains two — while
    `git grep` and `grep -n … CLAUDE.md` both find them. Every by-hand claim sweep in this
    project that used a recursive grep has been blind to one of the surfaces carrying the
    metrics and the rule count; W52 caught `CLAUDE.md` only because it looped over named
    files. `scripts/scan_external_claims.sh` is **not** affected — it reports three hits in
    `CLAUDE.md` — because a script gets the real binary rather than the shell's grep. Use
    `git grep`, or `grep -r --no-ignore`, for any future sweep.

---

## 3. `scripts/release_v0200.sh`

925 lines, executable, `--dry-run` supported. It follows `finalize_run7.sh`: preflight
everything before the first mutation, print a before/after for each step, have each step verify
its own result, abort on any mismatch. Every stage is gated by a `read -p` that states what is
about to happen and whether it can be undone.

| # | stage | before → after it prints | can it be undone? |
|---|---|---|---|
| 1 | **preflight** | the whole verification set, the artifacts by hash and content, the remote state, and both package indexes | **nothing to undo — it only reads** |
| 2 | **merge** `fix/py314-blocker` → `master`, `--no-ff` | `master` sha before and after; verifies two parents, branch contained, trees identical, tree clean | **yes, completely** — `git reset --hard <the sha it printed>`; nothing has left the machine |
| 3 | **push `master`** | remote sha before and after, and the list of commits it publishes | **no, not really** — a force-push moves the ref but cannot un-fetch |
| 4 | **tag `v0.20.0`, annotated, and push the tag** | local and remote tag before and after; verifies the object is a tag, points at `master`, and is on the remote | **partly** — deletable at both ends, but anyone who fetched keeps a v0.20.0 pointing here |
| 5 | **TestPyPI**: upload, then a clean venv installs `agent-audit==0.20.0` *from TestPyPI* and scans a fixture | HTTP 404 → 200; version; the scan summary; and that the project page carries "66 rules" | **no — and it does not matter.** Nothing installs from TestPyPI |
| 6 | **PyPI** | HTTP 404 → 200, then the same clean-venv install and scan | **NO. PyPI never allows re-uploading a version number — not after a delete, not after a yank. A wrong 0.20.0 can only be answered with 0.20.1** |

Stage 5 is before stage 6 because it is the only rehearsal available for the only step that
cannot be taken back: rejected metadata, a long description that renders as plain text, a
dependency that will not resolve, a missing entry point, a wheel that installs but cannot scan
— stage 6 gets one attempt at all of them, and stage 5 gets them wrong for free first. The
script says so in a comment above the stage and again in the stage-6 prompt.

Two things it does that the hand-written block in `RELEASE_CHECKLIST.md` § 6 did not: it pushes
`refs/tags/v0.20.0` rather than `--tags`, which would also have published
`skillscanner-core-frozen` — the one local tag not on the remote — and it rehearses before it
publishes.

**Run this run: `--dry-run` only.** Its preflight executed for real (a few minutes), passed
every check except `twine`, and printed the plan for stages 2–6 without running any of it. The
run is 258 lines on a clean tree and is abridged in `NIGHT_RUN_LEDGER.md` § W53. On its **first** run the preflight
caught the flaky test (finding 6) and aborted its own suite check — which is the behaviour the
whole design is for.

---

## 4. `NEEDS-HEADY`

1. **Install `twine`** — `python3 -m venv ~/.venvs/rel && ~/.venvs/rel/bin/pip install twine`.
   Mechanical, and the only hard blocker to stages 5–6.
2. **Decide whether 0.20.0 ships the WIP work, and whether it ships it silently** (findings 7
   and 8). It is in the branch and in the wheel, so excluding it means surgery, not a flag. The
   cheap answer is three lines in the CHANGELOG: `agent-audit report` exists and needs
   `[report]`; SkillScanner ships; `langdetect` is a new required dependency. Saying nothing is
   also a choice, but it is the one this release spent ten runs arguing against.
3. **The flaky wall-clock test** (finding 6). Options, in order of how much they lie: mark it
   `@pytest.mark.slow`/`skip` in CI, widen the tolerance, or delete it — it measures the
   machine, not the scanner. Whichever you take, it is a threshold change, so it is yours.
4. **`"withdrawn in v0.19.3"` on eight surfaces** (finding 9). Suggested text: *"withdrawn
   during 0.19.3 development; first released in 0.20.0"*. It is eight edits on published pages,
   two of them blog posts that already carry dated correction notes.
5. **`CAPABILITY_BOUNDARIES.md` § 3, seven instances or nine** (finding 10). Either add the
   gate and the claims scanner as rows 8 and 9, or state why an instrument is not counted
   beside a detector. `dbae329` exists because a previous run asserted an ordinal it had not
   counted; this run declined to repeat that.
6. **Carried, unchanged, and still outside this repository:** the slide deck and
   `docs/cais-2026/` still carry the retracted set (`RELEASE_CHECKLIST.md` rows B and C), and
   `openclaw-skill/` was never scanned. Nothing outside the repository was read this run.
7. **Posting the issue replies.** Five bodies in `ISSUE_REPLIES.md`, confirmed current: #10 and
   #12 close on posting, #8 and #11 stay open, #5 keeps `enhancement` / `needs-design`.

---

## 5. Statement

I did NOT push, merge, tag, publish, `git rm`, post to GitHub, or read outside the repository.

No oracle, dataset, ground-truth label, existing fixture, confidence value, tier boundary or
threshold was modified — including the flaky test's tolerance, for that reason. No detection
code was changed. Two guard denials this run, neither bypassed: a read-only command containing
`git merge-base` (the guard matches `merge` as a prefix), and a heredoc whose prose named the
publishing commands; both were rewritten rather than worked around, which is also why
`scripts/release_v0200.sh` was written with the editor.

All network traffic was read-only: `git ls-remote` against the GitHub remote, and GETs against
the two package indexes — two per dry run, plus one by hand to list the published versions,
which is what makes "0.19.3 was never released" a measurement rather than an inference.
