# Claude Code Execution Prompt — SkillScanner Phase 2B (Packaging / OpenClaw / Demo)

Execute the roadmap in `SKILLSCANNER_PHASE2B_PLAN.md`. **Read it in full first.**
Phase 2B builds **against the frozen tag `skillscanner-core-frozen`**. It is
engineering/distribution only — it does NOT touch evaluation (Phase 2A, in
flight), the frozen judge, the v2 prompt, the schema, or any `eval/` artifact.

---

## Global rules

1. **Verify the frozen base first.** Confirm `skillscanner-core-frozen` exists;
   branch from it (`feature/skillscanner-dist`). Confirm SkillScanner module tests
   pass on the tagged state before anything.
2. **No precision/fairness number in any user-facing artifact** (README, OpenClaw
   listing, demo, release notes) until Phase 2A's human-annotated result lands.
   Use a placeholder. You MAY describe the mechanism (semantic vs surface-statistic
   judging, fail-closed on unsupported languages); you may NOT state an outcome.
3. **Additive only.** Do not edit frozen code/judge/schema. The F-005 fix is an
   EXTERNAL sanitization wrapper, never an edit to the frozen module, and NEVER a
   JUDGE_PROMPT_VERSION bump (that invalidates 2A comparability).
4. **Community-first / no public surfacing without go.** Do not post to OpenClaw
   Discord or submit to ClawHub. Do not upload to PyPI. Do not git push. All
   public/publish actions are human-gated.
5. **No hardcoded credentials.** Judge reads ANTHROPIC_API_KEY from env; the
   `judge` optional extra stays optional (NullJudge fallback without it).
6. **Stop at every sub-phase gate.** Surface and wait.

---

## 2B.1 — Packaging & clean-install (gate)

1. Inspect `pyproject.toml`: confirm the SkillScanner CLI entry and the `judge`
   optional extra are exposed correctly. Do NOT clobber the pre-existing in-flight
   version/extra work (the 0.19.0 bump + report extra) — coordinate additively.
2. Build sdist + wheel. In a FRESH venv, install the wheel (with and without
   `[judge]`) and run `agent-audit scan` on a sample SKILL.md end-to-end. This
   catches packaging gaps the in-repo tests miss.
3. **F-005 graceful-degradation fix, OUTSIDE the frozen surface:** wrap the judge
   call so a lone-surrogate (or otherwise un-encodable) description is skipped
   with a logged warning instead of aborting the scan. Implement as a sanitization
   layer in a NEW module that wraps the frozen judge — do NOT edit
   `skill_description_judge.py`, do NOT bump JUDGE_PROMPT_VERSION. Add a test:
   a lone-surrogate description → scan completes, that row is skipped+warned.

Verify: fresh-venv install runs end-to-end both with and without `[judge]`;
surrogate input no longer aborts; `git diff` shows zero edits to frozen modules.
**STOP. Surface install-test results + the F-005 wrapper diff. Wait.**

## 2B.2 — SARIF + GitHub Action (gate)

1. Confirm SARIF output works for SKILL.md scans (drops into CI security tabs).
2. Provide a GitHub Action that scans SKILL.md files and emits SARIF.
3. **Behavioral non-gating (hard requirement):** configure so code-level findings
   may gate CI, but behavioral SKILL-010 (WARN ceiling) NEVER hard-fails — it
   annotates only. This encodes the poster's severity-separation implication.

Verify: Action runs on a sample repo, SARIF lands, a SKILL-010 finding annotates
without failing the build.
**STOP. Surface the Action config + a sample run. Wait.**

## 2B.3 — OpenClaw integration (build, do NOT submit) (gate)

1. Build an OpenClaw/ClawHub-compatible integration following the existing
   `agent-audit-scanner` ClawHub precedent.
2. Ensure output is consumable in that ecosystem.
3. **Do NOT submit to ClawHub. Do NOT post in OpenClaw Discord.** Build locally,
   surface what would be submitted, and HOLD — the human decides if/when to
   surface publicly (prior ban history for posting without community presence).

Verify: integration works locally against a sample Skill.
**STOP. Surface the integration + the would-be submission. Wait for explicit go.**

## 2B.4 — Demo (gate)

1. Build a side-by-side on ONE real Skill: Cisco's English-style heuristic
   false-flags a clear JA description as vague; SkillScanner clears it. Use the
   Yoshi-vouched `api-design` JA sample from the Phase 1 smoke test (already
   human-verified clear, provenance recorded, v2 returns `clear`).
2. Record as asciinema / short screen capture. Narrate the MECHANISM (semantic
   judging vs surface statistics), NOT a precision number. Leave any quantitative
   claim as a placeholder pending 2A.
3. Keep it honest: the demo illustrates how it works on one case; it is NOT
   evidence. Evidence is Phase 2A.

Verify: demo runs, narration is mechanism-only, no unproven number stated.
**STOP. Surface the demo + script. Do not publish it.**

---

## Final report format

At each gate: what was produced, the verification result, and the §4 anti-patterns
you confirmed you did not hit (especially: no precision claim, no frozen-surface
edit, behavioral non-gating, nothing published/pushed/submitted). Surface blockers
rather than working around them. Hold all publish/push/submit actions for explicit
human authorization.
