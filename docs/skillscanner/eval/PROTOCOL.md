# SkillScanner Evaluation Protocol (Phase 0, frozen)

> Companion to `docs/skillscanner/design/SKILLSCANNER_PLAN.md` §1.
> This document is the **frozen annotation + evaluation protocol** that the
> SkillScanner finding schema must satisfy. It MUST be written before any
> scanner code is committed (PLAN §0 constraint).

---

## 0. Scope & non-negotiable framing

The contribution being evaluated is a **fairness / calibration** fix to
multilingual Skills scanning, not a detection-capability improvement. Every
metric in this protocol is chosen so that an improvement in detection (recall
↑) is **not** the success signal. The success signal is:

> Non-English behavioral precision rises toward English-comparable levels
> **without** degrading English behavioral precision or any code-level recall.

Reviewers should be unable to read this protocol and conclude "the new scanner
finds more vulnerabilities." If that reading is possible, the framing has
drifted and the protocol must be revised.

The scanner's own output is **never** ground truth.

---

## 1. Corpus

- Dataset: `HeadyZhang/skills-crosslingual-security` (3,656 Skills,
  8 languages, CC BY 4.0). PLAN §0 constraint #6 — no synthetic data.
- Subsets used in evaluation:
  - **Pass A (code-level, control):** the full corpus, code-block-bearing
    Skills only. Used to verify no code-level regression.
  - **Pass B (behavioral, fairness target):** per-language stratified samples
    of Skills flagged by the behavioral rule `SKILL-010`. Per-language sample
    size N ≥ 20.
