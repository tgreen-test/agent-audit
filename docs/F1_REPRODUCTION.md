# Reproducing F1 (v0.20.0)

> **RETRACTION NOTE (2026-05, revised 2026-09-12).** Earlier versions of public docs
> reported an adjusted F1 of 0.842, derived by excluding raw false positives from post-v0.16
> rules that the ground truth does not yet label. Public docs now report the **raw** F1, so
> that every headline figure is directly reproducible from the included script.
>
> Two things in the original note were wrong by the time you are reading it, and both are
> corrected above rather than left to be inferred: the raw figure is **0.7581**, not the
> 0.778 this note used to name, and the adjusted figure is **not** merely deferred to
> GT v2.3 — it is not published at all. `docs/decisions/METRICS_RETRACTION.md` § 3(b) states
> the corpus incompleteness as a bound on the raw figure instead, because adjusting one side
> of a ratio to compensate for an incomplete corpus is the same move this project retracted.
> The derivation is kept below as a record of where 0.842 came from.

## TL;DR

The current **headline F1 = 0.7581** (raw, reproducible, v0.20.0) used in `README.md`, `README_CN.md`, `COMPETITIVE-COMPARISON.md`, `BENCHMARK-RESULTS.md`, `CLAUDE.md`, and `docs/index.html` is produced directly by **`tests/benchmark/precision_recall.py`** against the ground-truth file **`tests/ground_truth/labeled_samples.yaml`** (v2.2, 2026-02-04). The historical adjusted F1 of 0.842 — derived post-hoc by excluding FPs from rules added after v0.16 — is documented below for full transparency but is no longer cited as a headline figure.

## Test set

| Field | Value |
|---|---|
| GT file | `agent-security-suite/tests/ground_truth/labeled_samples.yaml` |
| GT version | v2.2 (2026-02-04) |
| Sample files | **81** |
| Total labels | 238 (236 positive, 2 negative; 12 of the 81 files are safe-files with no vulns) |
| Header field | `total_vulnerabilities: 238` (matches on-disk count post-D-C reconciliation; was 218 pre-reconciliation) |
| Fixtures scanned | `agent-security-suite/tests/fixtures/` |

## Reproduce

```bash
cd agent-security-suite
python3 tests/benchmark/precision_recall.py --output-json /tmp/pr.json
```

The script runs `agent-audit scan tests/fixtures --format json`, parses findings, and matches them to GT keys `(file, line, rule_id)` with a 3-line tolerance.

### Raw output, agent-audit 0.20.0

```
$ python3 tests/benchmark/precision_recall.py
True Positives:  199
False Positives: 90
False Negatives: 37
Precision: 68.86%   Recall: 84.32%   F1: 75.81%   FP Rate: 31.14%
```

Raw F1 **0.7581**, measured at v0.20.0.

> **The heading above used to read "reproduced on 2026-05-31 (agent-audit 0.19.0)" over
> this block.** The numbers in it are the v0.20.0 ones, so the attribution dated a current
> measurement to a superseded release — in the one document whose entire claim is that the
> headline reproduces. The block now names the command that produces it, which is also what
> puts it inside `tests/test_published_metrics.py`.

> **Superseding the 0.778 this section used to print.** Precision fell from 73.58% and
> recall rose from 82.63% between v0.19.0 and v0.20.0, and the cause is not a detection
> regression. Two file-discovery bugs were fixed (`f649dcc`, MCP configuration discovery;
> and `package_scanner._scan_ai_tool_hooks`), which made previously unreachable findings
> possible. Most of them are correct by their rules' own definitions and the corpus does
> not label them, so they count against precision. Quoting the F1 movement without this
> paragraph asserts a quality regression that did not happen. See
> `docs/decisions/METRICS_RETRACTION.md` § 3(a).

## Where "0.842" came from, and why it is not reproduced here

**This section is a record of a v0.19.0 derivation. It is not a current figure, and nothing
below is recomputed against the current run on purpose.**

