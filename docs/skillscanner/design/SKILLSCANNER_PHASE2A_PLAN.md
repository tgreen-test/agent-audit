# SkillScanner Phase 2A Plan — Before/After Evaluation vs Cisco v2.0.9

> Companion spec for `SKILLSCANNER_PHASE2A_PROMPT.md`. This is the **what and why**;
> the prompt file is the **how**. Claude Code MUST read this fully before any code.
> This phase builds **against the frozen tag** `skillscanner-core-frozen` and the
> Phase 0/1 PROTOCOL. It does not modify frozen code, the v2 judge, or the schema.

---

## 0. What Phase 2A is, and the one way it fails

Phase 2A produces the **single number that the entire fairness claim rests on**:
a clean before/after showing that the language-aware SkillScanner raises
non-English behavioral precision from near-zero toward English-comparable,
**without** dropping English precision and **without** changing code-level recall.

**The one way this phase fails: evaluation credibility.** The CAIS demo paper was
rejected for synthetic benchmarks and self-referential ground truth. Phase 2A is
the highest-risk place to repeat that mistake. Three rules are absolute:

1. **No circular ground truth.** SkillScanner's own verdicts are NEVER the
   yardstick. Behavioral precision is measured against **independent
   native-speaker annotation** (PROTOCOL Pass B), not against the judge.
2. **Before/after baseline is Cisco v2.0.9 unmodified** (PROTOCOL §2 lock). The
   comparison is *Cisco v2.0.9 behavioral flags* vs *SkillScanner SKILL-010*, on
   the **same Skills**, scored by the **same human annotators** blind to which
   tool produced which flag.
3. **The claim is fairness, not detection.** Report precision and false-positive
   rate by language. Do NOT headline recall or "more findings." Code-level recall
   appears ONLY as a regression guard (must be unchanged), never as a win.

If at any point the analysis would let the scanner grade its own homework, stop.

---

## 1. The drift problem is a first-class design constraint

Phase 1 established (F-002) that the published corpus is ~97% non-reproducible at
origin today: of 70 JA behavioral-flagged rows, only 2 still sha256-match, 44 are
now frontmatter-less, 10 are 404. **This is not a footnote — it dictates the
evaluation's data strategy.** A before/after that silently re-fetches from origin
HEAD would compare Cisco's historical flags against SkillScanner run on *different
bytes*. That is not a valid comparison.

**Data integrity rule for Phase 2A:**

- Every Skill entering the evaluation must have its **exact evaluated bytes
  pinned and recorded** (sha256 + the bytes themselves, stored locally for the
  eval run). The eval operates on a **frozen local snapshot**, never live origin
  fetches mid-analysis.
- Where the corpus row still sha256-matches origin → use it, record MATCH.
- Where it has drifted/404'd → it CANNOT carry Cisco's original behavioral flag
  as ground truth (Cisco flagged different bytes). Such rows are either excluded
  from the before/after, or re-scanned by *both* tools on the current bytes and
  treated as a fresh paired observation — never mixed.
- The snapshot, its manifest (row → sha256 → MATCH/DRIFT/404 → bytes-source), and
  the build script are part of the released artifact. This is what makes Phase 2A
  reproducible where the original poster's corpus no longer is — and is itself a
  methodological contribution worth stating.

**License/redistribution tension (record, don't resolve here):** the dataset
README says original SKILL.md files are not redistributed. Pinning bytes for a
reproducible eval is in tension with that. Flag it for the human; do NOT
unilaterally redistribute third-party Skill bodies. Options to surface: store
sha256 + offsets only and provide a fetch+verify script; or store bytes only for
the subset whose license permits; or seek per-repo permission. Human decides.

---

## 2. Evaluation design

### 2.1 The paired before/after

For each Skill in the evaluation set, on the **same pinned bytes**:

- **Before**: Cisco v2.0.9 behavioral flag (SOCIAL_ENG_VAGUE_DESCRIPTION etc.) —
  either the recorded historical flag (MATCH rows) or a fresh Cisco re-scan
  (DRIFT/404 rows, paired-fresh).
- **After**: SkillScanner SKILL-010 verdict on the same bytes, frozen v2 judge.

The unit of comparison is **per-language behavioral precision**:
precision = TP / (TP + FP), where TP/FP are decided by **human annotators**
(PROTOCOL Pass B), not by either tool.

### 2.2 Languages and samples

- Primary contrast: **EN vs JA** (the poster's sharpest gap: EN 10% precision,
  JA 0%). These two must be fully powered.
- Secondary: **ZH, KO** (poster showed significant behavioral gaps). Include if
  annotator coverage allows.
- Per PROTOCOL Pass B: each language's flagged sample annotated by **≥2
  independent native speakers**; report **per-language Cohen's κ** (κ_EN, κ_JA,
  κ_ZH, κ_KO separately — never a pooled headline κ).

