# Capability boundaries

What agent-audit does not do, why, and how you can tell.

This document exists because the tool's output is easy to over-read. A scan that reports
"0 files skipped, 0 parse failures" and then finds nothing looks like a clean bill of
health. It is not one. It means the analyses that ran found nothing, and the set of
analyses that run is much smaller than the set of ways agent code goes wrong.

Everything below is measured on this repository at v0.20.0 and reproducible with the
commands given. Where a limit has a number attached, the number is the honest one, not the
flattering one.

---

## 1. What the analysis is

agent-audit is a **single-file, single-pass static analyser**. Every rule reaches its verdict
from one file's syntax tree or one file's text, plus a small amount of within-file data flow.

That framing implies the boundaries, and they are worth spelling out one at a time.

### No cross-file analysis

A finding is computed from one file. If a tainted value enters `handlers.py` from
`routes.py`, the tool sees only what `handlers.py` says about it. A parameter arriving from
another module is, to every rule, just a parameter.

There is one deliberate exception and it is not general cross-file analysis: MCP **tool
shadowing** (AGENT-055) is computed tree-wide, because "two servers export the same tool
name" is not a property any single file has. That exception is why a whole-tree scan and a
per-directory scan can disagree about shadowing, and it is the only place they can.

### No call graph

The tool does not know who calls what. "Is this function ever reached?", "is this validator
always applied before this sink?", "does this handler run with elevated privileges?" — none
of those questions is asked, because there is no structure in which to ask them.

Concretely: a sanitiser called in the *caller* rather than in the function containing the
sink does not suppress the finding, and a sink guarded by an unreachable branch is still
reported.

### No import following

An import is a line of text. `from .safety import validate` tells the analyser that a name
called `validate` exists, not what it does. A rule that wants to know whether a value was
validated can only look for validation **in the same function body**.

### No type resolution

This is the largest single source of false positives, and issue #10 is the clean example.
`x.execute(q)` is a SQL sink if `x` is a DB cursor and is not if `x` is an agent, a task
runner, a `concurrent.futures.Executor`, or an ORM query builder. The tool matches the
method name, because the method name is what a single file reliably provides. It does not
know the receiver's type, and in an agent codebase — where `.execute()` is a *common
non-SQL idiom* — that guess is wrong often.

The same shape recurs: `.eval()` on a Redis client is not `eval()`; `.fetch()` on a request
handler is not the global `fetch()`. Each of those has been fixed individually, by receiver
heuristics rather than by types, and each fix is a pattern rather than a principle.

### No object-lifecycle or resource-ownership modelling

The tool has no notion of an object being created, owned, transferred, or released. Use
after free, double close, leaked handles, and "this connection is closed on one path but not
the other" are all outside what a single-file syntactic pass can represent.

### No runtime dispatch-order reasoning

Which middleware runs first, which hook fires before which, whether a decorator wraps before
or after another — the tool reads the declarations and cannot order the executions.

### No runtime behaviour of any kind

Nothing is executed, no server is started, no model is called. `agent-audit inspect` talks
to a live MCP server, but that is introspection of a declared interface, not observation of
behaviour under input.

---

## 2. The blind-audit result

The most useful number in this document is a failure.

agent-audit was run against a real agent codebase with six known, independently confirmed
defects, without being told where they were.

**With 0 files skipped and 0 parse failures, recall on those 6 real defects was 0.**

Coverage was complete and detection was zero. The two are not the same measurement, and the
gap between them is the whole point: *"we read every file"* is a statement about the reader,
not about the defects.

The failures concentrated in **cross-package and cross-lifecycle defects** — exactly the
classes section 1 says are outside the analysis. That is the reassuring part of an otherwise
unflattering result: the tool missed the things its design says it cannot see, rather than
missing things at random. But it means the honest summary of a clean agent-audit report is
"no single-file syntactic defect of a known shape was found", and nothing broader.

Use it accordingly. It is a filter, not an assurance.

