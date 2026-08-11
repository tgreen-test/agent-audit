# F-006 — The out-of-universe `fm_present` pool shows a 43 % 404 rate at origin, ~3× the SOCIAL_ENG-flagged subset's rate

**Status:** Phase 2A observational finding (Phase 3 ecosystem-
reproducibility supporting material). **Observed fact only; both
candidate interpretations recorded as undetermined; no inference
chosen.**
**Recorded:** 2026-06-07.
**Cross-references:** F-001 (single-Skill anchor case), F-002
(70-row SOCIAL_ENG-flagged JA drift survey), F-003 (Cisco-tool
unavailability), F-004 (judge robustness on well-formed input),
F-005 (input-sanitization gap). F-006 extends the data-side drift
picture from F-001/F-002 onto a *different* corpus subset and
records that the drift signature differs across subsets.

---

## 1. Why this finding exists

The Phase 1 F-002 survey measured drift on the 70-row JA SOCIAL_ENG-
flagged subset and recorded a 14 % HTTP 404 rate on origin fetches.
The Phase 2A multilingual confirm fetch (2026-06-07) measured drift
on a *disjoint* corpus subset — the OOU `fm_present` pool, rows
Cisco did **not** behavioral-flag historically and which had a
parseable manifest at collection. The two subsets are partitioned
by Cisco's collection-time flag. F-006 records that the 404 rates
on the two subsets are very different and lists what can and
cannot be said from one such observation.

## 2. Observed (raw counts, two subsets, both reachable today)

### 2.1 SOCIAL_ENG-flagged subset (2A.0 snapshot, fetched 2026-06-06)

| Lang | Universe | 404 | 404 rate |
|---|---:|---:|---:|
| EN | 157 | 20 | 12.7 % |
| JA | 71 | 10 | 14.1 % |
| **All (EN+JA)** | **228** | **30** | **13.2 %** |

### 2.2 Out-of-universe `fm_present` subset (multilingual confirm fetch, 2026-06-07)

| Lang | Universe | 404 | 404 rate |
|---|---:|---:|---:|
| EN | 2,213 | 1,076 | 48.6 % |
| JA | 148 | 23 | 15.5 % |
| ZH | 244 | 50 | 20.5 % |
| KO | 85 | 8 | 9.4 % |
| **All (EN+JA+ZH+KO)** | **2,690** | **1,157** | **43.0 %** |

### 2.3 Side-by-side contrast (the F-006 observation)

| Subset | 404 rate (all langs combined) | Notes |
|---|---:|---|
| SOCIAL_ENG-flagged | 13.2 % | Cisco behavior-flagged at collection |
| OOU `fm_present` | **43.0 %** | Cisco did NOT behavior-flag; manifest parsed at collection |

The OOU subset's 404 rate is ~**3.3×** the SOCIAL_ENG-flagged subset's
rate. The contrast is driven mostly by EN (48.6 % vs 12.7 %). JA's
two subsets differ by only ~1 percentage point (15.5 % vs 14.1 %);
ZH and KO have no comparable SOCIAL_ENG-flagged measurement on this
sample-fetch basis (we did not fetch their SOCIAL_ENG-flagged
universe).

### 2.4 What we know about the OOU pool's character (non-causal context)

- The OOU pool was selected by Cisco's *historical* behavioral
  rule firing or not firing. SOCIAL_ENG_VAGUE_DESCRIPTION fires on
  short descriptions; rows that escaped it had longer descriptions
  at collection time.
- The OOU pool's MANIFEST_MISSING_LICENSE filter further restricts
  it to rows whose manifest Cisco parsed successfully — i.e.
  collection-time `fm_present` rows.
