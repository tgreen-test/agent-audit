# RUN 4 REPORT

Target confidentiality: referred to throughout as "the audit target". No target path,
repository name, or source excerpt appears in this file, in the ledger, in any test
fixture, or in any commit message.

W15 through W18 are complete. **The signal-to-noise target was met: 4.35:1 against
≤5:1.** The more valuable result is W15, which turned "the same defect shape twice" into
a test that fails on it, and found three more instances of the same shape in the process.

---

## 0. The metric, recomputed rather than inherited

```
$ ./run_eval.sh --commit ef3a0a3 --verbose
total findings        : 395
noise / high-value    : 375 / 20
```

High-value is **still 20** — 13 AGENT-110 across its three titles, 4 AGENT-115, 3
AGENT-041 — unchanged from RUN3. Starting ratio **375 / 20 = 18.75:1**. Target ≤5:1
means noise ≤ 100.

| | noise | high | ratio |
|---|---|---|---|
| blind-audit anchor `1009782` | 1156 | 20 | 58:1 |
| start of this run `ef3a0a3` | 375 | 20 | 18.75:1 |
| **end of this run `38fe5bd`** | **87** | **20** | **4.35:1** |

---

## 1. W15 — the wiring audit, and what it found

### The guard

`tests/test_rule_reachability.py`, commit `309e36e`. For every advertised rule it records
whether the rule fires when its probe file is named directly and whether it fires when an
**ancestor directory** is scanned. `file > 0 and dir == 0` is dead-in-normal-use and
fails. The corpus sits three directories below the scan root, because a probe at the root
would not have caught `f649dcc`.

Proved in both directions. On HEAD, `5 passed in 11s`. With `mcp_config_scanner` reverted
to non-recursive `iterdir()`, it fails and names **exactly the six rules `f649dcc`
restored** — AGENT-005, AGENT-029, AGENT-030, AGENT-031, AGENT-032, AGENT-033 — each with
the probe file that reached it. Full output in the ledger.

Three companion tests cover what that comparison cannot see: a rule with no production
path has *both* counts at zero, so the orphan set is pinned separately; known-dead
mechanisms carry a reason so wiring one up fails the test; and probe coverage is pinned at
52 of 72 so the guard cannot quietly lose teeth.

### Which rule count is canonical: 72

Four sources disagreed. `RULE_CWE_MAPPING` (92) minus the 20 DeFi rules (behind
`--profile defi`) is **set-equal** to `docs/RULES.md` (72), and the test asserts that
equality so they cannot drift.

### Three more instances of the same defect shape

**Six advertised rules cannot be produced by any input.** AGENT-003, 011, 013, 015, 016,
036 are published and have no code path that constructs them — five map only to a
`pattern_type` no scanner emits. This lands on W11: five ground-truth labels cite
AGENT-015, which RUN3 named as the largest contributor to ASI-04 reading 0.0%. It is now
measured rather than inferred — **AGENT-015 can never fire, at any commit, on any input.**

**The YAML rule engine is loaded on every scan and consulted by nobody.**
`RuleEngine.evaluate()` — the generic evaluator for the 52 YAML definitions carrying
`detection.patterns` — has one caller in the repository, `tests/test_rules/test_engine.py:39`.
`scan.py` parses the YAML on every scan and then uses only the four hand-written
evaluators. No `detection.patterns` block has ever matched anything on a real scan. The
rule-authoring checklist in `CLAUDE.md` tells contributors to write those blocks.

**`ts_tool_boundary_detector.py` is imported by nothing.** 325 lines, a full test file,
and its own unit test is the only thing in the repository that mentions it. It is the
TypeScript counterpart of the gate that, on the Python side, stops AGENT-034 firing
outside a `@tool` entry point. See §4.

### The analyzer wiring matrix

Every public callable in all 21 `analysis/` modules was instrumented to record its
immediate non-analysis caller, then a real `run_scan()` ran over the audit target and
over `tests/fixtures`. An import is not a call; this records calls. Full matrix in the
ledger. Ranked by findings affected:

| gap | findings | disposition |
|---|---|---|
| `context_classifier` never called by `typescript_scanner` | 174 in test paths | **superseded — see §2** |
| `ts_tool_boundary_detector` ABSENT, zero production references | up to 191 | reported, not fixed — DECISIONS 25 |
| `tool_description_analyzer` imported by 3 MCP scanners, never called | 0 | note — `_detect_tool_poisoning` has zero callers, so AGENT-056/057 cannot fire from a static config; proved with a designed trigger |
| `dangerous_operation_analyzer` imported, call site only reachable on a `TaintTracker` crash | 0 | note |
| `confidence_matrix`, `env_tracer` ABSENT entirely | 0 | note |

### Item 18 — the correction that mattered

