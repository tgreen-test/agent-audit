# RUN 5 REPORT

Target confidentiality: referred to throughout as "the audit target". No target path,
repository name, or source excerpt appears in this file, in the ledger, in any test
fixture, or in any commit message.

W19 through W22 are complete. The headline is not the noise number, though that halved
again — **87 → 44, a 2.2:1 ratio against a 5:1 target.**

The headline is that **the advertised rule set is now a measured quantity.** It was 72.
Six of those rules could not fire on any input at any commit; a seventh could not be
reached below the scan root. It is 66, every one of them demonstrated firing on a real
scan, and a test with no allow-list fails the suite if that stops being true.

---

## 0. What the producer audit found, in one paragraph

RUN4 reported four defects of one shape and treated them as four. Two of them are one.
Five of the six rules with "no producer" have their detection **written out in full** — 
pattern types, indicators, regexes, config keys — as `detection.patterns` blocks in
`rules/builtin/*.yaml`, the place `CLAUDE.md` instructs contributors to write it. The only
code that can execute such a block is `RuleEngine.evaluate()`, which has no runtime caller.
The detection was not missing. It was written into an evaluator nobody calls.

And the evaluator could not have run it anyway: `_evaluate_rule` dispatches on a key called
`type`, and **81 of the 84 pattern entries across all 52 YAML rules use `pattern_type`
instead** — a key it never reads.

---

## 1. W19 — every advertised rule, classified by runtime

Method: a real `run_scan()` over 122 probes (the 117-file fixture corpus plus five
synthetic files) three directories below the scan root, each probe scanned as a file and
the root scanned as a directory. Static search is used only to explain a zero.

```
Counter({'LIVE': 52, 'UNREACHABLE': 14, 'YAML-ONLY': 5, 'NO-PRODUCER': 1})
```

The 14 "unreachable" were then resolved by building, from each producer's own source
condition, the input that condition asks for. **Twelve fire.** They are not unreachable;
nothing in the repository tests them.

| class | n | disposition |
|---|---|---|
| LIVE — observed on the corpus | 52 | — |
| LIVE, **no fixture anywhere** | 12 | corpus gap, DECISIONS 33 — not mine to fill |
| LIVE, reachable only via `inspect` | 1 | AGENT-054, now disclosed |
| Unreachable below the scan root | 1 | AGENT-120 — **fixed** |
| No producer — five of them YAML-only | 6 | **withdrawn**, 72 → 66 |

### Which count is canonical, and what the others count

Seven published rule counts, not two. **72 was canonical** (`RULE_CWE_MAPPING` minus the 20
DeFi rules, set-equal to `docs/RULES.md` — verified, not assumed); it is now **66**. `92` is
the same set including `--profile defi`. `52` is the YAML files. And `53`, the number on the
**PyPI description**, matches no set at any commit I could find. `63`, `49` and `40+` are
stale. Full table in `CLAIMS_RECONCILIATION.md § 3`.

### The sixth instance of the same defect, and it is new

`package_scanner._scan_ai_tool_hooks` resolved its targets as `path / ".claude/settings.json"`
— a direct join onto the scan root, no `rglob`. Measured:

```
AGENT-120@root     dir=YES   .claude/settings.json AT the scan root
AGENT-120@nested   dir=no    the same file ONE DIRECTORY BELOW the root
```

This is `f649dcc` again — the non-recursive `iterdir()` that hid six MCP rules — in a rule
that shipped five months later. `_scan_mcp_json_commands` had it too.

**The RUN4 guard could not catch it, and the seam is worth understanding.**
`test_no_rule_is_reachable_only_by_file_argument` fires on `file > 0 and dir == 0`.
AGENT-120 needs a directory, so its file count is *also* zero — which reads as "orphan" —
and it has a producer, so the orphan test skips it. It fell exactly between the two tests.

### The disposition, per rule

**Withdrawn, not implemented, for all six.** Four state no operational threshold at all
("lacks explicit goal boundaries", "without integrity validation"), so a producer would
encode a guess, and a rule implemented from a guess is worse than an absent one. Two are
duplicates of rules that already work: **AGENT-015 is AGENT-030** (same severity, same
CWE-494, same ASI-04, same detection content), superseded at v0.3.0 and never withdrawn;
AGENT-013 is covered by AGENT-004.

`docs/RULES.md` gains a Withdrawn Rules section naming each one, **the coverage gap it
leaves** (exfiltration chains, goal boundaries, RAG provenance and tool-output trust are
real ASI risks this tool does not detect), and the two that are genuinely covered
elsewhere. IDs are retired, not recycled.

### AGENT-015 — diagnosed, labels untouched

Three different things carry this ID.

*As published*: an MCP-config rule, duplicate of AGENT-030. *As implemented*: not at all.
*As labelled*: something else entirely. The five corpus labels citing it are runtime
`npm install`, `curl | bash`, `git clone` + exec, install-from-remote-requirements, and
PyPI typosquatting — **not one involves an MCP server** — and the AVB taxonomy annotates it
`# unverified_tool_source`.

