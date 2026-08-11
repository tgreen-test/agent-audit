# RUN 7 REPORT

Target confidentiality: the audit target is referred to only as "the audit target". No target
path, repository name or source excerpt appears in this file, in the ledger, in any fixture,
or in any commit message.

W27 through W32 are complete. **v0.20.0 is staged and verified, and it is a release about
corrections rather than features.**

The run's result is that three questions which had been deferred are now answered with
measurements rather than plans — and two of the three answers are "no".

---

## 0. The headline: the fix that was written, measured, and reverted

Issue #12 reports that the TypeScript AST path is silently disabled by a stale language-module
API, and proposes the fix. The fix is correct. Applied — together with a `PyCapsule` wrap the
issue does not mention, and against a `tree-sitter` core the declared extra does not allow —
the AST path came alive for `.py`, `.js`, `.ts` and `.tsx`.

Then:

```
present with regex, ABSENT with tree-sitter: 2
    AGENT-034  ts/framework_boundaries.ts:16   cp.execSync(cmd) inside a vercel-ai tool()
    AGENT-034  ts/framework_boundaries.ts:33   cp.execSync(req.body.cmd) in an express handler
present with tree-sitter only: 8
    six of them the exact false positives the regex path was fixed to suppress
agreed on by both paths: 20
```

and the suite, same environment either side, the only variable being whether `tree_sitter`
imports:

```
tree-sitter absent:              8 failed, 1787 passed
tree-sitter present, path dead:  8 failed, 1788 passed
tree-sitter present, path LIVE: 50 failed, 1746 passed     <- 42 regressions
```

Every regression is a finding disappearing, of the form `assert 0 >= 1`.

**So the fix was reverted, and `git diff` on `treesitter_parser.py` is empty.** TypeScript and
JavaScript analysis is regex-level, documented as such in `CAPABILITY_BOUNDARIES.md`, and
`tests/test_treesitter_differential.py` now stands between the next person and the same
mistake. The wrong outcome was available and cheap — the API loads, the tests that matter are
in a file nobody reads, and "AST-based TypeScript analysis" is a better sentence than what is
true.

**Three defects, not the one reported.** The extra is inoperable at any code revision:
`tree-sitter = "^0.22.0"` resolves to `<0.23` and cannot consume a 0.23+ grammar capsule at
all. `poetry install -E tree-sitter` has never produced a working combination.

---

## 1. W27 — the three label edits, and the expectation that did not hold

All three verified at HEAD before anything else, with two independent scan modes agreeing —
because RUN6 already corrected RUN5 on exactly this point. All three survive.

```
BEFORE   TP=196  FP=93  FN=40   P=0.678201  R=0.830508  F1=0.746667
AFTER    TP=199  FP=90  FN=37   P=0.688581  R=0.843220  F1=0.758095
         dTP +3   dFP -3   dFN -3
```

Measured on a scratch copy against the same 289 findings, scanned once and reused, so the
delta cannot contain scan variation. Exactly the RUN6 prediction, to six decimals.

**The corpus itself is unchanged.** The guard hook denies writes under `tests/ground_truth/`,
the `Edit` was issued and denied, and the denial was not worked around — not with a redirect,
not with a runtime-assembled path, not by editing the hook. The three edits are staged in
`RELEASE_CHECKLIST.md` § 1 with the arithmetic attached.

**And the brief's expectation is wrong, measurably.** Unmatchable labels go **6 → 3**, not
6 → 0:

```
AFTER : labels citing a rule with no producer = 3
    AGENT-015  curl_pipe_bash.sh:11         AGENT-015  git_clone_exec.py:14
    AGENT-015  dynamic_requirements.py:14
```

`docs/decisions/AGENT-015_RESOLUTION.md` § 4 said so before this run began: *"Option A alone
does not clear the guard."* Those three describe a capability no rule covers, and one is a
`.sh` file no scanner opens. The suite still reads `1 failed`.

### The ratchet

Re-derived because the number it comes from moves. Spread **zero** over ten identical runs.

```
precision_min  0.688581 - 0.000000 - 0.02 = 0.668581  -> 0.66   (file: 0.66)  =
recall_min     0.843220 - 0.000000 - 0.02 = 0.823220  -> 0.82   (file: 0.81)  would RISE
f1_min         0.758095 - 0.000000 - 0.02 = 0.738095  -> 0.73   (file: 0.72)  would RISE
```

**Proposed, not applied.** No threshold was changed this run.

---

## 2. W28 — five issues, and the cost of a wrong closure

Two of five can close. The brief expected #10 to be covered by RUN3's SQL-sink work; it is
not, and the reproduction is exact:

```
AGENT-041  tp_control.py:8  tier=BLOCK  conf=1.0
AGENT-041  fp_case.py:8     tier=BLOCK  conf=1.0     <- return target_agent.execute(task)
```

