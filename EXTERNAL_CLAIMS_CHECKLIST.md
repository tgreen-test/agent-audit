# External surfaces: where the retracted figures may have gone

**This is the gating input for `docs/decisions/METRICS_RETRACTION.md` § 5 step 1**, the one
item in the v0.20.0 release that nobody but Heady can produce. The in-repo half of the
retraction is done; the published half cannot start until this list is filled in.

The tool does the mechanical part:

```bash
./scripts/scan_external_claims.sh ~/wherever/your/papers/live
./scripts/scan_external_claims.sh --list          # what it looks for, and why
```

**Run it wherever you like — but this repository's own scan must be run with the allowlist**,
or you get 200 lines of documents whose job is to quote the figures:

```bash
./scripts/scan_external_claims.sh --allowlist scripts/external_claims_allowlist.txt .
```

It reads only. It never writes, edits or uploads.

---

## 1. The rule, before the list

`METRICS_RETRACTION.md` § 5: **nothing new is published on top of a surface that still
carries a retracted figure.** A new blog post or release note citing current numbers, while
a preprint still says 98.51%, invites the reader to discover the contradiction rather than
the correction.

And § 4: **retract first, restate second, and do not merge the two into one "updated
results" note.** This is the only item in the whole release where sequencing genuinely
matters.

---

## 2. Destinations, in the order I would check them

Each row: what to search for, and what the corrected value is. The point of column 3 is that
a correction should be a substitution, not a re-derivation.

### 2.1 The TrustAgent paper, and its arXiv version if uploaded

| search for | if found | replace with |
|---|---|---|
| `98.51`, `0.9851`, `98.5` near "precision" | **RETRACT** | no equivalent. The figure is withdrawn — see § 3 |
| `100%` near "recall", `0 FN`, "no false negatives" | **RETRACT** | recall 84.32%, and say it was never measured before |
| `99.25`, `0.9925` | **RETRACT** | no equivalent |
| `1.49%` FP rate | **RETRACT** | FP rate 31.14% |
| `0.778`, `77.8%`, `73.58`, `82.63` | **UPDATE** + causal note | F1 0.7581, P 68.86%, R 84.32% |
| `195` / `70` / `41` as TP/FP/FN | **UPDATE** | TP 199 / FP 90 / FN 37 |
| `198 annotations`, `42 sample files`, `v2.1` | **UPDATE** | GT v2.2, 81 files, 238 labels |
| a rule count of 40, 49, 52, 53, 56, 63, 72 or 92 | **COUNT** | 66 |

**Check the arXiv version separately even if the source is the same file.** A v1 on arXiv is
permanent; it cannot be edited, only superseded by a v2 with a note. If a retracted figure is
in an arXiv v1, the correction is a **v2 with a change note**, and that is a different piece
of writing from a correction to a working draft. Decide which before editing anything.

Also check: the paper's own `results/` or `figures/` directory, and any `.tex` macro file —
`\newcommand{\ourprecision}{98.51\%}` is the shape that survives a search of the prose.

### 2.2 The SkillScanner camera-ready

Camera-ready has the hardest deadline and the least room, so check it early even if the
probability is lower.

Two distinct risks here, and the second is easy to miss:

1. Does it cite agent-audit's Layer 1 figures at all? If so, § 2.1 applies unchanged.
2. Does it cite **its own** Cisco-comparison figures? Those are a separate line with a
   separate defect already recorded: `docs/skillscanner/findings/F-003_cisco_scanner_unobtainable.md`
   shows the published reproduction path does not reproduce on a clean machine, and
   `ERRATA_skills_crosslingual_security.md` is a drafted, unapplied correction to the dataset
   repo. Not part of this retraction — but if the camera-ready is being opened anyway, it is
   the cheapest moment in the year to fix it.

### 2.3 Slide decks

**Highest risk per unit of effort, for two reasons.** A slide states a number with no
methodology beside it, so a retracted figure on a slide is maximally naked. And decks get
re-used: last quarter's results slide is next quarter's results slide.

```bash
./scripts/scan_external_claims.sh ~/Documents/talks ~/Desktop
```

* `.pptx` — the script unzips and searches the XML. Covered.
* `.pdf` exports — covered if `pdftotext` is installed (`brew install poppler`). **Install it
  before the run**, or PDFs are silently listed as unread rather than searched.
* `.key` (Keynote), `.pages`, `.numbers` — **not searchable by anything here.** The script
  lists them by name under "NOT SEARCHED". Those you open by hand. There is no way round it;
  Keynote stores a binary plist.
* Google Slides — not on disk at all. Search inside Drive for `98.51`, `0.778`, `100%
  recall`.

### 2.4 GitHub Pages / README badges

`docs/index.html` and the two READMEs were corrected in-repo this release. What is **not**
covered by that:

* **The rendered Pages site, if it is served from a branch or a build that has not been
  redeployed.** Corrected source and stale HTML look identical from inside the repository.
  Check the live URL, not the file.
