# Claude Code Execution Prompt — SkillScanner (Phase 0 + Phase 1)

You are extending the `agent-audit` repository. Execute the roadmap in
`SKILLSCANNER_PLAN.md`. **Read that file in full before writing anything.** It is
the source of truth for *what* and *why*; this file is *how*.

---

## Global rules (apply to every step)

1. **Read before write.** Before touching any existing module, open it and read
   its public interface. You will CALL `PythonScanner`, `PrivilegeScanner`, and
   the `confidence_to_tier` / `RuleEngine` paths — you will NOT modify their
   internal logic. After every change, run `git diff` and confirm existing files
   show no logic edits.
2. **Additive-only.** New functionality lives in new files. The only permitted
   touch to existing files is registering the new scanner at the dispatch point
   (`cli/commands/scan.py`) and the rule map — and only by *adding* entries.
3. **Phase gates are hard.** Do not start Phase 1 until Phase 0 exit criteria
   pass. Do not declare Phase 1 done until its exit criteria pass and you have
   created the freeze tag.
4. **The contribution is fairness/calibration, not detection.** Do not write any
   code, comment, or test that frames the goal as "detecting more." If you find
   yourself adding a heuristic that *increases* behavioral findings, stop — that
   is the opposite of the goal.
5. **Fail-closed behavioral layer.** When in doubt about language or judge
   availability, emit nothing on the behavioral rule. A silent disable is always
   preferable to a false positive.

---

## PHASE 0 — Annotation protocol (no scanner code)

### Step 0.1 — Read context
- Read `SKILLSCANNER_PLAN.md` §0–§1 fully.
- Read enough of the existing finding/Finding dataclass and `RuleEngine` to know
  the shape of an existing finding (rule_id, severity/tier, file, line, message,
  confidence). Your `finding.schema.json` must be compatible with it.

### Step 0.2 — Write the protocol & schemas
Create:
- `eval/PROTOCOL.md` — encode PLAN §1.2 (two passes), §1.3 (baseline lock =
  Cisco v2.0.9 unmodified), §1.4 (frozen metrics: Wilson CI, Fisher's exact,
  Bonferroni; primary success = JA precision ↑, EN not ↓, code recall unchanged).
  Pass B must specify **≥2 native-speaker annotators per language** and
  **per-language Cohen's κ**.
- `eval/schema/finding.schema.json` — JSON Schema for a SkillScanner finding.
  Fields at minimum: `rule_id`, `tier`, `language`, `file`, `line`, `message`,
  `confidence`, `layer` (one of frontmatter|code|behavioral|policy).
- `eval/schema/annotation.schema.json` — one annotation record: `skill_id`,
  `language`, `rule_id`, `annotator_id`, `verdict` (TP|FP), `rubric_pass`
  (bool: "≥1 functional sentence in primary language"), `notes`.
- `eval/annotation_template.csv` — header row matching the annotation schema.

### Step 0.3 — Verify Phase 0
- [ ] Hand-write one example finding JSON; validate it against
      `finding.schema.json` (use `python -c` with `jsonschema`). It must pass.
- [ ] PROTOCOL.md states the baseline is Cisco Skill Scanner v2.0.9 unmodified.
- [ ] PROTOCOL.md requires ≥2 native annotators per language and per-language κ.
- [ ] PROTOCOL.md primary success metric matches PLAN §1.4 exactly (fairness, not
      recall).
- [ ] No scanner code written yet.

**STOP. Confirm all four boxes before Phase 1.**

---

## PHASE 1 — SkillScanner core

### Step 1.1 — Layer 1: frontmatter & Skill validation
Create `agent_audit/analysis/skill_frontmatter.py` and the skeleton of
`agent_audit/scanners/skill_scanner.py`.
- Parse `---`-delimited YAML head. Extract `name`, `description`, `risk`,
  `restricted_tools`, declared language hint.
- No valid frontmatter → emit only `SKILL-000` (INFO), set a flag that **disables
  all behavioral analysis** for this file.
- Register `.md` / `SKILL.md` dispatch in `cli/commands/scan.py` **additively**.

Verify: a file without frontmatter yields exactly one `SKILL-000` and nothing
behavioral. `git diff` shows only additive dispatch registration.

### Step 1.2 — Layer 2: code-block extraction (reuse + freeze)
Create `agent_audit/analysis/skill_code_extractor.py`.
- Extract fenced blocks; classify `python` / `bash`|`sh` / unmarked.
- Python blocks → call existing `PythonScanner` public scan interface.
- Shell blocks → route through existing privilege/pipeline-taint logic
  (`curl | sh`, `find -exec /bin/sh`).
