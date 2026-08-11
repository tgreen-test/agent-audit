# PROGRESS

**Session 7 state: COMPLETE. W27–W32 all done.** Read `RUN7_REPORT.md` first (one page),
then `RELEASE_CHECKLIST.md`, which is the only file that asks anything of you.

**v0.20.0 is staged, not released.** Artifacts built and verified, both clean-venv installs
green, nothing pushed, merged, tagged or published, and no public-facing claim edited.

## Start here

**`RELEASE_CHECKLIST.md`.** Seven steps, in order. The first three change measured numbers:

1. **Three `rule_id` edits** in `tests/ground_truth/labeled_samples.yaml` — lines 1636, 1669,
   1709. The guard hook denied them and I did not work around it. Each was re-verified at
   HEAD with two scan modes agreeing. F1 **0.7467 → 0.7581**, +3 TP / −3 FP / −3 FN, zero
   detection change.
2. **The ratchet**, re-derived from the new number: `f1_min` 0.72 → **0.73**, `recall_min`
   0.81 → **0.82**, `precision_min` unchanged at 0.66. Proposed, not applied — a rising floor
   is a promise about every future build.
3. **Two `git rm`** for the dead threshold files, with the evidence in
   `docs/decisions/DEAD_FILES.md`.

Then step 4: **twenty published rule counts**, in four contradictory values (40, 49, 53, 72),
with exact replacement text. The PyPI description is the priority and is wrong in the built
artifacts, deliberately.

## The one thing the brief got wrong

**The three authorised label edits do not turn the corpus-label guard green.** Measured, not
argued: unmatchable labels go **6 → 3**, and the suite still reads `1 failed`. The three
survivors describe untrusted package acquisition in general code — a capability no rule
covers — and one of them is a `.sh` file no scanner opens.
`docs/decisions/AGENT-015_RESOLUTION.md` § 4 said this before the run started, and closing
the guard by moving those labels onto a nearby rule would recreate the drift that let one
identifier mean three things.

## Current commit

`fix/py314-blocker`.

| W | what |
|---|---|
| W27 | three retargets verified and measured on a scratch copy; ratchet re-derived; **corpus unchanged, guard denied, not bypassed** |
| W28 | `ISSUE_TRIAGE.md` — five issues reproduced at HEAD; two can close, three cannot; replies drafted, none posted |
| W29 | tree-sitter **declared, not fixed**; differential corpus + permanent test landed; the fix was written, measured and reverted |
| W30 | `docs/decisions/DEAD_FILES.md`; `METRICS_RETRACTION.md` gains the mechanism and a per-surface table with commands |
| W31 | `CAPABILITY_BOUNDARIES.md` |
| W32 | v0.20.0 staged — version bumps, classifiers, CHANGELOG, build, artifact inspection, two clean-venv installs, `RELEASE_CHECKLIST.md` |

## Invariants at the end of the run

| invariant | result |
|---|---|
| Layer 1 | **TP 196 / FP 93 / FN 40**, P 0.678201 / R 0.830508 / F1 0.746667 — unchanged from RUN5 and RUN6 |
| run-to-run spread | **zero** — ten identical runs, six decimals, three hash seeds |
| `quality_gate_check.py` | **exit 0** |
| full suite | **1796 passed, 1 failed, 3 skipped** — the failure is the corpus-label guard, still red on purpose |
| `git diff -- packages/ rules/` | version bump in 3 files + 2 classifier lines. **No detection code changed.** |
| advertised rules | **66** |
| thresholds changed | **none** |
| built artifacts | sdist + wheel, 98 package files each, identical contents, zero forbidden paths, zero target-identifying strings |
| clean-venv installs | **3.12.12 and 3.14.3, both `agent-audit, version 0.20.0`, both scanning identically** |

## The five things a reader needs

1. **The tree-sitter question is answered, and the answer is no.** Issue #12's fix — plus the
   `PyCapsule` wrap it does not mention, plus a version pin that makes the declared extra
   inoperable — was applied, measured, and reverted. Live, the AST path **loses 2 true
   positives, adds 6 known false positives and breaks 42 tests**. TypeScript/JavaScript
   analysis is regex-level and is now documented as such.
2. **The differential's first version certified a build that was failing 40 tests.** It
   contained only the eval and child_process families, so it could not see the regression. An
   insensitive differential is worse than none. The corpus was rebuilt from the test classes
   that actually moved, and the test now has a vacuity guard: an empty differential over a
   dead path skips loudly instead of passing.
3. **#10 is not fixed and #8 is one-quarter fixed.** Both reproduce at HEAD from the
   reporter's own case. Closing an issue that still reproduces costs more than leaving it
   open.
4. **The 98.51% was a goal recorded as an achievement**, not a stale measurement. The "→ 100%"
   values are the v0.4.1 brief's *target* block. That changes the correction from an update to
   a withdrawal, because there is no commit to update them *to*.
5. **`CAPABILITY_BOUNDARIES.md` is the artifact worth keeping.** It states the limits, carries
   the blind-audit 0/6, and names the structural reason the whole defect class survived: a
   rule that never fires and a clean codebase produce identical output, so nothing that
   observes output can tell them apart.

## Still open, in priority order

* **Run `scripts/finalize_run7.sh`** — one script, written session 8 and deliberately unrun,
  doing the three changes the guard denies me: the three item-39 `rule_id` edits, the ratchet
  (`f1_min` 0.73, `recall_min` 0.82), and the two dead-file `git rm`s. Each step diffs and
  verifies itself; it stops short of measuring, so re-run `precision_recall.py` after it and
  check § 1's prediction, F1 0.746667 → 0.758095. It has only been parse-checked, never
  executed. Ledger § W33.
* **`DECISIONS.md` item 39, rows 2–4** — the three remaining unmatchable AGENT-015 labels.
  Build the supply-chain rule, or mark them as known-uncovered. Either closes the guard
  honestly; retargeting them does not.
* **`DECISIONS.md` item 35** — four unlabelled true positives in `vulnerable_hooks`.
* **`DECISIONS.md` item 36** — AGENT-049, detected at 0.85 and discarded for want of a YAML
  definition.
* **`METRICS_RETRACTION.md` § 5 step 1** — which external surfaces carry the 98.51%. Only you
  can answer it, and it gates the rest of the retraction.
* **Issues #10 and #8** — receiver typing, and a provenance model that separates configuration
  from user input. These are the tool's two largest measured false-positive sources.

## Environment

`python` is NOT on PATH — use `python3` (3.14.3). Session 7 created venvs under the
scratchpad only: `venv312` (uv-provided CPython 3.12.12), `venv314`, `venv-build`, and four
tree-sitter matrix venvs. Nothing was installed globally and no existing `agent-audit`
installation was touched.

## Guard-hook friction

Four denials, none bypassed: the authorised ground-truth `Edit`; a scan command whose
`2>/dev/null` made the guard scan a fixture path token; an `rm -rf` on a scratch directory;
and a `grep` denied for the same redirect reason. Each was solved by changing the command,
never by editing the hook or assembling a path at runtime. The false-positive direction
remains the safe one.
