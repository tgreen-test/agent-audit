# v0.20.0 release checklist

> **Status, 2026-09-13 (RUN 12). The preflight passes clean — `scripts/release_v0200.sh
> --dry-run` reports 0 problems, where RUN 11 left 1. Steps 1–5 are DONE and re-verified.
> What remains is two edits outside this repository, then steps 6–7, and nothing in this
> repository is waiting on a decision.**
>
> **What RUN 12 closed.** The three things RUN 11's preflight surfaced that no document
> recorded, all three decided by Heady and implemented here: the seven pre-existing commits
> ship **labelled preview** (`CHANGELOG.md` and `RELEASE_NOTES_v0.20.0.md` now name
> SkillScanner, `agent-audit report` and the new required `langdetect` dependency); the push
> publishes **one ref per step**, with § 1.12b now enforcing that as a class — see the ref
> audit in § 6; and `"withdrawn in v0.19.3"` — a version that was never released — is
> corrected to v0.20.0 on every surface, with `tests/test_published_versions.py` failing the
> suite if a published page ever names a release that does not exist. `twine` is installed.
>
> **One thing RUN 12 found by executing a path RUN 11 read:** `agent-audit report` without
> the `[report]` extra printed *"Install with: pip install agent-audit"*, because Rich ate the
> `[report]` as a style tag. Fixed and pinned; the artifacts were rebuilt, so § 5's hashes
> moved again.
>
> **Status, 2026-09-12 (RUN 11). Steps 1–5 are DONE and re-verified; the artifacts were
> rebuilt this run because one of them was wrong.**
>
> **Blocker A is answered for the paper.** Heady corrected `paper/main.tex` and re-uploaded
> the arXiv paper. That closes row B's paper item and removes the ordering constraint that
> `METRICS_RETRACTION.md` § 5 placed on everything downstream of it. It says nothing about
> the slide deck or `docs/cais-2026/`, which are separate surfaces and still carry the
> retracted set. **Nothing outside this repository was read or edited in RUN 11** — the
> brief placed it out of scope — so rows B and C are reported from RUN10's findings, not
> re-verified.
>
> **New this run, and it would have shipped:** `packages/audit/README.md` published
> "60+ rules" — a *sixth* count, on the file that renders as the PyPI project page. Fixed,
> guarded, and the artifacts rebuilt; see § 5. The three documents that define the current
> Layer 1 figures were also stale and are corrected; `NIGHT_RUN_LEDGER.md` § W52.
>
> **Execution order — and the first item genuinely gates the rest.**
>
> | # | step | state |
> |---|---|---|
> | **A** | **Establish whether any external material is already submitted, on arXiv, or presented** | **answered for the paper.** It was on arXiv; Heady has corrected `paper/main.tex` and re-uploaded. Still unanswered for the deck and `docs/cais-2026/` |
> | **B** | **Correct the external surfaces** — ~~`paper/main.tex:325` + `main.pdf`~~ (done by Heady), `agent-audit-slides.html`, `docs/cais-2026/` (5 files) | **two of three remain.** Located and itemised with line numbers in `RUN10_REPORT.md` § 2. Out of scope in RUN 11; nothing outside the repo was read or edited |
> | **C** | **Look at `openclaw-skill/`** — not scanned (skipped as not-a-paper-repo), but checklist § 2.7 names the ClawHub listing as an outreach destination | **not done** |
> | 6 | merge, tag, publish | **not done, and now staged, with a preflight that passes clean.** `scripts/release_v0200.sh` does all six steps behind a preflight and a per-stage confirmation. `twine` 7.0.0 is installed in `~/.venvs/rel`, where § 1.11 now looks for it (`TWINE_BIN` overrides), and `twine check` **PASSES** on both artifacts. `--dry-run` reports **0 problems**. The guard blocks every mutating step for an automated session, correctly — a human runs it |
> | 7 | the issue replies | **not done.** Five bodies ready in `ISSUE_REPLIES.md`, re-confirmed current in RUN 11; #10 and #12 close on posting, #8 and #11 stay open, #5 is deferred with labels |
>
> **Do not start B before A.** `METRICS_RETRACTION.md` § 5: nothing new is published on top of
> a surface that still carries a retracted figure — and a v2 with a change note is a different
> piece of writing from a correction to a draft.
>
> **Two verified results that reduce B:** `paper/neurips/submission/` has **0 matches** and
> `paper/skillsworkshop/` (the SkillScanner camera-ready and poster) is clean. And
> `paper/main.tex:401`'s "100\% recall on injection/RCE and MCP" is **true** — AVB Set A 19/19,
> Set B 9/9, re-measured at v0.20.0 — so it must **not** be retracted with the rest.
>
> **Re-run the claims scanner before trusting any earlier sweep.** It was broken until
> 2026-09-10: 18 of its 34 patterns silently matched nothing. `EXTERNAL_CLAIMS_CHECKLIST.md`
> § 4.
>
> Steps 1–5 below are kept as the record of what was done and why. Current measured values:
> **TP 199 / FP 90 / FN 37, P 0.688581 / R 0.843220 / F1 0.758095**; suite **1,924 passed, 1
> failed by design, 4 skipped**.