- Reuse existing AGENT-* rule IDs for code-level findings; invent none.

Verify: a SKILL.md containing `curl -L ... | sh` in a shell block produces the
existing pipeline-taint code-level finding. A SKILL.md with `eval(user_input)` in
a python block produces the existing eval finding. `git diff` shows NO edits to
`PythonScanner` / `PrivilegeScanner` internals.

### Step 1.3 — Layer 3: language-aware description judge (CORE)
Create `agent_audit/analysis/skill_language_router.py` and
`agent_audit/analysis/skill_description_judge.py`.
- Router: `langdetect` + CJK Unicode correction → supported language or
  `unsupported`.
- Define interface `DescriptionJudge` with `judge(description, language) ->
  {verdict: clear|vague|cannot_judge, reason: str}`.
- `SemanticJudge`: Claude API backend (mirror defi-shield's semantic layer
  pattern). Prompt the model to judge functional clarity **in the target
  language** and return strict JSON. Wrap in try/except: any API error →
  `cannot_judge`.
  - **Use the frozen constants from PLAN §2.3.1 exactly — do not choose your
    own:** `JUDGE_MODEL = "claude-sonnet-4-6"` (pinned version string, never the
    `sonnet` alias, never the retired `claude-sonnet-4-20250514`),
    `temperature = 0`, `max_tokens = 300`, `JUDGE_PROMPT_VERSION = "v1"`. Define
    these as module-level constants in `skill_description_judge.py`.
  - **Key from env, never hardcoded:** read `ANTHROPIC_API_KEY` from the
    environment. (This tool flags hardcoded credentials; do not hardcode one.)
  - **Cache verdicts:** key on
    `sha256(description) + language + JUDGE_MODEL + JUDGE_PROMPT_VERSION`;
    identical inputs must not re-hit the API.
  - **Stamp provenance:** every `SKILL-010` finding records `JUDGE_MODEL` and
    `JUDGE_PROMPT_VERSION`. Confirm `finding.schema.json` (Phase 0) has these two
    fields; add them if missing.
- `NullJudge`: always returns `cannot_judge`.
- Routing: supported language AND SemanticJudge available → SemanticJudge;
  else NullJudge. `cannot_judge` and `clear` → **emit nothing**. Only `vague`
  emits `SKILL-010`.
- **There must be no surface-statistic (word count, keyword density, sentence
  count) code path anywhere in this module.**

Verify with the two decisive tests:
- [ ] JA Skill with a clear Japanese description → **no** `SKILL-010`.
- [ ] EN Skill with description `"build"` → `SKILL-010` emitted.
- [ ] `unsupported`-language Skill → **no** `SKILL-010` (NullJudge path).
- [ ] Simulated API error → `cannot_judge` → **no** `SKILL-010`.

### Step 1.4 — Layer 4: tiering & policy
Create `agent_audit/rules/skill_rule_context.py`; wire SkillScanner findings
through the existing `confidence_to_tier`.
- `SKILL-010` and any behavioral rule: **tier ceiling = WARN** (clamp in code;
  assert it can never be BLOCK).
- `SKILL-020` (missing license / metadata) → INFO.
- Code-level findings from Layer 2 keep existing tiering untouched.

Verify: a unit test asserts no behavioral SkillScanner finding can be assigned
BLOCK regardless of confidence.

### Step 1.5 — Tests
Add `tests/test_skill_scanner.py` covering each layer, including the four
decisive Layer-3 cases and the BLOCK-ceiling assertion. Build small fixture
`SKILL.md` files under `tests/fixtures/skills/` for: no-frontmatter,
clear-JA-description, vague-EN-description, unsupported-language,
curl-pipe-sh-shell-block. Run the full suite; all green.

### Step 1.6 — Freeze
- [ ] All Phase 1 exit criteria in PLAN §2.6 pass.
- [ ] `git diff` confirms zero logic edits to existing scanners.
- [ ] Full test suite green.
- [ ] Run through the PLAN §4 anti-patterns checklist; none present.
- Then: `git tag skillscanner-core-frozen` and report the tag.

**After the freeze tag, STOP.** Phase 2A (evaluation harness) and Phase 2B
(packaging / OpenClaw / demo) are separate file pairs built against this tag. Do
not begin them in this run.

---

## Final report format

When you stop, report exactly:
1. Phase 0: files created + the one-line confirmation each verify box passed.
2. Phase 1: files created per layer, the four decisive Layer-3 test results, the
   BLOCK-ceiling assertion result, and the `git diff` additive-only confirmation.
3. The freeze tag name.
4. Anything that blocked you or any constraint you could not satisfy (do not
   silently work around a constraint — surface it).
