# Claude Code Execution Prompt — SkillScanner Phase 2A (Before/After Evaluation)

Execute the roadmap in `SKILLSCANNER_PHASE2A_PLAN.md`. **Read it in full first.**
This phase builds **against the frozen tag `skillscanner-core-frozen`**. You do
NOT modify frozen code, the v2 judge, the judge constants, or the schema.

---

## Global rules

1. **Verify you're on the frozen base.** First action: confirm
   `skillscanner-core-frozen` exists and check out / branch from it
   (`feature/skillscanner-eval` off the tag). Confirm the SkillScanner module
   tests are 28/28 on the tagged state before doing anything else.
2. **The evaluation must never grade itself.** Behavioral ground truth comes ONLY
   from human native-speaker annotation. If any step would use SkillScanner's or
   Cisco's output as the correctness yardstick, stop.
3. **Frozen snapshot, never live fetch mid-analysis.** All scanning runs on the
   pinned local snapshot built in 2A.0.
4. **Cisco v2.0.9 unmodified** is the before-baseline.
5. **Pre-register success before scoring** (2A.3). Do not adjust it afterward.
6. **A negative result is a result.** Report it honestly.
7. **Stop at every sub-phase gate.** Surface and wait.
8. Local only. No push. No commit unless I ask.

---

## 2A.0 — Build the pinned snapshot (gate)

- Read the corpus manifest (`skills_metadata.json` + `cisco_scanner_results.json`)
  from the dataset path established in Phase 1.
- For the evaluation set (start with EN + JA behavioral-flagged rows; ZH/KO
  noted for later), build a snapshot manifest: per row → repo/path → stored
  sha256 → fetch current bytes → compute sha256 → classify MATCH / DRIFT / 404.
- **Before storing ANY third-party Skill bytes locally, STOP and surface the
  license/redistribution decision** (PLAN §1). Present the options (sha256+fetch
  script only / bytes for permissive-license subset / per-repo permission) and
  WAIT for my call. Do not store bytes until I answer.
- Output: the manifest table (counts of MATCH/DRIFT/404 per language) + the
  proposed snapshot composition. Do not scan yet.

**STOP. Surface the manifest + the license question. Wait.**

## 2A.1 — Paired scan (gate)

- Vendor/pin Cisco Skill Scanner v2.0.9 (the Phase 2A deliverable flagged in
  PROTOCOL §2). Record exactly how it's pinned.
- Run BOTH on the pinned snapshot:
  - Cisco v2.0.9 → behavioral flags. For MATCH rows you may use the recorded
    historical flag; for DRIFT/404 rows, re-scan fresh and label the pair
    "paired-fresh" — never mix a historical Cisco flag with a SkillScanner run on
    different bytes.
  - SkillScanner (frozen tag) → SKILL-010 verdicts, same bytes.
- Output: paired rows `(skill_id, language, bytes_sha256, match_class,
  cisco_behavioral_flag, skill010_verdict, judge_model, judge_prompt_version)`.
- Note: the v2 judge calls the real API — confirm `~/.anthropic_key.env` (or the
  agreed key path) and the `judge` extra are available; use the verdict cache so
  repeated rows don't re-bill. Surface the API cost estimate before a large run.

**STOP. Surface paired-row counts + cost estimate. Wait before annotation.**

## 2A.2 — Human annotation (gate — this is mostly off-Claude-Code)

- Generate per-language annotation sheets from the Phase 0
  `annotation_template.csv`, populated with the flagged samples, **blind to which
  tool produced the flag** (do not leak cisco vs skillscanner into the sheet).
- Per PROTOCOL Pass B: ≥2 independent native speakers per language. This step
  happens with humans — your job is to produce the sheets and, when labels come
  back, ingest them and compute **per-language Cohen's κ** (κ_EN, κ_JA, … —
  never pooled as headline).
- Output: the blind sheets ready to dispatch; then (after I return labels) the
  κ per language + the merged TP/FP ground truth.

**STOP after producing sheets. Wait for me to return human labels.**

## 2A.3 — Statistics (gate)

- **First, write the pre-registered success criterion to
  `docs/skillscanner/eval/PREREGISTRATION.md` and commit it (ask me to confirm
  the commit) BEFORE computing any precision.** Criterion per PLAN §2.5.
- Then compute, per language: precision before (Cisco) and after (SkillScanner)
  with Wilson 95% CI; Fisher's exact EN-vs-non-EN and pairwise; Bonferroni with
  the comparison count stated.
- Compute the code-level regression guard (PLAN §2.4): code-level recall on the
  snapshot = SkillScanner ∪ SkillBodyScanner ∪ AGENT-* — confirm unchanged vs
  Phase 1 baseline. One pass/fail line.

**STOP. Surface the raw stats table + the regression line. Wait.**

## 2A.4 — Results writeup (gate)

- Write results against the pre-registered criterion — including, explicitly,
  whether the primary criterion was met, and reporting any negative result
  plainly.
- Produce figures: per-language precision before/after with CIs (mirror the
  poster's Figure 1 style for continuity).
- Output to `docs/skillscanner/eval/RESULTS.md` + figure files.

**STOP. Surface results + figures. Do not start Phase 2B or any paper writeup.**

---

## Final report format

At each gate, report: what was produced, the relevant counts/numbers, and the
specific PLAN §4 constraints you verified you did not violate. Surface any
blocker rather than working around it. Never grade the evaluation with the tools
being evaluated.
