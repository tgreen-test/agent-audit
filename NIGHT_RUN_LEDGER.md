# NIGHT RUN LEDGER — 2026-08-11

Branch: `fix/py314-blocker` (cut from master `78e1337`). Anchor tag: `v0.19.2` = `1009782`.
Interpreter: Python 3.14.3 (`/opt/homebrew/bin/python3`). `python` is not on PATH.

Rules honored: no push/merge/tag/publish; no edits to oracle, dataset ground truth,
benchmark fixtures, or `quality_gates_v2.yaml` thresholds.

---

## W0 — The AVB 0.0% was a broken editable install, not a detection failure or a 3.14 incompatibility.

**BEFORE**

```
$ cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" \
    --tool agent-audit --dataset knowns --output /tmp/avb_before.json

  Version: agent_audit
  Scanning KNOWN-001... TP:0 FN:1 FP:0 (0.0s)
  Scanning KNOWN-002... TP:0 FN:1 FP:0 (0.0s)
  ... (all 12 samples identical shape) ...
  Scanning KNOWN-012... TP:0 FN:1 FP:0 (0.0s)

  Summary for agent-audit:
    Recall: 0.0%
    Precision: 0.0%
    F1: 0.0000
```

Note the reported `Version: agent_audit` — that is already the smoking gun. It is
`output.split()[-1]` of the string `"…/python3.14: No module named agent_audit"`.

**CAUSE**

Three-link chain, all mechanical:

1. `/opt/homebrew/lib/python3.14/site-packages/agent_audit.pth` contained the single line
   `/Users/heady/Documents/agent-audit/agent-security-suite/packages/audit`.
   That directory does not exist — the repo now lives under `Documents/**Research**/agent-audit/`.
   The editable install was made before the repo was moved, so `import agent_audit`
   failed process-wide:
   ```
   $ python3 -c "import agent_audit"
   ModuleNotFoundError: No module named 'agent_audit'
   ```
   (`pip show agent-audit` still reported `0.18.2` installed, which is why the stale-version
   hypothesis looked plausible. Nothing was stale — nothing was importable at all.)

2. `tests/benchmark/agent-vuln-bench/harness/adapters/agent_audit_adapter.py:87` shells out with
   `subprocess.run([sys.executable, "-m", "agent_audit", "scan", …], capture_output=True)`.
   That subprocess exited 1 with `No module named agent_audit` on **stderr** and nothing on stdout.

3. `agent_audit_adapter.py:103-109` — `output = result.stdout`; empty; stderr does not start with
   `{`; therefore **`return []`**. The adapter never inspects `result.returncode`. A total
   failure to launch the tool is reported to the harness as a successful scan that found nothing.

That is exactly the observed signature: every sample FN, zero FP, 0.0 s elapsed.

The root `tests/` suite (1542 tests) kept passing throughout because pytest's rootdir insertion
puts the repo on `sys.path`; it never exercises the installed distribution. So the breakage was
invisible to the test suite by construction.

**FIX**

Part 1 — environment (this machine only, not a repo change):
```
$ python3 -m pip install -e packages/audit --no-deps --break-system-packages
Successfully uninstalled agent-audit-0.18.2
Successfully installed agent-audit-0.19.2

$ python3 -c "import agent_audit; print(agent_audit.__file__, agent_audit.__version__)"
/Users/heady/Documents/Research/agent-audit/agent-security-suite/packages/audit/agent_audit/__init__.py 0.19.2
```
(Prior `.pth` backed up to the session scratchpad before overwriting.)

Part 2 — repo, so this can never again be silent: see the adapter hardening entry below (W0b).

**AFTER**