* **Badge images.** `img.shields.io/badge/tests-1905...` renders whatever the URL says, and
  the URL is in the markdown — so a corrected file is a corrected badge. But a badge whose
  URL points at a *service* (coverage, CI) reflects the last run, not the file.
* **The repository's social preview card and the GitHub "About" description**, both of which
  are set in the GitHub UI and are in no file in this repository. If either says a rule count
  or a metric, nothing in this release touched it.

### 2.5 PyPI

The description is `packages/audit/pyproject.toml:4`, corrected to 66 rules for v0.20.0.

**The correction is not retroactive.** Every already-published version keeps the description
it was built with, and PyPI renders each version's own page. If v0.16–v0.19 said "53 rules",
those pages still say it:

```
https://pypi.org/project/agent-audit/<version>/
```

PyPI does not allow editing a released distribution's metadata. The options are exactly two:
leave the historical pages as the record they are, or yank versions — and yanking to fix a
description would be disproportionate. **Recommendation: leave them, and make sure the
*latest* page is right**, since that is the one everyone lands on.

Verify after upload:

```bash
pip download agent-audit==0.20.0 --no-deps -d /tmp/pypicheck
python3 -c "import zipfile,glob;print(zipfile.ZipFile(glob.glob('/tmp/pypicheck/*.whl')[0]).read([n for n in zipfile.ZipFile(glob.glob('/tmp/pypicheck/*.whl')[0]).namelist() if n.endswith('METADATA')][0]).decode()[:1200])"
```

### 2.6 Zenodo / artifact DOIs

A DOI is the worst case: **it is designed to be permanent and citable.** If any figure in
this document's scope has a DOI attached, that is the first thing to correct, because it is
the one a third party will cite in a year.

Zenodo supports a **new version** of a record with its own DOI, plus a concept DOI that
resolves to the latest. It does not support editing files in place on a published record.
So the correction is a new version with a change note, and the note must say **retraction**,
not "updated results".

Check: Zenodo, figshare, OSF, any conference artifact-evaluation submission, and any
`CITATION.cff` or `codemeta.json` in a repository that names a figure.

### 2.7 Outreach messages

Not correctable, and that changes what the item is: the question is not "fix them" but
"**who was told, and do they need telling again**".

Worth a pass through:

* the ClawHub skill listing description for `agent-audit-scanner`
* Hacker News / Reddit / X posts, and the two published blog posts already carrying
  correction notes (`docs/blog/hackernews-post.md`, `docs/blog/launch-post.md`)
* Discord/Slack announcements in agent-security communities
* any email to a reviewer, PC chair, funder or collaborator quoting a figure
* the three untracked drafts at the repository root — handled, see `OUTREACH_CLAIMS.md`

**The test to apply per recipient:** did they receive a number they might act on or repeat?
If yes, a short direct correction is owed. If it was a link to a page that is now corrected,
the page did the work.

---

## 3. The wording, so it does not have to be written twice

Use `METRICS_RETRACTION.md` § 4 verbatim, adjusting only the venue. Do not soften the middle
sentence. The three things that make it a retraction rather than a correction notice:

1. The mechanism is named in the first three sentences — *false negatives were assumed to be
   zero rather than measured*. Burying that below a paragraph of context is how a retraction
   becomes a correction notice.
2. The word is **retracting**, not "updating" or "revising", with the reason retraction is
   the right verb: no re-run can reproduce the figures, so there is nothing to update *to*.
3. The contemporaneous measurement is quoted — FN 124, recall 47.46%. It is the strongest
   available fact and it is self-incriminating. Leaving it out invites the reader to wonder
   what else is missing.

Current values, restated in the same paragraph so no reader is left with a hole where a
number was:

| figure | value | command |
|---|---|---|
| Layer 1 | **P 68.86% / R 84.32% / F1 0.7581**, TP 199 / FP 90 / FN 37, over 238 labels in 81 files | `cd packages/audit && python3 ../../tests/benchmark/precision_recall.py` |
| rules | **66** | `python3 -c "import sys;sys.path.insert(0,'tests');from test_rule_producers import advertised_rules;print(len(advertised_rules()))"` |
| tests | **1,905 passing**, 1 red on purpose, 4 skipped | `python3 -m pytest tests/ packages/audit/tests/ -q` |
| AVB `knowns` | **R 100.0% / P 88.0% / F1 0.9362** — unaffected, measured against an explicit oracle | `cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" --tool agent-audit --dataset knowns` |
| version | **0.20.0** | `python3 -c "import agent_audit;print(agent_audit.__version__)"` |

**Two qualifications must travel with the Layer 1 row or the restatement misleads in the
opposite direction** (`METRICS_RETRACTION.md` § 3):

* Precision fell from the previously published 73.58% because **two file-discovery bugs were
  fixed**; the tool began finding correct things the corpus does not label yet. Recall rose
  over the same period. Stating the F1 drop without this asserts a quality regression that
  did not happen.
* 68.86% is a **lower bound**. At least 21 of the 90 FPs are correct by their rule's own
  definition and merely unlabelled. Say "a bound, and the corpus is being repaired" — not
  "≈75% after adjustment", which is the 98.51% again in the other direction.

