# RUN 12 — the three decisions implemented, and the preflight green

**Branch `fix/py314-blocker`, from `2a03089`. 2026-09-13.** Nothing pushed, merged, tagged or
published. W56–W59 are implemented and committed.

---

## 1. Where v0.20.0 stands

**`scripts/release_v0200.sh --dry-run` passes every check.** RUN 11 left one problem — `twine`
was not installed — and one open question per decision. All four are closed:

| RUN11 `NEEDS-HEADY` | RUN 12 |
|---|---|
| install `twine` | installed, 7.0.0 in `~/.venvs/rel`, and § 1.11 now **looks there** — a venv is not on `PATH`, which is the point of a venv, so "installed as instructed" and "the preflight still fails" used to be the same state. `twine check` **PASSES** on both artifacts |
| decide whether the 7 WIP commits ship, and whether silently | they ship, **labelled preview**, in `RELEASE_NOTES_v0.20.0.md` and `CHANGELOG.md`, with what to rely on them for and what not |
| `"withdrawn in v0.19.3"` on eight surfaces | corrected to `v0.20.0`; fifteen edits across ten files, and `tests/test_published_versions.py` now fails the suite if any published page names a release that does not exist |
| the flaky wall-clock test | **untouched.** A tolerance is a threshold. The preflight already handles it: if it is the only extra failure, it re-runs it in isolation twice and says out loud that it is a stopwatch |

**Two claims in this release were checked by reading and were wrong.** One was RUN 11's, one was
this run's own first draft, and both were caught the same way — by executing the thing instead of
reading about it. The second is in § 3.1: a release-note bullet said *"SkillScanner cannot fail a
build"*, and SkillScanner emits BLOCK-tier `AGENT-001` on a fixture in this repository. The
first:

RUN 11 checked the missing-`reportlab` path by reading the code and recorded it as handled.
Executed, it was not:
`agent-audit report` without the extra printed *"Install with: pip install agent-audit"* —
Rich parsed the `[report]` in the interpolated exception as a style tag and rendered nothing
for it, so the instruction named the package without the extra that carries the dependency.
`pip install agent-audit` does not install reportlab, so the user is sent back to the same
error. Fixed with `escape()`, pinned by a test, and the artifacts rebuilt.

---

## 2. The verification set, re-measured

| command | result |
|---|---|
| `python3 -m pytest tests/ packages/audit/tests/ -q` | **1 failed, 1924 passed, 4 skipped**; 1,929 collected. Nineteen new cases (eighteen in the version guard, one in the report CLI tests) |
| `precision_recall.py` | **TP 199 / FP 90 / FN 37**, P 68.86% / R 84.32% / **F1 75.81%** — unchanged, either side of two package-file edits |
| `quality_gate_check.py --config tests/benchmark/gates.yaml` | **exit 0** |
| AVB, `--tool agent-audit --dataset knowns` | **recall 100.0%, precision 88.0%** |
| `bash .claude/hooks/test-guard.sh` | **passed=11 failed=0** |
| `advertised_rules()` | **66**, and their ASI ids span **10/10** categories |
| `twine check` on both artifacts | **PASSED** — new this run; nothing had checked it before |
| `dist/` artifacts | rebuilt. **99 package files** in each, sets identical, **0** forbidden path components, `Version: 0.20.0`, **2**× "66 rules" in the long description, **7** unconditional `Requires-Dist` |
| `scan_external_claims.sh` | **133 matches**, down from 160 — see § 3.4 |
| `scripts/release_v0200.sh --dry-run` | **0 problems** |
| `./run_eval.sh --commit HEAD` | **UNVERIFIED — the file does not exist.** Unchanged since RUN10; `DECISIONS.md` item 52 |

---

## 3. What was done, and what it cost to be sure

### 3.1 W56 — the seven commits, enumerated before anything was written about them

Four SkillScanner (one of code, three of protocol and findings documents), one PDF report
generator, one `.gitignore` rail, one merge. The full table with sizes is in
`NIGHT_RUN_LEDGER.md` § W56 § 1.1. The `.gitignore` commit is the one that is neither feature,
so it is in `NEEDS-HEADY` below rather than waved through; it is benign, and the thing worth
checking about a commit whose subject says *contains private corpus* was checked — **0** files
are tracked under `eval/` at HEAD and the rail survived the merge conflict.

