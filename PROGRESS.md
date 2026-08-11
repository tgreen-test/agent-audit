# PROGRESS

**Session 5 state: COMPLETE. W19–W22 all done and committed.** Read `RUN5_REPORT.md`
first (one page), then `CLAIMS_RECONCILIATION.md`.

**The advertised rule set is now a measured quantity: 66, not 72.** Six rules could not
fire on any input at any commit; a seventh could not be reached below the scan root.
Every one of the 66 has a producer and a demonstration that it fires, and
`tests/test_rule_producers.py` fails the suite — with no allow-list — if that stops
being true.

**Noise 87 → 44 = 2.2:1** against a ≤5:1 target, from wiring the TypeScript
tool-boundary gate. All 20 high-value findings intact, Layer 1 true positives unchanged
at 196, AVB unchanged, no threshold touched.

Next session starts at **`DECISIONS.md` item 31, because CI is red** — not through
anything detection-related. Then item 30 (does `eval` outside a tool handler count?).

## Current commit

`fix/py314-blocker`. Five commits this session plus one revert:

| sha | W | what |
|---|---|---|
| `d4d2850` | W19 | AI-tool hook discovery joined onto the scan root; AGENT-120 could not fire below it |
| `6adedd1` | W19 | six unproducible rules withdrawn, 72 → 66, each with a stated reason |
| `2ee8345` | W20 | AGENT-034 gated on a tool entry point (noise 87 → 44) |
| `3f52f90` | W21 | scratch: flag-gated `RuleEngine.evaluate()` wiring, for measurement |
| `25636c3` | W21 | revert of the scratch commit |
| — | W22 | `CLAIMS_RECONCILIATION.md`, RUN5 report, ledger, decisions |

## Invariants at `25636c3`

| invariant | result |
|---|---|
| noise / high-value | **44 / 20 = 2.2:1** |
| recall on the target | **0/6, unchanged both directions** |
| AVB knowns | **R 100.0% / P 88.0% / F1 0.9362, unchanged** |
| Layer 1 | **TP 196 / FP 93 / FN 40**, P 0.6782 / R 0.8305 / F1 0.7467 |
| `quality_gate_check.py` | **exit 0** (ratchet 0.66 untouched) |
| `precision_recall.py` | **exit 1** — its own hard-coded F1 < 0.75 floor, DECISIONS 31 |
| full suite | **1748 passed, 1 skipped** (1731 at RUN4 + 17) |
| advertised rules | **66**, all with a producer and a firing demonstration |

## The four things a reader needs

1. **Two of RUN4's four defects are one defect.** Five of the six rules with "no
   producer" have their detection written out in full as YAML `detection.patterns`
   blocks — in the place `CLAUDE.md` tells contributors to write it — and the only code
   that could run one is `RuleEngine.evaluate()`, which nothing calls. And it could not
   have run them anyway: **81 of 84 pattern entries use a key (`pattern_type`) that the
   evaluator never reads.**
2. **CI is red, and not for a detection reason.** `precision_recall.py:503` carries its
   own `f1 < 0.75 → sys.exit(1)`, while `gates.yaml` — which calls itself the single
   source of truth — carries 0.72. Two blocking gates on one layer, the exact
   contradiction `gates.yaml`'s header says was eliminated. F1 is 0.7467. Before this
   run it was 0.7510, one thousandth above the floor. **No threshold was touched.**
3. **The gate costs seven findings, one at BLOCK.** Wiring the TypeScript tool boundary
   silences `return eval(expr)` at confidence 0.95 because it sits outside a tool
   handler. Narrowing the gate to shell execution is one line; it is a rule-scope
   decision, so it is DECISIONS 30 and not something I nudged.
4. **`tests/README.md`'s 98.51% is not a stale measurement — it is not a measurement.**
   TP = the annotation count, FP = 3, **FN assumed zero**. Reproduces all four published
   figures to four decimal places. The results file committed alongside it measured
   FN = 124.

## What is canonical, established this run

**66 rules** for a default scan, 86 including `--profile defi`. `RULE_CWE_MAPPING` minus
DeFi is set-equal to `docs/RULES.md` and both guards assert it. Of the 66: **12 have no
fixture anywhere** (they fire only on hand-built triggers recorded in the ledger), and
**1 (AGENT-054) is reachable only via `agent-audit inspect`**, now disclosed in
`docs/RULES.md`.

Eight different rule counts are published across the repo — 66 / 72 / 92 / 63 / 53 / 52 /
49 / 40+. `53` is the **PyPI description** and matches no set at any commit.

## Environment

Unchanged from sessions 1–4. Harness at `/Users/heady/Documents/Research/audit-harness/`,
outside the repo. `python` is NOT on PATH — use `python3`. Session 5 added nothing outside
the repo.

## Guard-hook friction worth knowing

Unchanged. It fired once this session, on a `grep` naming `tests/ground_truth/` for a
read-only lookup. Workaround as before: write the script with the Write tool and run it
with `python3`. Not changed — the false-positive direction is the safe one for a guard.