- Non-Skill files (no valid YAML frontmatter) are **excluded from every
  denominator**. The Layer 1 `SKILL-000` emit-and-skip exists precisely so
  these files cannot enter behavioral metrics (the 23% non-Skill-file
  contamination on JA flagged by the AgentSkills '26 poster).

---

## 2. Baseline lock

The before/after comparison baseline is **Cisco Skill Scanner v2.0.9,
unmodified** — the exact version evaluated in the AgentSkills '26 poster
*"Do Agent Skills Speak Safety in Every Language?"*.

- Source: pinned tag / commit `cisco-skill-scanner@v2.0.9`.
- The baseline is run with **its default configuration**. No flag changes,
  no rule disables, no language-specific patches.
- The baseline is **never** the prior version of agent-audit's own
  SkillScanner. Comparing the scanner to itself would be a circular ground
  truth (PLAN §0 constraint #3, CAIS rejection lesson).

If Cisco v2.0.9 cannot be reproduced bit-for-bit on the evaluation host, that
fact is reported and the evaluation does not proceed.

> **Phase 2A owes the pin.** Vendoring or pinning Cisco Skill Scanner v2.0.9
> (the exact tag/commit, default config, install steps reproducible on a
> clean host) is a **Phase 2A** deliverable, not Phase 1. Phase 1 emits
> schema-conforming findings; Phase 2A stands the baseline up beside them.
> This note exists so the Phase 2A team does not have to re-derive the
> requirement.

### 2.1 What counts as "agent-audit code-level coverage"

The "agent-audit" side of the before/after is **not** SkillScanner
alone. By design, several existing AGENT-* rules detect Skill-relevant
code-level patterns from sibling scanners that already operate on
`SKILL.md`. The most important is `AGENT-058 skill_obfuscated_shell`,
which `SkillBodyScanner` emits on patterns such as `curl ... | sh` and
`wget ... | sh` — exactly the AgentSkills '26 poster's Case 1 finding.
SkillScanner does **not** duplicate this detection (PLAN §0
constraint #1, additive-only). Instead:

> **agent-audit code-level coverage = `SkillScanner` ∪ `SkillBodyScanner`**
> (and any other existing AGENT-* scanner that fires on the SKILL.md;
> in the present codebase that is also `SkillMetaScanner` for
> AGENT-058..AGENT-064 metadata rules).

This union is the denominator side of Pass A's "code-level recall
unchanged" regression guard (§4.5 success criterion #3). Counting only
`SkillScanner` findings would systematically undercount agent-audit
relative to Cisco v2.0.9 — falsely suggesting a regression that does not
exist. The evaluation harness MUST take the union before computing
per-language code-level recall.

The behavioral evaluation (Pass B, `SKILL-010`) is unaffected by this
union: `SKILL-010` is SkillScanner-only by construction.

---

## 3. Two annotation passes

### 3.1 Pass A — Code-level (language-agnostic, control)

**Purpose:** verify the language-aware change did not regress code-level
detection. The AgentSkills '26 poster showed code-level scanning has no
cross-lingual gap; this pass is the regression guard, not a contribution.

- Population: Skills with at least one fenced code block (`python`, `bash`,
  `sh`, or unmarked).
- Rules in scope: existing AGENT-* code-level rules surfaced via Layer 2
  (e.g., command injection, prompt injection, hardcoded secrets, pipeline
  taint). No SKILL-* behavioral rule appears in Pass A.
- Labels: TP or FP against the rule's CWE.
- Annotators: 1 LLM rater + 1 human auditor.
- Reliability: Cohen's κ reported across the LLM/human pair.
- Expected outcome (regression guard, not contribution): κ high; no
  per-language effect; per-language code-level **recall** unchanged between
  Cisco v2.0.9 and agent-audit SkillScanner.

### 3.2 Pass B — Behavioral description quality (the fairness target)

**Purpose:** measure the cross-lingual calibration of the behavioral rule
`SKILL-010 vague-description`, before and after.

- Languages annotated: **EN, ZH, JA, KO** (one Latin-script, three CJK).
  Other supported languages MAY be added but EN+CJK is the minimum.
- Sample size: **N ≥ 20** Skills per language flagged by `SKILL-010`.
- Annotators per language: **≥ 2 independent native speakers** of that
  language. **Not** a single LLM. **Not** the author. **Not** a non-native
  reader using machine translation.
- Annotation question (binary, rubric-anchored):

  > "Does this Skill's description contain **≥ 1 sentence** that
  > communicates the Skill's functionality, **written in the Skill's primary
  > language**?"

  YES → the `SKILL-010` flag is a **false positive**.
  NO  → the `SKILL-010` flag is a **true positive**.

- The rubric is fixed *before* any annotator sees the data. It is not
  language-specific: the same single sentence-level criterion applies in EN,
  ZH, JA, KO.

### 3.2.1 Deterministic pre-judge short-circuit (frozen v2 contract)

Not every `SKILL-010` emit comes from the LLM. The frozen judge
(`SemanticJudge`, `JUDGE_PROMPT_VERSION="v2"`) contains exactly one
deterministic non-LLM path:

> **Empty / whitespace-only descriptions** → verdict `vague`, emitted
> *without* an API call. Provenance for these emits is the version tag
> (`v2`), not the model. The verdict reason field is the literal string
> `"v2 pre-judge: empty or whitespace-only description (no LLM call)"`
> so an annotator can distinguish pre-judge emits from LLM emits at a
> glance.

Reasoning for putting this in code rather than in the prompt:

1. The empty case is **language-agnostic and certain** — there is no
   linguistic judgment to make. Routing it through the LLM would burn API
   calls and introduce a non-zero chance the model returns `cannot_judge`
   on a case where the rubric is clear.
2. Keeping the empty rule **outside** the prompt means the prompt's only
   job is to judge *content* clarity. The prompt declares (at the head of
   `JUDGE_PROMPT_V2`) that the input is guaranteed non-empty, which is
   what the pre-judge enforces. The two paths cannot disagree.
3. The "every behavioral verdict has known provenance" guarantee is
   preserved: provenance for empty-case emits is the version tag plus the
   `v2 pre-judge` reason string; provenance for non-empty emits is the
   recorded prompt sha256 and model id.

This short-circuit is **the only** non-LLM verdict path in
`skill_description_judge.py`. It is *not* a surface-statistic
heuristic for content quality (PLAN §4 anti-pattern #1): it handles the
*absence* of content, not the quality of content. Any future addition
that infers quality from a surface statistic (word count, sentence count,
keyword density) without an LLM call is a violation of this protocol.

For annotation: an annotator who lands on a `SKILL-010` emit whose
`judge_reason` starts with `"v2 pre-judge"` does not need to evaluate the
description — the description is empty by definition; the verdict is
trivially correct (`rubric_pass = false`, `verdict = TP`). Pre-judge
emits and LLM emits are counted in the same per-language precision
denominator; they are not segregated in the metric, but the annotation
file retains the distinction for diagnostic analysis.

### 3.2.2 Phase 1 freeze smoke test (out-of-corpus, native-speaker-vouched)

The Phase 1 freeze of the v2 judge is gated by a **minimal 2-sample
smoke test**, recorded in full at `eval/SMOKE_TEST_v2_freeze.md`. This
section anchors the **provenance rules** the smoke test obeys, so a
future replay can verify them without re-reading the gating artifact.

- The smoke test is **gating-only**. It produces no per-language
  precision, no Cohen's κ, no Wilson CI, no Fisher's exact, no
  Bonferroni-corrected p. It is *not* a Phase 2A evaluation. It does
  not replace Pass A or Pass B above. Anything stronger than
  "the judge is functional on at least one canonical example in each
  direction" is reserved for Phase 2A.
- The smoke test is **2 samples total**: one JA, one EN. The pass bar
  is "JA → `clear` and EN → `vague`, where the expected verdict
  comes from an independent human ground truth, not from the judge
  itself".
- The **JA sample is out-of-corpus**. The corpus-locked route was
  closed by drift (`findings/F-002_corpus_drift_survey.md`: only
  2/70 sha256-matched JA flagged rows still match origin HEAD, and
  neither maps to a "Clear JA description" annotator note). The
  out-of-corpus JA description is the `description:` field of the
  `api-design` Skill from `atomic-kanta-sasaki/claude-code-general-skills`,
  vouched by **"a Japanese native-speaker collaborator"**
  (anonymity preserved per the collaborator's preference).
- **Ground truth = the native speaker's judgment, not the judge's
  self-assessment.** Using the judge's own verdict as the ground
  truth it is then evaluated against would be circular ground truth
  (PLAN §0 constraint #3; the CAIS rejection lesson). The smoke
  test verifies *agreement* between the judge and the native
  speaker on one example; it does not verify anything self-
  referentially.
- The **EN sample is the poster's documented genuine TP**:
  `description = "build"`, labeled TP by index #18 of
  `annotations/behavioral_precision.py`.
- The smoke test must **pass before the `skillscanner-core-frozen`
  tag is created**. A failing smoke test means the v2 prompt needs
  a v3 revision before freezing — the tag must not be applied to a
  judge that has never produced a real-API verdict.

A future replay of the smoke test that returns a different verdict
than the recorded one — assuming the same model id, the same
`JUDGE_PROMPT_V2` sha256, and `temperature = 0` — is the condition
under which the freeze tag's pass invariant is in question.

### 3.3 Inter-annotator agreement (per language)

- Compute **Cohen's κ per language separately** for the ≥ 2 native annotator
  pair: κ_EN, κ_ZH, κ_JA, κ_KO.
- A single pooled κ is **forbidden** as the headline reliability number.
  Pooling κ across languages would average away exactly the cross-lingual
  variance this protocol exists to measure (PLAN §1.2).
- If κ for any language falls below 0.6, the corresponding precision number
  is reported with a stated reliability caveat and is **not** used to claim
  per-language fairness improvement for that language.

### 3.4 Adjudication

- Disagreements within a language pair are adjudicated by a third native
  speaker of that language.
- The adjudication outcome, not either original label, is the ground truth
  for that record.
- All three labels are retained in the annotation file for reliability
  computation.

---

## 4. Frozen metric definitions

### 4.1 Per-rule, per-language precision

```
behavioral_precision(language) = TP(language) / (TP(language) + FP(language))
```

reported on the **flagged sample** for that language. The denominator is
flagged-only because behavioral recall is not the contribution (PLAN §0
core claim; §4 anti-pattern #7).

### 4.2 Confidence intervals

- **Wilson 95% CI** on every reported precision proportion.
- CI half-widths reported with point estimates.

### 4.3 Hypothesis tests

- **Fisher's exact test** for pairwise comparisons of behavioral precision:
  EN vs JA, EN vs ZH, EN vs KO (one test per non-EN language).
- This is the **comparison family** for multiplicity correction.

### 4.4 Multiplicity correction

- **Bonferroni** correction across the comparison family above.
- Family-wise α = 0.05.
- Reuses the poster's α = 0.05 / (#comparisons) convention.

### 4.5 Primary success metric (the one fairness signal)

The evaluation succeeds if **all three** of the following hold under the
above tests:

1. **Non-EN behavioral precision rises.** For each of JA, ZH, KO, the
   behavioral precision of agent-audit SkillScanner is **strictly greater**
   than the Cisco v2.0.9 baseline by an amount whose Wilson 95% CI excludes
   the baseline rate, with the Bonferroni-corrected Fisher's exact p < α.
2. **EN behavioral precision does not drop.** Cisco v2.0.9 EN precision is
   inside or below the Wilson 95% CI of agent-audit SkillScanner EN
   precision (i.e., we cannot reject "EN unchanged or better").
3. **Code-level recall is unchanged.** Per-language Pass A recall of
   agent-audit SkillScanner is inside the Wilson 95% CI of Cisco v2.0.9 per
   the same flagged corpus.

If any of (1), (2), (3) fails, the evaluation is **negative** and the
scanner is not claimed to deliver the fairness contribution. There is no
backup metric, no "improved coverage," no "more findings" framing.

### 4.6 What is NOT a success signal

- Higher number of total behavioral findings.
- Higher per-language behavioral recall.
- Higher number of unique CWEs touched.
- "More languages covered" if coverage is measured by emission rather than
  by precision.

Anyone reading this protocol who concludes the goal is "find more" has
misread it.

---

## 5. Reporting template

Each evaluation run produces a row per (scanner, language) of:

| scanner | language | n_flagged | TP | FP | precision | wilson_lo | wilson_hi | fisher_p_vs_EN | bonferroni_p |
|---------|----------|-----------|----|----|-----------|-----------|-----------|----------------|--------------|
| cisco_v2.0.9 | EN | … | … | … | … | … | … | — | — |
| cisco_v2.0.9 | JA | … | … | … | … | … | … | … | … |
| agent-audit SkillScanner | EN | … | … | … | … | … | … | — | — |
| agent-audit SkillScanner | JA | … | … | … | … | … | … | … | … |

Plus a per-language κ table:

| language | κ (native pair) | n_records |
|----------|-----------------|-----------|
| EN | … | … |
| JA | … | … |
| ZH | … | … |
| KO | … | … |

---

## 6. Files in this directory

- `PROTOCOL.md` (this file) — frozen evaluation protocol.
- `schema/finding.schema.json` — JSON Schema for a single SkillScanner
  finding; the contract between scanner output and Pass A/B scoring.
- `schema/annotation.schema.json` — JSON Schema for a single annotation
  record.
- `annotation_template.csv` — header-only CSV matching the annotation
  schema; copied per (language, annotator) to start an annotation run.

The scanner's emit MUST validate against `finding.schema.json` before any
finding can enter Pass A or Pass B. A scanner output that fails schema
validation is treated as a scanner bug, not as data.

---

## 7. Freeze point — `skillscanner-core-frozen`

The Phase 1 freeze is a **single-tag freeze in one repository**. The
scanner source and the evaluation protocol live in the same git repo
(`HeadyZhang/agent-audit`, root `agent-security-suite/`): the
protocol and schemas live at `docs/skillscanner/` inside the code
repo, so one commit reaches both surfaces and one tag pins both.

An earlier draft of this section described a two-tag freeze; that was
based on a misread of the on-disk topology (the docs tree was
temporarily outside the code repo at
`/Users/heady/Documents/agent-audit/docs/skillscanner/`). The docs
tree has since been moved into the code repo at
`agent-security-suite/docs/skillscanner/` and the §7 design is
correspondingly collapsed to a single tag.

| Field | Value |
|---|---|
| Repo | `HeadyZhang/agent-audit` |
| Repo root on disk | `agent-security-suite/` |
| Branch | `feature/skillscanner` |
| Tag | `skillscanner-core-frozen` |
| Tagged commit hash | `<TBD: filled in at tagging>` |
| Tag locality | **local only**, no `git push`, no remote tag |
| Date of freeze | 2026-06-06 |

Procedure (executed at freeze time):

1. Create branch `feature/skillscanner` off the current HEAD.
2. Stage **only** the Phase 1 files: new `skill_*` analyses, the
   `SkillScanner` module, the new tests, the new fixtures, the new
   `docs/skillscanner/` tree, the additive dispatch block in
   `cli/commands/scan.py`, and the additive `judge` extra in
   `pyproject.toml` + the chunk of `poetry.lock` introduced by
   `anthropic`. Do **not** stage unrelated pre-existing modifications
   on the surrounding branch.
3. Confirm `git diff --staged` against the staged set:
   - **0 lines** of edit to `python_scanner.py`, `privilege_scanner.py`,
     `secret_scanner.py`, `taint_tracker.py`, `rules/engine.py`,
     `models/finding.py`.
   - `cli/commands/scan.py` and `pyproject.toml` edits are purely
     additive (no key removed, no logic changed).
4. Commit on `feature/skillscanner`. Capture the commit hash.
5. Edit this section (`§7`) to replace the `<TBD>` slot with the
   captured hash. Commit that edit as a follow-up commit on the
   same branch.
6. `git tag skillscanner-core-frozen` on the follow-up commit (so
   the tag points at the version of PROTOCOL.md that records its
   own hash slot).
7. **No `git push`.** No remote tag. The freeze is a local invariant.

Reproducing the freeze later: clone
`HeadyZhang/agent-audit`, `git checkout skillscanner-core-frozen`,
cross-check the §7 hash against `git rev-parse HEAD`. Any divergence
is a freeze-integrity bug.

Verifying the freeze post hoc:

- **Code freeze invariant.** `pytest tests/test_skill_scanner.py`
  from `packages/audit/` must report all SkillScanner tests passing,
  including `TestJudgeFreeze::test_prompt_text_sha256_locked` (the
  `JUDGE_PROMPT_V2` sha256 fence) and the BLOCK-ceiling exhaustive
  check.
- **Schema freeze invariant.** Every `SKILL-010` finding emitted by
  the tagged code MUST validate against
  `docs/skillscanner/eval/schema/finding.schema.json` at the tagged
  commit. The v2 → `claude-sonnet-4-6` pin in the schema's `allOf`
  cross-checks the code's frozen constants.
- **Smoke-test freeze invariant.** Replaying
  `eval/SMOKE_TEST_v2_freeze.md` §6 against the same model id,
  prompt sha256, and `temperature = 0` must reproduce
  `clear` / `vague` on the JA / EN samples respectively. A
  `cannot_judge` outcome on either sample at replay time indicates
  an upstream API issue, not a judge-logic change.