---

## 3. The structural lesson: a rule that never fires looks exactly like a clean codebase

This is the finding this project spent seven passes on, and it generalises past this tool.

**A detector that cannot fire and a target with no defects produce identical output.** No
test suite, no benchmark, no CI gate and no coverage report distinguishes them, because all
of them observe the output. So a broken detector is not merely undetected — it is
*undetectable* by any instrument pointed at results.

Seven separate instances of that one shape were found, each a mechanism that existed, was
unit-tested, and was never reached in real use:

| # | mechanism | how it was unreachable | state at v0.20.0 |
|---|---|---|---|
| 1 | MCP configuration discovery | used a non-recursive `iterdir()` over the scan root where nine other scanners use `rglob`, so **six rules had a directory-scan count of exactly zero** | fixed; the fix's comment records the defect |
| 2 | `analysis/ts_tool_boundary_detector.py` | 325 lines with a full test file, imported by nothing — AGENT-034 on TypeScript had no boundary constraint from the day it shipped | fixed; now imported by `typescript_scanner.py` |
| 3 | `RuleEngine.evaluate()` | the evaluator for 52 YAML `detection.patterns` blocks, called only by a unit test — while `CLAUDE.md` instructed contributors to write those blocks | measured, and **retired rather than wired**: 81 of 84 pattern entries use a key the evaluator never reads, and switching it on cost 4.7 points of precision |
| 4 | six advertised rules | detection written out in full as YAML, no reachable evaluator to run it | **withdrawn** in v0.19.3; the published count went 72 → 66 |
| 5 | `package_scanner._scan_ai_tool_hooks` | resolved config paths by joining onto the scan root instead of `rglob` — AGENT-120 fired only when the scan root *was* the project directory | fixed |
| 6 | AGENT-049 | detected correctly at confidence 0.85, then **discarded**, because `_create_finding_from_pattern` looks the rule up in the YAML table and AGENT-049 has no YAML definition. The mirror image of #4: a producer with no definition, where those were a definition with no producer | **open**, pinned by a test that asserts the mechanism so fixing it fails the pin |
| 7 | sixteen advertised rules | no fixture anywhere in the repository — invisible to every quality gate, and unable to regress because nothing measured them | fifteen now have a trigger fixture; one is pinned with a written reason |

The graded corpus explains #7 in one line:

```
graded corpus file types:  .py 95   .json 10   .md 9   .sh 3
```

No Solidity, no Go, no TypeScript. The Solidity scanner, the Go scanner and the TypeScript
half of several rules had never had a single input to run on.

### What now catches this class, and what still does not

Three guards were added, and each fails the suite rather than warning:

* **`tests/test_rule_producers.py`** — every advertised rule must have a code path that can
  construct it. No allow-list. This is the check that took six rules out of the published
  list.
* **`tests/test_rule_fixture_coverage.py`** — every advertised rule must have an input
  somewhere in the repository that makes it fire.
* **`tests/test_corpus_label_rules.py`** — every ground-truth label must cite a rule the tool
  can emit. Layer 1 keys on `file:line:rule_id`, so a label naming an unproducible rule is
  unmatchable by construction: a false negative on every input at every commit, forever.

They close the specific hole. **They do not close the general one.** All three ask "can this
fire at all?" — none asks "does this fire on the code people actually write". A rule that
fires on its own fixture and on nothing else in the world passes every one of them. The
blind-audit result in section 2 is what that gap looks like from outside.

---

## 4. Language coverage, stated plainly

| language | how it is analysed | what that means |
|---|---|---|
| Python | AST, plus within-function taint tracking | the deepest path; still single-file |
| TypeScript / JavaScript | **regex, not AST** | see below |
| Go | regex | pattern matching over text |
| Solidity | regex | pattern matching over text |
| YAML / JSON / `.env` | parsed as configuration | structural, not semantic |
| **Shell scripts** | **not read at all** | no scanner opens a `.sh` file, so no rule of any kind can fire on one |

