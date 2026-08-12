# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.20.0] - 2026-08-11

This is a correction release. The improvements are real, but the first thing an existing
user needs is the list of things that were wrong, so that is what leads.

### Withdrawn — six rules removed from the advertised set

**The advertised rule count is 66. It was 72, and six of those rules could never fire.**

`AGENT-003`, `AGENT-011`, `AGENT-013`, `AGENT-015`, `AGENT-016`, `AGENT-036` are withdrawn.
No code path in the package could construct any of them, at any commit. Five had their
detection written out in full as a `detection.patterns` block in `rules/builtin/*.yaml` —
the place `CLAUDE.md` tells contributors to put it — and the only code that can execute
such a block, `RuleEngine.evaluate()`, has never had a caller outside a unit test. The
sixth, `AGENT-003`, had no detection of any kind.

Two of the six were also duplicates of live rules: `AGENT-015` duplicates `AGENT-030` (same
severity, same CWE-494, same ASI-04 category, same detection content), and `AGENT-013`
likewise. Those defects are still detected, under the surviving IDs.

**If you filter, suppress or report on any of the six IDs, that configuration was matching
nothing and can be deleted.** The gaps the withdrawals leave — notably untrusted package or
code acquisition in general application code — are recorded in `docs/RULES.md` under
Withdrawn Rules rather than papered over.

`tests/test_rule_producers.py` now fails the suite if an advertised rule has no producer.
There is no allow-list, deliberately: pinning the known-bad set is what made "advertised and
unproducible" a permanently acceptable state for six rules across four minor versions.

### Retracted — benchmark figures that were never measurements

**Any previously published figure of 98.51% precision, 100% recall, 99.25% F1 or 1.49%
false-positive rate is withdrawn.** So is `CHANGELOG.md`'s "Precision: 98.51% → 100%",
"Recall maintained at 100%" and "F1 Score: 100%" under `[0.4.1]`.

These are not stale measurements. The recall figure was `FN = 0` **by assertion** — the
v0.4.1 development brief states `Recall = 100% (0 FN)` in as many words — and the "→ 100%"
values were copied from that brief's *target* block and published as an achievement. The
`results/layer1.json` committed in the same commit measured **124 false negatives and 47.46%
recall**. There is no commit at which the published numbers were produced by any script, so
there is nothing to update them *to*; they are withdrawn.

The reproducible current value, from `python3 tests/benchmark/precision_recall.py`:

```
TP 199  FP 90  FN 37
Precision 68.86%   Recall 84.32%   F1 75.81%   FP Rate 31.14%
```

Two qualifications travel with that, and both are in
`docs/decisions/METRICS_RETRACTION.md` § 3: precision fell since v0.19.0 because three
*discovery bugs were fixed* and the tool began finding correct things the corpus does not
label, and at least 21 of the 90 false positives are unlabelled true positives — so 68.86%
is a floor, not a point estimate. It is stated as a bound rather than silently adjusted.

### Corrected — one rule count, on every surface that publishes one

**Four different numbers were published for one set of rules: 40, 49, 53 and 72.** The set
contains 66. `packages/audit/pyproject.toml` said 53 and is the PyPI description — the only
rule count on a distribution surface, and the most-read line the project has.

Eighteen in-repo locations now say 66, and the number is checkable rather than asserted:

```bash
python3 -c "import sys;sys.path.insert(0,'tests');from test_rule_producers import advertised_rules;print(len(advertised_rules()))"
```

`tests/test_published_rule_count.py` fails the suite if a published count and the rule set
ever disagree again, and fails per surface if a page stops stating a count at all — a page
dropping quietly out of the guard is how `docs/index.html` came to publish 49 while the
README published 72. The two published blog posts are left as written, with dated
correction notes: "40+" is vague rather than false, and the record of what was posted is
worth more than a silently-updated page.

Every metric on every in-repo surface is now the measured value with the command that
produces it beside it. `tests/README.md` carried the largest error — 30 points of precision
and 17 of recall, twice over, with no retraction note — and now opens with one.