The branch is `fix/py314-blocker`. Nothing has been pushed, merged, tagged or published.

---

# Record of steps 1–5 (done)

## 1. The three corpus-label edits — the one change I was authorised to make and could not

`.claude/hooks/night-guard.sh` protects `tests/ground_truth/`, so the `Edit` was issued and
denied. It was not worked around. Apply these three, and nothing adjacent.

All three were re-verified at HEAD before being written down, with two independent scan
modes agreeing — a whole-corpus scan and a single-file scan of each fixture:

| yaml line | file:line the label points at | from | to | what actually fires there |
|---|---|---|---|---|
| `tests/ground_truth/labeled_samples.yaml:1636` | `asi-02-tool-misuse/direct/subprocess_unsandboxed.py:8` | `AGENT-036` | `AGENT-001` | AGENT-001 at line 9, within tolerance |
| `tests/ground_truth/labeled_samples.yaml:1669` | `asi-04-supply-chain/direct/npm_install_runtime.py:13` | `AGENT-015` | `AGENT-001` | AGENT-001 at line 13, exact |
| `tests/ground_truth/labeled_samples.yaml:1709` | `asi-04-supply-chain/indirect/pypi_typosquatting.py:12` | `AGENT-015` | `AGENT-034` | AGENT-034 at line 14, within tolerance |

Each is a single-token change on the `rule_id:` line:

```
:1636   -        rule_id: "AGENT-036"
        +        rule_id: "AGENT-001"
:1669   -        rule_id: "AGENT-015"
        +        rule_id: "AGENT-001"
:1709   -        rule_id: "AGENT-015"
        +        rule_id: "AGENT-034"
```

Also review the `owasp_id` on line 1670: row 2 moves from an ASI-04 label onto an ASI-02
rule, which shifts one expectation between per-ASI recall buckets. That is a judgement call
and is not part of the three.

Then confirm — measured on a scratch copy, so this is a prediction you can check exactly:

```bash
cd packages/audit && python3 ../../tests/benchmark/precision_recall.py
```

```
BEFORE   TP=196  FP=93  FN=40   P=0.678201  R=0.830508  F1=0.746667
AFTER    TP=199  FP=90  FN=37   P=0.688581  R=0.843220  F1=0.758095
```

**Zero detection code changes.** The scan is byte-identical either side; only the scoring key
moves. Each label corrects three counters at once, because a mislabelled detection is scored
as a miss *and* as a false alarm.

### What this does NOT do

**It does not turn the corpus-label guard green.** Measured:

```
BEFORE: labels citing a rule with no producer = 6
AFTER : labels citing a rule with no producer = 3
    AGENT-015  asi-04-supply-chain/direct/curl_pipe_bash.sh:11         (yaml:1679)
    AGENT-015  asi-04-supply-chain/direct/git_clone_exec.py:14         (yaml:1689)
    AGENT-015  asi-04-supply-chain/indirect/dynamic_requirements.py:14 (yaml:1699)
```

`tests/test_corpus_label_rules.py` still fails, and the suite still reads `1 failed`. Those
three labels describe a capability the tool does not have — untrusted package or code
acquisition in general application code — and `curl_pipe_bash.sh` is a `.sh` file no scanner
opens. `docs/decisions/AGENT-015_RESOLUTION.md` § 4 sets out both ways to close them, and
warns against the third: retargeting them onto an approximately-related rule to make a guard
go green would recreate exactly the drift that let one identifier mean three things.

