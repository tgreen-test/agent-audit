# Phase 2A Pre-Registration

> **STATUS: LOCKED ON COMMIT.** No precision / κ / TP-FP / TOST
> computation may proceed until human annotation labels have
> returned. The criterion in §6 is locked at this commit: it cannot
> be edited, weakened, or reframed in response to results. Edits
> after this commit require a separate, dated amendment file
> documenting the change and the reason; the original criterion
> remains in git history as the immutable record.

**Recorded:** 2026-06-07.
**Scope:** Phase 2A of the SkillScanner project.
**Frozen base:** `skillscanner-core-frozen` →
`05c3f98855413091f6671bb0acbd4281a59ae37d`. This pre-registration
operates *against* that tag; the frozen scanner / judge / schema /
prompt code is not modified.
**Companion documents:**
[PROTOCOL §3 / §4]
(./PROTOCOL.md) (definitions of Pass B, statistical machinery, success
metric anchors); [target framing](../design/PHASE2A_TARGET_FRAMING.md)
(operational design); F-004 (judge robustness), F-006 (OOU pool
character), [Phase 1 freeze tag annotation]
(git tag -n9 skillscanner-core-frozen).

---

## 1. What this pre-registration is, in one paragraph

The Phase 2A evaluation tests whether the v2 frozen judge has a
**language-correlated false-positive bias** on real, frontmatter-
bearing Skills — the bias the AgentSkills '26 poster documented for
Cisco Skill Scanner v2.0.9 (JA `SOCIAL_ENG_VAGUE_DESCRIPTION` 31.7 %
vs EN 6.1 %). The PRIMARY result is the test of that hypothesis on
SkillScanner alone. The Cisco "before" baseline is **cited from the
published poster, not re-derived**, for the reproducibility reason in
§4. A SECONDARY case-study set is preserved on the small head-to-head
sub-population where both tools touched the same identity-locked
rows; it is qualitative and is not a statistical claim. The
NEGATIVE-RESULT clause in §9 binds us to report honestly if the
hypothesis fails.

---

## 2. Sub-populations (locked here; both originate in the
   2026-06-07 snapshot in `eval/snapshot/private/`)

### 2.1 PRIMARY population — "OOU sample"