`precision_recall.py` has never computed an adjusted figure. The adjustment described in
older READMEs — "excludes findings from 18 new rules added since v0.16 that have not yet
been labeled in GT" — was applied by hand afterwards, by subtracting false positives whose
`rule_id` fell in the ranges added after v0.16 (AGENT-053+, AGENT-058–064, AGENT-110–119).

At v0.19.0 the raw run had **70** false positives, 40 of them from those ranges:

| cutoff | FPs excluded | TP | FP (adj) | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|
| ≥ AGENT-053 | 40 | 195 | 30 | 41 | 86.67% | 82.63% | **0.846** |
| ≥ AGENT-054 | 37 | 195 | 33 | 41 | 85.53% | 82.63% | **0.840** |

The published 0.842 falls between those two. Every input to that table — 70, 40, TP 195,
FN 41 — belongs to the v0.19.0 run and none of them is the current measurement.

**The adjustment is not carried forward, and that is a decision rather than an oversight.**
Subtracting false positives because the corpus has not labelled them yet is the same
*shape* of move as setting false negatives to zero: a correction applied to one side of a
ratio to compensate for an incomplete corpus. That is the mechanism
`docs/decisions/METRICS_RETRACTION.md` exists to document. § 3(b) sets out what replaces it
— state the incompleteness as a **bound** on the raw figure, and let the raw figure be the
headline:

> P 68.86% measured; at least 21 of the 90 false positives are correct by their own rule's
> definition and simply unlabelled, so the true precision is higher and the corpus is being
> repaired.

`CLAUDE.md` says the same in one line: **no adjusted figure is published.**

## False positives by rule, current run

Reproducible, and the command is the point:

```bash
python3 - <<'EOF'
import collections, json, re
d = json.load(open("results/layer1.json"))
c = collections.Counter(re.search(r"AGENT-\d+", s).group(0) for s in d["fp_details"])
print(sum(c.values()), "false positives across", len(c), "rules")
for rule, n in c.most_common():
    print(f"  {rule}  {n}")
EOF
```

90 false positives across 32 rules. The ten largest:

| rule | FPs | | rule | FPs |
|---|---:|---|---|---:|
| AGENT-004 | 7 | | AGENT-026 | 4 |
| AGENT-034 | 7 | | AGENT-058 | 4 |
| AGENT-116 | 6 | | AGENT-059 | 4 |
| AGENT-030 | 5 | | AGENT-114 | 4 |
| AGENT-032 | 5 | | AGENT-001 | 3 |
| AGENT-047 | 5 | | AGENT-053 | 3 |

Split by era: **46** from rules predating v0.16, **44** from AGENT-053 and later. The table
this section replaced was the 2026-05-31 breakdown of a 70-FP run, still headed "raw run"
with no version attached.

## Bottom line

- **Raw F1 0.7581**: fully reproducible, run the script. This is the headline, and the only
  F1 this project publishes.
- **Adjusted F1 0.842**: **not a current figure and not a published one.** It was derived
  once, at v0.19.0, from inputs that no longer exist (70 false positives, TP 195, FN 41).
  What replaces it is a bound on the raw number, not a different number — § 3(b) of
  `docs/decisions/METRICS_RETRACTION.md`. The line that stood here called it "reproducible
  within ±0.004", which invited exactly the re-derivation the retraction rules out.
- **There is no CI gate inside `precision_recall.py`.** This document previously said
  one was "set at `f1 < 0.75` (line 485) — passes today". Three things were wrong with
  that sentence: the line number was already stale, the gate was *failing* rather than
  passing at the time it was written, and the gate itself was deleted at `78d8fe5` because
  it was a second Layer 1 floor competing with `tests/benchmark/gates.yaml`. The floor now
  lives in exactly one place and is evaluated by `quality_gate_check.py`. Verify with
  `python3 -m pytest tests/test_layer1_gate_singleton.py -q`.