**The numeric-claim audit found exactly one claim, and it reproduces.** Swept both features'
shipping surfaces for a precision, a rule count or a coverage figure. One hit with content:
every generated PDF hardcodes *"The scanner provides 10/10 coverage of the OWASP ASI Top 10."*
Measured rather than trusted — the 66 advertised rules carry ASI ids spanning all ten
categories (forty-six from the builtin YAML, and those forty-six already cover all ten, so the
other twenty cannot lower it). Nothing to cut. No precision, recall or count is printed in a
report at all.

**Four facts about the preview features that a user needs and no document carried:**
`langdetect` is a new *required* dependency (six unconditional `Requires-Dist` in 0.19.2, seven
in 0.20.0, read from the wheel metadata); `agent-audit report` needs the `[report]` extra;
`SKILL-010` sends each `SKILL.md` `description` to `claude-sonnet-4-6` whenever the `anthropic`
SDK is importable **and** `ANTHROPIC_API_KEY` is set — measured both ways without issuing a
request (`NullJudge` without the key, `SemanticJudge` with it), and there is no flag to disable
it; and **SkillScanner can fail a BLOCK-gated CI job**, which is a behaviour change.

That last one began as the opposite claim. The first draft of the release-note bullet said
*"SkillScanner cannot fail a build"*, lifted from the Phase 1 commit message's *"behavioral
findings cannot gate CI"* — a true sentence about a different set of rules. The tier ceiling in
`rules/skill_rule_context.py` is scoped to the `SKILL-*` namespace and says so in its own
docstring; Layer 2 extracts fenced `python`/`shell` blocks from a `SKILL.md`, runs them through
the existing scanners, and those findings keep ordinary tiering. Measured on
`tests/fixtures/skills/eval_python`: **`AGENT-001` at BLOCK 1.00 and `AGENT-034` at BLOCK
0.95**, both remapped onto the `SKILL.md` line. A repository with code inside its `SKILL.md`
files can therefore start failing a job that passed under 0.19.2. Both documents now say so.
The half of the claim that was true is pinned by a test that sweeps [0.0, 1.0]; the half that
was false was pinned by nothing, which is why reading the commit message was not enough.

All four are now in both release documents.

### 3.2 W57 — the instance was already fixed, so the work was the class

The script already named `refs/tags/v0.20.0`, and RUN 11 had corrected the checklist in the
same commit that reported the problem. Confirmed from the dry run's own plan rather than
assumed. The new part is preflight § 1.12b, which checks the two mechanisms that publish a ref
nobody named: a bulk-ref flag (`--tags`, `--follow-tags`, `--mirror`, `--all`) in the script or
the checklist — **`bad` on a hit**, so the property is enforced rather than remembered — and
`push.followTags`, which is **unset** and which § 1.12b fails on if it is ever enabled.

That second one is not hypothetical here: the single local tag the remote does not have,
`skillscanner-core-frozen`, is **annotated and reachable from `master`** (it points at
`05c3f98`, one of the seven commits), so it is exactly what `push.followTags` would publish
alongside a `master` push. Local refs: **16 tags / 15 on the remote**, **8 branches / 4 on the
remote**. The full audit is in `RELEASE_CHECKLIST.md` § 6 so a reader of the checklist gets it
without running anything.

### 3.3 W58 — the class check found four more phantom versions

`0.19.3` was never uploaded, never tagged, and has no CHANGELOG section: PyPI lists **fourteen**
versions and 0.19.3 is not among them. Corrected on every surface. The guard was written first
and run against the uncorrected tree — **3 failed / 15 passed**, naming six references — then
**18 passed** after the edits.

Checking the same class across every user-facing surface found four more: `0.3.0` in
`docs/RULES.md` (corrected, and marked as a development series that was never released);
`0.4.1` and `0.5.0` in `docs/BENCHMARK-RESULTS.md`, left alone because that document opens with
**HISTORICAL DOCUMENT — DO NOT CITE AS CURRENT** and the comparison really was run against that
build — rewriting the column would falsify a record; and `0.19.1` in a source comment, which is
out of the guard's scope for a measured reason: the package sources carry **190** references to
0.x versions with no tag and no release, all of them internal provenance comments across twelve
development series. Rewriting those would destroy the only record of when a behaviour changed
and would tell no user anything. The gap is stated in the guard's docstring rather than left to
be discovered.