RUN3 called wiring `context_classifier` into the TypeScript scanner the highest-value
remaining item, worth 174 of 375. **That estimate does not survive contact with the
measurement, and the reason is worth more than the item.**

`context_classifier` **downweights** confidence; it does not suppress emission. The JSON
formatter emits every finding regardless of tier — `by_tier` at the start of this run read
`BLOCK 1, WARN 340, INFO 12, SUPPRESSED 42`, and all 42 SUPPRESSED findings were in the
395 the harness counts. Wiring the classifier would have moved 174 findings from WARN to
SUPPRESSED and changed the noise count by **zero**.

So the 174 estimate was measuring the wrong thing, and I did not implement it as
specified. Everything in §2 suppresses emission instead. The wiring gap is real and is
still worth closing for users who filter by tier; it is now DECISIONS-logged rather than
silently skipped.

---

## 2. W17 — noise 375 → 87, in ten measured steps

Every row is `./run_eval.sh --commit <sha>`, last line verbatim in the ledger. **No
threshold, tier boundary or confidence value was changed anywhere in the phase.**

| # | pattern | commit | before | after | delta |
|---|---|---|---|---|---|
| 1 | `fetch` receiver resolution | `709fcdc` | 375 | 310 | −65 |
| 2 | declarations, comments, quoted source | `a668822` | 310 | 265 | −45 |
| 3 | fixed non-shell executable | `5d92330` | 265 | 177 | **−88** |
| 4 | a property chain is not a hostname | `fca978a` | 177 | 165 | −12 |
| 5+6 | weak prompt names; 034 subsumes 047 | `df962e4` | 165 | 142 | −23 |
| 7+8 | `page.evaluate` literal callback; js-yaml v4 | `2701059` | 142 | 110 | −32 |
| 9+10 | the sandbox is not "without sandbox"; multi-line programs | `38fe5bd` | 110 | **87** | −23 |

`total − noise` is **20 at every one of the seven commits.** Recall stays 0/6 in both
directions. 87 new regression tests across the ten patterns, every set split into
suppression cases and true-positive controls.

Two patterns are worth naming because they are the same fix shape as `a37bfba`, applied
where nobody had looked: `fetch` is a global, so the *member* form is the one that is
almost never an outbound request — `handler.fetch(request)` is a server handler receiving
one, which inverts the finding's direction. And `page.evaluate(() => …)` passes a function
literal compiled from the scanned file, so neither half of "Browser Automation Without
Sandbox" is present.

One is worth naming because it is version-dependent rather than syntactic: js-yaml renamed
`safeLoad` to `load` in v4, so whether `yaml.load(x)` is a finding depends on the declared
dependency. The nearest `package.json` decides it; no declaration, an unreadable manifest,
or a range admitting v3 all leave the finding in place.

### What remains at 87

**58 of the 87 are AGENT-034**, and by the rule's own emitted title they are correct:
`spawn(command, args)` with a runtime executable, plus `eval` / `new Function` /
`vm.runInNewContext`. The rest is a long tail — 8 SSRF (6 of them genuine), 5 AGENT-010
(all five genuine `prompt` interpolations), 4 AGENT-047, and single-digit remainders. Full
table in the ledger.

Closing the 58 is not another predicate. It is §4.

### The one behaviour change, stated plainly

Pattern 3 supersedes a contract W14 set. Three W14 controls asserted that a variable
*argument* keeps an AGENT-034 finding even when the program is fixed. They are renamed
`*_superseded`, inverted, and kept in the suite rather than deleted.

**What is given up: argument injection against a fixed binary** —
`spawnSync('git', ['-C', root, ...userArgs])`, where `git --upload-pack=…` is the standard
exploit. AGENT-034 no longer reports it. My reasoning is that the rule's title is "Shell
Command Execution", `execFile`/`spawn` involve no shell, and 84 findings of that shape
buried the 50 that are the rule's actual subject. **The counter-argument is real and it is
yours** — DECISIONS item 24, with the narrower alternative spelled out.

---

## 3. W16 — the 20 restored MCP findings, triaged

The set was established rather than assumed: scanning `tests/fixtures` with the tool at
`2e80a59` (pre-W10) gives 267 findings, at `1c297d8` (post-W10) gives 287. **Exactly +20**,
every one in an MCP config file.

**18 TP / 1 FP / 1 AMBIGUOUS**, judged against each rule's published definition rather
than against usefulness. Per-finding table with config excerpts in the ledger.

**The labelling-gap explanation is confirmed.** The AGENT-029→033 family does not have a
precision problem that the wiring bug was hiding. No narrowing predicate is proposed,
because none is warranted. The 18 unlabelled true positives are logged as corpus additions
under NEEDS-HEADY item 27; **I added none of them.**

Two things the triage found are worth more than the verdict.

