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