Layer 1 matches on `file:line:rule_id`. **A label citing a rule that cannot be produced is
unmatchable: a guaranteed false negative at every commit, forever.** Five of them. What the
tool actually emits at those lines:

```
npm_install_runtime.py   line 13  -> AGENT-001  (exact line)
curl_pipe_bash.sh        line 11  -> NOTHING
git_clone_exec.py        line 14  -> AGENT-034  (exact line)
dynamic_requirements.py  line 14  -> NOTHING
pypi_typosquatting.py    line 12  -> AGENT-034 at line 14 (within tolerance)
```

**Three of the five are detected at the labelled line under a different ID**, and are
therefore scored as a false negative *and* a false positive at once. Two are real misses.

The mechanism behind the drift is the point: **a rule that never fires can be labelled to
mean anything, because no output ever contradicts the label.** No ground-truth label was
changed.

---

## 2. W20 — the TypeScript gate, and the one finding I could not justify losing

`ts_tool_boundary_detector.py` — 325 lines, a full test file, imported by nothing — is now
the gate on AGENT-034, applied once per file after both the tree-sitter and regex paths.
Membership only; `get_tool_confidence_boost` is deliberately unused, so no confidence value
moves.

| | noise | high | Layer 1 TP / FP / FN | AVB knowns |
|---|---|---|---|---|
| before `6adedd1` | 87 | 20 | 196 / 93 / 40 | R 100.0 / P 88.0 / F1 0.9362 |
| after `2ee8345` | **44** | **20** | **196 / 93 / 40** | **unchanged** |

**No true positive is suppressed on either benchmark** — and the reason is itself a
finding: both corpora are overwhelmingly Python, so **AGENT-034's TypeScript emission has
never been in the denominator of any number this project publishes.** It was unbounded for
its entire life and no published precision figure ever reflected it.

On the audit target, 57 findings removed, 14 added, itemised finding-by-finding:

```
    14  Shell Command Execution   -> line still reported, as AGENT-047
    36  Shell Command Execution   -> line now silent
     7  Dangerous Code Execution  -> line now silent
```

The 14 are a re-labelling: `RULE_SUBSUMPTION_MAP` was suppressing AGENT-047 under
AGENT-034, and the rule actually titled "Subprocess Execution Without Sandbox" now
surfaces.

**The 7 are the cost, and one of them I will not defend:**

```
AGENT-034  Dangerous Code Execution   tier=BLOCK  confidence=0.95  severity=critical
           return eval(expr)
```

`eval` is dangerous whether or not it sits in a tool handler. AGENT-034's boundary
constraint follows from its being a rule about unvalidated *tool input*; it does not follow
that dynamic code execution stops mattering outside a tool, and the Python side reports
that shape under AGENT-017, which has no tool gate. Narrowing the gate to the
shell-execution pattern types is one line and returns all seven. **I did not make it** —
which pattern types belong inside the gate *is* the gate's semantics, and that is
DECISIONS 30, not a nudge.

**43 tests encoded the old contract.** They were not inverted and not deleted: their
subject is call-shape recognition — receiver resolution, constant-argument suppression, the
fixed-non-shell-program predicate, all RUN4 denoise coverage — so they now write their
snippets inside a real MCP tool handler. The suppression tests moved inside the boundary
too, because on bare files they would pass *vacuously*, the gate suppressing the finding
whatever the predicate did. `TestToolBoundaryGate` adds the contract itself, both
directions, three other frameworks, and a call below the handler scope.

---

## 3. W21 — measured, reverted, recommendation: retire

Scratch commit `3f52f90`, flag-gated, reverted in `25636c3`.

Before the measurement, the code settles it. `_evaluate_rule` implements three branches and
dispatches on `type`:

```
total pattern entries: 84
values of the 'type' key the evaluator dispatches on:
  {'<MISSING>': 81, 'python_ast': 1, 'function_call': 1, 'regex': 1}
```

Wiring turns on **3 of 84 blocks**. The other 81 use `pattern_type` plus ~70 bespoke keys
nothing parses. This is not a dormant mechanism; it is an evaluator that does not read the
dialect the rules are written in.

Measured, flag off vs. on at the same commit:

| | Layer 1 TP | FP | FN | precision | F1 | target noise |
|---|---|---|---|---|---|---|
| off | 196 | 93 | 40 | 0.6782 | 0.7467 | 44 |
| on | 197 | **115** | **44** | **0.6314** | **0.7125** | 45 |

**Wiring loses four true positives.** The +35 AGENT-001 findings duplicate lines already
covered; dedup and subsumption then remove the AGENT-034/047 findings that *were* matching
labels. A rule engine that reduces recall is an unusual enough result to make the
recommendation unambiguous: **retire**, and fix the `CLAUDE.md` checklist either way —
it is what manufactured five of the six rules W19 withdrew.

