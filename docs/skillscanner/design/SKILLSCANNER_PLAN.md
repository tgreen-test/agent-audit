# SkillScanner Plan — Cross-Lingual Skills Security (Phase 0 + Phase 1)

> Companion spec for `SKILLSCANNER_PROMPT.md`. This document is the **what and why**;
> the prompt file is the **how to execute**. Claude Code MUST read this file fully
> before writing any code.

---

## 0. Provenance & Non-Negotiable Constraints

This work extends `agent-audit` to scan `SKILL.md` packages, motivated by the
AgentSkills '26 poster *"Do Agent Skills Speak Safety in Every Language?"*
(Zhang, Yuan, Nian, Zhao). The poster **diagnosed** a multilingual calibration
bias in Skills scanners (behavioral heuristics produce 3–5× more false positives
on non-English Skills; JA behavioral precision 0%, EN 10%). This project
**fixes** that bias and ships the fix as a tool.

### Core claim (memorize — every design decision serves this)

> We did **not** invent new vulnerability categories. We **fixed** the
> multilingual calibration bias in Skills scanning, raising non-English
> behavioral precision from near-zero to English-comparable levels **without
> degrading English precision or any code-level recall.**

This is a **fairness / calibration** contribution, NOT a detection-capability
contribution. Do not write code or evaluation that implies "we detect more
vulnerabilities." If a reviewer would ask "did your recall improve?", the framing
has drifted — recall is not the story.

### Hard constraints (violating any of these fails the task)

1. **Additive-only.** No edits to existing logic in `PythonScanner`,
   `PrivilegeScanner`, `SecretScanner`, `TaintTracker`, or `RuleEngine` core.
   The new `SkillScanner` *consumes* these via their public interfaces.
   Every change verified with `git diff` after each step.
2. **Tool-task match is mandatory.** `SKILL.md` is Markdown frontmatter +
   multilingual natural-language prose + fenced code blocks. It is NOT Python
   source. The 12% precision failure in the original cross-lingual work came
   from feeding Markdown to a Python-source scanner. The code-block extraction
   layer exists precisely to route only *real code* to the code scanners.
3. **No circular ground truth.** The scanner's own output is NEVER used as
   ground truth. (This is the CAIS rejection lesson.) Ground truth comes from
   independent native-speaker annotation (Phase 0 protocol below).
4. **Fail-closed-to-silent on the behavioral layer.** When language support or
   the semantic judge is unavailable, the description-quality rule is
   **disabled** (emits nothing), never falls back to the English heuristic.
   A disabled rule is correct; a false positive is not.
5. **Behavioral findings never reach BLOCK.** Tier ceiling for all behavioral
   rules is WARN. Code-level findings keep their existing tier logic.
6. **Reuse the published dataset.** `HeadyZhang/skills-crosslingual-security`
   (3,656 Skills, 8 languages, CC BY 4.0). No synthetic data.

---

## 1. Phase 0 — Annotation Protocol (do FIRST, before code)

Phase 0 produces a frozen **annotation protocol document + schema**, not code.
It exists first because the annotation schema *defines the SkillScanner finding
fields* — the scanner must emit exactly what the evaluation will score.

### 1.1 What Phase 0 delivers

- `eval/PROTOCOL.md` — the human-facing annotation guide.
- `eval/schema/finding.schema.json` — JSON Schema for a SkillScanner finding,
  the shared contract between scanner output and annotation.
- `eval/schema/annotation.schema.json` — JSON Schema for one annotation record.
- `eval/annotation_template.csv` — empty annotation sheet generator.

### 1.2 Annotation design (write into PROTOCOL.md)

**Two annotation passes, mirroring and extending the poster's design:**

- **Pass A — Code-level (language-agnostic).** Label security-tier findings
  (command injection, prompt injection, hardcoded secrets, pipeline taint) as
  TP/FP against CWE. One LLM rater + one human, Cohen's κ reported. This pass
  is the *control*: the poster showed code-level has no cross-lingual gap, so we
  expect κ high and no language effect. It anchors that our code layer didn't
  regress.

- **Pass B — Behavioral description quality (the fairness target).**
  For each language in {EN, ZH, JA, KO}, sample N≥20 Skills flagged by the
  description-quality rule. **Each language annotated by ≥2 independent native
  speakers** (not a single LLM, not the author). The annotator answers a single
  binary question with a fixed rubric:

  > "Does this description contain ≥1 sentence that communicates the Skill's
  > functionality, written in the Skill's primary language?"
  > YES → the flag is a false positive. NO → the flag is a true positive.

  Report per-language precision with Wilson 95% CI and inter-annotator Cohen's κ
  **per language** (κ must be reported separately for JA, ZH, KO, EN — a single
  pooled κ hides exactly the cross-lingual effect we study).

### 1.3 Baseline lock