---

## 4. The tool was broken until 2026-09-10 — read this before trusting an earlier scan

This section previously read *"What the in-repo run found, so you know the tool works"*. It
did not work, and the way it failed is the reason this document exists.

`scan_external_claims.sh` cut each pattern's regex at its **first** `|`. Any regex using
alternation was truncated mid-group into an unbalanced parenthesis, `grep -E` rejected it,
and the error went to `/dev/null` — so it silently matched nothing. **18 of 34 patterns were
dead**, including every form of *"100% recall"* and *"0 false negatives"* (`R-100`,
`R-100-alt`, `R-0FN`, `P-100`, `F1-100`, `ARROW`), the `PREC-80` pattern this release was
written to catch, and all three count patterns (`RULES-N`, `TESTS-N`, `VER`).

Same command, same eight-claim specimen, before and after the fix: **1 match, then 11.**

Fixed in RUN10: split from the right, plus `validate_patterns()`, which runs every regex
before scanning and exits 2 if any is malformed rather than under-reporting. The header now
prints `patterns: 34 (all validated)` — and it is **34**, not the 35 stated here, in
`PROGRESS.md` and in `RUN9_REPORT.md:183`.

**If you ran this script before 2026-09-10, re-run it.** A clean result from the old script
is not evidence of a clean surface.

### What the fixed run found outside the repository

Scanned, per `docs/overhaul/RUN10_PROMPT.md`: `docs/`, `agent-audit-slides.html`, `paper/`.
Read-only; nothing outside this repository was edited. Full detail in `RUN10_REPORT.md` § 2
and the `NIGHT_RUN_LEDGER.md` RUN10 entry.

| destination | what it carries | class |
|---|---|---|
| `agent-audit-slides.html` — a public deck | slide "Current Metrics (v0.16.0)": precision 98.51%, **recall 100%**, F1 99.25%, FP rate 1.49%; a closing slide repeating F1 99.25%; "42 synthetic samples, 198 annotations"; "1,142 passing"; "49 Rules" x4; "v0.16.0" x5 | RETRACT + COUNT |
| `paper/main.tex:325` and `paper/main.pdf` — an ACM `sigconf` paper | "achieves 98.51\% precision at 100\% recall" — in both source and the compiled PDF | RETRACT |
| `docs/cais-2026/PAPER_DATA_SUMMARY.md` | a column headed **`LaTeX (v0.16.0)`** holding paste-ready `98.51\%`, `100\%`, `99.25\%`, under an explicit recommendation to report the v0.16.0 Layer 1 metrics in the paper | RETRACT — and it is an *instruction*, not just a stale number |
| `docs/cais-2026/` — 4 more files | `AVB_EVALUATION_REPORT.md`, `EXECUTION_SUMMARY.md`, `AVB_EXPANSION.md`, `SEMGREP_COMPARISON_REPORT.md` | RETRACT |
| `paper/neurips/trustagentfiles1/audit/COMPREHENSIVE_AUDIT_SUMMARY.md:145` | "Total audited: **63 rules**" | COUNT, now 66 |

**Clean, and both have hard deadlines:**

* `paper/neurips/submission/` — **0 matches.**
* `paper/skillsworkshop/` (the SkillScanner camera-ready and poster) — only `WILSON` hits,
  each of them the workshop's own cross-lingual confidence intervals, not the 58.4–91.9
  interval that travels with the unsubstantiated 80%.

**Two things no command can answer, and they gate the order of work:**

1. **Has any of it been submitted, uploaded to arXiv, or presented?** Nothing on disk says.
   An arXiv v1 needs a v2 with a change note; a working draft needs an edit. § 2.1.
2. `main.tex:401`'s *"100\% recall on injection/RCE and MCP"* is **true and must not be
   retracted with the rest** — it is AVB Set A/Set B against an oracle, re-measured at
   v0.20.0 this run: Set A 100.0% (19/19), Set B 100.0% (9/9).

### What the in-repo run finds now

```
$ ./scripts/scan_external_claims.sh --allowlist scripts/external_claims_allowlist.txt .
 patterns: 34 (all validated)
 132 match(es)
```

`README.md` no longer matches at all — its ClawHub clause was cut in RUN10 (`RUN10_REPORT.md`
§ 4). The remainder are documents whose job is to quote the figures, plus
`docs/F1_REPRODUCTION.md` and `docs/COMPETITIVE-COMPARISON.md`, which stay unallowlisted on
purpose so their correction notes keep showing up. The bulk of the rest is `VER`, which is
loose by design and mostly matches version strings in source and dated reports.

## Related

* `docs/decisions/METRICS_RETRACTION.md` — the retraction, the mechanism, § 4's wording, § 5's ordering
* `CLAIMS_RECONCILIATION.md` — the claims table
* `OUTREACH_CLAIMS.md` — the three drafts, and what was removed from them
* `scripts/scan_external_claims.sh` — the tool; `--list` prints every pattern and its correction
* `scripts/external_claims_allowlist.txt` — what an in-repo scan skips, and why each entry is there
