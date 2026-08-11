# The 98.51% — a retraction path

**Status:** retraction drafted, not issued. Nothing public-facing has been edited.
**Date:** 2026-08-11 · RUN6 / W25
**Measured at:** `950e308` on `fix/py314-blocker`, `agent_audit.__version__ == 0.19.2`

This document exists because of a distinction that changes the correction. A **drifted
number** — one that was measured correctly on an older commit and has since moved — gets
an update. A number whose **denominator was never measured** gets a retraction and a
restatement, because the original was never a measurement of the thing it named. The
98.51% is the second kind.

**Nothing here has been applied.** Editing a public claim is out of scope by instruction,
and rightly so: if any of this has reached a paper, a slide or an outreach message, the
order is retract-then-restate and the sequencing is Heady's call.

---

## 1. The mechanism

### The claim

`tests/README.md` publishes, twice (lines 116–119 and 279–282):

```
- Precision: **98.51%** ✅ (目标: ≥90%)
- Recall: **100.00%** ✅ (目标: ≥85%)
- F1-Score: **99.25%** ✅ (目标: ≥0.87)
- FP Rate: **1.49%** ✅ (目标: ≤5%)
- 剩余误报: 3 个（规则精度问题，非标注错误）
```

`CHANGELOG.md:175-177`, under `## [0.4.1] - 2026-02-04`, carries it forward as a further
improvement:

```
- 3 false positives eliminated (Precision: 98.51% → 100%)
- Recall maintained at 100%
- F1 Score: 100%
```

### The commit

```
$ git log --all --oneline -S "98.51" -- .
74ef74b docs: RUN5 …                      (this run's own report, quoting it)
e4a939d docs: RUN4 …                      (this run's own report, quoting it)
1ef3cbc release: agent-audit v0.7.0 …     (deletes the source document, below)
a65b341 feat: release v0.5.2 - Industrial-grade benchmark & OWASP Agentic Top 10 full coverage
```

`a65b341`, 2026-02-04, is the origin. Both `tests/README.md` and `CHANGELOG.md` gained the
figure in that single commit.

### The evidence that false negatives were assumed, not measured

Two independent lines of evidence, and the second is not an inference.

**(a) The results file committed in the same commit measured something else entirely.**

```
$ git show a65b341:results/layer1.json
  "true_positives": 112,
  "false_positives": 4,
  "false_negatives": 124,
  "precision": 0.9655172413793104,
  "recall": 0.4745762711864407,
  "f1_score": 0.6363636363636365,
```

**P 96.55% / R 47.46% / F1 0.6364, with 124 false negatives.** Not one of the four
published figures appears here. The number was never produced by the script whose output
the repository committed beside it.

**(b) The source document states the assumption in words.**

`a65b341` also added `agent-audit-v041-prompt.md`, the development brief for v0.4.1. It was
deleted at `1ef3cbc` (v0.7.0), which is why it is easy to miss. Its "current benchmark
metrics" block reads, verbatim:

```
$ git show a65b341:agent-audit-v041-prompt.md
当前 benchmark 指标:
  Precision = 98.51% (3 FP / 201 total)
  Recall    = 100%   (0 FN)
  F1        = 99.25%

目标指标:
  Precision = 100%   (0 FP)
  Recall    = 100%   (0 FN)
```

**`Recall = 100% (0 FN)`.** Written down. And `3 FP / 201 total` gives the precision
directly: 198/201.

The arithmetic closes with no residue:

```
$ python3 -c "tp,fp=198,3; p=tp/(tp+fp); r=1.0; print(p, r, 2*p*r/(p+r), fp/(tp+fp))"
P = 98.5075%   R = 100.00%   F1 = 99.2481%   FP rate = 1.49%
```

All four published figures to four decimal places, from **TP = the annotation count**,
**FP = the three residual false positives the document itself names**, and **FN = 0 by
assertion**.

### What that makes the numbers

Recall was not measured. It was set to 1.0, so:

* **Recall 100%** is a restatement of the assumption, not a result.
* **F1 99.25%** is arithmetic between a real precision and a constant. Nothing in it
  reflects what the scanner missed.
* **Precision 98.51%** is the only figure with any measurement behind it, and even that
  assumes every one of the 198 annotations was matched — which is TP = 198, i.e. the same
  zero-miss assumption entering through the numerator.
* **FP rate 1.49%** is `3/201`, the complement of the precision, and is sound in the same
  narrow sense.

The measured false-negative count on the day the claim was published was **124 out of 236
positive labels**. Recall was 47.46%, not 100%.

### One more inconsistency inside the same commit

`tests/README.md` describes the corpus as **v2.1, 42 sample files, 198 annotations**. The
corpus actually in the tree at that commit was:

