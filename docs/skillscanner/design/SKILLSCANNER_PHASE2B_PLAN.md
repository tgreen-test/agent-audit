# SkillScanner Phase 2B Plan — Packaging, OpenClaw Integration, Demo

> Companion spec for `SKILLSCANNER_PHASE2B_PROMPT.md`. This is the **what and why**;
> the prompt file is the **how**. Claude Code MUST read this fully before any code.
> Phase 2B builds **against the frozen tag** `skillscanner-core-frozen`. It is the
> engineering/distribution phase — it does NOT touch evaluation, the frozen judge,
> the v2 prompt, the schema, or any 2A artifact.

---

## 0. What Phase 2B is, and what it must not borrow from 2A

Phase 2B turns the frozen SkillScanner into something people can install, run, and
adopt: PyPI distribution, OpenClaw ecosystem integration, CI usage, and a demo.
The goal serves the "tool landing / stars / OpenClaw / demo" objective.

**The hard separation from 2A:** Phase 2A produces the fairness numbers
(precision, TOST). Those numbers are NOT YET FINAL — they depend on human
annotation still in flight. Therefore:

- **Phase 2B must NOT state any precision/fairness number in any user-facing
  artifact** (README, OpenClaw listing, demo narration, release notes). Leave a
  placeholder and fill it ONLY after 2A completes and the human-annotated TOST
  result is known. Claiming "fixes multilingual bias, JA precision X%" before the
  annotation returns repeats the CAIS pre-evidence-claim mistake.
- Phase 2B may describe the **mechanism** ("language-aware semantic description
  judging instead of English-style heuristics; fail-closed on unsupported
  languages") because that's a design fact, not an unproven result. It may NOT
  describe the **outcome** ("X% precision improvement") until 2A lands.
- The honest framing until 2A completes: "designed to avoid the English-centric
  calibration bias documented in [poster]" — a design claim, not a measured one.

## 1. Build base & hard constraints

1. Build against `skillscanner-core-frozen`. Do NOT modify frozen code, the v2
   judge, constants, schema, or any `eval/` artifact. Phase 2B is additive
   packaging/integration on top of the frozen core.
2. The `judge` optional extra pattern stays: `pip install agent-audit[judge]`
   enables the semantic judge; without it, NullJudge fallback (behavioral rule
   silently disabled). Never make the Anthropic SDK a hard runtime dependency.
3. No credentials in code or config. The judge reads `ANTHROPIC_API_KEY` from env;
   this tool flags hardcoded credentials — do not ship one.
4. No precision/fairness numbers in user-facing text until 2A lands (§0).
5. Keep everything local until the human explicitly authorizes a publish/push.
   PyPI upload, OpenClaw submission, and git push are all human-gated.

## 2. Workstreams (independent; can be done in any order)

### 2.1 Packaging & distribution (PyPI)

- Confirm `pyproject.toml` exposes the SkillScanner CLI path and the `judge`
  extra cleanly. Version bump per the project's scheme (coordinate with the
  pre-existing in-flight version work — do NOT clobber it).
- `agent-audit scan path/to/SKILL.md` must work end-to-end from a clean install
  in a fresh venv (test this — the freeze tests pass in-repo, but a clean-install
  smoke test catches packaging gaps).
- Verify the F-005 surrogate-encoding bug does NOT crash a user-facing scan:
  a lone-surrogate description must degrade gracefully (skip that row with a
  logged warning), not abort the run. **Fix this OUTSIDE the frozen surface** —
  an input-sanitization layer wrapping the judge, NOT an edit to the frozen
  `skill_description_judge.py` (editing it breaks the v2 sha256 fence and the
  schema pin). Prefer this over a `JUDGE_PROMPT_VERSION` bump, which would
  invalidate the 2A evaluation's comparability.
- Build sdist + wheel; do a clean-room install test. Do NOT upload to PyPI
  without human go.

### 2.2 OpenClaw ecosystem integration

- SkillScanner's natural home: scanning Agent Skills, which is exactly the
  OpenClaw/ClawHub ecosystem. Produce an OpenClaw-compatible integration
  (the existing `agent-audit-scanner` ClawHub pattern is the precedent).
- Output must be consumable: ensure SARIF output works for SKILL.md scans so it
  drops into existing CI/security-review pipelines.
- **Community-first rule (hard):** do NOT post in the OpenClaw Discord or submit
  to ClawHub until the human says so — there's prior history of a ban for posting
  tools without community participation. Build the integration; the human decides
  when/whether to surface it publicly.

### 2.3 CI / GitHub Actions

- Provide a GitHub Action that runs SkillScanner on SKILL.md files in a repo and
  emits SARIF to the security tab.
- **Severity separation for CI gating** (this is a real design point from the
  poster's implication #3): code-level findings (language-agnostic) may gate;
  behavioral SKILL-010 (WARN ceiling) must NOT hard-fail CI — it's advisory,
  requiring human judgment. The Action config must reflect this: behavioral
  findings annotate, never block.

### 2.4 Demo

- The single most compelling demo artifact: a side-by-side on ONE real Skill
  where Cisco's English-style heuristic false-flags a clear non-English (JA)
  description as vague, and SkillScanner correctly clears it. Use the
  provenance-clean Yoshi-vouched JA sample from the Phase 1 smoke test (the
  `api-design` skill description) — it's already human-verified clear, already
  has recorded provenance, and the v2 judge already returns `clear` on it.
- Record as asciinema or a short screen capture. Narrate the MECHANISM (semantic
  vs surface-statistic), NOT an unproven precision number.
- The demo is mechanism illustration, not evidence — keep that honest. The
  evidence is 2A; the demo shows how it works on one case.

## 3. Phasing & gates

- **2B.1** — Packaging: clean-install smoke test + F-005 graceful-degradation fix
  (outside frozen surface). Gate: fresh-venv install runs end-to-end.
- **2B.2** — SARIF + GitHub Action with behavioral-non-gating. Gate: Action runs
  on a sample repo, SARIF lands, behavioral findings annotate-not-block.
- **2B.3** — OpenClaw integration built (NOT submitted). Gate: integration works
  locally; surfacing held for human.
- **2B.4** — Demo recorded with mechanism narration, precision placeholder.
- Each gate: stop, surface, wait. No publish/push/submit without explicit go.

## 4. Anti-patterns (reject the work if any appear)

- [ ] Any precision/fairness number in user-facing text before 2A completes.
- [ ] Editing the frozen judge/schema/code (incl. "fixing" F-005 inside the
      frozen module — must be an external sanitization layer).
- [ ] Behavioral SKILL-010 configured to hard-fail CI (must be advisory).
- [ ] Hardcoded API key anywhere.
- [ ] Anthropic SDK as a hard runtime dependency (must stay optional extra).
- [ ] Posting to OpenClaw Discord / ClawHub before human authorization.
- [ ] PyPI upload / git push without explicit human go.
- [ ] Bumping JUDGE_PROMPT_VERSION to fix F-005 (invalidates 2A comparability).

## 5. Out of scope

- Phase 2A evaluation (separate, in flight, human-annotation-blocked).
- Phase 3 paper writing (consumes 2A's numbers).
- Any fairness claim stated as a measured result (belongs to 2A/Phase 3).
