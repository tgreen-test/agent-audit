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
