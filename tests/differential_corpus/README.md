# `tests/differential_corpus/` — inputs for the tree-sitter differential

This tree exists for one test: `tests/test_treesitter_differential.py`. It is **not**
part of the graded corpus (`tests/fixtures/`, scored by Layer 1) and **not** part of the
rule-trigger tree (`tests/rule_fixtures/`, which proves every advertised rule has an
input). Nothing here is labelled and nothing here is scored.

## Why it is separate

The graded corpus contains `.py`, `.json`, `.md` and `.sh` files and nothing else — no
TypeScript, no JavaScript. That is the reason the tree-sitter question went unanswered for
so long: **there was no input on which the two parsing paths could disagree**, so
"tree-sitter is disabled" and "tree-sitter is enabled" produced identical benchmark
numbers, and the choice looked free.

Putting these files in `tests/fixtures/` would score them as unlabelled false positives
and deflate a published floor with test scaffolding — the measured cost of doing exactly
that with the rule-trigger tree was +26 FP, −5.6 points of precision and −0.035 F1
(`NIGHT_RUN_LEDGER.md § W26`). Two trees, two questions, two gradings.

## What is here

| file | exercises |
|---|---|
| `ts/eval_family.ts` | `eval`, `new Function`, `vm.runInNewContext`, and the aliases `window.eval` / `globalThis.eval` / `global.eval` / `self.eval` |
| `ts/child_process.ts` | `exec`, `execSync`, `spawn`, `spawnSync`, `execa`, destructured and namespace-imported |
| `ts/member_eval_control.ts` | **negative control** — `redisClient.eval(script)` and friends must NOT be flagged. This is the v0.19.2 Redis false-positive fix. |
| `ts/decl_signature.ts` | **negative control** — `eval(args): Type` declaration signatures |
| `ts/tool_boundary.ts` | the same sinks inside an MCP `server.tool(...)` handler, where AGENT-034's boundary gate admits them |
| `ts/framework_boundaries.ts` | the other boundary-opening constructs — `tool()` from vercel-ai, `DynamicStructuredTool` from langchain-js, an express route handler |
| `ts/receiver_shapes.ts` | receiver aliases, destructured imports, template/concat/spread-assembled programs, and the `.fetch`-on-a-receiver negative controls |
| `ts/prompt_names.ts` | three template strings that are **not** system prompts and one that is |
| `py/literals.py` | f-string detection and `ValueType` classification, both of which route through `TreeSitterParser` |
| `js/eval_family.js` | the `.js` half — `tree_sitter_javascript` exposes `language()` and *does* activate today |
| `js/child_process.js` | the `.js` shell-execution half |
| `py/secrets.py` | the Python side — `TreeSitterParser` is used by `semantic_analyzer`, so installing the extra changes Python results too, not only TS/JS |
| `py/env_reads.py` | env-read classification, the other `TreeSitterParser` consumer in `semantic_analyzer` |

The Python files matter more than they look. `tree_sitter_python` exposes the `LANGUAGE`
attribute the parser already recognises, so **installing the `tree-sitter` extra switches
the Python credential path over with no code change at all.** Any differential run that
only looked at `.ts` files would miss that entirely.

## The first version of this corpus was not sensitive enough, and that is the point

Written with only the eval / child_process families in it, the differential came back
**empty in both directions** against a build where the AST path was fully wired — while
`pytest tests/test_typescript_scanner.py` on that same build reported 40 failures. An
insensitive differential is worse than no differential, because it issues a clean bill of
health.

The files added afterwards are drawn directly from the test classes that moved:
`TestFixedNonShellProgram`, `TestWeakPromptNames`, `TestToolBoundaryGate`,
`TestFetchReceiver`, `TestConstantArgumentSuppression`, `TestExecSpawnReceiver`, and the
two Python cases in `test_treesitter_parser.py`. With those in place the same build
produces a differential of 2 losses and 8 additions, six of the additions being the exact
false positives the regex path was fixed to suppress.

**If you add a detection behaviour to the TypeScript scanner, add its shape here too.**
Otherwise the next person to wire the AST path gets the clean bill of health this corpus
gave on its first run.

## How to run it

    python3 tests/test_treesitter_differential.py

prints the full symmetric difference and exits 0/1. Under pytest it is a normal test, and
it skips with a loud reason when `tree_sitter` is not importable — a skip here is not a
pass, it means the question was not asked.