```
at a65b341: version 2.2  samples declared 81  vulns declared 218
  actual samples: 81   actual labels: 238
```

Three descriptions of one dataset in one commit — v2.1/42/198 in the README, v2.2/81/218 in
the file's own header, 81/238 on counting it. So the "198 annotations" that became TP was
not the size of the dataset being measured either.

---

## 2. Every location the affected figures appear

Sources are those catalogued in `CLAIMS_RECONCILIATION.md`, re-checked at `950e308`. The
marking is the operative column: **same methodology error** means the figure is derived
from the FN = 0 assumption and cannot be reproduced by any re-run; **different figure**
means a genuine measurement that has since drifted, correctable by an update;
**unaffected** means neither.

### Same methodology error — retract, do not update

| # | location | figure | note |
|---|---|---|---|
| 1 | `tests/README.md:116` | Precision 98.51% | 198/201 |
| 2 | `tests/README.md:117` | Recall 100.00% | the assumption itself |
| 3 | `tests/README.md:118` | F1-Score 99.25% | arithmetic on the assumption |
| 4 | `tests/README.md:119` | FP Rate 1.49% | 3/201 |
| 5 | `tests/README.md:270` | "v2.1 … 添加 87 个新标注，达到 98.51% Precision" | additionally *attributes* the figure to a labelling change, which compounds it: adding annotations raises TP under this method by construction |
| 6 | `tests/README.md:279` | Precision 98.51% | second copy |
| 7 | `tests/README.md:280` | Recall 100.00% | second copy |
| 8 | `tests/README.md:281` | F1-Score 99.25% | second copy |
| 9 | `tests/README.md:282` | FP Rate 1.49% | second copy |
| 10 | `CHANGELOG.md:175` | "Precision: 98.51% → 100%" | **worse than the original.** A delta between an assumed figure and a perfect one, presented as a result |
| 11 | `CHANGELOG.md:176` | "Recall maintained at 100%" | "maintained" implies it was measured twice; it was measured zero times |
| 12 | `CHANGELOG.md:177` | "F1 Score: 100%" | follows from 10 and 11 |

Twelve locations, two files. `tests/README.md` is the primary; `CHANGELOG.md` is the one
that escapes into release notes.

**Also in scope, though not a figure:** `tests/README.md` lines 100–110 describe the corpus
as v2.1 / 42 files / 198 annotations. That description is wrong for the commit it was
written in and is wrong today (v2.2 / 81 / 238). It should be corrected in the same pass,
because it is the sentence that makes 198 look like a measured denominator.

### Different figure — update, with the cause attached

These are real measurements that have drifted. They need restatement, **not** retraction,
and the restatement is unsafe without its causal note (§ 3).

| # | location | figure | reproduces today as |
|---|---|---|---|
| 13 | `CLAUDE.md:11` | P 73.58% / R 82.63% / F1 0.778, TP 195 / FP 70 / FN 41 | P 67.82% / R 83.05% / F1 0.7467, TP 196 / FP 93 / FN 40 |
| 14 | `README.md:97`, `:233` | same | same |
| 15 | `README_CN.md:98`, `:214` | same | same |
| 16 | `docs/index.html:923,927` | R 82.63% / F1 0.778 hero tiles | as above |
| 17 | `docs/index.html:1074–1076` | R 82.63% / P 73.58% / F1 0.778 comparison row | as above |
| 18 | `docs/BENCHMARK-RESULTS.md:7`, `:228` | "F1 0.778 (raw, reproducible)" | F1 0.7467 |
| 19 | `docs/F1_REPRODUCTION.md:35,38` | "Raw F1 0.7784 matches the documented 0.778 exactly" + transcript | F1 0.7467 |
| 20 | `docs/F1_REPRODUCTION.md:50–51` | adjusted F1 0.840–0.846 | inputs all moved; already carries its own caveat |
| 21 | `results/layer1_v0.19.0.json:7` | `"f1_score": 0.7784431137724551` | 0.7467 |

**Row 19 deserves a flag of its own.** `docs/F1_REPRODUCTION.md` exists specifically to
prove the headline F1 is reproducible, and it no longer reproduces. A reproduction document
that does not reproduce is a stronger negative signal than a stale number in a README,
because its whole claim is auditability.

**Row 20 is the interesting near-miss.** The adjusted F1 of 0.84 is computed by subtracting
false positives attributable to rules the ground truth does not yet label. That is the same
*shape* of adjustment as assuming FN = 0 — a correction applied to one side of a ratio to
account for corpus incompleteness — and it is the reason `CLAUDE.md` is right to say it "is
not used as a headline figure because it isn't directly produced by the script". The
difference, and it is the whole difference, is that the adjustment is **disclosed, bounded
and attributed**. Keep it that way. If the adjusted figure ever migrates into a headline,
this section applies to it too.