```
$ cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" \
    --tool agent-audit --dataset knowns --output /tmp/avb_after.json

  Version: 0.19.2
  Scanning KNOWN-001... TP:1 FN:0 FP:0 (0.2s)
  Scanning KNOWN-002... TP:1 FN:0 FP:0 (0.2s)
  Scanning KNOWN-003... TP:3 FN:0 FP:2 (0.2s)
  Scanning KNOWN-004... TP:5 FN:0 FP:0 (0.2s)
  Scanning KNOWN-005... TP:3 FN:0 FP:0 (0.2s)
  Scanning KNOWN-006... TP:1 FN:0 FP:0 (0.2s)
  Scanning KNOWN-007... TP:2 FN:0 FP:1 (0.2s)
  Scanning KNOWN-008... TP:1 FN:0 FP:0 (0.2s)
  Scanning KNOWN-009... TP:2 FN:0 FP:0 (0.2s)
  Scanning KNOWN-010... TP:1 FN:0 FP:0 (0.2s)
  Scanning KNOWN-011... TP:1 FN:0 FP:0 (0.2s)
  Scanning KNOWN-012... TP:1 FN:0 FP:0 (0.2s)

  Summary for agent-audit:
    Recall: 100.0%
    Precision: 88.0%
    F1: 0.9362
```

Recall **0.0% → 100.0%**, per-sample time **0.0 s → 0.2 s**. Zero source changes to any scanner,
rule, threshold, oracle, or fixture. **H1 confirmed. H2 (CLI broken under 3.14) is refuted** —
see W5. H3 (path/format mismatch) not reached.

**GUARD** — see W0b.

---

## W0b — The adapter can no longer report a dead scanner as "zero findings". (guard for W0)

**BEFORE** (guard tests run against the pre-fix adapter, restored from `HEAD`):

```
$ python3 -m pytest tests/test_benchmark_adapter_guard.py -q
FAILED tests/test_benchmark_adapter_guard.py::test_agent_audit_importable_in_subprocess
FAILED tests/test_benchmark_adapter_guard.py::test_child_env_puts_working_tree_on_pythonpath
FAILED tests/test_benchmark_adapter_guard.py::test_version_probe_rejects_failed_subprocess
FAILED tests/test_benchmark_adapter_guard.py::test_version_probe_never_returns_module_name
FAILED tests/test_benchmark_adapter_guard.py::test_scan_raises_on_empty_output
FAILED tests/test_benchmark_adapter_guard.py::test_scan_raises_on_unparseable_output
6 failed, 2 passed in 0.06s
```

The two that already passed are the negative controls — a clean scan (`{"findings": []}`)
and a non-zero exit carrying valid JSON must *not* raise. They are in the file precisely so
the fix cannot be "raise on everything".

**CAUSE** — as W0: `agent_audit_adapter.py:109` `return []` on empty stdout, and
`agent_audit_adapter.py:68` `output.split()[-1]` turning an error message into a version.

**FIX** — commit `279082a`:
- `scan()` raises `ToolNotAvailable` on empty or unparseable output. Non-zero exit with
  valid JSON stays a success, because the scanner exits non-zero on BLOCK-tier findings —
  return code is not the failure signal, parseability is.
- `get_tool_version()` raises on a non-zero `--version` exit.
- Both subprocesses run with the in-repo `packages/audit` prepended to `PYTHONPATH`
  (`_child_env()`), so the benchmark runs from a bare checkout and is pinned to the working
  tree instead of whatever is in site-packages. This alone would have prevented tonight's
  failure.

**AFTER**

```
$ python3 -m pytest tests/test_benchmark_adapter_guard.py -q
........                                                                 [100%]
8 passed in 0.18s
```

**GUARD** — `tests/test_benchmark_adapter_guard.py`, 8 tests, collected by the default
root run. Falsified above: 6 fail on the old code, all 8 pass on the new.

*Honest caveat:* `test_agent_audit_importable_in_subprocess` fails on the old adapter with
`AttributeError: _child_env` rather than for the reason it exists. Its real value is
forward-looking — it asserts the adapter's own child environment can import the package,
which is the exact precondition that silently vanished.

---

## W0c — Root test suite was under-reporting: 10 async tests were erroring on a missing plugin.

**BEFORE**