---

## 2. The ratchet — proposed, not applied

Re-derived after step 1 because the number it comes from moves. Method unchanged: measured
minus observed run-to-run spread minus a 0.02 margin, truncated. **Spread is zero across ten
identical runs** (seven default seeds plus `PYTHONHASHSEED` 0, 1, 42), six decimal places.

| threshold | measured | spread | − 0.02 | derived | in `gates.yaml` | |
|---|---|---|---|---|---|---|
| `precision_min` | 0.688581 | 0.000000 | 0.668581 | **0.66** | 0.66 | unchanged |
| `recall_min` | 0.843220 | 0.000000 | 0.823220 | **0.82** | 0.81 | **would rise** |
| `f1_min` | 0.758095 | 0.000000 | 0.738095 | **0.73** | 0.72 | **would rise** |

**I did not raise them.** A rising ratchet is a promise about every future build and it is
yours to make deliberately. If you take it:

```bash
# tests/benchmark/gates.yaml, layer1.thresholds
#   recall_min: 0.81  ->  0.82
#   f1_min:     0.72  ->  0.73
python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml   # must exit 0
```

Do it **only after** step 1. Raising the floor before correcting the labels that raise the
measurement puts CI one point underwater.

---

## 3. The two dead threshold files

Full evidence in `docs/decisions/DEAD_FILES.md`, including the run with both files moved
aside where the guard self-test, the singleton test and `quality_gate_check.py` all still
pass. Nothing in the repository loads either one.

```bash
git rm tests/benchmark/quality_gates.yaml
git rm tests/benchmark/quality_gates_v2.yaml
```

Verify:

```bash
bash .claude/hooks/test-guard.sh                                                   # 11/11
python3 -m pytest tests/test_layer1_gate_singleton.py -q                           # 11 passed
python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml  # exit 0
```

`tests/README.md:40` lists `quality_gates.yaml` in the tree and will describe a file that no
longer exists. That edit is part of step 4, not this one.

---

## 4. The public claims — every location, with the replacement text

**I edited none of these.** They are counts and metrics on surfaces users read, and changing
them is a publishing decision.

### 4a. The rule count: 66

> **Applied. This table is now a record, not a work list.** Every one of the locations below
> was corrected in the RUN10/RUN11 passes and `tests/test_published_rule_count.py` guards all
> nineteen whole-set counts — measured 2026-09-12, all nineteen read 66. Do **not** paste the
> right-hand column onto a surface without checking it first: this table is exactly the shape
> of document that `METRICS_RETRACTION.md` § 3a turned out to be, a list of replacement values
> that went stale while the surfaces it described were corrected. One row here had already
> gone stale that way and is marked.

`docs/RULES.md:1419` already says 66 and is correct. Everything below did not, when this
table was written.