---

## 4. W22 — the 98.51% is not a stale measurement

`CLAIMS_RECONCILIATION.md`. **Nothing public-facing was edited.**

`git log -S "98.51"` returns one commit. The `results/layer1.json` committed **in that same
commit** reads P 96.55% / R 47.46% / F1 0.6364, TP 112 / FP 4 / **FN 124**. The published
figure is none of those. Where it comes from:

```
$ python3 -c "tp,fp=198,3; p=tp/(tp+fp); r=1.0; print(p, r, 2*p*r/(p+r), fp/(tp+fp))"
P = 98.5075%   R = 100.00%   F1 = 99.2481%   FP rate = 1.49%
```

All four published figures to four decimal places, from TP = the annotation count, FP = the
three residual false positives the README itself names, and **FN assumed to be zero**.
Recall was not measured; it was set to 100% by construction. `CHANGELOG.md` then carries it
forward as "98.51% → 100%".

That is why it needed tracing rather than updating. The rest of the claims table is stale
measurements a re-run corrects. This one no re-run can reproduce, and it should be struck.

**Also found while sweeping: a live red CI gate.** `precision_recall.py:503` ends
`if result.f1_score < 0.75: sys.exit(1)`, and `benchmark.yml` runs it with
`continue-on-error` deliberately removed. Current F1 is 0.7467 — the script exits 1 today.
Meanwhile `gates.yaml`, whose header calls itself "THE SINGLE SOURCE OF TRUTH" and
describes deleting the inline workflow gate *because two gates on one layer hid a
contradiction for six months*, carries `f1_min: 0.72` and passes. The inline gate was
deleted; this hard-coded floor was never noticed. Before this run F1 was 0.7510 — one
thousandth above it. **Neither threshold was touched** (DECISIONS 31).

---

## 5. Invariants at `25636c3`

| invariant | result |
|---|---|
| noise / high-value | **44 / 20 = 2.2:1** (target ≤5:1) |
| recall on the target | **0/6, unchanged in both directions** |
| AVB knowns | **R 100.0% / P 88.0% / F1 0.9362, unchanged** |
| Layer 1 | **TP 196 / FP 93 / FN 40**, P 0.6782 / R 0.8305 / F1 0.7467 |
| Layer 1 true positives | **196, unchanged from RUN4**; FN 40, unchanged |
| `quality_gate_check.py` | **exit 0** against `gates.yaml`; ratchet untouched |
| `precision_recall.py` internal floor | **exit 1** — see DECISIONS 31 |
| full suite | **1748 passed, 1 skipped** (1731 at RUN4 + 17 added, none deleted) |
| advertised rules | **66**, every one with a producer and a firing demonstration |
| producer guard | fails on HEAD before the fixes, passes after; **no allow-list** |

Layer 1 precision fell 0.6853 → 0.6782. **Itemised, not absorbed:** exactly three findings,
all AGENT-120, all in a fixture named `vulnerable_hooks` containing
`powershell -WindowStyle Hidden` and `curl … | bash`, all correct by the rule's own
definition, and **none of them labelled** — no label in the corpus cites AGENT-120 or that
fixture, across 81 labelled files. Someone wrote a fixture for the rule and the rule could
never see it. Third time this run's shape has produced a precision drop that is a labelling
gap rather than a regression.

---

## 6. What I would do first next

**DECISIONS 31, because it is red.** Delete the `sys.exit(1)` from `precision_recall.py` so
`gates.yaml` is what its header says it is, then label the three AGENT-120 findings. Both
are small; together they close a contradiction and un-red CI.

**Then DECISIONS 30.** Whether `eval` outside a tool handler is reportable is a
capability question, and a one-line answer either way.

**Then the corpus.** Twelve advertised rules have no fixture, and the two benchmarks that
grade this tool contain almost no TypeScript — which is how an entirely ungated rule path
survived to v0.19.2 without ever appearing in a published precision figure.

---

## 7. Confirmation

**I did NOT push, merge, tag, or publish, and I did not modify any oracle, fixture, or
dataset.**

Five commits to `fix/py314-blocker` plus one revert, all local. No file under
`tests/fixtures/` or `tests/ground_truth/` was written; every new test builds its inputs
with `tmp_path` or synthetic literals. No ground-truth label was changed — the AGENT-015
diagnosis and the three AGENT-120 corpus additions are logged, not applied. No threshold,
tier boundary, confidence value or ratchet was changed, including the two I found in
conflict. `results/layer1.json` was regenerated in place, which is the refresh DECISIONS 28
asked for.

Actions avoided: `git push`, `git merge`, `git rebase`, `git tag`, `gh` writes, PyPI/npm
publish, `rm -rf`, anything under `eval/`, and any edit to an oracle, dataset, fixture,
confidence threshold, or public-facing metric claim.