The comparison baseline is **Cisco Skill Scanner v2.0.9, unmodified** — the
exact version the poster evaluated. The evaluation is a clean before/after:
*Cisco v2.0.9* vs *agent-audit SkillScanner (language-aware)* on the identical
3,656-Skill corpus. The baseline is never our own prior version.

### 1.4 Frozen metric definitions (write into PROTOCOL.md)

- **Behavioral precision (per language)** = TP / (TP + FP) on the flagged sample.
- **Primary success metric**: JA behavioral precision rises from ~0% toward
  EN-comparable, AND EN behavioral precision does not drop, AND code-level
  recall is unchanged (regression guard).
- **Statistics**: Wilson CI for every precision; Fisher's exact for
  EN-vs-non-EN pairwise; Bonferroni across the comparison family. Reuse the
  poster's α = 0.05 / (#comparisons).

### 1.5 Phase 0 exit criteria

PROTOCOL.md + both schemas + template exist; `finding.schema.json` validates a
hand-written example finding; the metric definitions are unambiguous enough that
an annotator who never saw this project could follow them. **No scanner code yet.**

---

## 2. Phase 1 — SkillScanner Core (the build)

A new, standalone `SkillScanner` module. Four layers, in dependency order.

### 2.1 Layer 1 — Frontmatter parsing & Skill validation

**File:** `agent_audit/scanners/skill_scanner.py` (new) +
`agent_audit/analysis/skill_frontmatter.py` (new helper).

- Parse YAML frontmatter from `SKILL.md` (the `---` delimited head).
- A file **with no valid YAML frontmatter is NOT a Skill** → emit a single
  INFO `SKILL-000 not-a-skill` and **skip all behavioral analysis**. This
  directly resolves the poster's "23% of JA files are non-Skill files (game
  docs, portfolios) matched by filename" contamination. Non-Skills must not
  enter the behavioral denominator.
- Extract: `name`, `description`, `risk` annotation (if any),
  `restricted_tools` (if any), primary-language hint (if declared).

### 2.2 Layer 2 — Code-block extraction → reuse verified scanners

**File:** `agent_audit/analysis/skill_code_extractor.py` (new).

- Extract fenced code blocks; classify by info-string (`python`, `bash`/`sh`,
  unmarked).
- Route **Python blocks** through the existing `PythonScanner` AST path
  (taint analysis, eval/exec, SQL injection) — **call its public interface,
  do not modify it.**
- Route **shell blocks** through the existing privilege/pipeline-taint logic
  for `curl | sh`, `find -exec /bin/sh` patterns (poster Case 1).
- This layer is **language-agnostic** — the poster proved no cross-lingual gap
  here. It is reused as-is and **frozen**. Map code-block findings onto existing
  AGENT-* rule IDs; do not invent new code-level rule IDs.

### 2.3 Layer 3 — Language-aware description quality (CORE CONTRIBUTION)

**File:** `agent_audit/analysis/skill_language_router.py` (new) +
`agent_audit/analysis/skill_description_judge.py` (new).