| file:line | as written | replace with |
|---|---|---|
| `packages/audit/pyproject.toml:4` | `… secret detection. 53 rules mapped to OWASP Agentic Top 10.` | `… secret detection. 66 rules mapped to OWASP Agentic Top 10.` |
| `README.md:28` | `with 72 rules mapped to the [OWASP Agentic Top 10 (2026)]` | `with 66 rules mapped to the [OWASP Agentic Top 10 (2026)]` |
| `README.md:272` | `RuleEngine -- 72 Rules x OWASP Agentic Top 10 -- Findings` | `RuleEngine -- 66 Rules x OWASP Agentic Top 10 -- Findings` |
| `README.md:287` | `72 detection rules covering all 10 categories` | `66 detection rules covering all 10 categories` |
| `README_CN.md:29` | `当前已有 72 条规则` | `当前已有 66 条规则` |
| `README_CN.md:253` | `RuleEngine -- 40+ Rules x OWASP Agentic Top 10 -- Findings` | `RuleEngine -- 66 Rules x OWASP Agentic Top 10 -- Findings` |
| `README_CN.md:266` | `72 条规则覆盖 …全部 10 类` | `66 条规则覆盖 …全部 10 类` |
| `docs/index.html:7` | `<meta name="description" … 49 rules mapped to OWASP Agentic Top 10.">` | `… 66 rules mapped to OWASP Agentic Top 10.">` |
| `docs/index.html:10` | `<meta property="og:description" … 49 rules, OWASP Agentic Top 10 coverage …` | `… 66 rules, OWASP Agentic Top 10 coverage …` |
| `docs/index.html:896` | `v0.16.0 — 49 rules · 10/10 OWASP coverage · 1,142 tests passing` | **stale prescription — the file now reads** `v0.20.0 — 66 rules · 10/10 OWASP coverage · 1,924 tests`, which is the measured count; 1,796 was the count when this row was written |
| `docs/index.html:1190` | `49 rules · dedup · confidence tiers` | `66 rules · dedup · confidence tiers` |
| `docs/index.html:1207` | `49 detection rules mapped to every category` | `66 detection rules mapped to every category` |
| `docs/ARCHITECTURE.md:74` | `# Rule reference (40 rules)` | `# Rule reference (66 rules)` |
| `docs/ARCHITECTURE.md:134` | `(40 rules)` | `(66 rules)` |
| `docs/ARCHITECTURE.md:234` | `**Coverage: 10/10 ASI categories, 40 rules total**` | `**Coverage: 10/10 ASI categories, 66 rules total**` |
| `docs/README.md:12` | `Complete list of 40+ detection rules with OWASP mapping` | `Complete list of 66 detection rules with OWASP mapping` |
| `docs/README.md:199` | `**Coverage: 10/10 ASI categories, 40+ rules**` | `**Coverage: 10/10 ASI categories, 66 rules**` |
| `docs/ROADMAP.md:18` | `10/10 ASI categories, 40+ detection rules` | `10/10 ASI categories, 66 detection rules` |
| `docs/blog/hackernews-post.md:27` | `40+ rules mapped to the OWASP Agentic Top 10 [1]` | published post; correct only if the page is editable |
| `docs/blog/launch-post.md:84` | `**40+ detection rules** mapped to all 10 OWASP Agentic categories` | published post; same caveat |

**Four different numbers — 40, 49, 53, 72 — are currently published for one set.** The count
that is right is 66, and it is checkable:

```bash
python3 -c "import sys;sys.path.insert(0,'tests');from test_rule_producers import advertised_rules;print(len(advertised_rules()))"
```

`packages/audit/pyproject.toml:4` is the highest priority of these: it is the PyPI
description, the single most-read line the project has, and it is the only claim of any kind
on a distribution surface. **It is wrong in the artifacts built by this run** — deliberately,
because editing a public claim was out of scope. Fix it and rebuild (step 5) before
uploading.

### 4b. The metrics

`docs/decisions/METRICS_RETRACTION.md` § 3a is the authority: one row per surface, with the
reproducible value and the command that produces it. § 5 has the ordering, and its first step
is the one thing this run could not determine — **which external surfaces carry the 98.51%.**
That list is yours and it gates the rest.

Two things to carry forward from that document rather than re-deriving:

* **The 100% figures were never measurements.** They are the *target* block of the v0.4.1
  brief, published as an achievement. So the correction is a retraction with a stated
  mechanism, not an update — there is no commit to update them *to*.
* **`tests/README.md` is the priority.** It carries the largest error, twice, with no
  retraction note, in a file whose location tells the reader the numbers came from the script
  beside it.

---

## 5. Rebuild, if you changed anything above

```bash
cd packages/audit
rm -rf dist/agent_audit-0.20.0*
python3 -m build          # needs `pip install build` in a venv; poetry-core does the rest
```

Artifacts, rebuilt and verified 2026-09-13 (RUN12). **Identified by hash, not size** — the
sizes this section used to record (357,007 / 307,519, "98 package files") matched no build
that was ever on disk here, so the verification record described something other than the
artifacts it sat next to:

```
sha256  0f38b00ad570ccbbfac761bbc2751217b1f7bb79df6d53dfc1747179da7d63e7  agent_audit-0.20.0-py3-none-any.whl
sha256  dd0e21dd545a8228121fc32b9e1ce590d519db6cf00bcc4e495a53850b8b577d  agent_audit-0.20.0.tar.gz
```