### Fixed — the quality gate could pass without measuring anything

`quality_gate_check.py` decided the build by reading `results/layer1.json`, and read nothing
else. Two ways it exited 0 while proving nothing, both measured:

- **A stale results file passed.** `results/layer1.json` is committed, so every checkout has
  one whether or not anything measured it. A file describing a corpus three labels out of
  date cleared the ratchet and reported success.
- **No results file passed.** An empty results directory produced SKIP for two layers
  declared `enabled: true, blocking: true`, and SKIP is not counted as a failure.

Layer 1 results now carry a provenance stamp fingerprinting the three inputs a measurement
is a function of — the ground-truth labels, the fixture corpus, and the scanner source —
plus which `agent_audit` the interpreter that ran the scan actually imported. The gate
recomputes it and refuses to score a file that does not describe the tree it is checking.
Content-based, not time-based, so it does not fail correct builds in CI. A missing results
file for an enabled, blocking layer is now a failure; `--layers` lets a job state which
claim it is making instead of letting silence stand in for success.

**If you run the gate in your own CI, add `--layers` naming the layers that job measures**,
or a layer you do not produce results for will now fail the build rather than being skipped.

### Fixed — false positives, from two bug reports

- **AGENT-041 no longer treats every `.execute()` as a SQL sink** (issue #10). The KNOWN-008
  branch — SQL built upstream and passed in — had no evidence from its argument by design
  and asked none from its receiver, so `target_agent.execute(task)` was SQL injection at
  confidence 1.0. The receiver must now look like a database handle, by name or by an
  assignment in the same file that gives it one. Positive evidence, so an unrecognised
  receiver is silence rather than a BLOCK-tier accusation. Both true positives in the
  reporter's case survive, including the upstream-SQL one.
- **AGENT-004 no longer reports format strings as hardcoded credentials** (issue #8).
  `f"password={password}"` matched on the word and scored the entropy of `{password}\n`. A
  hardcoded credential is a literal in the source; a value that is entirely interpolation is
  not one. `f"sk-{suffix}"` keeps its literal prefix and is still analysed.
- **AGENT-010 distinguishes an inbound value from a computed one.** A prompt f-string that
  interpolates only locals scores 0.50 rather than 1.00. Downgraded rather than suppressed,
  because one step of distance is all a single-file pass can honestly see.
- **A subprocess call that names its own program is no longer treated as a shell sink.**
  `subprocess.run(["docker", "run", ..., image])` carried a taint flow claiming it reached a
  shell from user input. It does not. The reduction is confidence only, never suppression,
  because `["pip", "install", pkg]` has the identical shape and is a real finding.

None of these moved the benchmark, and that is worth knowing: the graded corpus contains
none of these shapes. They are validated against the reporters' code and pinned by tests.

### Decided — slopsquatting is not becoming a rule

A newly published attack class in this tool's declared territory, assessed and declined
with the measurement in `docs/decisions/SLOPSQUATTING.md`. The test that distinguishes
slopsquatting from any other supply-chain issue is *does this package name exist in the
registry*, and scanning makes no network calls by design. The half a static analyser can
see — runtime acquisition of code whose identity is not fixed in the source — is a rule this
project already owes its own corpus, and it is scoped for v0.21.0 in `NEXT_ROUND.md`.

### Added — `CAPABILITY_BOUNDARIES.md`

A new document at the repository root stating what the tool does not do: no cross-file
analysis, no call graph, no import following, no type resolution, no object-lifecycle
modelling, no runtime dispatch-order reasoning, no runtime behaviour. It includes the
blind-audit result — with 0 files skipped and 0 parse failures, recall on 6 real defects
in a real codebase was **0** — and the structural reason this class of defect survived:
**a rule that never fires and a clean codebase produce identical output**, so no test suite,
benchmark or CI gate could have distinguished them.

Read it before treating a clean report as an assurance.

### Fixed

- **MCP configuration discovery did not recurse.** It used a non-recursive `iterdir()` over
  the scan root where nine other scanners use `rglob`, so **six MCP rules had a
  directory-scan count of exactly zero** — they fired when a config file was named
  explicitly and never during a normal project scan. (`f649dcc`)
- **AI-tool hook discovery did not recurse.** `AGENT-120` resolved `.claude/settings.json`
  and friends by joining onto the scan root, so it fired only when the scan root *was* the
  project directory. (`d4d2850`)
- **AGENT-034 had no tool-boundary constraint on TypeScript.**
  `analysis/ts_tool_boundary_detector.py` — 325 lines with a full test file — was imported by
  nothing, so the rule fired outside tool entry points on every TypeScript scan since it
  shipped. Now wired. (`2ee8345`)
- **Python 3.12–3.14 support.** `ast.NameConstant` fallbacks removed in 3.14 are gone
  (`0f321ff`); the suite runs clean on 3.12, 3.13 and 3.14, and classifiers now say so.
- **Layer 1 had two thresholds.** `precision_recall.py` carried its own
  `if f1 < 0.75: sys.exit(1)` while `tests/benchmark/gates.yaml` — which calls itself the
  single source of truth — carried 0.72, so the same build could pass the documented gate and
  fail the undocumented one. The hard-coded floor is deleted; the script measures and
  `quality_gate_check.py` decides. **No threshold was lowered.** (`78d8fe5`)
- **Layer 1 scored non-deterministically** across identical runs. Fixed and pinned; ten
  consecutive runs now agree to six decimal places, including under three `PYTHONHASHSEED`
  values. (`cca9265`)
- Substantial false-positive reduction across the TypeScript scanner: receiver resolution for
  `.exec`/`.spawn`/`.fetch`, suppression of `child_process` calls with an all-literal argument
  list, fixed non-shell executables no longer treated as shell execution, declarations and
  quoted strings no longer treated as calls, `AGENT-041` requiring SQL statement syntax rather
  than a bare keyword, and weak prompt names requiring corroboration. Measured on a real agent
  codebase, this took the signal-to-noise ratio from **58:1 to 2.2:1**.

### Known limitations, stated rather than left to be discovered

- **TypeScript and JavaScript analysis is regex-level, not AST-level.** `TreeSitterParser`
  contains a tree-sitter path; it has never executed in any shipped environment and stays
  unreached deliberately. Wired up on a scratch build it **lost 2 true positives, added 6
  known false positives, and broke 42 tests**. The extra remains optional and the declared
  pin (`tree-sitter = "^0.22.0"` against `^0.23.0` grammars) cannot work in any case.
  `tests/test_treesitter_differential.py` now blocks anyone enabling it without re-measuring.
- **Shell scripts are not read.** No scanner opens a `.sh` file.
- **`AGENT-041` over-triggers on any `.execute()` receiver** — agent invocation, task
  dispatch and `concurrent.futures.Executor` are all reported as SQL sinks. Open, reproduced,
  see `ISSUE_TRIAGE.md`.
- **Configuration-derived values are treated as user input.** There is no provenance model
  separating configuration and internal computation from untrusted input, which is the root of
  several reported false positives. Open.

### Testing

The suite is **1796 passed / 1 failed / 3 skipped**. The one failure is deliberate:
`tests/test_corpus_label_rules.py` fails because three ground-truth labels still cite a rule
no code path can emit. It is committed red because ground truth is not the scanner author's to
edit and a guard that passes while the defect is present is what this project keeps
rediscovering.

New guards, all of which fail the suite rather than warn:

- `tests/test_rule_producers.py` — every advertised rule must have a producer
- `tests/test_rule_fixture_coverage.py` — every advertised rule must have an input that makes
  it fire
- `tests/test_corpus_label_rules.py` — every corpus label must cite a rule that can be emitted
- `tests/test_rule_reachability.py` — a rule that fires on a file scan must fire on a
  directory scan
- `tests/test_layer1_gate_singleton.py` — there is one Layer 1 threshold and it lives in
  `gates.yaml`
- `tests/test_treesitter_differential.py` — enabling tree-sitter may add findings, never
  remove them

## [0.19.2] - 2026-07-03

### Fixed
- **`scanned_files` counter under-reported** for TypeScript, Solidity, and Go scans. The counter was incremented only for Python / MCP-config / SKILL.md scanners; for any pure-TypeScript, pure-Solidity, or pure-Go target the counter reported 0 even when those scanners ran and produced real findings. Patched `cli/commands/scan.py` to increment per-file in the TypeScript, Solidity, and Go scanner blocks via a new `_count_files_by_extension` helper (orchestrator-level; no scanner internals touched). This is a visibility fix, not a new scanning capability — Solidity scanning has been working since AGENT-099 shipped in v0.13.x.
- **TypeScript scanner false positive on Redis `client.eval(...)`**: `AGENT-034` was firing on member-form calls like `redisClient.eval(luaScript)` (Redis EVAL Lua), `redis.evalsha(sha, ...)`, and any `someObj.eval(...)` because suffix-name matching against `TS_DANGEROUS_CALLS` treated any qualified name ending in `eval`/`Function` as the JS global sink. Fix: excluded `eval`/`Function` from generic suffix matching, added explicit entries for real global aliases (`window.eval`, `globalThis.eval`, `global.eval`, `self.eval`), enforced a dot-boundary rule for qualified-name matches, tightened the regex fallback (`(?<![\w.$])eval\b` for the bare form), and skipped TS interface/class method declarations of shape `eval(args): Type`. +12 regression tests in `TestEvalMemberCallDistinction`. Regression source: x402-foundation/x402 scan.

## [0.19.1] - 2026-04-01

### Added
- **AGENT-120** (CWE-78): AI Tool Configuration Hooks Poisoning — detects malicious hooks in .claude/settings.json, .cursor/settings.json, .mcp.json. Ref: CVE-2025-59536 (CVSS 8.7)

## [0.19.0] - 2026-03-31

### Added — Agent Architecture Security Rules

10 new detection rules (AGENT-110 to AGENT-119) targeting real-world AI agent architecture patterns identified from the Anthropic Claude Code source leak and vulnerability research across CrewAI, AutoGen, LangGraph, and Pydantic AI.

- **AGENT-110** (CWE-540): Source Map / Debug Artifact in Agent Package Distribution
- **AGENT-111** (CWE-200): Sensitive Internal Configuration Exposed in Package Metadata
- **AGENT-112** (CWE-250): Sub-Agent Spawn Without Permission Boundary
- **AGENT-113** (CWE-287): Cross-Agent Delegation Without Identity Verification
- **AGENT-114** (CWE-269): Multi-Agent Coordinator Without Scope Restriction
- **AGENT-115** (CWE-400): Agent Background Daemon Without Lifecycle Control
- **AGENT-116** (CWE-1321): Persistent Agent Session Without Memory Isolation
- **AGENT-117** (CWE-862): Automatic Tool Permission Approval Without Safety Classification
- **AGENT-118** (CWE-862): Human-in-the-Loop Bypass in Agent Execution Chain
- **AGENT-119** (CWE-778): Agent Activity Trace Suppression

### New Scanner
- `package_scanner.py` — Detects source map leakage and internal config exposure in agent package distributions (npm, PyPI)

## [0.17.0] - 2026-03-04

### New Rules (4)
- **AGENT-054** (CWE-494): MCP Rug Pull / Baseline Drift Detection — Detects unauthorized modifications to MCP server tools, resources, and prompts by comparing against a previously approved baseline using SHA-256 hash comparison
- **AGENT-055** (CWE-706): Cross-server Tool Shadowing — Detects identical or similar tool names registered across multiple MCP servers, which could enable malicious tool override attacks. Uses Levenshtein distance for fuzzy matching
- **AGENT-056** (CWE-74): Tool Description Poisoning — 5-category pattern analysis detecting prompt injection, hidden instructions (zero-width chars), command injection, data exfiltration guidance, and privilege escalation in MCP tool descriptions
- **AGENT-057** (CWE-74): Tool Argument Poisoning — Same analysis engine applied to tool input parameter descriptions

### New CLI Options
- `--dynamic`: Enable runtime MCP server scanning (enumerates tools/resources/prompts, analyzes descriptions for security threats)
- `--mcp-baseline <path>`: Specify baseline file for drift detection
- `--dynamic-only`: Run only dynamic scanning, skip static analysis
- `--dynamic-timeout <seconds>`: Set timeout for dynamic scanning
- `agent-audit inspect --baseline <path>`: Create or update MCP security baseline

### New Modules
- `analysis/tool_description_analyzer.py` (~220 lines): 5-category poisoning detection engine
- `scanners/mcp_baseline.py` (~600 lines): Baseline creation, serialization, SHA-256 hashing, and drift detection

### Stats
- Total rules: 49 → 53
- Total tests: 1,142 → 1,239 (97 new, 0 regressions)
- No new external dependencies

## [0.5.2] - 2026-02-05

### Micro-Patch: False Positive Reduction

#### AGENT-043 Tightened Daemon Detection
- Now distinguishes daemon registration from process management
- Excludes pkill, kill, nohup, &, tmux, and screen from daemon detection
- Only triggers on true daemon registration: launchctl bootstrap/load/enable, systemctl enable, pm2 startup/save

#### AGENT-046 Credential Store Deduplication
- Cross-file deduplication by credential store type (macOS Keychain, Linux keyring, Bitwarden, 1Password, etc.)
- Multiple calls to the same credential store type → single finding with highest confidence
- Reduces noise when same credential pattern appears multiple times

#### AGENT-047 Extended Safe Command List
- Added macOS-specific commands: open, pbcopy, pbpaste, say, osascript, defaults
- Added system info commands: which, where, whoami, uname, hostname, date
- Added text processing: wc, head, tail, grep, sed, awk, sort, uniq, cut, tr
- Added file utilities: ls, pwd, echo, cat, touch, mkdir, cp, mv, test
- Added archive/network: tar, gzip, zip, curl, wget, ping, dig, nslookup

#### Risk Score v2 Formula
- Switched from log2 to natural log (ln) for smoother scaling
- New formula: `1.8 * ln(1 + raw_score)` + BLOCK bonus
- BLOCK bonus: +0.3 per BLOCK finding, capped at 2.0
- Score capped at 9.8 (10.0 reserved for theoretical extremes)
- Calibration: 3 WARN → ~2.7, 10 WARN → ~5.0, 20 WARN → ~5.8, 50 WARN + 5 BLOCK → ~9.3

### Tests
- 716 tests passing (up from 715 in v0.5.1)
- New test suite: `test_micropatch_v052.py` with 21 tests

## [0.5.0] - 2026-02-04

### Major Changes

#### Multi-Language AST Support
- tree-sitter based parsing for TypeScript, JavaScript (optional dependency)
- Unified AST query interface with `find_assignments()`, `find_function_calls()`
- Graceful fallback to regex-based parsing when tree-sitter not installed

#### AGENT-004 Semantic Overhaul
- 3-stage analysis: candidate discovery -> value analysis -> context scoring
- Shannon entropy + placeholder detection for false positive reduction
- New credential formats: sk-proj-*, sk-ant-*, co-*, and more
- Confidence-based tiering: BLOCK(>=0.90), WARN(>=0.60), INFO(>=0.30), SUPPRESSED

#### Detection Range Expansion (AGENT-034/026/037)
- eval/exec detection beyond @tool context (addresses CVE-2023-29374, CVE-2023-36258)
- SSRF detection beyond @tool context
- Context-aware confidence scoring (tool_decorator=0.90, class_method=0.60, standalone=0.55)

#### New Privilege Detection Rules (AGENT-043~048)
- AGENT-043: Daemon privilege escalation (launchctl, systemctl, pm2)
- AGENT-044: Sudoers NOPASSWD configuration
- AGENT-045: Browser automation without sandbox
- AGENT-046: System credential store access (Keychain, gnome-keyring, pass)
- AGENT-047: Subprocess execution without sandbox
- AGENT-048: Extension/plugin permission boundaries

#### Confidence-Based Tiered Reporting
- Risk score calculation: logarithmic formula with severity weighting
- Terminal output grouped by tier (BLOCK -> WARN -> INFO -> SUPPRESSED)
- --verbose, --min-tier, --no-color CLI options
- JSON output includes confidence, tier, and reason fields

### Benchmark Results
- 656 tests passing
- All 6 benchmark samples (KNOWN-001~004, WILD-001~002) detected correctly
- Fixtures scan: 0.61 seconds

### Dependencies
- Optional: tree-sitter >= 0.22.0 (install with `pip install agent-audit[tree-sitter]`)

## [0.4.1] - 2026-02-04

### Fixed

- **AGENT-026: URL Allowlist Validation Detection** - Recognizes URL allowlist validation as SSRF mitigation:
  - Detects `urlparse()` + `netloc/hostname` + `in/not in` + `raise/return` patterns
  - Safe URL fetch patterns now receive `confidence=0.20` and `tier=SUPPRESSED`
  - Reduces false positives on properly validated network requests

- **AGENT-034: Safe AST Evaluation Detection** - Recognizes `ast.literal_eval()` and `ast.parse()` as safe:
  - `ast.literal_eval()` is recognized as a safe alternative to `eval()`
  - `ast.parse()` without `eval()/exec()` is recognized as safe AST-based validation
  - Safe AST patterns receive `confidence=0.10` and `tier=SUPPRESSED`

- **AGENT-034: Parameterized SQL Query Detection** - Recognizes parameterized queries as injection-safe:
  - Detects `cursor.execute(sql, params)` with 2+ arguments
  - Verifies first argument is not f-string, `.format()`, `%` formatting, or concatenation
  - Parameterized queries receive `confidence=0.10` and `tier=SUPPRESSED`

### Added

- **Finding Model: `tier` Field** - New field for confidence-based reporting tiers:
  - `BLOCK`: confidence >= 0.90 (high confidence, should fail CI)
  - `WARN`: confidence >= 0.60 (medium confidence)
  - `INFO`: confidence >= 0.30 (low confidence)
  - `SUPPRESSED`: confidence < 0.30 (very low, filtered by default)
  - Foundation for v0.5.0 tiered reporting architecture

- **`confidence_to_tier()` Helper** - Utility function to convert confidence scores to tiers

### Changed

- **`is_actionable()` Threshold** - Changed default from 0.50 to 0.30 to align with SUPPRESSED tier
- **JSON Output** - Now includes `tier` field in all findings

### Quality Metrics

- All 393 tests passing
- ~~3 false positives eliminated (Precision: 98.51% → 100%)~~ **WITHDRAWN 2026-08-11**
- ~~Recall maintained at 100%~~ **WITHDRAWN 2026-08-11**
- ~~F1 Score: 100%~~ **WITHDRAWN 2026-08-11**

  > These three lines were never measurements. They are the *target* block of the v0.4.1
  > development brief, published as an achievement — the brief states `Recall = 100%
  > (0 FN)` in as many words, and the evaluation output committed alongside this entry
  > measured 124 false negatives and 47.46% recall. They are struck rather than updated
  > because no re-run can reproduce them and there is no commit to update them *to*.
  > See `docs/decisions/METRICS_RETRACTION.md`.

## [0.4.0] - 2026-02-04

### Added

- **Standardized Benchmark Infrastructure** - New reproducible benchmark system:
  - `tests/benchmark/benchmark_config.yaml` - Configuration with locked scan paths for all 11 benchmark targets
  - `tests/benchmark/run_benchmark.py` - Automated runner with unified ASI extraction
  - Comparison with previous results and quality assessment
  - Report generation (Markdown + JSON)

- **Unified ASI Extraction** - Backward compatible ASI category handling:
  - Primary field: `owasp_id` in findings
  - Added `asi_categories` list to JSON output for compatibility
  - Supports both old (`owasp_agentic_id`) and new field names

### Changed

- **AGENT-018 Framework Path Filtering** - Extended path patterns for framework source code:
  - Added `langchain_core`, `langchain_community` patterns
  - Added OpenAI Agents SDK and Google ADK patterns
  - T3 (langchain-core) reduced from 44 to 3 findings
  - T6 (openai-agents) reduced from 47 to 28 findings
  - T7 (adk-python) reduced from 64 to 33 findings

- **AGENT-041 Precision Improvements** - Reduced SQL injection false positives:
  - Now requires SQL keyword prefix (SELECT, INSERT, UPDATE, DELETE, etc.)
  - Removed `sql_percent_injection` pattern (too many FP with parameterized queries)
  - Improved `.format()` detection logic
  - Only triggers for database-like callers (cursor, conn, db, etc.)

- **AGENT-004/005 ASI Mapping** - Fixed missing OWASP ID:
  - AGENT-004 (Hardcoded Credentials) now correctly maps to ASI-04
  - AGENT-005 (Unverified MCP Server) now correctly maps to ASI-04

- **MCP Config Scanner** - Handle non-dict values gracefully:
  - Skip comments and metadata fields in mcpServers
  - Prevents `'str' object has no attribute 'get'` errors

### Fixed

- MCP config scanning error when config contains comment fields
- Missing `owasp_id` in AGENT-004/005 findings
- `.format()` SQL injection detection not triggering correctly

### Technical Debt Addressed

- Four iterations of benchmark inconsistency resolved
- ASI field naming unified across codebase
- Scan path standardization for framework projects (T3, T6-T9)

### Quality Metrics

- All 385 tests passing
- mypy: 0 errors
- OWASP Coverage: 10/10 ASI categories
- Full backward compatibility maintained

## [0.3.2] - 2026-02-04

### Added

- **AGENT-041: SQL Injection Detection** - Detects SQL queries constructed with:
  - f-string interpolation (`f"SELECT * FROM users WHERE id = {user_id}"`)
  - `.format()` method
  - `%` formatting
  - String concatenation
  - Maps to ASI-02 (Tool Misuse)
- **AGENT-042: Excessive MCP Server Detection** - Warns when MCP configuration exceeds 10 servers
  - Maps to ASI-03 (Excessive Agency)
  - Enforces principle of least privilege
- **Extended Prompt/PromptTemplate Detection (AGENT-027)** - Now detects:
  - `Prompt()`, `PromptTemplate()`, `ChatPromptTemplate()` with variable templates
  - Risky `input_variables` configurations

### Changed

- **Improved Framework Allowlist (v0.3.2)** - Enhanced false positive suppression:
  - Added `/autogen/python/packages/` pattern for autogen monorepo
  - Added generic `/repos/{framework}/tests/` pattern detection
  - AGENT-018 (Memory Poisoning) now uses framework allowlist
  - AGENT-039 (Trust Boundary Violation) now uses framework allowlist
  - T9 (AutoGen) findings reduced from 449 to 70

### Fixed

- T1 (DVLLM) low detection - SQL injection now properly detected (3 findings, ASI-01/ASI-02)
- T2 (LangChain) narrow OWASP coverage - extended prompt detection adds ASI-01 coverage
- T9 (AutoGen) excessive false positives - framework test files now filtered
- ASI-03 coverage gap - now triggered via AGENT-042 on T10

### Benchmark Results (v0.3.2)

| Project | Findings | Change |
|---------|----------|--------|
| T1 - DVLLM | 3 | +2 (SQL injection) |
| T9 - AutoGen | 70 | -179 (framework filter) |
| T10 - MCP Config | 19 | +1 (ASI-03) |

**OWASP Coverage: 10/10 categories across all benchmark projects**

## [0.3.1] - 2026-02-04

### Added

- **LangChain Legacy API Detection (H1)** - Support for legacy LangChain patterns:
  - `ConversationalChatAgent`, `ConversationalAgent`, `ZeroShotAgent`, etc.
  - `AgentExecutor.from_agent_and_tools()` factory method
  - `initialize_agent()` function
- **Framework Allowlist for AGENT-028 (H2)** - Suppress false positives for framework internal code:
  - Added `rules/allowlists/framework_iteration.yaml`
  - Filters crewAI, LangChain, AutoGen, AgentScope framework source directories
  - Reduces T9 (crewAI) findings from 739 to 250 (AGENT-028: 489→0)
- AGENT-038 now maps to ASI-03 as secondary OWASP category
- New LangChain rules:
  - AGENT-040: LangChain AgentExecutor Without Safety Parameters (ASI-01)
  - AGENT-026: LangChain Tool Input Not Sanitized (ASI-02)
  - AGENT-027: Injectable System Prompt in LangChain Messages (ASI-01)
  - AGENT-028: Agent Without Iteration Limit (ASI-08)

### Changed

- **ASI ID Format Migration (H3)** - Unified OWASP ID format from `OWASP-AGENT-XX` to `ASI-XX`
- Rule ID conflict resolved: AGENT-025 in langchain_security_v030.yaml renamed to AGENT-040
- OWASP Agentic coverage remains 10/10 (100%)

### Fixed

- T1 (damn-vulnerable-llm-agent) zero detection issue - now detects legacy LangChain patterns
- T9 (crewAI) high false positive rate for AGENT-028 - framework paths now filtered
- ASI-03 coverage gap - restored via AGENT-002 + AGENT-038 secondary mapping
- `create_react_agent` incorrectly flagged for missing `max_iterations` - only check executors now

## [0.2.0] - 2026-02-03

### Added

- **Full OWASP Agentic Top 10 Coverage** - Expanded from 5 rules to complete coverage of all 10 ASI categories
- Custom rules support via `--rules-dir` option
- New detection rules:
  - AGENT-010: System Prompt Injection Vector (ASI-01)
  - AGENT-011: Missing Goal Validation (ASI-01)
  - AGENT-013: Long-Lived/Shared Credentials (ASI-03)
  - AGENT-014: Overly Permissive Agent Role (ASI-03)
  - AGENT-015: Untrusted MCP Server Source (ASI-04)
  - AGENT-016: Unvalidated RAG Data Source (ASI-04)
  - AGENT-017: Unsandboxed Code Execution (ASI-05)
  - AGENT-018: Unsanitized Memory Write (ASI-06)
  - AGENT-019: Unbounded Memory (ASI-06)
  - AGENT-020: Insecure Inter-Agent Communication (ASI-07)
  - AGENT-021: Missing Circuit Breaker (ASI-08)
  - AGENT-022: Tool Without Error Handling (ASI-08)
  - AGENT-023: Opaque Agent Output (ASI-09)
  - AGENT-024: No Kill Switch (ASI-10)
  - AGENT-025: No Observability (ASI-10)
- SARIF output now includes `OWASP-Agentic-{ASI-XX}` tags in `properties.tags`
- Extended Category enum with all OWASP Agentic categories
- OWASP Agentic ID mapping in Finding model

### Changed

- Improved Python AST scanner with additional detection patterns
- Enhanced rule engine to support OWASP Agentic ID mapping
- Updated SARIF formatter to include OWASP Agentic tags

### Fixed

- mypy type errors with class-level dict annotations
- Loop variable naming conflicts in scan command
- Cross-platform path normalization

## [0.1.0] - 2025-01-XX

### Added

- Initial release
- Python AST scanning for dangerous patterns
- MCP configuration scanning
- Secret detection (AWS keys, API tokens, etc.)
- Runtime MCP server inspection
- Output formats: terminal, JSON, SARIF, Markdown
- GitHub Action for CI/CD integration
- Baseline scanning for incremental analysis
- Configuration via `.agent-audit.yaml`
- Original 5 rules:
  - AGENT-001: Command Injection
  - AGENT-002: Excessive Permissions
  - AGENT-003: Data Exfiltration Chain
  - AGENT-004: Hardcoded Credentials
  - AGENT-005: Unverified MCP Server