- **Language router**: detect primary language via `langdetect` + CJK Unicode
  block correction (reuse the poster's correction). Output one of the supported
  languages or `unsupported`.
- **Semantic description judge** (replaces whitespace/keyword-density heuristics):
  - Input: `description`, detected `language`.
  - Question: "Does this description clearly communicate the Skill's
    functionality, judged in its own language?" → structured `{verdict, reason}`.
  - Implemented behind an **interface** `DescriptionJudge` with two backends:
    1. `SemanticJudge` — calls the Claude API semantic layer (the same pattern
       used in defi-shield). Prompt must instruct the model to judge clarity in
       the *target language* and return strict JSON.
    2. `NullJudge` — the fail-closed backend: returns "cannot judge" → rule emits
       nothing.
  - **Routing rule (this is the fix):**
    - language ∈ supported AND judge available → run `SemanticJudge`.
    - language == `unsupported` OR judge unavailable OR API error →
      use `NullJudge` → **emit no behavioral finding** (constraint #4).
  - **Never** fall back to an English-style surface-statistic heuristic. There is
    no such heuristic in this module by design.
- Emits rule `SKILL-010 vague-description` ONLY on a real negative verdict.

### 2.3.1 Judge Freeze (reproducibility — NON-NEGOTIABLE)

The semantic judge is a stochastic external dependency. If its model, sampling,
or prompt drift between runs, the Phase 2A precision numbers cannot be
reproduced — which directly breaks the evaluation-rigor goal. Therefore the
judge is **frozen** as a set of constants, exactly as we freeze verified code
layers. These constants live in one place (`skill_description_judge.py`) and are
treated as part of the experimental record.

**Frozen constants:**

| Constant | Frozen value | Why |
|----------|-------------|-----|
| `JUDGE_MODEL` | `"claude-sonnet-4-6"` | Pinned version string, **never** the `sonnet` alias. Aliases re-point over time and would silently change results across runs. Sonnet (not Opus) is the right tier: clarity judgment is lightweight and high-frequency; Opus adds cost/latency without accuracy gain for this task. Do NOT use `claude-sonnet-4-20250514` — that version is retired on the API. |
| `temperature` | `0` | Minimize non-determinism so the same `(description, language)` yields a stable verdict across runs. |
| `max_tokens` | `300` | Verdict + short reason only. |
| `JUDGE_PROMPT_VERSION` | `"v1"` | Tag the exact prompt text. Any wording change MUST bump this tag; a precision number is only comparable within one prompt-version. The version tag is recorded in every emitted finding and every annotation record. |

**Result caching (cost + reproducibility):**
- Key the cache on `sha256(description) + language + JUDGE_MODEL +
  JUDGE_PROMPT_VERSION`. Identical inputs under the same frozen judge never
  re-hit the API — this both cuts cost on the 3,656-Skill corpus and guarantees
  a rerun reuses prior verdicts rather than re-sampling.
- Only invoke the judge on Skills the cheap pre-filter has flagged; never call
  it on the full corpus indiscriminately.

**Provenance stamping:** every `SKILL-010` finding records the
`JUDGE_MODEL` and `JUDGE_PROMPT_VERSION` that produced it, so Phase 2A can
verify all findings in a comparison came from one frozen judge. The
`finding.schema.json` from Phase 0 must accommodate these two fields (add them
if absent).

**On freeze:** these constants are fixed at the Phase 1 freeze tag. Changing any
of them after `skillscanner-core-frozen` invalidates prior Phase 2A numbers and
requires a re-run — treat a change as a new experiment, not a patch.

### 2.4 Layer 4 — Tiering & policy separation

**File:** integrate via the existing `confidence_to_tier` mechanism; add a new
small config `agent_audit/rules/skill_rule_context.py`.

- Behavioral rules (`SKILL-010`, autonomy-abuse if added) have a **tier ceiling
  of WARN** — they can be INFO or WARN, never BLOCK. (poster implication #3:
  behavioral flags require human judgment, must not gate CI.)
- Code-level findings surfaced via Layer 2 keep their existing AGENT-* tiering.
- Policy findings (missing license, invalid metadata) are INFO only.

### 2.5 New rule IDs (Skill-namespaced, additive)

| Rule | Tier ceiling | Meaning | Layer |
|------|--------------|---------|-------|
| `SKILL-000` | INFO | File lacks valid frontmatter → not a Skill | 1 |
| `SKILL-010` | WARN | Description does not communicate functionality (semantic verdict) | 3 |
| `SKILL-020` | INFO | Missing license / metadata policy violation | 4 |
| (code-level) | existing | Reuse AGENT-* IDs from PythonScanner/privilege path | 2 |

Do not reuse `AGENT-*` numbers for behavioral Skill rules; keep the namespaces
separate so the evaluation can cleanly separate code-level from behavioral.

### 2.6 Phase 1 exit criteria & FREEZE POINT

- `agent-audit scan path/to/SKILL.md` runs end-to-end.
- A non-frontmatter file emits only `SKILL-000`, no behavioral finding.
- A JA Skill with a clear Japanese description emits **no** `SKILL-010`
  (this is the single most important behavioral test — it is the exact false
  positive the poster documented).
- An EN Skill with description "build" emits `SKILL-010` (poster's genuine TP).
- A Skill with `curl | sh` in a shell block emits the existing pipeline-taint
  code-level finding.
- `git diff` confirms zero changes to existing scanner logic.
- Unit tests green; new tests added for each layer.

**At this point, `git tag skillscanner-core-frozen`.** Logic is frozen; only
packaging, OpenClaw adapter, and the evaluation harness proceed after this.

---

## 3. What is explicitly OUT of scope for this file pair

- Phase 2A evaluation harness (separate file pair, built against the frozen tag).
- Phase 2B packaging / OpenClaw integration / demo recording.
- Phase 3 fairness framing write-up.
- These depend on the frozen core and the Phase 0 protocol; they are not built
  here. The dependency order is: Phase 0 → Phase 1 (freeze) → {2A eval, 2B
  engineering} in parallel → Phase 3 framing (consumes 2A numbers).

---

## 4. Anti-patterns checklist (reject the work if any appear)

- [ ] Any whitespace/word-count/keyword-density heuristic for description quality.
- [ ] Behavioral finding emitted when language is unsupported or judge errored.
- [ ] Behavioral finding at BLOCK tier.
- [ ] A non-frontmatter file producing behavioral findings.
- [ ] Edits to existing scanner logic (must be additive).
- [ ] Scanner output used as ground truth anywhere.
- [ ] Any claim or test implying improved detection/recall as the contribution.