**All 20 carry `confidence=1.0` and `tier=BLOCK`.** `scan.py` constructs MCP security
findings with no `confidence=` argument, so they take the `Finding` default. **No analyzer
is in the loop on that path.** The single false positive is
`API_KEY: "AKIAIOSFODNN7EXAMPLE"` — the AWS documentation example key — reported as
AGENT-004 at BLOCK, while `rule_context_config.py` names that exact string in a comment as
something that should be suppressed. The AGENT-004 the secret scanner produces goes
through `semantic_analyzer` → `placeholder_detector` → `value_analyzer`; the AGENT-004 the
MCP path produces goes through none of it. **The wiring pattern again, at rule granularity.**

**One fixture's negative label is about a different axis than the rule.**
`benign/validated/mcp_restricted.json` is labelled safe and AGENT-030 fires on it
correctly: the package is genuinely unpinned. The fixture is restricted in *permissions*,
not in *supply chain*.

### The ratchet

Measured at `38fe5bd`, `PYTHONHASHSEED` pinned, four seeds, one distinct result:
**TP 196 / FP 90 / FN 40, P 0.6853 / R 0.8305 / F1 0.7510.**

| basis | precision |
|---|---|
| as measured | **0.6853** |
| excluding the 1 AMBIGUOUS from the denominator | 0.6877 |
| if the 18 TP-by-definition were labelled | 0.7483 |

**The ratchet should sit on the as-measured 0.6853, and the 0.66 floor is unchanged.**
The ratchet's job is catching regression in what the script actually produces. Moving it
onto a basis that subtracts findings the script still emits would make the floor
unfalsifiable by the same script that enforces it. 0.7483 is the argument for adding the
labels, not for moving the floor. **I did not change the ratchet.**

Worth recording: Layer 1 precision **rose** 0.6829 → 0.6853 across all ten patterns, with
**TP 196 and FN 40 unchanged**. Ten denoise patterns, zero Layer 1 true positives lost.

---

## 4. The pattern itself, which is the point of this run

Three runs, five instances, one shape:

| run | mechanism | how it hid |
|---|---|---|
| RUN3 | MCP config discovery used `iterdir()` | six rules had a directory-scan count of zero |
| RUN3 | TS scanner never called `context_classifier` | 174 findings unweighted |
| RUN4 | `ts_tool_boundary_detector` imported by nothing | 187 findings emitted through an ungated path |
| RUN4 | `RuleEngine.evaluate()` called only by a unit test | 52 YAML pattern sets never matched anything |
| RUN4 | six rules with no producer at all | published, unreachable, silent |

Every one is invisible in unit tests, because a unit test calls the mechanism directly.
Every one is invisible in the output, because a rule that never fires looks exactly like a
clean codebase. `tests/test_rule_reachability.py` catches the first, third and fifth
directly; the second and fourth are why it also pins the known-dead set and the orphan set
rather than only comparing counts.

**The sharpest instance, and the one I did not fix.** `docs/RULES.md` and
`rules/builtin/asi_coverage_v030.yaml` both define AGENT-034 as "Tool Function Without
Input Validation": CWE-20, `pattern_type: tool_no_input_validation`, gated on `@tool`
decorators and `str`/`Any` parameters. The Python scanner implements exactly that and
gates it on `is_tool_entry_point()`. The TypeScript scanner emits the same rule ID under
"Shell Command Execution" and "Dangerous Code Execution", **with no tool-boundary gate at
all**, and that path produced 187 of 191 AGENT-034 findings on the audit target.

The gate exists. It is `ts_tool_boundary_detector.py`, and nothing imports it.

I did not wire it, for two reasons stated in full in DECISIONS item 25: it is written as a
confidence *helper*, not the hard gate the Python side uses, so wiring it as a gate is a
design decision rather than a connection; and doing so would remove essentially every
TypeScript AGENT-034 finding and invalidate a dozen tests encoding current behaviour. My
recommendation is to split the rule — give the TypeScript emission its own ID and title —
because it is the only option that keeps both behaviours and makes the reachability test
meaningful for AGENT-034, which today reaches a directory scan through three pattern types
with three different meanings.

---

## 5. W18 — the two loose ends

**Gate location: `tests/benchmark/gates.yaml`.** `quality_gate_check.py --config` defaults
to it (line 207). Proved both directions on a **fresh** measurement, not the committed
one: exit 0 on current results, exit 1 with precision set one point below the 0.66 floor.
Both transcripts in the ledger. `tests/benchmark/quality_gates_v2.yaml` is still on disk,
referenced by nothing, **and not deleted** — the W9 guard protects that filename and the
`git rm` is yours.