- **Frame:** corpus rows with `language ∈ {EN, JA, ZH, KO}` that were
  **not** in the SOCIAL_ENG_* universe historically (Cisco
  collection-time SOCIAL_ENG_* did not fire), AND had collection-time
  `MANIFEST_MISSING_LICENSE` firing (proxy for "Cisco parsed the
  manifest at collection time" = `fm_present`).
- **Today-filter:** the bytes at origin on 2026-06-07 pass
  SkillScanner's strict frontmatter parse, have a non-empty
  `description`, and the description's detected language is in
  `SUPPORTED_LANGUAGES`.
- **Confirmed pool sizes:** EN 1,118, JA 125, ZH 192, KO 77.
- **Sample sizes (LOCKED here):** EN 50, JA 50, ZH 50, KO 40.
- **Stratification (LOCKED here):** all MATCH judge-eligible rows
  taken first; the remainder filled from a fixed-seed shuffle of
  the DRIFT judge-eligible pool.
- **Seed (LOCKED here):** `0xFA1F1E55` (4,196,244,053).
- **Sample composition (LOCKED here):** EN 50 = 36 MATCH + 14 DRIFT;
  JA 50 = 2 MATCH + 48 DRIFT; ZH 50 = 9 MATCH + 41 DRIFT; KO 40 = 1
  MATCH + 39 DRIFT.
- **Sample manifest:** `eval/snapshot/private/sample_manifest.json`
  (gitignored; bytes also gitignored under
  `eval/snapshot/private/bytes_oou/{LANG}/`).

### 2.2 SECONDARY population — "SOCIAL_ENG head-to-head case-study set"

- **Frame:** the 18 rows from the 2A.0/2A.1 SOCIAL_ENG-flagged
  snapshot that reached the v2 semantic judge — i.e., bytes pinned
  to the corpus row's identity-locked or paired-fresh state, AND
  passed SkillScanner's strict frontmatter + non-empty-description
  + supported-language gates.
- **Composition:** EN 14 (4 vague + 9 clear + 1 surrogate-error;
  see F-005), JA 4 (1 vague + 3 clear). All judge-reached EN/JA
  cases on the in-universe pool.
- **Use (LOCKED here):** *qualitative case studies only.* Each row
  receives a native-speaker label per the same annotation
  instrument as the PRIMARY sample. We report whether the
  SkillScanner verdict (vague | clear) agreed with the native
  speaker's judgment, **as individual cases**, not as a precision
  estimate. No Wilson CI, no Fisher's exact, no Bonferroni
  computed on this sub-population. The reason is power: at
  JA n = 4, no statistic is informative; reporting one would
  misrepresent confidence.

### 2.3 Populations explicitly NOT in scope for Phase 2A

- The full corpus's vague-rate per language on bytes today.
  (Out-of-scope reason: drift contaminates a re-derivation; the
  poster's published Cisco gap is the only Cisco "before" we
  cite — see §4.)
- The general SkillScanner false-negative rate. (Out-of-scope
  reason: the fairness claim is about false positives, not
  recall.)

---

## 3. Tools and frozen scope

| Tool | Pinning | Code path |
|---|---|---|
| Cisco Skill Scanner v2.0.9 | Locally-installed `cisco-ai-skill-scanner 2.0.9` at `/opt/homebrew/lib/python3.14/site-packages/skill_scanner/` (Author: Cisco, License: Apache-2.0). PyPI absent as of 2026-06-07; provenance F-003. | `skill_scanner.core.scanner.SkillScanner()` default constructor + `scan_skill(tmp_dir, lenient=True)`; mirrors corpus-production `run_cisco_fast.py` exactly. |
| SkillScanner (this project) | `skillscanner-core-frozen` → `05c3f98855413091f6671bb0acbd4281a59ae37d`. `JUDGE_MODEL = "claude-sonnet-4-6"`, `JUDGE_TEMPERATURE = 0`, `JUDGE_MAX_TOKENS = 300`, `JUDGE_PROMPT_VERSION = "v2"`, `JUDGE_PROMPT_V2` sha256 `a40bc2194c409eecdf7af43c884ef1ffc1adea85f655b9c4660550087816e56f`. | `agent_audit.scanners.skill_scanner.SkillScanner(judge=SemanticJudge())` per row via the tempfile / `SKILL.md` pattern. |

Both tools have already run on the PRIMARY sample (see
`eval/snapshot/private/cisco_oou_sample.json` and
`skillscanner_oou_sample.json`). The vague-rate numbers (Cisco 0/0/0/0,
SkillScanner 5/1/5/3 over EN/JA/ZH/KO) are visible **before this
pre-registration is signed off** — a deliberate ordering trade-off
described in §10.

---

## 4. The Cisco baseline — cited, not re-derived

The Cisco non-English over-flag is **cited from the AgentSkills '26
poster** (Zhang, Yuan, Nian, Zhao 2026):

> "Code-level security findings affect 2.3 % of Skills with no
> significant cross-lingual difference. Behavioral flags are 3–5×
> higher for non-English Skills (p < 0.001, Bonferroni-corrected).
> Manual precision: EN behavioral precision 10 %, JA behavioral
> precision 0 %."

The poster's headline Cisco gap is approximately **JA
SOCIAL_ENG_VAGUE_DESCRIPTION 31.7 % vs EN 6.1 %** on the
collection-time full corpus (3,656 Skills).

**Why we do not re-derive it on today's bytes:**

1. **Drift contamination.** F-001 / F-002 / F-006 document that the
   corpus has drifted substantially since collection. A fresh
   Cisco-on-today's-bytes gap could *change* relative to the
   poster's number for drift reasons unrelated to Cisco's behavior,
   creating reader confusion ("which Cisco gap is the real one?").
2. **The poster's number is already trustworthy on its own terms.**
   It was measured on the collection-time corpus by the corpus
   author, peer-reviewed by the AgentSkills '26 workshop, and
   published. We are not adding evidential strength by re-running
   it on drifted bytes.
3. **The fairness claim does not require the Cisco gap to be
   re-measured today.** The claim is that *SkillScanner does not
   reproduce that gap.* For that claim, we need SkillScanner's
   per-language vague-rate + precision on the OOU sample;
   Cisco's gap is the contrast we cite.

The poster's number appears in the Results table as a cited reference
row labeled `(cited; AgentSkills '26 poster)`. We do not present it as
our own measurement.

---

## 5. Annotation procedure (PROTOCOL §3.2 Pass B, applied here)

- **Annotators:** ≥ 2 independent native speakers per language for
  the PRIMARY sample, blind to which tool flagged each row.
- **Question (verbatim from PROTOCOL §3.2):** *"Does this Skill's
  description contain ≥ 1 sentence that communicates the Skill's
  functionality, written in the Skill's primary language?"* YES →
  flag is a **false positive**; NO → flag is a **true positive**.
- **Rubric:** fixed before any annotator sees the data;
  language-uniform; not adjusted per-language.
- **Adjudication:** disagreements within a language pair adjudicated
  by a third native speaker; the adjudication outcome is the ground
  truth for that record (PROTOCOL §3.4).
- **Schema:** records validate against
  `eval/schema/annotation.schema.json` (Phase 0 contract).
- **What goes into the sheet (LOCKED here):** **all 208 rows** —
  the full PRIMARY sample (n = 190) **plus** the full SECONDARY
  sample (n = 18), regardless of whether either tool flagged
  each row. This is the bidirectional-fairness design: an
  over-flag fairness gap (Cisco false-positive bias on non-EN)
  is one failure mode; an under-flag fairness gap (a scanner
  *missing* genuinely-vague non-EN descriptions) is the
  symmetric failure mode that flagged-only annotation cannot
  detect. Annotating every row — including the rows neither
  tool flagged — produces ground truth for both directions,
  enabling §8's "false-negative analysis" line. The
  rubric question is the same for every row regardless of
  flag status: it is the PROTOCOL §3.2 rubric question, not
  "do you agree with the scanner".
- **What does NOT go into the sheet:** tool attribution
  (`SKILL-010` vs `SOCIAL_ENG_*` vs neither). The mapping is
  preserved in a separate, non-dispatched
  `_KEY_DO_NOT_DISPATCH.json`.

---

## 6. PRIMARY criterion (LOCKED on sign-off — the headline claim)

### 6.1 What "fairness holds" means, in precise terms

Let, for each language `lang ∈ {EN, JA, ZH, KO}`, on the PRIMARY
sample:

- `vague(lang)` = (# SkillScanner SKILL-010 emits on `lang` sample) /
  (sample size `n_lang`).
- `precision(lang)` = TP(lang) / (TP(lang) + FP(lang)), where TP/FP
  are native-speaker labels (post-adjudication ground truth) on the
  rows SkillScanner flagged in that language.
- `Δ(lang, axis)` = the observed difference `axis(L) − axis(EN)` for
  `L ∈ {JA, ZH, KO}` and `axis ∈ {vague, precision}`.

### 6.2 The PRIMARY test — TOST equivalence

The headline claim — "the v2 judge has *no* language-correlated
false-positive bias" — is an **equivalence claim**, not an absence
of evidence. Fisher's one-sided "fail to reject" cannot support
an equivalence claim (absence of evidence ≠ evidence of absence,
especially at n = 40–50 per language). The PRIMARY criterion is
therefore the **Two One-Sided Tests (TOST) equivalence procedure**,
applied per-axis-per-language.

For each non-English language `L ∈ {JA, ZH, KO}` and each axis
`axis ∈ {vague, precision}`:

- **Equivalence bound:** `Δ = ±0.15` (= ±15 percentage points). See
  §6.6 for the rationale; Δ is pre-committed and not derived from
  observed SkillScanner numbers.
- **TOST test:** the two one-sided null hypotheses are
  - `H₀_lower : axis(L) − axis(EN) ≤ −Δ`
  - `H₀_upper : axis(L) − axis(EN) ≥ +Δ`

  We **conclude equivalence on this (L, axis) pair iff BOTH
  one-sided nulls are rejected at level α'** (see §6.3 for α').

- **Operational form (for two-proportion equivalence):** the cleanest
  computational form is the **`100·(1 − 2α')` confidence interval**
  for the difference of proportions, computed via the **Newcombe-
  Wilson hybrid score method** (`statsmodels.stats.proportion
  .confint_proportions_2indep`, `method='newcomb'`,
  `compare='diff'`, `alpha = 2·α'`). Equivalence is concluded iff
  the entire CI lies inside `(−Δ, +Δ)`. This form is mathematically
  equivalent to the two-one-sided-tests formulation for the
  Wald/Newcombe family and is more interpretable for the reader.

### 6.3 Multiplicity correction (LOCKED)

The comparison family is **6 tests** (3 non-English languages × 2
axes). Bonferroni-corrected threshold:

```
α' = 0.05 / 6 = 0.008333…
```

For the TOST primary criterion, the relevant CI width is therefore
`100·(1 − 2·0.00833) % = 98.333 %`. (Each one-sided test in the
TOST pair uses level α', so the union of the two CIs is the
98.333 % CI — the standard equivalence-CI construction.)

For the secondary Fisher's-exact readout (§6.5), each one-sided
p-value is also compared to **α' = 0.00833**, on the same family
budget. The Fisher's-exact readout shares the Bonferroni budget
because it is reported alongside the TOST result on the same
hypothesis space; the secondary status (§6.5) does not relax its
multiplicity correction.

### 6.4 PRIMARY success criterion (LOCKED)

**PRIMARY succeeds if and only if all 6 of the following hold:**

For every `L ∈ {JA, ZH, KO}` and every `axis ∈ {vague, precision}`,
the 98.333 % Newcombe-Wilson CI for `axis(L) − axis(EN)` lies
entirely within `(−0.15, +0.15)`.

If all 6 hold, the registered conclusion is:

> *"On the PRIMARY sample, the v2 frozen judge is equivalent in
> vague-rate and equivalent in precision between EN and each of
> JA, ZH, KO, at family-wise α = 0.05 with a registered
> equivalence bound of ±15 percentage points."*

The conclusion is an **equivalence claim**, not "fairness exists
in some absolute sense" — it is bounded by the registered
tolerance and the sample sizes.

### 6.5 SECONDARY readout — Fisher's one-sided (kept for familiarity)

Reported alongside the TOST primary but **not** the registered
criterion:

- **AXIS A (vague-rate over-flag):** Fisher's exact, one-sided,
  H₁ : `vague(L) > vague(EN)`. p-value compared to α' = 0.00833.
- **AXIS B (precision deficit):** Fisher's exact, one-sided,
  H₁ : `precision(L) < precision(EN)`. p-value compared to
  α' = 0.00833.

The Fisher's-exact readout is provided because many readers (and
the AgentSkills '26 poster) are calibrated to it; it tests a
*directional* (not equivalence) hypothesis. **A "non-significant"
Fisher's-exact p-value does NOT support the fairness claim** — that
is exactly the asymmetry the PRIMARY TOST replaces. The Fisher's-
exact readout exists to give the reader a familiar comparator,
nothing more. Any Phase 3 narrative that elevates the Fisher's-
exact result above the TOST result has departed from this
pre-registration.

### 6.6 Δ rationale (LOCKED) — why ±15 percentage points

The choice of Δ is a pre-committed practical-significance bound,
fixed independently of any observed SkillScanner numbers. The
rationale on the record:

1. **Practical significance.** A language-correlated false-positive
   rate difference of ≥ 15 percentage points represents a *user-
   visible* fairness gap on a Skill registry: an author publishing
   a JA Skill that would face a 15-percentage-points-higher
   chance of behavioral mis-flagging than an EN counterpart would
   reasonably regard the scanner as language-biased. Below 15
   percentage points, the per-Skill experience is dominated by
   other variance sources (per-row description quality, scanner
   non-determinism if any, registry policy) and the language
   signal is not a load-bearing user-experience claim.
2. **Power alignment.** At n = 50, n = 50 (EN vs L), the
   approximate power of the Newcombe-Wilson TOST for proportions
   to *reject* a true effect of zero against an equivalence bound
   of ±0.15 at the per-test level α' = 0.00833 is about 80 %, under
   typical baseline rates (EN vague-rate near the 10 % observed
   on the PRIMARY sample). The Δ is *aligned with* what the
   sample size can actually distinguish — choosing a smaller Δ
   would mean the criterion is mostly inconclusive; choosing a
   larger Δ would mean the criterion is trivially met by any
   reasonable judge. Δ = ±15 pp is the principled match between
   the practical-significance threshold and the sample size's
   resolving power.
3. **Pre-committed independence from data.** Δ is not derived from
   the observed SkillScanner vague-rates (EN 10 % / JA 2 % /
   ZH 10 % / KO 7.5 %). If those numbers had been EN 5 % /
   JA 30 % / etc., Δ would still be ±15 pp. The honesty
   disclosure in §10 records that the SkillScanner numbers were
   visible at draft time; the Δ choice survives that visibility
   because it is anchored to (1) and (2), not to the gap between
   any pair of observed numbers.

### 6.7 Power note and acknowledged limitations of TOST equivalence
(LOCKED — not editable post-sign-off)

- The criterion is a test of equivalence *up to ±15 pp*. A real
  language gap of, say, 5 percentage points would not be
  detectable as non-equivalent at this sample size — and that is
  by design (such a gap is below the practical-significance
  threshold). Phase 3 narrative must state this honestly.
- Equivalence claims are sensitive to baseline rate. If
  `vague(EN)` is very low (say 2 %), `vague(L) + 15 pp` can be
  proportionally large; the equivalence claim still holds at the
  registered Δ but the *relative* difference may be substantial.
  Phase 3 narrative reports both the absolute difference (with
  CI) and the baseline rates, so the reader can judge.
- The CI is two-sample asymptotic; at small n (KO precision in
  particular, if SkillScanner flags few rows) the Newcombe-
  Wilson method's small-sample behavior is the documented
  fallback. We do not switch to exact methods post-hoc; if a CI
  is wide enough to fail the TOST equivalence test purely from
  small-sample width, that failure is reported per §9 with the
  width acknowledged.

### 6.8 Code-level regression guard (PROTOCOL §2.1 / Contribution 1
tile)

