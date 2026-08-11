# PROGRESS — night run 2026-08-11

**State: COMPLETE. W0 through W5 done. Stopped before P0A denoise, as instructed.**

Read `NIGHT_RUN_REPORT.md` first (one page), then `NIGHT_RUN_LEDGER.md` for evidence,
then `DECISIONS.md` for the six `NEEDS-HEADY` items.

## Where things stand

Branch `fix/py314-blocker`, 5 commits on top of `78e1337`:

```
d95b62d bench: make the AVB baseline real instead of inert, and refresh layer1.json
363cfa3 ci: fix the AVB invocation and stop masking failures with continue-on-error
7a79d28 test: declare packages/audit on the pytest import path
0f321ff fix(scanner/python): drop ast.NameConstant fallbacks removed in Python 3.14
279082a fix(benchmark): stop AVB adapter reporting a dead scanner as zero findings
```

Working tree carries only the three night-run markdown files
(`NIGHT_RUN_LEDGER.md`, `NIGHT_RUN_REPORT.md`, `DECISIONS.md`, this file) plus untracked
per-run benchmark outputs (`results/avb_results.json`, `results/results.json`,
`results/avb_report.md`) that are regenerated on every run and were left uncommitted.

## Proven

- AVB knowns: **0.0% → 100.0% recall**, 0.0s → 0.2s per sample. Cause was a stale editable
  install `.pth` pointing at the pre-move repo path, laundered into "zero findings" by a bare
  `return []` in the benchmark adapter.
- `python3 -m pytest tests/ packages/audit/tests/ -q` → **1606 passed, 1 skipped**.
- Layer 1 reproduces the documented v0.19.0 metric: P 73.41% / R 82.70% / F1 77.78%.
- No behavioural divergence between Python 3.11 / 3.12 / 3.13 / 3.14 at HEAD.
- Pre-fix, on 3.14 only, one Python file with `while running:` zeroed an entire directory
  scan: 8 findings → 0.

## The one open question

Whether the blind audit's "0 of 6 on a large TypeScript codebase" was that crash or a real
gap. It hinges on whether that codebase contains any `.py` files. Re-run the audit at
`0f321ff` and diff. This is the first task tomorrow and is described in
`NIGHT_RUN_REPORT.md` §4.

## Environment changes made outside the repo (reversible)

Listed with undo instructions in `DECISIONS.md` § "Environment changes made outside the repo":
editable install repointed (0.18.2 → 0.19.2), `pytest-asyncio 1.4.0` installed,
Python 3.13.11 installed via uv, throwaway venvs under `/tmp/w5/venvs/`.
Nothing under `eval/` was touched.
