# Phase 2A Target Framing (design note — NOT pre-registration)

**Status:** Internal design note used to ensure the 2A sampling step matches
the eventual pre-registered criterion. **This file is NOT the
pre-registration.** PROTOCOL §3.2.2 reserves the pre-registration to a
later commit that the user confirms awake; this note exists only so the
sampling already in flight is aligned with the criterion the user has
indicated they intend to lock.

**Recorded:** 2026-06-07.
**Cross-references:** PROTOCOL §3.2 (Pass B), PROTOCOL §2.1 (code-level
coverage union), F-004 (judge robustness on well-formed input), and
the Phase 2A diagnostic chain that revealed the SOCIAL_ENG-flagged
pool is the wrong population for the judge-fairness claim.

---

## 1. Why this note exists, in one paragraph

Phase 1's freeze gates "fairness, not detection" as the core
contribution. The naïve before/after comparison on the SOCIAL_ENG-
flagged corpus subset is **doubly wrong** for that target: (a) it
conflates SkillScanner's Layer-1 frontmatter filter (a language-
agnostic contamination contribution) with its Layer-3 semantic judge
(the fairness contribution), and (b) Cisco's flag is a tool-side
selection event, so any cherry-picked-by-Cisco subset trivially
shows both tools low on vague-rate (selection bias). The OOU
`fm_present` pool — corpus rows Cisco *did not* SOCIAL_ENG-flag and
that have a parseable manifest — is the population that lets the
fairness contrast be tested cleanly: it represents *real Skills as
deployed*, not *Skills the prior tool flagged*. The framing below
locks the sampling to that population so the next stages can
proceed without re-litigation.

## 2. Population (locked for the 2A sample)

- **Universe:** corpus rows with `language ∈ {EN, JA, ZH, KO}`,
  **not** in the SOCIAL_ENG_* universe historically, with
  collection-time `MANIFEST_MISSING_LICENSE` having fired (proxy
  for "Cisco parsed the manifest at collection time" =
  `fm_present`).
- **Filter:** today's bytes pass SkillScanner's strict frontmatter
  parse, have a non-empty `description`, and the description's
  detected language is in `SUPPORTED_LANGUAGES`. This is the
  *judge-eligible* subset of the OOU `fm_present` pool, measured
  on the 2026-06-07 snapshot at
  `eval/snapshot/private/bytes_oou/{LANG}/`.
- **Confirmed sizes** (from the multilingual confirm fetch):
  EN 1,118, JA 125, ZH 192, KO 77.
- **Excluded from this sample, by design:** the 198-row
  SOCIAL_ENG-flagged 2A.1 snapshot. That snapshot continues to
  exist on disk; it serves *Contribution 1* (Layer-1 contamination
  filtering) only. The two contributions live on disjoint
  populations on purpose.

## 3. Target framing (the question the 2A.3 stats answer)

**Claim 2 — semantic-judge cross-lingual fairness, on the population
of real, frontmatter-bearing, judge-eligible Skills:**

