# PROGRESS

**RUN 12 state: COMPLETE. W56–W59 all done. The preflight passes clean — 0 problems — and
nothing in this repository is waiting on a decision. The release is one command away.**

Nothing pushed, merged, tagged or published. No file outside this repository was read or
edited.

## The release: what you run

```bash
scripts/release_v0200.sh --dry-run    # preflight runs for real; expect "every check passed"
scripts/release_v0200.sh              # then stage by stage, each one asks
```

`twine` 7.0.0 is already installed in `~/.venvs/rel` and § 1.11 looks there, so no `PATH`
prefix is needed (`TWINE_BIN=/path/to/twine` overrides if you keep it elsewhere).

Six stages, each behind a confirmation that says whether it can be undone: preflight (read
only) → merge → push `master` → tag and push the tag → **TestPyPI, then install back out of
it** → PyPI. The rehearsal is deliberately before the permanent step, because PyPI never
allows re-uploading a version number and a wrong 0.20.0 could only be answered with 0.20.1.
`--dry-run` prints every command and runs only the preflight.

**Its preflight passes on everything.** Verified by running it: `RUN12_REPORT.md` § 2, full
output in `NIGHT_RUN_LEDGER.md` § W56–W59. `twine check` passes on both artifacts, which is the
only evidence available before stage 5 that PyPI will render the long description rather than
print it as plain text.

**The 7 pre-existing commits are decided and documented.** Local `master` is 7 commits ahead of
`origin/master`: SkillScanner Phase 1 and its three protocol/findings commits, the PDF report
generator, a `.gitignore` rail, and the merge. They ship **labelled preview** — named in
`CHANGELOG.md` and in `RELEASE_NOTES_v0.20.0.md`, with what to rely on them for and what not.
The preflight still lists them at stage 3 and still stops; the list is now expected rather than
a surprise. Three facts a reader of that prompt should have: `langdetect` is a new *required*
dependency, `agent-audit report` needs `pip install "agent-audit[report]"`, and `SKILL-010`
sends `SKILL.md` descriptions to the Claude API if `ANTHROPIC_API_KEY` is set in the
environment.

Then: the GitHub release from the tag with `RELEASE_NOTES_v0.20.0.md` as the body, and the
five bodies in `ISSUE_REPLIES.md` — #10 and #12 close on posting, #8 and #11 stay open, #5
keeps its labels.

## Start here

1. **`RUN12_REPORT.md` § 1** — what the three decisions turned into, and the one defect found
   by executing a path a previous run only read.
2. **`RUN12_REPORT.md` § 4** — `NEEDS-HEADY`: three new, none blocking.
3. **`RUN11_REPORT.md` § 4** — the carried items, still accurate except for the three now
   closed.
4. **`RUN10_REPORT.md` § 6** — the external surfaces, still open and still outside this
   repository: the slide deck and `docs/cais-2026/`.

## The one thing to read if you read nothing else

**The external-claims scanner never worked, and a document certified that it did — using the
broken scanner's own output as the evidence.**

It cut each pattern's regex at the first `|`, turning every alternation into an unbalanced
parenthesis. `grep -E` rejected them and the error went to `/dev/null`. **18 of 34 patterns
matched nothing for the tool's entire life**, including every form of "100% recall" and
"0 false negatives", the 80%-precision pattern this release was written to catch, and all
three count patterns.

Same command, same specimen: **1 match before the fix, 11 after.**

Everything W48 reports was re-scanned after the fix. **If you ran that script before
2026-09-10, re-run it** — a clean result from the old script is not evidence of a clean
surface.

## What this session did

| W | what |
|---|---|
| W48 | **the external surface, twice** — once with the broken tool, then again after fixing it. The retracted set is live on a public slide deck, in an ACM paper's source *and* compiled PDF, and in a `docs/cais-2026` file that tells a future author to paste `98.51\%` into a paper |
| W49 | **the competitive table re-measured**, all three tools, one corpus, v0.20.0. Bandit and Semgrep beat agent-audit on precision and FPR, and the table now says so |
| W50 | **`README.md:147` cut and guarded.** The 80% was a 20-sample draw attached to an 18,899 denominator |
| W51 | release evidence re-run; one command in the expected set **does not exist** |

## The three things a reader needs

1. **A mechanism whose failure mode is silence must prove it can still fire.** Eighteen dead
   patterns and a clean repository produce identical output: nothing. The fix is not the
   one-character split — it is `validate_patterns()`, which refuses to scan with a malformed
   pattern, and `test_guard_can_actually_fail`, which caught a defect in one of this run's own
   new patterns within a minute of being written.

2. **The competitive table was incomparable for a reason nobody had stated.** RUN9's caveat
   said the baselines "have not been re-run against the 81-sample GT" — implying re-running
   was the missing step. It is impossible: `precision_recall.py:332` requires
   `e_rule == d_rule`, so any tool emitting its own rule IDs scores a structural zero. The fix
   was to move the comparison to the corpus built for cross-tool matching, not to re-run the
   baselines on the one that cannot score them.