```
$ python3 -m pytest tests/ -q
FAILED tests/test_utils/test_mcp_client.py::TestStdioTransport::test_connect_creates_process
... (10 total) ...
10 failed, 1539 passed, 1 skipped, 2301 warnings in 11.46s

PytestUnknownMarkWarning: Unknown pytest.mark.asyncio - is this a typo?
```

**CAUSE** — `pytest-asyncio` is declared at `packages/audit/pyproject.toml:70`
(`pytest-asyncio = "^0.21.0"`) but was not installed in this interpreter, so every
`@pytest.mark.asyncio` coroutine test was collected, never awaited, and failed. Not a
code defect; a second instance of the same class of problem as W0 — the declared
environment and the actual environment had drifted apart.

**FIX** — environment only, no repo change:
`python3 -m pip install pytest-asyncio --break-system-packages` → `pytest-asyncio-1.4.0`.
(Resolver picked 1.4.0, not the `^0.21.0` pin, because the installed pytest is 9.0.2 while
the pyproject dev pin is `pytest = "^7.0"`. That pin drift is logged in DECISIONS.md.)

**AFTER**

```
$ python3 -m pytest tests/ -q
1549 passed, 1 skipped, 2291 warnings in 11.38s
```

**GUARD** — none in-repo. This is dev-environment provisioning, not source. The durable fix
is a documented `poetry install`/dev-extras step; logged under `NEEDS-HEADY` in DECISIONS.md.

---

## W1 — The two NameConstant edits were necessary and are behaviour-neutral; they should be deletions, not duplicated isinstance checks.