> *Hypothesis (from the AgentSkills '26 poster):* Cisco
> v2.0.9 over-flags non-English real Skills with
> `SOCIAL_ENG_VAGUE_DESCRIPTION`, producing a substantial
> language gap in vague-rate (the poster reported JA 31.7 % vs
> EN 6.1 %). SkillScanner's v2 frozen judge does not exhibit
> this gap — its vague-rate on JA, ZH, and KO is comparable to
> its vague-rate on EN, within Wilson 95 % CIs.

**The fairness result is the *gap-in-Cisco vs no-gap-in-SkillScanner*
contrast**, not a "more findings" claim about either tool. The
*direction* of the gap matters: Cisco's JA / ZH / KO vague-rate
should be higher than its EN vague-rate; SkillScanner's JA / ZH / KO
vague-rate should be close to its EN vague-rate, and any deviation
must be both small and *bidirectional* (we are not claiming
SkillScanner is uniformly better; we are claiming it does not
have a *language-correlated* bias).

**Two measurement axes per language (per tool):**

1. **Vague-rate** = (# rows flagged as behaviorally vague) /
   (# rows sampled). Tool-side artifact; no human label needed.
2. **Precision on flagged rows** = TP / (TP + FP), where TP / FP are
   decided by ≥ 2 independent native speakers per language per
   PROTOCOL Pass B. Human-only ground truth, blind to tool.

The two together let us distinguish "Cisco flags a lot and is right
about it" from "Cisco flags a lot and is wrong about it". The
poster's framing — and what this evaluation tests — is the latter
for non-English Skills.

**Code-level regression guard (Contribution 1's tile in this report
table; PROTOCOL §2.1):** unchanged code-level recall on the OOU
sample, measured as `SkillScanner ∪ SkillBodyScanner ∪ any
AGENT-* scanner that fires on SKILL.md`. Reported as a single
pass/fail line, not a contribution number.

## 4. Sampling rules (locked)

- **N per language**: EN 50, JA 50, ZH 50, KO ≤ 40 (KO pool is
  77 judge-eligible; less replacement headroom — cap at 40 so
  bad-sample replacement is feasible).
- **Stratification within each language**: take all MATCH
  judge-eligible rows first (identity-locked to the corpus's
  collection-time bytes), fill the rest with DRIFT-sampled rows.
  Carry `match_class` on every sampled row so 2A.3 can stratify
  MATCH and paired-fresh separately — never merge.
- **Sampling method**: deterministic, fixed-seed
  `random.Random(seed)` shuffle of the eligible-DRIFT subset
  followed by a head-take to fill the slot count. Seed recorded
  in the sample manifest. **Seed for this run:** `0xFA1F1E55`
  (4196244053 dec).
- **Replacement-of-bad-samples**: if a sampled row turns out to
  be undecodable, scan-failed, or otherwise unusable during the
  paired scan, replace from the deterministic next-row-in-the-
  shuffled-order. The replacement queue is itself fixed by the
  seed, so the sample is reproducible. Replacements are
  recorded explicitly in the sample manifest.

## 5. What this note is NOT

- Not the pre-registration. The pre-registration document
  (`PREREGISTRATION.md`) will, when written, state the
  pre-registered primary success metric in the exact form
  PROTOCOL §3.2.2 requires, including the Wilson CI form,
  the Fisher's exact comparison family, and the Bonferroni
  correction count. **That criterion has not been written yet
  and is not implied by this note.** The user is reserving
  awake-confirmation of the exact wording per the same
  PROTOCOL §3.2.2 anchor.
- Not a license to compute precision. Precision computation is
  blocked by the sequence: target framing (this note) →
  pre-registration (forthcoming) → annotation labels return →
  precision computation. The current step (sampling + paired
  scan) precedes all of that.
- Not a new freeze invariant. The frozen tag
  `skillscanner-core-frozen` → `05c3f988…` remains the truth
  for code; this note is design material for the eval that
  builds *against* that tag.
- Not a contradiction of any earlier 2A note. PROTOCOL §3.2,
  §3.2.2, F-004 all stand; this note operationalizes them
  for the sample about to be drawn.

## 6. Audit checklist (verifiable after the sampling step)

- [ ] Sample manifest records the seed `0xFA1F1E55`.
- [ ] Per-language sample sizes: EN 50, JA 50, ZH 50, KO ≤ 40.
- [ ] Each sampled row carries `match_class ∈ {MATCH, DRIFT}`.
- [ ] All available MATCH judge-eligible rows per language are
      included before any DRIFT row is sampled.
- [ ] DRIFT rows are drawn by `random.Random(0xFA1F1E55).sample`
      from the deterministically-ordered DRIFT-judge-eligible
      pool.
- [ ] Replacement queue per language is documented if any
      replacements occurred.
- [ ] No code-level recall computation, no precision, no κ in the
      sampling artifact.