A single pass/fail line, reported alongside the PRIMARY result but
independent of it:

> *"Code-level findings (command injection, prompt injection,
> hardcoded secrets, pipeline taint) on the PRIMARY sample are
> unchanged between `SkillScanner ∪ SkillBodyScanner ∪ any AGENT-*
> scanner that fires on SKILL.md` and the Phase 1 baseline on the
> same bytes."*

Pass criterion: per-language code-level finding count on the
PRIMARY sample matches the Phase 1 SkillScanner ∪ siblings output
to ±0 findings (these are deterministic; any drift is a bug).
This is a regression guard, not a contribution.

---

## 7. SECONDARY case studies (qualitative; LOCKED scope)

The 18-row SOCIAL_ENG-flagged head-to-head set receives the same
native-speaker annotation as the PRIMARY sample. We report:

- A **case-study table** of all 18 rows: skill_id (anonymized),
  language, Cisco verdict (historical `SOCIAL_ENG_VAGUE_DESCRIPTION`
  yes/no), SkillScanner verdict (vague | clear | cannot_judge), and
  the native-speaker label.
- A **narrative** of the head-to-head agreement pattern: in how many
  rows did SkillScanner agree with the native speaker against
  Cisco's flag (i.e., SkillScanner correctly cleared a row Cisco
  false-positive flagged)? In how many did it agree with Cisco
  against the native speaker (i.e., SkillScanner missed an actual
  clear case)? In how many did all three agree?