**BEFORE** (uncommitted working-tree edits reverted, i.e. master's code, on Python 3.14):

```
$ python3 -m pytest tests/test_scanners/test_py314_ast_constant.py -q
FAILED ...TestShellKeywordNonLiteral::test_non_literal_shell_does_not_raise[subprocess.run(cmd, shell=use_shell)]
FAILED ...TestShellKeywordNonLiteral::test_non_literal_shell_does_not_raise[subprocess.run(cmd, shell=cfg.use_shell)]
FAILED ...TestShellKeywordNonLiteral::test_non_literal_shell_does_not_raise[subprocess.run(cmd, shell=bool(flag))]
FAILED ...TestShellKeywordNonLiteral::test_non_literal_shell_does_not_raise[subprocess.run(cmd, shell=(a or b))]
FAILED ...TestShellKeywordNonLiteral::test_non_literal_shell_does_not_raise[subprocess.run(cmd, shell=opts['shell'])]
FAILED ...TestInfiniteLoopNonLiteral::test_non_literal_while_test_does_not_raise[running]
FAILED ...TestInfiniteLoopNonLiteral::test_non_literal_while_test_does_not_raise[a and b]
FAILED ...test_end_to_end_scan_of_non_literal_shell_and_loop
12 failed, 13 passed in 0.35s
```

Every failure is `AttributeError: module 'ast' has no attribute 'NameConstant'`.

**CAUSE**

`ast.NameConstant` was deprecated in 3.8 as an alias for `ast.Constant` and **removed in
3.14** — attribute access itself now raises. Two sites referenced it:

- `python_scanner.py:1249` in `_has_shell_true`
- `python_scanner.py:4384` in `_check_agent_infinite_loop_no_timeout` (AGENT-115)

In both, the reference sat in a branch reached only when the preceding
`isinstance(x, ast.Constant)` was False — that is, on any *non-literal* node. So on 3.14 the
scanner crashed on exactly the ordinary code real projects are made of: `shell=use_shell`,
`while running:`. Confirmed on this interpreter:

```
$ python3 -c "import ast, sys; print(sys.version_info[:2], hasattr(ast,'NameConstant'))"
(3, 14) False
```

**Did the naive `NameConstant → Constant` swap widen what these sites accept?** No — and
this is the question W1 asked, so here is the explicit answer with evidence:

- Site 1 compares with `keyword.value.value **is True**` — an identity test against the
  `True` singleton. `1 is True` and `"yes" is True` are both False, so admitting numbers and
  strings into the branch changes nothing. Pinned by
  `test_truthy_non_bool_is_not_shell_true[1|'true'|'yes'|1.0|[1]]`.
- Site 2's second branch became `elif isinstance(child.test, ast.Constant)` immediately
  after `if isinstance(child.test, ast.Constant)` — **unreachable**. Same at site 1, where
  the first branch always returns.

So no `isinstance(x.value, bool)` guard is required at either site.

**FIX** — commit `0f321ff`. Deleted both dead branches instead of leaving a duplicated
isinstance check, and left a comment at each site recording why the fallback existed and why
it is safe to drop. Behaviour is identical on 3.8-3.13 (the alias was the same class object)
and fixed on 3.14.

**AFTER**

```
$ python3 -m pytest tests/test_scanners/test_py314_ast_constant.py -q
.........................                                                [100%]
25 passed in 0.05s

$ python3 -m pytest tests/ -q
1574 passed, 1 skipped, 2291 warnings in 11.06s
```

**GUARD** — `tests/test_scanners/test_py314_ast_constant.py`, 25 tests. Three-way run over
the same command, same test file:

| scanner variant | result |
|---|---|
| A. master (`ast.NameConstant`) | **12 failed**, 13 passed |
| B. naive swap (duplicate `ast.Constant` branch) | 25 passed |
| C. shipped (dead branches deleted) | 25 passed |

**UNVERIFIED — one sub-goal of W1 cannot be met, and I am not going to fake it.**
W1 asked for "a test that fails on the naive replacement and passes on the correct one".
No such test can exist: rows B and C above are the *same program*. The naive swap's extra
branch is unreachable (site 1 returns unconditionally before it; site 2 is an `elif` on an
identical condition), so there is no input that distinguishes them. The difference is dead
code, not behaviour. What the test file does discriminate is A vs B/C — the actual 3.14
defect — plus the strict-truthiness pins that would fail if anyone later "fixed" this by
relaxing `is True` to a truthiness check, which is the widening W1 was worried about.

Also checked, since the same removal class bites other aliases:
`grep -rn "ast\.(NameConstant|Str|Bytes|Num|Ellipsis|Index|ExtSlice|AugLoad|AugStore|Param)\b" packages/ tests/`
returns no live references — only my new comments and three *scanned test fixtures*
(`tests/fixtures/**`) that use `ast.Num` as input data and are never executed. Fixtures left
untouched per the hard rules.

---

## W2 — packages/audit/tests/ never worked, and tests/ only worked by accident.

**BEFORE**

```
$ python3 -m pytest packages/audit/tests/ -q
ERROR packages/audit/tests/test_report/test_charts.py
ERROR packages/audit/tests/test_report/test_cli_report.py
ERROR packages/audit/tests/test_report/test_generator.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
3 errors in 0.05s
```
(each `ModuleNotFoundError: No module named 'agent_audit'`)

**CAUSE — two layers, and the second one matters more than the reported symptom.**

*Layer 1, the reported symptom:* same broken editable install as W0. `agent_audit` was not
importable by any process, so this root's modules could not import it.

*Layer 2, found while verifying:* there is no packaging or path configuration tying the test
roots to the package at all. `packages/audit/agent_audit` is not importable from the repo
root, and there was no `pytest.ini` / `[tool.pytest.ini_options]` / root `conftest.py` path
setup anywhere. The root suite's 1542 green tests were importing the package **by accident**:

```
tests/benchmark/performance_test.py:21
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "audit"))
```

That file matches pytest's `*_test.py` collection glob and sorts first under `tests/`, so
importing it during collection injected the path for the rest of the session. Proof — same
interpreter, same moment, install deliberately broken:

```
### A: full tests/ collect      -> 1575 tests collected in 0.30s        (inherits the hack)
### B: tests/test_scanners/     -> no tests collected, 19 errors in 0.08s  (does not)
```

So "the suite is green" was never evidence the package was installed, and any subset run was
already broken. This is the same failure family as W0: a real dependency held together by a
side effect nobody declared.

**FIX** — commit `7a79d28`. New root `pytest.ini`:

```ini
[pytest]
pythonpath = packages/audit
markers =
    asyncio: mark test as an asyncio coroutine test (requires pytest-asyncio)
```

`pythonpath` is pytest's own built-in ini option (>=7), which is why this is a
packaging/path-configuration fix rather than another `sys.path` hack. No test file was
edited; `performance_test.py`'s insert is now redundant but harmless and was left alone.

**AFTER** — run with the editable install **deliberately re-broken**, so the ini is provably
doing the work rather than the reinstall:

```
### WITH pytest.ini, install still BROKEN (/Users/heady/Documents/agent-audit/...)
-- packages/audit/tests:      32 passed, 12 warnings in 2.61s
-- tests/test_scanners subset: 375 passed, 13 warnings in 0.34s
```

And with the install correct:

```
$ python3 -m pytest packages/audit/tests/ -q
32 passed, 12 warnings in 2.56s
$ python3 -m pytest tests/ -q
1574 passed, 1 skipped, 2291 warnings in 10.90s
```

**GUARD** — partial, and I want to be exact about it. `pytest.ini` is itself the mechanism, and
`python3 -m pytest tests/test_scanners/ -q` passing is a check that fails without it. There is
no test asserting "a subset run can import the package", because such a test would run inside
the very session whose path it is asserting about. The honest guard is CI: W3 adds a subset
invocation so a regression here fails a job rather than hiding until someone runs a subset by
hand.

**NEEDS-HEADY** — unifying the two test roots is an architecture-level move and was not done
tonight. Logged in DECISIONS.md.

---

## W3 — The CI benchmark step could never have succeeded, and the quality gate could never have failed.

**BEFORE** — the exact command from `.github/workflows/benchmark.yml` "Run Agent-Vuln-Bench":

```
$ cd tests/benchmark && python3 agent-vuln-bench/harness/run_eval.py \
    --tool agent-audit --dataset knowns --output /tmp/x.json
Traceback (most recent call last):
  File ".../tests/benchmark/agent-vuln-bench/harness/run_eval.py", line 35, in <module>
    from .adapters.agent_audit_adapter import AgentAuditAdapter
ImportError: attempted relative import with no known parent package
```

**CAUSE** — two independent mechanisms, both required for the silence:

1. `run_eval.py` uses relative imports (`from .adapters...`) and its package directory
   name contains a hyphen, so it cannot be run as a script — only as
   `python -m "agent-vuln-bench.harness.run_eval"` with `tests/benchmark` importable.
   `benchmark.yml:181` and `benchmark.yml:260` both used the script form.
2. `continue-on-error: true` on that step (`benchmark.yml:187`) turned the guaranteed
   failure into a green job. The downstream "Generate baseline" step (`:195`) was masked
   the same way — which is the direct answer to why `results/baseline.json` has never
   existed.

**Audit of all 7 `continue-on-error: true` occurrences:**

| file:step | verdict | reasoning |
|---|---|---|
| benchmark.yml `Run Agent-Vuln-Bench` | **REMOVED** | hid an invocation that could never work |
| benchmark.yml `Generate baseline (main only)` | **REMOVED** | hid why baseline.json never existed |
| benchmark.yml `Upload baseline artifact` | **REMOVED** | hid the missing artifact |
| benchmark.yml `Run Quality Gate (v2)` | **REMOVED** | the job named "Quality Gate Check" was structurally incapable of failing |
| benchmark.yml `Download baseline (if exists)` | KEPT | there genuinely is no baseline before the first successful main run |
| benchmark.yml `Run Multi-Tool Evaluation` | KEPT | `workflow_dispatch`/schedule only, depends on best-effort bandit/semgrep, gates nothing. Invocation still fixed to module form. |
| ci.yml `Upload SARIF to GitHub` | KEPT | `upload-sarif` fails on forks and without code-scanning permissions |

One more mask found while auditing, not in the original list —
`ci.yml:90`, `agent-audit scan . --format sarif ... || true`. Findings should not fail CI,
but that `|| true` also swallowed a scanner *crash*: no SARIF would be produced, and the
upload step's `continue-on-error` then hid the miss. A dead scanner looked exactly like a
clean one — the same failure shape as W0. Replaced with: findings tolerated, missing or
invalid SARIF is an error.

**FIX** — commit `363cfa3`. Module form + `PYTHONPATH=tests/benchmark` at both call sites;
`python` → `python`(GitHub-provided, kept) with explicit output assertions
(`test -s results/avb_results.json`); the quality gate now honours the script's own
documented exit contract (0 pass / 1 blocking / 2 warning) instead of a blanket mask;
CI runs both test roots plus a subset guard.

**AFTER** — GitHub Actions cannot be run locally, so each changed step's command was
executed in a shell. `python` → `python3` is the only substitution.

```
$ PYTHONPATH=tests/benchmark python3 -m "agent-vuln-bench.harness.run_eval" \
    --tool agent-audit --dataset all --output results/avb_results.json \
    --report results/avb_report.md
run_eval exit=0
results/avb_results.json OK
    Recall: 95.2%   Precision: 87.0%   F1: 0.9091

$ python3 tests/benchmark/scripts/save_avb_baseline.py \
    --eval-results results/results.json --output results/baseline.json
save_avb_baseline exit=0        results/baseline.json OK

$ # ci.yml self-scan step, verbatim
agent-audit exited 1
SARIF present (48909 bytes)
SARIF valid JSON

$ python3 -m pytest ../../tests/ tests/ -q        # from packages/audit
1606 passed, 1 skipped, 2303 warnings in 13.58s   # 1574 + the 32 that CI never ran

$ python3 -m pytest ../../tests/test_scanners/ -q
375 passed, 13 warnings in 0.32s

$ python3 -c "import yaml; [yaml.safe_load(open(f)) for f in (...)]"
YAML OK .github/workflows/ci.yml
YAML OK .github/workflows/benchmark.yml
YAML OK .github/workflows/publish.yml
```

**GUARD** — the removed `continue-on-error` lines are themselves the guard: these steps can
now fail the job. The subset-run step in ci.yml guards W2.

**NEEDS-HEADY — read this before merging.** Removing `continue-on-error` from the quality
gate makes it real, and the first run will be **RED**. Not because of anything changed
tonight: `quality_gates_v2.yaml` layer1 demands P≥0.90 / R≥0.85 / F1≥0.87, while measured
reality is P 73.41% / R 82.70% / F1 77.78%, and `benchmark.yml`'s own inline Layer 1 gate
uses a different, realistic set (0.72 / 0.80 / 0.75). Two contradictory threshold sets for
one layer. I did not touch either. Options and recommendation are in DECISIONS.md.

---

## W4 — The baseline existed nowhere, and the first one I generated was inert.

**BEFORE**

```
$ ls results/baseline.json
ls: results/baseline.json: No such file or directory

$ python3 tests/benchmark/quality_gate_check.py \
    --config tests/benchmark/quality_gates_v2.yaml --results results/
  ⏭️ [SKIP] Agent-Vuln-Bench results not found
```

`quality_gates_v2.yaml` sets `regression.allow_regression: false` against
`results/baseline.json`, so with no file the regression gate was inert.

**CAUSE** — layered:

1. The baseline was never produced because the CI step that produces it was masked (W3).
2. Producing it by hand exposed a second defect. `save_avb_baseline.py:extract_passing_samples`
   needs per-sample data (`<tool>.samples[].fn_count`), which lives in run_eval's directory
   output `results/results.json`. The workflow fed it `results/avb_results.json`, the
   *aggregate* CI-metrics file (keys `overall`, `set_A`, …) which has no `samples[]`. Result:

   ```
   ✅ Baseline written to results/baseline.json
      Passing samples: 0
   ```

   A baseline file that exists and satisfies every existence check, while
   `check_regression` compares against an empty set — so no sample can ever be reported as
   newly failing. Present, and still inert.
3. `save_avb_baseline.py:run_eval_internal` invoked run_eval **as a script**, so the
   no-`--eval-results` fallback path hit the same ImportError as the CI step and could
   never have worked either.

**FIX** — commit `d95b62d`. Workflow feeds `results/results.json`; the script now refuses to
write a baseline with zero passing samples and says why; `run_eval_internal` uses the module
form and reads the per-sample file. Also regenerated `results/layer1.json` — the committed
copy was dated 2026-07-04 and reported R 47.5% / F1 63.6%, i.e. it was itself a broken-
environment artifact.

**AFTER**

```
$ python3 tests/benchmark/scripts/save_avb_baseline.py \
    --eval-results results/avb_results.json --output /tmp/w3/inert.json
Error: extracted 0 passing samples — refusing to write an inert baseline.
       Input was: results/avb_results.json
       Expected run_eval's per-sample output (results/results.json) ...
exit=1

$ python3 tests/benchmark/scripts/save_avb_baseline.py \
    --eval-results results/results.json --output results/baseline.json
✅ Baseline written to results/baseline.json
   Passing samples: 21
   Recall: 95.2%   Precision: 87.0%
exit=0

$ python3 tests/benchmark/quality_gate_check.py \
    --config tests/benchmark/quality_gates_v2.yaml --results results/
============================================================
Quality Gate Results
============================================================
  ❌ [FAIL] Layer 1 recall 47.5% < 85%      <- stale layer1.json, now regenerated
  ... 10 failures, 2 warnings, 0 skipped
🚫 QUALITY GATE BLOCKED — fix failures before merging
GATE EXIT=1
```

A real verdict with a real exit code, which is what W4 asked for. The verdict is BLOCKED,
and it stays BLOCKED after regenerating layer1.json, for the threshold-mismatch reason in
W3's NEEDS-HEADY note. I did not adjust anything to turn it green.

Refreshed Layer 1, tool working:

```
$ python3 tests/benchmark/precision_recall.py --output-json results/layer1.json
  True Positives:  196     False Positives: 71     False Negatives: 41
  Precision: 73.41%   Recall: 82.70%   F1-Score: 77.78%
```

Within one finding of the documented v0.19.0 raw figures (P 73.58 / R 82.63 / F1 0.778).
**The headline metric in CLAUDE.md reproduces.** The 47.5% recall sitting in the repo was
the artifact, not the 82.6%.

**GUARD** — falsified rather than asserted. With a synthetic baseline that additionally
claims T12 passes:

```
regression: {"regression_free": false, "newly_failing": ["T12"],
             "total_prev": 22, "total_curr": 21}
gate:       ❌ [FAIL] AVB regression: 1 samples regressed: ['T12']
```

So the regression path detects a real regression end-to-end, and the committed baseline
(21/22 passing) is the thing being compared against. Plus the script-level guard: a zero-
sample baseline can no longer be written at all.

**NEEDS-HEADY** — `results/layer2.json` is a placeholder, not a measurement: one target
named `test1`, `scan_duration_seconds: 150.0`, `tool_version: 0.5.0`,
`timestamp: 2026-02-04T12:00:00`. It is the source of both current Layer 2 warnings.
Regenerating it means cloning the external benchmark targets over the network; not done
tonight. Logged in DECISIONS.md.

---

## W5 — Full-matrix sanity, and the answer to the TypeScript question.

Not a fix, so no BEFORE/AFTER pair — this is measurement. Every number below is from a
clean `uv venv` per interpreter with `uv pip install -e packages/audit`, all four pointing
at the same working tree.

**Interpreters present on this machine**

| version | present | path |
|---|---|---|
| 3.9  | no  | — |
| 3.10 | no  | — |
| 3.11 | yes | `/opt/homebrew/bin/python3.11` (3.11.14) |
| 3.12 | yes | `~/.local/share/uv/python/...` (3.12.12) |
| 3.13 | **installed tonight** via `uv python install 3.13` (3.13.11) | `~/.local/bin/python3.13` |
| 3.14 | yes | `/opt/homebrew/bin/python3` (3.14.3 system, 3.14.2 in venv) |

CI's matrix is `['3.9','3.10','3.11','3.12']` and pyproject declares `python = "^3.9"`, so
3.13 and 3.14 are tested by nobody — which is how the `ast.NameConstant` removal reached a
developer machine as a mystery.

**Matrix result — current HEAD, identical on all four:**

| Python | `import agent_audit` | tree_sitter | KNOWN-004 (Python) | agent.ts (TypeScript) | AVB knowns |
|---|---|---|---|---|---|
| 3.11.14 | OK 0.19.2 | absent | 7 findings | 4 findings | R 100.0% / P 88.0% / F1 0.9362 |
| 3.12.12 | OK 0.19.2 | absent | 7 findings | 4 findings | R 100.0% / P 88.0% / F1 0.9362 |
| 3.13.11 | OK 0.19.2 | absent | 7 findings | 4 findings | R 100.0% / P 88.0% / F1 0.9362 |
| 3.14.2  | OK 0.19.2 | absent | 7 findings | 4 findings | R 100.0% / P 88.0% / F1 0.9362 |

**Zero divergence across versions at HEAD.** Byte-identical rule sets on the TS probe:
`AGENT-004, AGENT-026, AGENT-034, AGENT-034`.

### The blind-audit question, answered

W5 asked whether the tool scans TypeScript correctly on 3.14 versus 3.11, because the blind
audit's "0 of 6 real defects on a large TypeScript codebase" might be an environment
artifact. Three experiments:

**1. Does TypeScript scanning differ by Python version?** No. A TS file with four planted
defects (hardcoded `sk-proj-…` key, `exec()` with interpolated user input, `eval()`,
`fetch(req.query.url)` SSRF) returns the same 4 findings on 3.11, 3.12, 3.13 and 3.14. The
`ast.NameConstant` defect is in `python_scanner.py` and cannot touch a `.ts` file directly.

**2. Is the missing `tree_sitter` the explanation?** No measured effect. `tree_sitter` is
absent in every environment here, so `typescript_scanner.py` uses its regex fallback
everywhere — this is *not* 3.14-specific. Installing `tree-sitter`, `tree-sitter-python`,
`tree-sitter-javascript` and `tree-sitter-typescript` into the 3.14 venv changed the result
by nothing: 4 findings before, the same 4 after, AVB knowns unchanged at R 100% / P 88%.
On a larger corpus the fallback may well cost recall; on this probe it costs nothing, and I
am not going to extrapolate past what I measured.

**3. Could the 3.14 bug still have zeroed a whole scan?** **Yes — and this is the one that
matters.** The `ast.NameConstant` AttributeError is not caught per file; it aborts the
entire scan process. A directory containing one `.py` file with `while running:`, one
ordinary vulnerable `.py`, and the TypeScript file:

```
### PRE-FIX, 3.14:  AttributeError: module 'ast' has no attribute 'NameConstant'   (traceback, no JSON at all)
### PRE-FIX, 3.11:  8 findings
### POST-FIX, 3.14: 8 findings
```

**8 findings → 0, on 3.14 only, from one unremarkable Python file** — and the TypeScript
findings die with it. Feed that through the pre-hardening benchmark adapter (W0) and it
becomes "0 findings", silently.

Note the AVB `knowns` dataset does *not* trigger this: pre-fix 3.14 still scores R 100.0%,
because no KNOWN sample happens to contain a non-literal `shell=` or `while` test. So the
benchmark could not have caught it. That is a coverage gap in the corpus, not a mystery.

**GUARD** — `tests/test_scanners/test_py314_ast_constant.py` (W1) covers the crash. Nothing
guards the version matrix itself; CI stops at 3.12. Logged in DECISIONS.md.
