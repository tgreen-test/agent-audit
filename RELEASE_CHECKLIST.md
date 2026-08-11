# v0.20.0 release checklist

**Everything below is a command for you to run. This run executed none of them.**

The branch is `fix/py314-blocker`. Nothing has been pushed, merged, tagged or published, and
no public-facing claim has been edited. The artifacts exist and are verified; the release is
staged, not made.

Work top to bottom. Steps 1–3 change measured numbers and must precede the rest.

---

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

`docs/RULES.md:1419` already says 66 and is correct. Everything below does not.

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
| `docs/index.html:896` | `v0.16.0 — 49 rules · 10/10 OWASP coverage · 1,142 tests passing` | `v0.20.0 — 66 rules · 10/10 OWASP coverage · 1,796 tests passing` |
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

Artifacts from this run, already verified:

```
-rw-r--r--  357,007  agent_audit-0.20.0-py3-none-any.whl
-rw-r--r--  307,519  agent_audit-0.20.0.tar.gz
```

Contents checked and clean: 98 package files in each, sdist and wheel **identical** in
package content, and **zero** entries matching `audit-eval`, `eval/`, `datasets/`, `knowns`,
`wilds`, `noise/`, `results/`, `ground_truth`, `labeled_samples`, `NIGHT_RUN`, `DECISIONS` or
`.claude/`. No local evaluation data and no target-identifying string.

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

```bash
git checkout master
git merge --no-ff fix/py314-blocker
git tag -a v0.20.0 -m "v0.20.0 — corrections: six rules withdrawn, metrics retracted, four reachability fixes"
git push origin master --tags

cd packages/audit
twine upload dist/agent_audit-0.20.0*
```

---

## 7. The issue replies

`ISSUE_TRIAGE.md` has a drafted reply per issue, with the reproduction and the before/after
output behind each verdict. **Drafts only — nothing was posted; the guard blocks `gh` writes
and that is correct for an unattended run.**

| # | action |
|---|---|
| #12 | close as **won't fix, documented**, with the measurement |
| #10 | reply, **leave open** — reproduces at HEAD, unchanged |
| #8 | reply, **leave open** — one of four claims fixed; partial credit is not a closure |
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