**One more thing about row 19's neighbourhood:** `docs/F1_REPRODUCTION.md:75` describes a CI
gate at `f1 < 0.75` inside `precision_recall.py` and says it "passes today". That gate was
deleted in W24, and before deletion it was failing, not passing. Not a metric claim, but it
sits in the same file and should be corrected in the same pass.

### Unaffected

| location | figure | why |
|---|---|---|
| AVB `knowns` R 100.0% / P 88.0% / F1 0.9362 | measured at HEAD | measured against an oracle with an explicit expected set; false negatives are counted, and the 100% recall here is a result, not an assumption |
| `docs/BENCHMARK-RESULTS.md` AVB-19 / 22-sample figures | point-in-time on different sample sets | not comparable to each other and not deltas, but each was measured |
| the rule counts (66 / 72 / 92 / 53 / 52 / 49 / 40+) | counts, not ratios | a different defect — `CLAIMS_RECONCILIATION.md § 3` |
| version and test-count claims | mechanical staleness | `CLAIMS_RECONCILIATION.md § 7` |
| `README.md:146` "18,899 ClawHub skills at 80% precision", `blog_post.md:88` BLOCK-tier 80% | unverifiable from this repository | neither confirmed nor implicated; they need their data committed, not a retraction |

---

## 3. The correct current values, measured now

```
$ python3 tests/benchmark/precision_recall.py
INFO: Loading ground truth from tests/ground_truth/labeled_samples.yaml
INFO: Loaded 238 labels for 81 files
INFO: Running scan on tests/fixtures
INFO: Got 289 findings

============================================================
PRECISION/RECALL EVALUATION REPORT
============================================================

Summary Metrics:
  True Positives:  196
  False Positives: 93
  False Negatives: 40

  Precision: 67.82%
  Recall:    83.05%
  F1-Score:  74.67%
  FP Rate:   32.18%
============================================================
$ echo $?
0
```

Reproducible: ten consecutive runs of that command return identical figures to six decimal
places, including under the two `PYTHONHASHSEED` values that used to disagree
(`NIGHT_RUN_LEDGER.md § W24 step 1`).

**Two qualifications must travel with these numbers, or the restatement misleads in the
opposite direction.**

**(a) The F1 fell for reasons that are not detection regressions.** Precision dropped in
three steps since v0.19.0, and every one was a *discovery bug being fixed* — the tool began
finding things the corpus never labelled:

| step | what happened | FP | precision |
|---|---|---|---|
| v0.19.0 as published | — | 70 | 0.7358 |
| `f649dcc` | MCP config discovery made recursive; 20 findings became possible, 18 correct and unlabelled | 90 | 0.6853 |
| `d4d2850` | AI-tool hook discovery made recursive; 3 findings became possible, all correct and unlabelled | 93 | 0.6782 |
| `2ee8345` | AGENT-034 gated on a tool boundary | 93 | 0.6782 |

Recall rose over the same period, 0.8263 → 0.8305. Publishing "F1 fell from 0.778 to 0.747"
without that paragraph would assert a quality regression that did not happen.

**(b) 67.82% is a floor, not a point estimate, and saying so is the honest version of the
same lesson this document is about.** At least 21 of the 93 false positives are findings
that are correct by their rule's own definition and simply unlabelled (18 MCP + 3
AGENT-120). A further 3 are the AGENT-015 / AGENT-036 double-counts (`AGENT-015_RESOLUTION.md`),
each scored as a false positive *and* a false negative. Correcting only the accounting
already known today gives P 0.6886 / R 0.8432 / F1 0.7581, measured. The corpus is
incomplete, and precision measured against an incomplete corpus reads low.

**The discipline that follows: state it as a bound, do not silently adjust for it.** "P
67.82% measured; at least 21 of the 93 false positives are unlabelled true positives, so
the true precision is higher and the corpus is being repaired" is honest. "P ≈ 75% after
adjustment" is the 98.51% again, in the other direction.

---

## 4. Draft retraction

Plain, one paragraph, no hedging. Adjust the venue-specific wording; do not soften the
middle sentence.