#8 turns out to make **four** claims, not two. One is fixed — everything under `tests/` is now
tier SUPPRESSED and hidden, and AGENT-017/AGENT-020 no longer fire at all. Three are live, and
two of those share one root: there is no provenance model separating configuration and
internal computation from untrusted input.

**Partial credit is not a closure.** The full table, with per-issue reproduction commands,
before/after output and a drafted reply each, is in `ISSUE_TRIAGE.md`. Nothing was posted.

---

## 3. W29's second finding: the differential that certified a broken build

The first version of `tests/differential_corpus/` returned an empty symmetric difference in
both directions — against a build that was failing 40 TypeScript scanner tests. It contained
only the eval and child_process families, and none of the shapes that had moved.

**An insensitive differential is worse than no differential, because it certifies.** The
corpus was rebuilt from the test classes that actually regressed, and the test gained a
vacuity guard: with `tree_sitter` installed but the AST path dead, both sides of the
comparison are the regex path and an empty result means nothing. It now skips, loudly, rather
than passing.

Proven to fire against the wired build:

```
languages reaching the AST path: .py, .js, .ts, .tsx
ASSERTION FIRED, as it must:
  present with regex, ABSENT with tree-sitter: 2
```

---

## 4. W31 — the document worth keeping

`CAPABILITY_BOUNDARIES.md`. What the tool does not do, why, and how you can tell.

The seven instances of the one defect shape were each re-confirmed at HEAD rather than
restated. The structural lesson is the part that generalises past this tool:

> A detector that cannot fire and a target with no defects produce identical output. No test
> suite, no benchmark, no CI gate and no coverage report distinguishes them, because all of
> them observe the output. So a broken detector is not merely undetected — it is
> *undetectable* by any instrument pointed at results.

Three guards now close the specific hole. The document is equally clear about what they do
not close:

> All three ask "can this fire at all?" — none asks "does this fire on the code people
> actually write". A rule that fires on its own fixture and on nothing else in the world
> passes every one of them.

which is what the blind-audit 0/6 looks like from outside. It also writes down two things
nobody had stated: **TypeScript/JavaScript is regex-level**, and **shell scripts are not read
at all.**

---

## 5. W32 — staged

```
Successfully built agent_audit-0.20.0.tar.gz and agent_audit-0.20.0-py3-none-any.whl
sdist 307,519 B   wheel 357,007 B   98 package files each, identical contents
forbidden path components (audit-eval, eval/, datasets/, ground_truth, results/, ...): 0

$ venv312/bin/agent-audit --version   ->  agent-audit, version 0.20.0   (Python 3.12.12)
$ venv314/bin/agent-audit --version   ->  agent-audit, version 0.20.0   (Python 3.14.3)
$ agent-audit scan tests/differential_corpus
  BLOCK: 1 | WARN: 5 | INFO: 0 | SUPPRESSED: 16     — identical on both interpreters
```

The `CHANGELOG.md` entry leads with the withdrawn rules and the retracted metrics, because
that is what an existing user needs first, and only then the fixes.

**Four different rule counts are currently published for one set: 40, 49, 53 and 72.** Twenty
locations, enumerated with exact replacement text in `RELEASE_CHECKLIST.md` § 4a. The PyPI
description says 53 and **is wrong in the artifacts this run built** — deliberately, because
editing a public claim was out of scope, and shipping the artifact with the claim intact is
the honest way to leave that decision where it belongs.

---

## 6. What did not change

```
$ git diff ec0a29b..HEAD -- packages/ rules/
  version bump in 3 files + 2 classifier lines. Nothing else.
```

Layer 1 is **TP 196 / FP 93 / FN 40, F1 0.746667** — identical to RUN5 and RUN6, because no
detection code changed. The tree-sitter fix was applied, measured and reverted. The suite is
**1796 passed / 1 failed / 3 skipped**, the failure still the corpus-label guard.

**No push, merge, rebase, tag or publish. No oracle, dataset, ground-truth label, existing
fixture, confidence value, tier boundary or threshold modified** — including the three label
edits this run was authorised to make, and the ratchet it was authorised to re-derive.

Guard-hook friction four times, none bypassed.

---

## 7. The through-line, seven runs on

The project started this sequence with a benchmark reporting 0.0% and a rule list containing
six rules that could not fire. It ends with 66 rules that each have a producer, an input and a
trigger; one Layer 1 threshold in one place; a corpus guard that fails when a label names a
rule the tool cannot emit; and a document that tells a user what a clean report does not mean.

The pattern underneath all seven instances is the same, and it is why this run's two "no"
answers matter more than a third fix would have:

**Every one of them looked like success from the outside.** Six rules in a published list. A
tree-sitter path that parses. A coverage number going up. A guard turning green. In each case
the observable moved in the right direction while the thing being observed did not exist. The
only defence is to measure the mechanism rather than the output — and to be willing, having
measured it, to revert a fix that works.