3. **The test count drifted inside the fix for it, for the third session running.** Adding
   four guard tests moved 1,891 → 1,895. Corrected on every current-state surface. Three more
   stale counts surfaced *only because the scanner was fixed* — `docs/index.html:896`,
   `README_CN.md:367` and `CLAUDE.md:56`, the last of which said the CWE mapping holds 92
   rules when it holds 86.

## Current commit

`fix/py314-blocker`. RUN 12 committed on top of `2a03089`; the working tree is clean, which the
preflight requires. RUN 9's section above was written when its work was uncommitted.

## Invariants at the end of the run

| invariant | result |
|---|---|
| Layer 1 | **TP 199 / FP 90 / FN 37**, P 68.86% / R 84.32% / F1 0.7581 — unchanged; no detection code touched |
| `quality_gate_check.py` | **exit 0** — 0 failures, 0 warnings, 0 skipped |
| full suite | **1,924 passed, 1 failed, 4 skipped** (`pytest tests/ packages/audit/tests/`), 1,929 collected |
| `tests/` alone | **1,873 passed, 1 failed, 4 skipped** |
| the one failure | `tests/test_corpus_label_rules.py`, committed red on purpose |
| AVB, all three tools | agent-audit R 95.24 / P 86.96 / F1 0.9091 · Bandit R 26.19 / P 100 / F1 0.4151 · Semgrep R 23.81 / P 100 / F1 0.3846 |
| guard self-test | 11/11 |
| scanner patterns | **34, all validated** (was: 34 declared, 16 working, "35" published) |
| advertised rules | **66** |
| thresholds changed | **none** |
| detection code changed | **none** |
| `./run_eval.sh` | **UNVERIFIED — the file does not exist.** `DECISIONS.md` item 52 |

## RUN 11 (2026-09-12) — W52, the pre-release audit

Every figure in the brief was re-measured rather than trusted. Five of six reproduce exactly;
the sixth — signal-to-noise 2.2:1 — has no producer in this repository and was not restated,
unchanged from RUN10's item 52.

**Two defects found, both of which would have shipped.**

1. **The documents that define the current metrics were the stale ones.** `fda9f06` moved the
   measurement from F1 0.746667 to 0.758095 and every *user-facing* surface was updated. The
   three documents those surfaces cite as the authority were not:
   `METRICS_RETRACTION.md` § 3 (heading: *"The correct current values, measured now"*),
   `CAPABILITY_BOUNDARIES.md` § 6 (directly under *"Reproduce with…"*), and § 3a's table of
   replacement values — which, followed literally, would have written 0.7467 back onto a
   surface that was already correct.

   The claims scanner carries patterns for exactly those numbers and reported nothing,
   because its allowlist exempts those documents by path — correctly, since they must keep
   quoting the *withdrawn* figures as evidence. The allowlist is drawn around documents;
   these documents hold both kinds of block. `tests/test_published_metrics.py` now relates
   any block naming `precision_recall.py` to `results/layer1.json`. Red on the two stale
   blocks before, 9 passed after.

2. **A sixth rule count, on the PyPI project page.** `packages/audit/README.md:26` said
   "60+ rules". It is the `readme` declared in that directory's `pyproject.toml`, so it is
   the wheel's long description — and RUN10 corrected the *other* distribution claim in the
   same directory while this one went unlisted in the rule-count guard. Fixed, guarded, and
   the artifacts rebuilt because the README ships inside them.

Also corrected: `tests/README.md`'s corpus description (v2.1/42/198 → v2.2/81/238, flagged by
`METRICS_RETRACTION.md` § 2 and never done) and its "3 个误报" — which was not a measurement
but the `3 FP / 201` residue of the 98.51% derivation, surviving because it carries no percent
sign.

**The test count drifted inside the fix for it, for the fourth session running.** Nine new
tests moved 1,895 → 1,904. Corrected on every current-state surface, and 1,895 added to the
scanner's stale-count pattern so the next one is caught rather than discovered.

## RUN 11 (2026-09-12) — W53–W55, the release staged

`scripts/release_v0200.sh`, `RELEASE_NOTES_v0.20.0.md`, `RUN11_REPORT.md`, and the eleven-run
table in `NIGHT_RUN_LEDGER.md` § W55. Evidence for all of it is § W53–W55 of the ledger.

**The script's own preflight found four things, none of which was in any document.**

1. **`twine` is not installed** — the one thing standing between here and stage 5.
2. **A flaky test.** `performance_test.py::TestThroughput::test_consistent_performance` asserts
   three wall-clock timings stay within 50% of their average on a scan that takes 0.06s. It
   failed 1 of 4 whole-suite runs today and passed 10 of 10 on its own. The suite check now
   compares the *failure set* and re-runs that one test rather than either ignoring a red
   suite or refusing to release over a stopwatch. **The tolerance was not changed** — that is
   a threshold.
3. **Local `master` is 7 commits ahead of `origin/master`** (SkillScanner + PDF report, marked
   WIP), so the push publishes 64 commits, not 57. Already inside the branch, so it ships
   either way; the push is when it becomes public.
4. **`git push origin master --tags`, the command in the checklist, would also publish
   `skillscanner-core-frozen`** — the one local tag not on the remote. The script pushes the
   release tag only.