> **Retraction.** We previously reported benchmark results of 98.51% precision, 100%
> recall, 99.25% F1 and a 1.49% false-positive rate for agent-audit's Layer 1 evaluation
> (v0.4.1–v0.5.2, `tests/README.md` and `CHANGELOG.md`). Those figures were not produced by
> our evaluation script. They were computed by taking the number of ground-truth
> annotations as the true-positive count and **setting false negatives to zero rather than
> measuring them**; recall was therefore 100% by construction, and the F1 derived from it is
> arithmetic on a constant rather than a result. The evaluation output committed alongside
> the claim measured 124 false negatives and 47.46% recall on the same corpus. We are
> retracting all four figures rather than updating them, because no re-run can reproduce
> them: they were never a measurement of what they named. The current measured values, from
> `python3 tests/benchmark/precision_recall.py` at version 0.19.2, are **precision 67.82%,
> recall 83.05%, F1 0.747** over 238 labelled annotations in 81 files (TP 196 / FP 93 /
> FN 40). Precision is lower than our later published figure of 73.58% because we fixed two
> file-discovery bugs that caused the scanner to miss findings entirely; the additional
> findings are correct but not yet labelled in our ground truth, so they currently count
> against precision. We regard 67.82% as a lower bound for that reason and are repairing the
> corpus.

Notes on what the draft deliberately does and does not do:

* It names the mechanism in the first three sentences. Burying "false negatives were assumed
  to be zero" below a paragraph of context is how a retraction becomes a correction notice.
* It says **retracting**, not "updating" or "revising", and gives the reason retraction is
  the right verb.
* It quotes the contemporaneous measurement (FN 124, R 47.46%). That is the strongest fact
  available and it is self-incriminating; leaving it out invites the reader to wonder what
  else is missing.
* It restates the current figures **in the same paragraph**, so no reader is left with a
  hole where a number was.
* It explains the precision drop without using it as mitigation. The drop is a real fact
  with a real cause; the cause is stated once and not leaned on.
* It does not apologise, editorialise, or characterise the original as a "typo",
  "oversight" or "legacy artifact". It was a methodology error and the word for it is
  methodology error.
* It claims a lower bound rather than an adjusted number, per § 3(b).

---

## 5. Ordering

The governing constraint: **nothing new should be published on top of a surface that still
carries a retracted figure.** A new release note, blog post or paper that cites current
numbers while `tests/README.md` still says 98.51% invites the reader to discover the
contradiction rather than the correction.

### Must be corrected before anything new is published on top of them

1. **Any external artifact** — paper, preprint, slide deck, outreach message, conference
   submission. **Retract first, restate second, and do not merge the two steps into one
   "updated results" note.** This is the only item where sequencing genuinely matters
   rather than merely being tidy, and it is the only item this document cannot scope, because
   I searched inside the repository only. **The list of external surfaces is Heady's to
   produce, and it is the gating input for everything below.**
2. **`CHANGELOG.md:175-177`** — release notes travel. "Precision: 98.51% → 100%" and "F1
   Score: 100%" are the most quotable form of the error, and a changelog is the document a
   downstream reader trusts to be a factual record. Struck, with a dated retraction note in
   place — not silently deleted, because silent deletion of a published claim is its own
   problem.
3. **`tests/README.md`** — all nine locations plus the corpus description at lines 100–110.
   It is the document that reads as the benchmark's own specification, so a reader
   verifying the claim starts here.

### Next, and in this order

4. **`docs/F1_REPRODUCTION.md`** — a reproduction document that does not reproduce. Its
   0.778 transcript, and the stale CI-gate sentence at line 75. Higher priority than the
   other 0.778 locations despite carrying the same figure, because its subject *is*
   verifiability.
5. **The remaining 0.778 family** (rows 13–18, 21 above; nine locations). Mechanical once
   the wording of the causal note is settled — write the note once, paste it everywhere.
   `docs/index.html` and the two READMEs are the highest-traffic of these.
6. **`packages/audit/pyproject.toml` "53 rules"** — not part of this retraction, but it is
   the only claim of any kind on a distribution surface, and it is unattributable to any set
   at any commit. If a correction pass is being made, it costs nothing to include and it is
   the single most-read line in the project.
7. **The rule counts and version/test-count staleness** — `CLAIMS_RECONCILIATION.md` §§ 3, 7.
   Mechanical, no sequencing constraint.

### Not to be corrected as part of this

* The AVB figures. They are measured against an explicit oracle and are unaffected;
  bundling them into a retraction would imply a defect that is not there.
* The adjusted F1 of 0.84. It is disclosed, bounded and attributed, and `CLAUDE.md` already
  declines to use it as a headline. Leave it exactly as it is — and note that leaving it
  alone is only defensible *because* it is disclosed. That is the standard the retracted
  figures failed.

---

## Related

* `CLAIMS_RECONCILIATION.md` — the full claims table this document draws its locations from
* `NIGHT_RUN_LEDGER.md § W22` — the original trace
* `NIGHT_RUN_LEDGER.md § W25` — the primary-source evidence added here
* `docs/decisions/AGENT-015_RESOLUTION.md` — the corpus-accounting defect behind § 3(b)
* `DECISIONS.md` item 35