Verified on the rebuilt pair: **99 package files** in each and the two file sets identical;
**0** forbidden path components; `Version: 0.20.0`; **2** occurrences of "66 rules" in the long
description; **7** unconditional `Requires-Dist` entries (0.19.2 had six — `langdetect` is the
seventh); `twine check` **PASSED** on both. The RUN11 pair — wheel
`cff62109…5ee1`, sdist `9649f1f1…0e8a` — is superseded and must not be uploaded: it predates
the `report.py` markup fix and still carries `# v0.19.3:` in `rules/engine.py`.

**RUN12's rebuild was required too.** Two package files changed: `rules/engine.py` (the
withdrawal comment said v0.19.3, a release that does not exist) and
`cli/commands/report.py` (the missing-`reportlab` message named the package without the
extra). Both ship inside the wheel, so the artifacts audited in RUN11 were no longer the
artifacts this tree describes.

**The rebuild was required, not cosmetic.** `packages/audit/README.md` is the `readme` in
`packages/audit/pyproject.toml`, so it is the wheel's long description and the PyPI project
page — and it read "60+ rules", a sixth published count on a distribution surface. The
artifacts standing in `dist/` before this run carried that text.

Contents checked and clean: **99** package files in each, sdist and wheel **identical** in
package content, and **zero** entries matching `audit-eval`, `datasets/`, `knowns`, `wilds`,
`results/`, `ground_truth`, `labeled_samples`, `NIGHT_RUN`, `DECISIONS` or `.claude/`. No
local evaluation data and no target-identifying string. `Summary` carries 66 rules.

One nit, not a blocker: `agent_audit/scanners/typescript_scanner.py:54` contains the comment
`… see TOOL_SCOPED_RULES use below and NIGHT_RUN_LEDGER § W20`, which ships a pointer to a
document that is not in the distribution. Reword to `see DECISIONS.md` or drop the reference
if you would rather not ship it.

### Clean-venv installs — both done, both green

```
$ python3.12 -m venv /tmp/v312 && /tmp/v312/bin/pip install dist/agent_audit-0.20.0-py3-none-any.whl
$ /tmp/v312/bin/agent-audit --version
agent-audit, version 0.20.0                        # Python 3.12.12

$ python3.14 -m venv /tmp/v314 && /tmp/v314/bin/pip install dist/agent_audit-0.20.0-py3-none-any.whl
$ /tmp/v314/bin/agent-audit --version
agent-audit, version 0.20.0                        # Python 3.14.3
```

and a real scan from each, byte-identical between the two:

```
$ agent-audit scan tests/differential_corpus
📊 Summary:
  BLOCK: 1 | WARN: 5 | INFO: 0 | SUPPRESSED: 16
  Risk Score: 5.2/10 (MEDIUM)
```

---

## 6. Merge, tag, publish

> **Count them, do not read a count.** This line has said six and then nine, and each
> correction to it was itself a commit that made it wrong again — it was 9 at `7ddf826`,
> 10 at `0e5dfcf`, 11 at `a7854bd`. The range is what is stable:
> `git rev-list --count 48c1a89..HEAD`.
> Review them as a unit with `git log --oneline 48c1a89..HEAD` — one applies
> `finalize_run7.sh`, one fixes the quality gate, one fixes two issues, one corrects the
> published claims, and the rest are documentation and claim guards. The last, `7ddf826`,
> is the pre-release audit: it corrects the three documents that define the current metrics,
> fixes a sixth rule count on the PyPI project page, and adds
> `tests/test_published_metrics.py`. `git diff 48c1a89..HEAD -- packages/` is version bumps, the PyPI
> description, and four scanner fixes with their tests.


**Run `scripts/release_v0200.sh` rather than these commands.** It stages the same six steps
behind a preflight that re-runs the whole verification set, a before/after per step, and a
per-stage confirmation saying whether that step can be undone — and it puts a TestPyPI upload
and a clean-venv install back out of it *before* the PyPI upload, which is the one step that
can never be taken back.

```bash
scripts/release_v0200.sh --dry-run    # the preflight runs for real; nothing else does
scripts/release_v0200.sh              # then stage by stage, each one asks
```

The block below is what it automates, kept for reference. **Two differences, both deliberate:**