**PYTHONHASHSEED blast radius.** Determinism confirmed at HEAD across four seeds, one
distinct result. **I could not re-measure the pre-fix distribution and do not claim to
have**: running the `2e80a59` harness from a `git archive` extraction gives TP 4 / FN 232,
which is an artifact of the extraction, not a sample of the old evaluator. The spread
stands at RUN3's observed ±1 TP, which on this corpus is worth **±0.0035 precision,
±0.0042 recall, ±0.004 F1**.

**19 quoted numbers found across `CLAUDE.md`, `README.md`, `README_CN.md`,
`docs/index.html`, `docs/BENCHMARK-RESULTS.md`, `docs/F1_REPRODUCTION.md`,
`CHANGELOG.md`, `tests/README.md`, `results/*.json`, `results/avb_report.md`,
`blog_post.md` and `twitter_thread.md`.** Full table with per-row deltas in the ledger.
**Nothing was edited.** No `agent-audit-slides.html` or `*-EXECUTION-SUMMARY.md` quoting
Layer 1 or AVB exists in the tree.

The headline: **P 73.58% / R 82.63% / F1 0.778, TP 195 / FP 70 / FN 41** is quoted in six
places. Current reproducible value is **P 68.53% / R 83.05% / F1 0.751, TP 196 / FP 90 /
FN 40** — precision **−5.05pp**, F1 **−0.027**, FP **+20**, all one to two orders of
magnitude above the ±0.004 spread. The cause is known and innocent: the +20 false
positives are exactly the MCP findings W10 made reachable, and W16 has now shown 18 of
them are correct and merely unlabelled. Precision fell because the tool started finding
things the corpus never labelled. **That fact has to travel with the number wherever it
has gone** — along with the fact that 0.778 sat at the high end of a ±1 TP coin flip when
it was recorded.

**The number I would look at first is not that one.** `tests/README.md` claims
**P 98.51% / R 100% / F1 99.25% / FP rate 1.49%** against a v2.1 ground truth from
2026-02-04 — **30 points of precision above the current figure**, predating GT v2.2, and
unlike the 0.778 family it carries no retraction note anywhere.

---

## 6. Invariants at `38fe5bd`

| invariant | result |
|---|---|
| noise / high-value | **87 / 20 = 4.35:1** (target ≤5:1) |
| recall on the target | **0/6, unchanged in both directions** |
| AVB knowns | **R 100.0% / P 88.0% / F1 0.9362, unchanged** |
| Layer 1 ratchet | **exit 0** on a freshly generated `layer1.json`; P 0.6853 / R 0.8305 |
| Layer 1 true positives | **196, unchanged**; FN 40, unchanged |
| full suite | **1731 passed, 1 skipped** — 1639 baseline + 92 new, none deleted or skipped |
| reachability guard | **5 passed**; fails on re-broken wiring, naming the six rules |

The baseline count is measured, not inherited: `pytest tests/ -q` on a clean `git archive`
of `ef3a0a3` gives **1639 passed, 1 skipped**, so the delta is exactly the 92 tests added
(87 denoise + 5 reachability). RUN3 recorded 1671 for the same tree; that figure was taken
in the working directory rather than a clean extraction, and 1639 is the reproducible one.

`tests/benchmark/performance_test.py::TestThroughput::test_consistent_performance` failed
once mid-run and passed on the two reruns either side. It is a wall-clock variance
assertion; recorded rather than smoothed over.

---

## 7. What I would do first next, and why

**Decide AGENT-034 (DECISIONS 25).** 58 of the remaining 87 findings sit behind it, it is
the sharpest instance of this run's pattern, and the decision — split the rule, gate the
TypeScript path, or amend the published definition — is a rule-design call that should not
be inferred. Everything else on the list is smaller than it.

Then **route MCP findings through the analyzers (DECISIONS 26)**: it is the same wiring
shape at rule granularity, it turns a BLOCK-tier false positive into a suppressed one, and
it needs no new capability.

One thing I would *not* do next: chase the remaining 87 with more predicates. The
long tail is genuine by each rule's own definition, and the next real gain is a rule-scope
decision, not a regex.

---

## 8. Confirmation

**I did NOT push, merge, tag, or publish, and I did not modify any oracle, fixture, or
dataset.**

Nine commits to `fix/py314-blocker`, all local. `git log --name-only` over the session
touches no file under `tests/fixtures/` or `tests/ground_truth/`; every new test builds
its inputs with `tmp_path` or synthetic literals. No ground-truth label was changed — the
18 corpus additions from W16 are logged, not applied. No threshold, tier boundary,
confidence value or ratchet was changed. The gate file protected by my own guard was left
in place and its location reported instead.

Actions avoided: `git push`, `git merge`, `git rebase`, `git tag`, `gh` writes, PyPI/npm
publish, `rm -rf`, anything under `eval/`, `pip install agent-audit`, and any edit to an
oracle, dataset, fixture, confidence threshold, or public-facing claim.