### 2.3 Statistics (reuse the poster's frozen framework)

- **Wilson 95% CI** on every per-language precision (before and after).
- **Fisher's exact** for EN-vs-non-EN and per-language pairwise.
- **Bonferroni** across the comparison family; α = 0.05 / (#comparisons), state
  the count explicitly.
- The headline result is a **precision-improvement table**: per language,
  Cisco-before precision [CI] vs SkillScanner-after precision [CI], with the
  Fisher p and whether it survives Bonferroni.

### 2.4 Code-level regression guard (NOT a result, a safety check)

Per PROTOCOL §2.1, "agent-audit code-level coverage" = SkillScanner ∪
SkillBodyScanner ∪ any existing AGENT-* scanner that fires on SKILL.md. Confirm
on the pinned snapshot that code-level recall (command injection, prompt
injection, hardcoded secrets, pipeline taint) is **unchanged** vs the Phase 1
baseline. Report as a single pass/fail line. If it dropped, that's a bug to
surface, not a tradeoff to accept.

### 2.5 Pre-registration of the success criterion

Before running the scoring, write the success criterion to a file and commit it,
so the analysis cannot be retrofitted to the result:

> PRIMARY: non-EN (at least JA) behavioral precision after > before, with the
> improvement surviving Bonferroni-corrected Fisher's exact; AND EN behavioral
> precision after ≥ before (not degraded); AND code-level recall unchanged.

State up front what a **negative result** looks like and that it will be reported
honestly: if SkillScanner does not beat Cisco on JA precision, that is a
publishable finding about the difficulty of the problem, not a failure to bury.

---

## 3. Phased execution

- **2A.0** — Build the pinned snapshot + manifest from the corpus; record
  MATCH/DRIFT/404 per row; surface the license/redistribution decision to the
  human BEFORE storing any third-party bytes.
- **2A.1** — Run Cisco v2.0.9 (vendored/pinned per PROTOCOL §2 — this is the
  Phase 2A deliverable flagged earlier) and SkillScanner (frozen tag) on the
  snapshot; produce paired (Skill, language, cisco_flag, skill010_verdict) rows.
- **2A.2** — Annotation: dispatch the flagged samples to ≥2 native speakers per
  language using the Phase 0 `annotation_template.csv`; collect TP/FP labels
  blind to tool. Compute per-language κ.
- **2A.3** — Statistics: per-language precision (Wilson), Fisher + Bonferroni,
  the before/after table, the code-level regression line.
- **2A.4** — Write results honestly against the pre-registered criterion;
  produce the figures (precision before/after by language, mirroring the
  poster's Figure 1 style for continuity).

Each sub-phase has its own gate; stop and surface between them.

---

## 4. Hard constraints

1. Build against `skillscanner-core-frozen`. Do NOT modify frozen code, the v2
   judge, constants, or schema. If the eval reveals a judge problem, that's a
   v3/Phase-3 decision, surfaced — not an in-place edit.
2. No live origin fetches during analysis — frozen snapshot only.
3. Human annotators are the only behavioral ground truth. Never the judge,
   never Cisco, never SkillScanner.
4. Cisco v2.0.9 unmodified as the before-baseline.
5. Pre-register the success criterion before scoring.
6. A negative result is reported, not buried.
7. Surface the license/redistribution decision before storing third-party bytes;
   do not unilaterally redistribute.
8. Keep everything local; no push. No commit without the human asking.

## 5. Anti-patterns (reject the work if any appear)

- [ ] SkillScanner (or Cisco, or any tool) used as behavioral ground truth.
- [ ] Re-fetching origin HEAD mid-analysis instead of the pinned snapshot.
- [ ] Comparing Cisco's historical flag against SkillScanner run on drifted bytes.
- [ ] Pooled κ presented as the headline instead of per-language κ.
- [ ] Headlining recall / "more findings" as the contribution.
- [ ] Success criterion written/adjusted after seeing the scores.
- [ ] Redistributing third-party Skill bodies without the human's license call.
- [ ] Editing the frozen judge/schema/code to make a number look better.