The case-study table is **not** subjected to any statistical
test. n = 4 for JA is not a Wilson CI's job, and presenting one
would misrepresent confidence. The case studies are illustrative
support for the PRIMARY result, **not** an independent test.

---

## 8. Statistical machinery (LOCKED)

| Quantity | Method | Status | Note |
|---|---|---|---|
| Per-language vague-rate point estimate | `vague_count / n_lang` | reported | direct count |
| Per-language vague-rate CI | **Wilson 95 %** | reported | per PROTOCOL §4.2 |
| Per-language precision point estimate | `TP / (TP + FP)` after adjudication | reported | denominator can be small if SkillScanner flagged few rows |
| Per-language precision CI | **Wilson 95 %** | reported | per PROTOCOL §4.2 |
| **AXIS A PRIMARY — vague-rate equivalence** | **TOST via `confint_proportions_2indep(method='newcomb', compare='diff', alpha=2·α')`**; equivalence iff entire 98.333 % CI ⊂ (−0.15, +0.15) | **PRIMARY** | one test per non-EN language; family size 6 |
| **AXIS B PRIMARY — precision equivalence** | same TOST procedure on the precision proportions | **PRIMARY** | one test per non-EN language; family size 6 |
| AXIS A SECONDARY — Fisher's one-sided over-flag test | `scipy.stats.fisher_exact(alternative='greater')` on the 2×2 (vague vs not-vague) × (L vs EN) table | secondary readout | p compared to α' = 0.00833; NOT the registered criterion |
| AXIS B SECONDARY — Fisher's one-sided precision-deficit test | `scipy.stats.fisher_exact(alternative='less')` on the 2×2 (TP vs FP) × (L vs EN) table | secondary readout | p compared to α' = 0.00833; NOT the registered criterion |
| Multiplicity correction | **Bonferroni** across the family of 6 PRIMARY tests | LOCKED | α' = 0.00833; SECONDARY Fisher tests share the same budget |
| Per-language inter-annotator agreement | **Cohen's κ**, computed **per language separately** | reported | PROTOCOL §3.3; pooled κ forbidden as headline |
| False-negative analysis (bidirectional fairness check) | per-language counts of `(rubric_pass=False) ∧ (no tool flagged)` rows | reported | enabled by all-208 annotation (§5); not part of the PRIMARY criterion but reported alongside as the symmetric counterpart to false positives |
| Replacement / dropout handling | locked in §2.1: deterministic from seed `0xFA1F1E55` | LOCKED | new rows substituted from the replacement queue, recorded |