### TypeScript and JavaScript are regex-level, by decision

`TreeSitterParser` contains a tree-sitter AST path alongside the regex path. **The AST path
has never executed in any shipped environment, and as of v0.20.0 it stays that way
deliberately.** The reasoning is measured, not assumed:

* The AST path was unreachable for three independent reasons — a missing
  `language_typescript()` accessor (issue #12), a `PyCapsule` handed to `Parser()` where a
  `tree_sitter.Language` is required, and a `tree-sitter = "^0.22.0"` core pin that cannot
  consume any 0.23+ grammar at all. The first alone would not have activated anything.
* All three were fixed on a scratch build and the AST path came alive for `.py`, `.js`,
  `.ts` and `.tsx`.
* On that build the differential against the regex path was **2 true positives lost and 8
  additions, six of the additions being the exact false positives the regex path had been
  fixed to suppress** — the `.eval`-on-a-client and `.fetch`-on-a-receiver families, and
  template strings that are not system prompts.
* The full suite went from 8 failures to 50 in the same environment: **42 regressions**,
  across 40 TypeScript scanner tests and 2 Python parser tests. Every failure was a finding
  disappearing, of the form `assert 0 >= 1`.

**A path that parses but detects less is worse than one that never ran**, because it looks
like an upgrade. So the fix was written, measured, and reverted, and
`tests/test_treesitter_differential.py` now stands between the next person and the same
mistake. It skips loudly rather than passing when the AST path is inactive — a skip there
means the question was not asked.

Reproduce:

```bash
python3 tests/test_treesitter_differential.py
```

---

## 5. What the confidence tiers actually claim

| tier | threshold | what it means |
|---|---|---|
| BLOCK | ≥ 0.92 | high confidence; fails CI by default |
| WARN | ≥ 0.60 | worth a human look |
| INFO | ≥ 0.30 | informational |
| SUPPRESSED | < 0.30 | hidden unless `--verbose` |

Confidence is a property of **the pattern match**, not of the exploitability of the finding.
A BLOCK-tier result means "this syntactic shape is one this rule is sure about", not "this is
exploitable in your deployment". Nothing in the tool reasons about reachability from an
attacker-controlled entry point, because — see section 1 — there is no call graph in which to
do so.

---

## 6. The benchmark numbers, and what they are numbers about

Reproduce with `python3 tests/benchmark/precision_recall.py`.

```
TP 196   FP 93   FN 40
Precision 0.6782   Recall 0.8305   F1 0.7467
```

These are measured against a **synthetic labelled corpus of 81 files written for this
purpose**. They describe how well the tool finds defects of the kinds it was built to find,
in files written to contain them. They do not transfer to real codebases, and section 2 is
the demonstration: the same tool that scores 0.83 recall here scored 0 on six real defects.

Two further honesty notes:

* The corpus contains only `.py`, `.json`, `.md` and `.sh`. **No number here says anything
  about TypeScript, Go or Solidity detection.**
* Any published figure of 98.51% precision, 100% recall or "F1 100%" from before v0.19 is
  withdrawn. See `docs/decisions/METRICS_RETRACTION.md` — the recall figure was never a
  measurement.

---

## 7. If you are deciding whether to trust a clean report

A short version of everything above.

**A clean agent-audit report means:** no single-file syntactic pattern from a set of 66 rules
matched, in the languages the tool actually parses.

**It does not mean:** the code is safe; the data flows are safe; the agent's tools are
correctly scoped; the dependencies are trustworthy; the deployment is sound. It does not even
mean every file was analysed in a meaningful sense — a `.sh` file is counted as scanned and is
never opened.

Use it as one filter among several, weight the BLOCK tier and read the WARN tier, and treat
"0 findings" on a large codebase as a prompt to check whether the rules that should have
fired have inputs at all. That last question is one this project had to learn to ask, and the
guards in section 3 are what asking it looks like.
