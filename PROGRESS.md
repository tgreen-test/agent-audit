# PROGRESS

**Session 11 state: COMPLETE. W48–W51 all done.** Read `RUN10_REPORT.md` first (one page),
then § 6 — **seven decisions, all yours, with the first gating the rest.**

Nothing pushed, merged, tagged or published. No file outside this repository was edited.

## Start here

1. **`RUN10_REPORT.md` § 1** — two sentences on whether v0.20.0 can ship. It cannot yet, and
   the reason changed this run.
2. **`RUN10_REPORT.md` § 2** — the external hits, grouped by document.
3. **`EXTERNAL_CLAIMS_CHECKLIST.md` § 4** — rewritten. It used to certify the scanner; it now
   records that the scanner was broken and what the fixed run found.

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

`fix/py314-blocker`, working tree ahead of `dbae329`. Nothing committed by this run.

## Invariants at the end of the run

| invariant | result |
|---|---|
| Layer 1 | **TP 199 / FP 90 / FN 37**, P 68.86% / R 84.32% / F1 0.7581 — unchanged; no detection code touched |
| `quality_gate_check.py` | **exit 0** — 0 failures, 0 warnings, 0 skipped |
| full suite | **1,904 passed, 1 failed, 4 skipped** (`pytest tests/ packages/audit/tests/`), 1,909 collected |
| `tests/` alone | **1,872 passed, 1 failed, 4 skipped** |
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