No other statistics are computed for the PRIMARY claim. No
multi-language pooled tests. No regression / latent-variable
modelling. No multiple-imputation. If any of these would be needed
post-hoc to defend a result, that result is a post-hoc finding
and must be labeled as such.

---

## 9. NEGATIVE-RESULT clause (LOCKED — honest reporting bound)

PRIMARY fails on a `(L, axis)` pair iff the 98.333 % Newcombe-Wilson
CI for `axis(L) − axis(EN)` is **not** entirely contained in
`(−0.15, +0.15)`. PRIMARY as a whole fails iff any one of the 6
`(L, axis)` pairs fails. If PRIMARY fails, the write-up MUST contain:

1. The exact `(L, axis)` pair(s) that failed, the observed
   difference `axis(L) − axis(EN)`, the 98.333 % CI bounds, and
   the specific bound that the CI crossed (lower −0.15 or upper
   +0.15). If the CI crossed the **upper** bound on AXIS A, the
   plain-English read is: *"SkillScanner over-flags `L` relative
   to EN by more than the registered ±15 pp practical-
   significance threshold."* If the CI crossed the **lower**
   bound on AXIS B, the plain-English read is: *"SkillScanner is
   substantially less precise on `L` than on EN, beyond the
   registered ±15 pp threshold."*