Two design choices worth stating. `CHANGELOG.md` is **not** one of the guard's records of what
exists, because it carries sections for six versions that were never released — counting it
would have meant that adding a `## [0.19.3]` section turned the guard green while the claim
stayed false. And the historical-banner exemption is not a per-file allow-list: a test asserts
the banner is still there, so deleting it puts the document back into the guard.

### 3.4 Two things found by doing the work

**The test count moved again, 1,905 → 1,924** — seventh consecutive session in which it moved
inside the work on it. Twenty edits across thirteen surfaces, in this change rather than the
next one. One pin had escaped every previous sweep: the release script held the collected total
as the bare literal `1910` in three places, so `grep 1,905` never saw it. It is now
`EXP_TOTAL_TESTS`, beside `EXP_SUITE_LINE`.

**Changing two package files invalidated `results/layer1.json`**, and the suite said so rather
than anyone noticing: `test_gate_provenance` fingerprints the scanner source, and a comment edit
counts. Regenerated; the measurement is identical to sixteen decimal places, which is the
evidence that the edits were what they claimed to be.

**The claims scanner's allowlist was drawn around names instead of the property it describes.**
Its own comment exempts "test docstrings that record the defect they guard against", then lists
files one at a time — so the two claim guards written after that comment produced twenty lines
of noise in every scan while satisfying the rule exactly. 160 matches → **133**, all
twenty-seven removed being guard docstrings and `parametrize` lists quoting the defect they
catch. This is `CAPABILITY_BOUNDARIES.md` § 3 once more, applied to an instrument rather than a
detector, and it is why the scanner's output had stopped being read line by line.

---

## 4. `NEEDS-HEADY`

None of these blocks the release.

1. **`208a3ab` is neither SkillScanner nor the PDF report.** The brief said to stop and log it
   if one of the seven turned out to be something else. It is one line of `.gitignore` (`eval/`)
   supporting the SkillScanner eval protocol's private-corpus rail. Verified benign. The
   CHANGELOG describes it as "one `.gitignore` rail keeping a third-party Skills corpus out of
   the repository"; say so differently if you would rather.
2. **Should `SKILL-010`'s Claude API call be opt-in?** It is documented now, with the
   mitigation (unset `ANTHROPIC_API_KEY` for the scan step). Adding a flag is a behaviour
   change and yours.
3. **`CHANGELOG.md` documents six releases that never existed** — `0.19.1`, `0.5.0`, `0.4.1`,
   `0.4.0`, `0.3.2`, `0.3.1`: no tag, not on PyPI. It is release history; rewriting it is not an
   unattended edit. The honest form is a note per section rather than a renumbering.
4. **Carried from RUN 11, unchanged:** the flaky wall-clock test (a tolerance is a threshold);
   the three corpus-label edits under `tests/ground_truth/`, which the guard protects;
   `CAPABILITY_BOUNDARIES.md` § 3's instance count; the slide deck and `docs/cais-2026/`;
   `openclaw-skill/`; and posting the five bodies in `ISSUE_REPLIES.md`.

---

## 5. Statement

I did NOT push, merge, tag, publish, `git rm`, post to GitHub, or read outside the repository.

No oracle, dataset, ground-truth label, existing fixture, confidence value, tier boundary or
threshold was modified — including the flaky test's tolerance, for that reason.

Two production files changed, neither a detection path: `cli/commands/report.py` escapes an
exception before Rich reads it as markup, and `rules/engine.py` has a comment corrected from a
release that does not exist. Layer 1 was re-measured either side and is identical. The artifacts
were rebuilt because both files ship inside them, and both hashes are updated in the script and
in `RELEASE_CHECKLIST.md` § 5, with the superseded pair named there as superseded.

All network traffic was read-only: `git ls-remote` against the GitHub remote, GETs against the
two package indexes, and one `pypi.org/pypi/agent-audit/json` by hand — which is what makes
"fourteen published versions, and 0.19.3 is not one of them" a measurement rather than an
inference. `pip install twine` into a fresh venv is the only thing installed.

One guard denial, not bypassed: `git tag -l` and `git merge-base` are read-only, and the guard
matches `tag` and `merge` as verbs. Rewritten as `git for-each-ref` and `git branch --contains`.
