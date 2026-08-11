# PROGRESS

**Session 2 state: COMPLETE. W6 through W9 done. Verdict is GO for P0A. Did not start
P0A denoise, as instructed.**

Read `SESSION2_REPORT.md` first (one page), then `NIGHT_RUN_LEDGER.md` § SESSION 2 for
evidence, then `DECISIONS.md` for the five `NEEDS-HEADY` items.
`NIGHT_RUN_REPORT.md` (session 1) is partly superseded and carries a banner saying so.

## The answer

**The 0/6 is real — a capability gap, not a broken environment.** Identical
`recall_hit 0 / noise 1156 / total 1176` at `1009782`, `78e1337`, and HEAD, and on both
Python 3.11.14 and 3.14.3. The blind run used the 0.19.2 working tree in a fresh venv
(recorded in the frozen JSON's `version` field and the run manifest), never the stale
0.18.2. Session 1's fixes change a 3.14 crash into a complete scan that finds exactly the
same nothing.

## Where things stand

Branch `fix/py314-blocker`. Session 1 added 6 commits on `78e1337`; session 2 adds
documentation and `.gitignore` only — no scanner, rule, gate, label, or fixture touched.

The eval harness lives **outside the repository** (sibling to the frozen evaluation data)
and is gitignored defensively inside it. One command:

```
./run_eval.sh --frozen            # validation: reproduces the frozen baseline exactly
./run_eval.sh --commit <sha>      # scan the target at any tool commit and score
./run_eval.sh --commit <sha> --python python3.14 --verbose
```

Last stdout line is always
`{"recall_hit":N,"recall_total":6,"noise":N,"total":N,"commit":"sha","python":"ver"}`.

## What P0A will be judged on

`./run_eval.sh --commit <sha>` → **noise < 118** (10% of 1176), with **recall still 0/6**
and AVB knowns recall not falling from R 100.0% / P 88.0%.

Caveat that matters: the noise metric encodes a one-time manual bucketing, so it is an
upper bound on any commit but the frozen one. Fit for P0A; must be re-adjudicated before
P1. See DECISIONS.md item 8.

## Blocking item

**Settle DECISIONS.md item 1 (the Layer 1 gate contradiction) before P0A lands.** The
forensics are now conclusive: the v2 gate has never been able to fail a build and its
thresholds were never met, not even on the day they were written. P0A's acceptance is a
threshold judgement and cannot be made against two definitions of pass.

## Environment changes (unchanged from session 1, plus)

Session 1's list is in `DECISIONS.md` § "Environment changes made outside the repo".
Session 2 added only: a dependency-only venv per interpreter and `git archive` extractions
under the harness directory, all outside the repo. Nothing under `eval/` was touched, and
agent-audit was never reinstalled, so the stale 0.18.2 evidence is preserved.
