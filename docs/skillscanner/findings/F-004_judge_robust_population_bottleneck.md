# F-004 — v2 judge is robust on every well-formed row it reached; the bottleneck is population size, not judge reliability

**Status:** Phase 2A diagnostic finding (Phase 3 supporting material).
**Recorded:** 2026-06-07.
**Scope:** Observational. The data is the 2A.1 paired-scan output on the
198-row EN+JA SOCIAL_ENG_*-flagged snapshot, plus the silent-verdict
disambiguation run authorized in 2A.1's follow-up.
**Cross-references:** F-001 / F-002 (data-side drift), F-003 (tool-side
reproducibility). F-004 is the *judge-side* counterpart — and lands on
the opposite conclusion from the data and tool findings: the judge is
fine; the *available population* is the problem.

---

## 1. Why this finding exists

The 2A.1 paired scan produced an asymmetric result: SkillScanner emitted
SKILL-010 on 5 rows vs Cisco's 196 SOCIAL_ENG_* on the same 198 bytes.
That asymmetry could mean **either** (a) SkillScanner's Layer-1
frontmatter filter is doing nearly all the work and the judge barely
runs, **or** (b) the judge is unstable and abstains on a lot of rows.
Telling these apart matters: (a) supports sourcing more real Skills to
exercise the judge; (b) would imply re-opening the frozen v2 prompt.
F-004 records which one is observed.

## 2. Observed (every cell is a count, not an estimate)

The v2 judge ran on 18 rows in 2A.1 (14 EN + 4 JA — the rows where
SkillScanner's Layer 1 + Layer 3 routing actually invoked
`SemanticJudge`). The 2A.1 main run persisted only the **vague**
verdicts (the only verdict that produces a SKILL-010 emit). The silent
rows (everything that resolved to either `clear` or `cannot_judge`)
were re-judged in the authorized 12-call disambiguation. One row was
excluded from re-judging because its description carries lone
surrogates that break the cache-key encoding entirely — see F-005.

Complete per-row verdict picture across the 18 judged-or-errored rows:

| Lang | `vague` | `clear` | `cannot_judge` | error (surrogates) | Total reached judge |
|---|---:|---:|---:|---:|---:|
| EN | 4 | 9 | 0 | 1 | 14 |
| JA | 1 | 3 | 0 | 0 | 4 |
| **All** | **5** | **12** | **0** | **1** | **18** |

The judge produced **zero `cannot_judge` verdicts** across all 17
well-formed inputs. Every JA input that reached the judge received a
substantive verdict; every EN input the same. The model returned strict
JSON parseable by `_parse_verdict_json` on every call — no
fallback-to-`cannot_judge` was needed for output-format reasons either.

## 3. The bottleneck is upstream, not in the judge

Of the 198 in-snapshot rows, the cascade by stage is:

| Stage | Rows leaving the stage | Cumulative routed-out |
|---|---:|---:|
| Snapshot (Cisco-flagged universe, EN+JA) | 198 | — |
| Layer 1 (frontmatter validation): 166 routed to SKILL-000, 0 to behavioral | 32 | 166 |
| Pre-judge: 12 fm-but-empty-description, 2 fm-but-unsupported-lang | 18 | 180 |
| Layer 3 (semantic judge): reaches the API | 18 | 180 |

166 of 198 rows (84 %) are routed out by Layer 1 alone — the
language-agnostic frontmatter contamination filter that the F-002
survey already showed is the dominant filtering signal in this
snapshot. The judge sees 18 rows total. With ZERO `cannot_judge`
verdicts in that 18, *the judge cannot be the reason population sample
sizes are small*. The judge would be just as reliable on 18 × 100 rows
if Layer 1 + the supported-language gate let that many through.

## 4. What this implies for the eval design

- **Contribution 1 (Layer 1 contamination filter, language-agnostic)**
  is doing the bulk of the SkillScanner-vs-Cisco-emission-rate work on
  any Cisco-flagged subset. Reporting it as a separately-powered
  finding (per Phase 2A's branch-3 design) lets the contribution be
  evaluated on its merits without competing for sample budget with
  the judge claim.
- **Contribution 2 (Layer-3 semantic judge, cross-lingual fairness)**
  needs a sample pool of *real Skills that reach the judge*. The
  pool is upstream-bounded by FM-presence + supported-language +
  non-empty-description, not by judge reliability. **Sourcing more
  real Skills is the correct action; doubting the judge is not.**
- The v2 freeze (frozen tag `skillscanner-core-frozen`,
  `JUDGE_PROMPT_V2` sha256 `a40bc2…7816e56f`, model
  `claude-sonnet-4-6`) is **further validated** by this observation,
  not weakened: on 17/17 well-formed inputs the judge produced a
  substantive verdict.

## 5. What this finding does NOT say

- Not that the judge has 0% `cannot_judge` rate in general. The
  observed 0/17 is a small sample. A 95% Wilson upper bound on
  P(cannot_judge | well-formed input) at 0/17 is ~18%. The point of
  F-004 is not the rate; it's that no judge-stability problem is
  *manifest* in the data we have, so the eval design should not be
  reorganized to compensate for one.
- Not a precision claim. F-004 is a robustness observation, not a
  TP/FP observation. Human-annotated precision is reserved for 2A.3
  per PROTOCOL Pass B.
- Not a claim that the EN/JA verdicts are *correct*. F-004 records
  that they were produced; the rubric-correctness of each verdict is
  the annotators' to decide.

## 6. Reproducibility

```bash
# Re-derive the cascade counts and verdict table from the local snapshot
# (no API spend; reads only).
poetry --directory=packages/audit run python <<'PY'
import json
from pathlib import Path
R = Path('/Users/heady/Documents/agent-audit/agent-security-suite/eval/snapshot/private')
disambig = json.load(open(R/'silent_verdict_disambig.json'))
ss = json.load(open(R/'skillscanner_results.json'))['results']
mani = json.load(open(R/'manifest.json'))
from collections import Counter
# Map row_id → recorded verdict (vague from the SS run; clear/cannot_judge from disambig)
verdict_map = {}
for rid, rec in ss.items():
    for f in rec.get('findings', []):
        if f['rule_id'] == 'SKILL-010':
            verdict_map[rid] = ('vague', rec.get('language'))
for d in disambig['rows']:
    verdict_map[d['row_id']] = (d['verdict'], d['language'])
print(Counter((lang, v) for v,lang in verdict_map.values()))
PY
```

## 7. Phase 3 framing note

The bottleneck observation is itself paper-relevant: even if Phase 2A
shows the v2 judge meets every fairness criterion, the *practical*
deployment of any cross-lingual Skills scanner has to contend with
the same population-availability constraint we hit. Real
non-English Skills are scarce in the public ecosystem; the F-002
+ F-004 combination quantifies how scarce they are even within a
multilingually-curated corpus. That qualifies any precision claim
the Phase 3 paper makes by noting "this is what's achievable on the
sample available, and the sample size limits the per-language
statistical resolution."