* `--tags` publishes *every* local tag, and one local tag is not on the remote:
  `skillscanner-core-frozen`, a freeze marker on unreleased work. Both the block below and the
  script name one ref per step — `master`, then `refs/tags/v0.20.0` — and nothing else.
* the upload below goes straight to the permanent index with no rehearsal.

**The ref audit, RUN 12 — the class rather than the instance.** Naming one ref per step fixes
the form of the command. It does not fix the two ways a ref gets published that nobody named,
so preflight § 1.12b now checks both and enumerates what is at stake. Measured on
2026-09-13:

| what | measured |
|---|---|
| local tags / tags on `origin` | **16 / 15** |
| the difference | **`skillscanner-core-frozen`** — annotated, and **reachable from `master`**, because it points at `05c3f98`, one of the seven pre-existing commits |
| `push.followTags` | **unset.** Were it set, naming `master` alone would publish every annotated tag reachable from it — which is exactly the one tag above. § 1.12b fails the preflight if it is ever enabled |
| bulk-ref forms (`--tags`, `--follow-tags`, `--mirror`, `--all`) in the script or this file | **none.** § 1.12b greps both files for a publish or fetch carrying one and fails on a hit, so the property is enforced rather than remembered |
| local branches / branches on `origin` | **8 / 4.** Not on the remote: `feature/skillscanner`, `feature/skillscanner-dist`, `feature/skillscanner-eval`, `release/v0.19.2`, and `fix/py314-blocker` itself. Stage 3 sends `master`; these stay local. `feature/compliance-report` exists at both ends and differs — `dee76ce` here, `fc92f6c` there — and is not this release's business either way |

```bash
git checkout master
git merge --no-ff fix/py314-blocker
git tag -a v0.20.0 -m "v0.20.0 — corrections: six rules withdrawn, metrics retracted, four reachability fixes"
git push origin master
git push origin refs/tags/v0.20.0

cd packages/audit
twine upload --repository testpypi dist/agent_audit-0.20.0*   # rehearsal
twine upload dist/agent_audit-0.20.0*                         # permanent
```

---

## 7. The issue replies

`ISSUE_TRIAGE.md` has a drafted reply per issue, with the reproduction and the before/after
output behind each verdict. **Drafts only — nothing was posted; the guard blocks `gh` writes
and that is correct for an unattended run.**

**`ISSUE_REPLIES.md` supersedes this table and `ISSUE_TRIAGE.md` where they disagree.** It
is the later document, its bodies are measured at `bea9901`, and no scanner or rule code has
changed since — `git diff bea9901..HEAD -- packages/ rules/` is one line of README text.

| # | action |
|---|---|
| #12 | close as **won't fix, documented**, with the measurement |
| #10 | reply, then **close as fixed**. This row used to read *leave open — reproduces at HEAD*; that was written before `9b366fc` and is wrong. Re-measured at `a7854bd` on the reporter's shapes: `target_agent.execute(task)` produces **nothing**, and both true positives in `tp_control.py` still fire |
| #8 | reply, **leave open** — two of four claims fixed; partial credit is not a closure |
| #11 | reply, **leave open** — blocked, and its premise is gone |
| #5 | label `enhancement` / `needs-design`, **leave open** with the deferral reason |

---

## What this run changed, so you can review it as a unit

```bash
git diff --stat ec0a29b..HEAD
git diff ec0a29b..HEAD -- packages/ rules/    # scanner code: version bump + classifiers only
```

New files: `CAPABILITY_BOUNDARIES.md`, `ISSUE_TRIAGE.md`, `RELEASE_CHECKLIST.md`,
`docs/decisions/DEAD_FILES.md`, `tests/test_treesitter_differential.py`,
`tests/differential_corpus/` (10 files).

Modified: `CHANGELOG.md` (the v0.20.0 entry), `docs/decisions/METRICS_RETRACTION.md`
(mechanism + per-surface table), `NIGHT_RUN_LEDGER.md`, `PROGRESS.md`, and the three version
files plus two classifier lines under `packages/audit/`.

**No oracle, dataset, ground-truth label, existing fixture, confidence value, tier boundary
or threshold was modified. No push, merge, rebase, tag or publish.**