2. The Wilson 95 % CIs for the underlying per-language rates
   (`vague(L)`, `vague(EN)`, `precision(L)`, `precision(EN)`) so
   the reader can see the absolute baseline and the effect size.
3. The matching SECONDARY Fisher's one-sided p-value (see §6.5),
   reported alongside the TOST result. If the SECONDARY directional
   p crosses α' = 0.00833, that is a *consistent* signal; if it
   does not, the TOST result still stands as the registered claim
   and the discrepancy is noted (TOST and one-sided Fisher answer
   different questions).
4. An acknowledgement that the failure may motivate a v3 prompt
   revision in Phase 3 (or an alternative fix entirely) — but
   the failure stays in the published Results section. It does
   not get demoted to a footnote, an appendix, or a
   "limitations" sentence.
5. The PRIMARY claim is **not** partially salvaged ("the fix works
   for ZH and KO but not JA") unless the language-specific
   `(L, axis)` results cleanly support that partial framing AND
   the failure on JA is reported with full prominence. We do not
   cherry-pick the languages where the fix worked.
6. **Inconclusive results are not successes.** If a CI straddles
   one of the equivalence bounds (e.g., −0.15 < CI_low < 0 <
   CI_high but CI_high > +0.15), the TOST does not conclude
   equivalence; this is reported as "inconclusive at this
   sample size with Δ = ±15 pp" — explicitly NOT as "no
   evidence of bias" and explicitly NOT as a fairness success.
   The inconclusive case is also subject to §9 reporting in
   full: which CI was inconclusive, the width, and whether
   a larger sample would have likely resolved it (computed
   from the width alone, no post-hoc power analysis).

The SECONDARY case-study set, the code-level regression guard, F-001
/ F-002 / F-006, F-004 / F-005 — none of these are affected by a
negative PRIMARY result and continue to be reported as written.
The fairness claim's failure is *one finding*, not a referendum
on the whole project.

---

## 10. Order-of-operations honesty disclosure (recorded here, not
amendable)

This pre-registration is being written *after* the PRIMARY sample
was scanned by both tools (vague-rates already visible in
`cisco_oou_sample.json` and `skillscanner_oou_sample.json`,
2026-06-07). Standard pre-registration practice writes the
criterion before any data is seen. **We are not doing that here.**
The reasons, recorded explicitly:

- The sample drawing required prior knowledge of the per-language
  judge-eligible pool sizes (confirmed only after the multilingual
  fetch landed); the criterion's per-language stratification
  depends on those sizes.