**Three documents would have shipped wrong, all three now corrected with paired evidence:**
`CHANGELOG.md` said `AGENT-041` still over-triggers on *any* `.execute()` receiver — measured
0 findings on all three shapes it names, and it sits thirty lines under the fix that made it
false, on the page that closes issue #10; the same entry published `1796 passed / 1 failed /
3 skipped` for a release containing 1,905; and `RELEASE_CHECKLIST.md` carried a stale
prescription (`1,796 tests` onto a surface already reading the measured count), a commit count that drifted
inside its own correction for the third time, and a § 7 row saying #10 stays open four lines
below a header saying it closes.

**`ISSUE_REPLIES.md` is confirmed current** — `git diff bea9901..HEAD -- packages/ rules/` is
one line of README text, so no measurement in it has moved, and #10 was re-run at HEAD on the
reporter's shapes rather than trusted.

## Still open

**Yours, and blocking — the full table is `RUN10_REPORT.md` § 6:**

1. **Has any of the external material been submitted, uploaded to arXiv, or presented?**
   Gates everything: an arXiv v1 can only be superseded by a v2 with a change note.
2. **`agent-audit-slides.html`** — five retracted figures, four wrong rule counts, five stale
   versions.
3. **`docs/cais-2026/PAPER_DATA_SUMMARY.md`** — a `LaTeX (v0.16.0)` column of paste-ready
   retracted macros, plus a recommendation to use them.
4. **`paper/main.tex:325` + `main.pdf`** — "98.51\% precision at 100\% recall", source and
   build.
5. **`openclaw-skill/`** was not scanned; checklist § 2.7 names the ClawHub listing as an
   outreach destination.
6. **The malware-campaign section**, **`RELEASE_CHECKLIST.md` steps 6–7**, and **whether the
   drafts go out** — all carried from RUN9, unchanged.

**Two findings that reduce the work, both verified:** `paper/neurips/submission/` has **0
matches**, and `paper/skillsworkshop/` (the SkillScanner camera-ready and poster) is clean.
And `main.tex:401`'s "100\% recall on injection/RCE and MCP" is **true** — re-measured at
v0.20.0, Set A 19/19, Set B 9/9 — so it must **not** be retracted with the rest.

**New from W53–W55, ranked, all in `RUN11_REPORT.md` § 4:** install `twine`; decide whether the
7 WIP commits go public with the release; the flaky wall-clock test; `"withdrawn in v0.19.3"`
on eight surfaces naming a version that was never published; and `CAPABILITY_BOUNDARIES.md`
§ 3 counting seven instances of the defect shape when two more have been identified since.

**Three of those five are closed by W56–W59 (RUN 12).** `twine` is installed and § 1.11 finds
it in the venv; the 7 commits ship labelled preview in both release documents; and the
`v0.19.3` references are corrected to `v0.20.0` with `tests/test_published_versions.py` failing
the suite if any published page ever names a release that does not exist. The two that remain
are unchanged and both are Heady's by their nature: the flaky test's tolerance is a threshold,
and `CAPABILITY_BOUNDARIES.md` § 3's instance count is a judgement about whether an instrument
is counted beside a detector. New from RUN 12, none blocking: whether `SKILL-010`'s API call
should be opt-in; that `CHANGELOG.md` documents six releases that never existed; and that one of
the seven commits (`208a3ab`) is a `.gitignore` rail rather than either feature — verified
benign, logged because the brief said to log it.

**Carried, not blocking:** `DECISIONS.md` items 35, 36, 38, 39 rows 2–4, 40, 41, 43, 46.
New this run: 47–52. `NEXT_ROUND.md` is v0.21.0 and needs no decision to start.

## Environment

`python` is NOT on PATH — use `python3` (3.14.3). `pdftotext` **is** installed (poppler
26.09.0), contrary to what the last PROGRESS said; PDFs are searched, and that is how the
compiled `main.pdf` was caught. Bandit 1.8.0 and Semgrep 1.99.0 are on PATH from
`~/Library/Python/3.9/bin`.

```bash
cd packages/audit && python3 ../../tests/benchmark/precision_recall.py --output-json ../../results/layer1.json
python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml
cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" --tool all --dataset all --output ../../results/avb_tool_comparison
```

A full in-repo claims scan takes ~60–90s now that all 34 patterns actually run; two
back-to-back exceed a 120s timeout.

## Guard-hook friction

Two denials, neither bypassed, both the same mechanism and both instructive.

`night-guard.sh:16` tokenises any command containing a redirect, and its `for tok in $(...)`
loop is **unquoted**. So `ls -d */ 2>/dev/null` glob-expanded onto the repository's own
protected corpus directory and was refused — a false positive in the guard, not in the
command. Solved with `find . -maxdepth 1 -type d`.

The second: appending the RUN10 ledger entry through a heredoc was refused because the prose
itself contains both `>` and that directory's name. Solved by writing the text with the
editor and appending the file, so no protected token ever reaches the shell. The guard wins,
every time; rewrite the command rather than reaching for a bypass.