- The OOU pool spans 1,380 distinct repositories (per the corpus
  README's repo count). The SOCIAL_ENG-flagged subset overlaps
  with these repositories but is much smaller.
- The corpus README states the corpus was collected over a fixed
  window in early 2026; the OOU pool and the SOCIAL_ENG-flagged
  pool share the same collection window.

## 3. Two candidate interpretations, both recorded as undetermined

**The data does not let us choose between these two readings.**
F-006 records both and chooses neither.

### Interpretation A — "author-unrelated churn"

Files in the OOU pool may have been deleted at higher rates than
the SOCIAL_ENG-flagged pool for reasons unrelated to either tool's
behavior. Possible mechanisms include: personal portfolio
maintenance (deletion of one-off scripts), repository
reorganizations (moves that break `HEAD` resolution), corporate
policy migrations (consolidation of `SKILL.md` files into
private internal stores), or stochastic ecosystem churn that
just happens to have produced different per-subset rates on this
single survey date.

**Why undetermined:** the corpus does not record per-row
deletion-event evidence; per-author intent is not visible from
file presence alone; a single 2026-06-07 snapshot cannot
distinguish churn from a directed cause.

### Interpretation B — "older / more abandoned OOU pool"

Files in the OOU pool may, on average, have been *older* at
collection time than the SOCIAL_ENG-flagged pool (because
verbose, long-description Skills are typically more mature
artifacts that have had time to be elaborated). Older files are
more likely to have been abandoned, archived, or removed by the
time of a later origin survey. The 43 % 404 rate then reflects an
**age-correlated deletion process** rather than any
tool-influenced behavior.

**Why undetermined:** the corpus metadata records collection
date per row but not author-side last-edit date or file age;
without per-row age data, the age-correlation hypothesis cannot
be directly tested. A Phase 3 follow-up survey that fetched
GitHub commit history per surviving row could test this, but is
out of F-006's scope.

### Interpretations *not* chosen here

- We do **not** claim Cisco's behavioral flag caused authors to
  delete files (that would be the F-001 motif extended to a
  *different* population, which F-001's softening in §3 already
  cautioned against generalizing from one anchor case).
- We do **not** claim SkillScanner's behavior had any effect —
  SkillScanner did not yet exist when the corpus was collected
  and has never run on these rows publicly.
- We do **not** claim the 404 rate is climbing over time — F-006
  is a single dated snapshot, not a longitudinal measurement.

## 4. Why F-006 matters for Phase 3

The F-001 / F-002 / F-003 / F-006 sequence shows:

| Reproducibility surface | Status at 2026-06-07 |
|---|---|
| F-001 | One anchor case shows author-driven structural change (frontmatter deleted) on a SOCIAL_ENG-flagged JA row. |
| F-002 | Corpus-wide drift on SOCIAL_ENG-flagged JA subset: 14 % 404, 63 % no-FM today. |
| F-003 | Cisco-tool reproducibility decayed publicly; local copy recovers it. |
| F-006 | On a *disjoint* corpus subset (OOU `fm_present`), 404 rate is **3.3× higher** in aggregate. |

This is consistent with a *general* claim that public Skills
ecosystem state at 2026-06-07 is substantially degraded from its
state in early 2026 when the corpus was collected — independent of
any cause-and-effect about behavioral flags. The aggregate
ecosystem-reproducibility surface is the Phase 3 talking point
F-006 supports.

What F-006 does **not** support is a specific causal claim about
*why* the OOU pool degrades faster than the SOCIAL_ENG-flagged
pool. That would require longitudinal per-row commit-history data
which we do not have.

## 5. Effect on Phase 2A sampling

The 43 % OOU 404 rate was absorbed before the eval-side sampling
was decided. The judge-eligible pool sizes after the 404 filter are
already in hand:

| Lang | OOU `fm_present` total | 404 | **judge-eligible today** |
|---|---:|---:|---:|
| EN | 2,213 | 1,076 | 1,118 |
| JA | 148 | 23 | **125** |
| ZH | 244 | 50 | 192 |
| KO | 85 | 8 | 77 |

All four languages clear PROTOCOL Pass B's N ≥ 20 floor with real
headroom. The user's sample-size decision (N = 50 EN/JA/ZH; N ≤ 40
KO) is well-supported. F-006 is **not** a blocker for the eval; it
is a *finding* the eval surfaces as a side-effect.

## 6. Reproducibility

```bash
# F-006 §2.1 — SOCIAL_ENG-flagged 404 rate (data is in eval/snapshot/private/manifest.json):
poetry --directory=packages/audit run python <<'PY'
import json
m = json.load(open('eval/snapshot/private/manifest.json'))
from collections import Counter
c = Counter((r['language'], r['match_class']) for r in m['rows'])
print({k:v for k,v in c.items() if k[1]=='404'})
PY

# F-006 §2.2 — OOU fm_present 404 rate (data in eval/snapshot/private/manifest_oou.json):
poetry --directory=packages/audit run python <<'PY'
import json
m = json.load(open('eval/snapshot/private/manifest_oou.json'))
from collections import Counter
c = Counter((r['language'], r['match_class']) for r in m['rows'])
print({k:v for k,v in c.items() if k[1]=='404'})
PY
```

The 2026-06-07 snapshot date is locked. Anyone re-running on a later
date will see further drift; the 43 % rate is a dated point, not a
permanent value.

## 7. What this finding is NOT

- Not a SkillScanner detection. F-006 is an ecosystem
  measurement, not a code-pattern emit.
- Not a freeze-invariant change. The `skillscanner-core-frozen`
  tag's invariants are unaffected by F-006.
- Not a competitor to F-001 / F-002. The data-side findings stack
  cumulatively; F-006 widens the observation surface without
  contradicting any of them.
- Not the basis for the fairness claim. The fairness claim is
  carried by Claim 2 in
  `docs/skillscanner/design/PHASE2A_TARGET_FRAMING.md`; F-006 is
  Discussion-section ecosystem material, not Results-section
  material.