- The Cisco vague-rates on the OOU sample (0/0/0/0) were a
  *structural* fact (OOU = "Cisco passed historically") that the
  user identified before the criterion was written; this informed
  the decision to cite the Cisco gap rather than re-derive it
  (§4). That decision affects the criterion but is not a
  data-driven adjustment.
- The SkillScanner vague-rates were seen (EN 10 %, JA 2 %,
  ZH 10 %, KO 7.5 %). These are *consistent* with a no-over-flag
  finding (JA / KO are below EN; ZH equals EN). The pre-reg
  criterion was *not* tightened in response to these numbers; the
  per-language Bonferroni-corrected α' = 0.00833 follows from the
  comparison-family count (6), not from the observed gaps, and the
  TOST equivalence bound Δ = ±0.15 follows from the §6.6 rationale
  (practical-significance + power-alignment), not from the
  observed gaps. The criterion was changed mid-draft from
  failure-to-reject (original §6) to TOST equivalence (current
  §6) at the user's direction — *not* in response to seeing the
  observed gaps were favorable, but because failure-to-reject
  cannot support an equivalence claim regardless of what numbers
  were observed.

- The **human precision ground truth is not yet produced.** The
  annotator labels do not exist at the time of this commit. The
  PRIMARY criterion's precision axis (AXIS B) is therefore
  pre-registered in the standard sense for the half of the claim
  that the headline rests on: precision per language under TOST
  equivalence cannot be computed without the labels, and the
  labels do not exist. The vague-rate axis (AXIS A) is the side
  of the criterion where the order-of-operations gap is real;
  the precision axis is genuinely pre-data.

**The honesty discipline this requires:** the criterion in §6 is
locked *as written*. It is not weakened in response to incoming
human labels. If the PRIMARY fails, §9 applies. If it succeeds,
the success is reported with the §6.5 limitation acknowledged.

Future Phase 2A or Phase 3 iterations should write their
pre-registration **before** any data is seen, on a new sample, and
should cite this Phase 2A as the prior. The order-of-operations
gap here is a known limitation.

---

## 11. Audit checklist (verifiable after annotation labels return)

- [ ] PRIMARY sample bytes still pinned at the seed-locked sha256s
      (manifest_oou.json).
- [ ] Per-language sample sizes: EN 50, JA 50, ZH 50, KO 40.
      Replacement-row substitutions (if any) match the seed-locked
      replacement queue and are recorded in
      `eval/snapshot/private/sample_manifest.json`.
- [ ] Annotation sheets dispatched blind (no tool-attribution leak;
      `_KEY_DO_NOT_DISPATCH.json` not shared).
- [ ] ≥ 2 native-speaker annotators per language; per-language
      Cohen's κ reported separately; pooled κ not headlined.
- [ ] Statistical machinery executed exactly per §8: PRIMARY = TOST
      via Newcombe-Wilson 98.333 % CI of difference of proportions,
      equivalence bound Δ = ±0.15, Bonferroni-corrected α' = 0.00833
      across the family of 6; SECONDARY = Fisher's one-sided at the
      same α'; Wilson 95 % CIs reported for every point estimate;
      per-language κ separately.
- [ ] No additional statistical tests beyond §8 in the headline.
      Post-hoc analyses labeled post-hoc.
- [ ] Negative result (if any) reported per §9 in full.
- [ ] Code-level regression guard per §6.6 reported as
      pass/fail.
- [ ] The §10 honesty disclosure remains in the committed
      version of this file.

---

## 12. Out-of-scope (recorded here so it stays out)

- A claim that SkillScanner is "better" than Cisco. We claim
  fairness, not superiority.
- A general claim about all LLM-based Skill scanners. We claim
  results for the v2 frozen judge under the specified frozen
  constants only.
- Any precision claim about Cisco today. We cite the poster's
  Cisco gap, period.
- A recall claim. Recall is the regression guard's domain; it is
  not a contribution number.

---

## 13. Sign-off

- **Drafted by:** the Phase 2A run agent (this run).
- **Awaiting sign-off:** user. The user's explicit "go" is the
  signal to commit this file (single commit, `feature/skillscanner-
  eval` branch, local only per current rails). After commit, the
  contents of §2 / §3 / §6 / §7 / §8 / §9 / §10 are locked; only
  §11 audit checks are added by the post-annotation run.

---

*— end of pre-registration draft —*
