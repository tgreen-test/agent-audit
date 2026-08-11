# DECISIONS — night run 2026-08-11

Forks hit while working unattended on `fix/py314-blocker`. Items under `NEEDS-HEADY` were
deliberately **not** acted on. Everything else was done and is reversible.

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

**Options**
- **(a) Recommended.** Align `quality_gates_v2.yaml` layer1 to the inline floors already
  reviewed and documented in `benchmark.yml` (0.72 / 0.80 / 0.75), and delete the duplicate
  inline gate so there is one source of truth. This is not loosening: the inline numbers are
  the ones CI has actually been enforcing on the hard-failing Layer 1 step since `1009782`.
  The v2 file is the stale aspirational copy.
- (b) Keep 0.90/0.85/0.87 and accept a red Quality Gate until denoise work lands. Honest,
  but a permanently-red gate gets ignored, which is how we got here.
- (c) Re-mask the step. Returns it to inert. Not recommended.

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

ASI-04 at a flat 0 with zero true positives is not a threshold problem — nothing in that
category is detected at all. That is a real coverage hole and the highest-value thing on
this list, independent of which threshold option you choose.

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

## Environment changes made outside the repo

Reversible, listed so they can be undone:

1. `/opt/homebrew/lib/python3.14/site-packages/agent_audit.pth` rewritten to the current repo
   path (agent-audit 0.18.2 → 0.19.2 editable). Prior file backed up in the session
   scratchpad as `agent_audit.pth.bak`.
2. `pytest-asyncio 1.4.0` installed into homebrew python 3.14.
3. `uv python install 3.13` → 3.13.11.
4. Throwaway venvs under `/tmp/w5/venvs/{3.11,3.12,3.13,3.14}`; the 3.14 one additionally has
   the tree-sitter extras. Nothing under `eval/` was touched.
