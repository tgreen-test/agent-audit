# Competitive Comparison: agent-audit vs Bandit vs Semgrep

> **⚠️ The original table below was measured on Agent-Vuln-Bench v1.0 (19 samples) on 2026-02-19 against v0.15.1/v0.16.0.** Those numbers are kept for the audit trail and remain the per-sample comparison record. For the **current** benchmark on the broader 81-sample labeled GT v2.2, see the **Current Snapshot** block below and the [README](../README.md). Reproduce with: `cd packages/audit && python3 ../../tests/benchmark/precision_recall.py`.

## Current Snapshot (v0.20.0, 2026-08-11, GT v2.2, 81 samples / 238 labels)

| Tool | Recall | Precision | F1 | measured on |
|------|-------:|----------:|---:|---|
| **agent-audit** (v0.20.0, raw, reproducible) | **84.32%** | **68.86%** | **0.7581** | GT v2.2, 81 samples |
| Bandit 1.8 (injection/RCE subset) | 29.7% | 100% | 0.458 | **AVB-19, 19 samples** |
| Semgrep 1.x (injection/RCE subset) | 27.0% | 100% | 0.426 | **AVB-19, 19 samples** |

**Read the fourth column before the first three.** The agent-audit row and the two baseline rows were measured on **different sample sets**, so this is not a like-for-like comparison and the ratios between rows are not meaningful. The baselines have not been re-run against the 81-sample GT; until they are, the honest reading of this table is three separate measurements printed adjacently, not a ranking.

The agent-audit row is the raw F1 directly produced by `precision_recall.py` (TP 199 / FP 90 / FN 37). Two things travel with it:

* **68.86% precision is a floor, not a point estimate.** At least 21 of the 90 false positives are correct by their own rule's definition and simply unlabelled in the ground truth. See `docs/decisions/METRICS_RETRACTION.md` § 3(b).
* **Precision fell from the 73.58% this table used to print, and that is not a detection regression.** It fell in three steps, each of which was a file-discovery bug being *fixed*: the scanner began finding things the corpus never labelled. Recall rose over the same period, 82.63% → 84.32%. § 3(a) of the same document has the per-step table.

A post-hoc adjusted F1 of 0.84 — computed by excluding FPs from rules added after v0.16 that are not yet labelled in GT — is documented as a footnote in [`docs/F1_REPRODUCTION.md`](F1_REPRODUCTION.md) and is **not** used as a headline figure, because it is not directly reproducible by the included script.

> **Correction, 2026-08-11 (v0.20.0).** This section published F1 0.778 / P 73.58% / R 82.63% (TP 195 / FP 70 / FN 41) at "v0.19.0, 2026-05-30", and a label count of 218 where the corpus has 238. It was missed by the v0.20.0 claims sweep: it appears in neither the location table of `CLAIMS_RECONCILIATION.md` § 2 nor that of `METRICS_RETRACTION.md` § 2, while `docs/F1_REPRODUCTION.md` listed this file among those already carrying the corrected headline. It was found by `scripts/scan_external_claims.sh`, which is the point of having the script.

---

## Historical: Agent-Vuln-Bench v1.0 (19 samples, 2026-02-19, v0.15.1/v0.16.0)

Evaluated on [Agent-Vuln-Bench v1.0](../tests/benchmark/agent-vuln-bench/) — 19 samples across 3 vulnerability categories with oracle ground truth.

| Metric | agent-audit | Bandit 1.8.6 | Semgrep 1.136.0 |
|--------|------------|-------------|-----------------|
| Recall (historical AVB-19) | 94.6% | 29.7% | 27.0% |
| Precision (historical AVB-19) | 87.5% | 100.0% | 100.0% |
| F1 Score (historical AVB-19) | 0.909 | 0.458 | 0.426 |
| True Positives | 35 | 11 | 10 |
| False Negatives | 2 | 26 | 27 |
| False Positives | 5 | 0 | 0 |
| Scan time | 2.9s | 1.7s | 55.4s |

## Per-Set Recall

| Set | Description | agent-audit | Bandit | Semgrep |
|-----|-------------|------------|--------|---------|
| **A** | Injection & RCE | **100.0%** | 68.8% | 56.2% |
| **B** | MCP & Component | **100.0%** | 0.0% | 0.0% |
| **C** | Data & Auth | **84.6%** | 0.0% | 7.7% |

## Per-Sample Detail

| Sample | agent-audit | Bandit | Semgrep |
|--------|------------|--------|---------|
| KNOWN-001 (eval CVE) | 1/0/0 | 1/0/0 | 1/0/0 |
| KNOWN-002 (exec CVE) | 1/0/0 | 1/0/0 | 1/0/0 |
| KNOWN-003 (MCP config) | 3/0/2 | 0/3/0 | 0/3/0 |
| KNOWN-004 (hardcoded creds) | 5/0/0 | 0/5/0 | 0/5/0 |
| KNOWN-005 (shell exec) | 3/0/0 | 3/0/0 | 2/1/0 |
| KNOWN-006 (eval injection) | 1/0/0 | 1/0/0 | 1/0/0 |
| KNOWN-007 (MCP multi-vuln) | 2/0/1 | 0/2/0 | 0/2/0 |
| KNOWN-008 (SQL injection) | 1/0/0 | 0/1/0 | 0/1/0 |
| KNOWN-009 (JWT hardcoded) | 2/0/0 | 0/2/0 | 1/1/0 |
| KNOWN-010 (SSRF) | 1/0/0 | 1/0/0 | 0/1/0 |
| KNOWN-011 (shell Popen) | 1/0/0 | 1/0/0 | 1/0/0 |
| KNOWN-012 (sensitive log) | 1/0/0 | 0/1/0 | 0/1/0 |
| WILD-001 (eval calculator) | 2/0/1 | 2/0/0 | 2/0/0 |
| WILD-002 (SSRF fetcher) | 3/0/0 | 1/2/0 | 1/2/0 |
| WILD-003 (self-modify) | 1/0/0 | 0/1/0 | 0/1/0 |
| WILD-004 (token collector) | 3/0/0 | 0/3/0 | 0/3/0 |
| WILD-005 (MCP wildcard) | 2/0/1 | 0/2/0 | 0/2/0 |
| WILD-006 (prompt inject) | 2/0/0 | 0/2/0 | 0/2/0 |

*Format: TP/FN/FP*

## Key Differentiators

### Set B: MCP Configuration (agent-audit exclusive)

Bandit and Semgrep cannot parse MCP JSON configurations. They have **0% recall** on KNOWN-003, KNOWN-007, and WILD-005. agent-audit's MCPConfigScanner is the only tool that detects:

- Overly broad filesystem access (`"args": ["/"]`)
- Wildcard command grants
- Unpinned NPX packages (`npx -y @some/package` without version lock)
- Hardcoded credentials in MCP server configs
- Missing authentication on MCP transports

### Set A: Injection / RCE (@tool context awareness)

Bandit detects basic `eval()`/`exec()`/`subprocess` calls but lacks `@tool` decorator context awareness. agent-audit's tool-boundary-aware taint analysis identifies LLM-controllable input flowing to dangerous sinks, enabling detection of:

- SQL injection via f-string in tool functions (KNOWN-008)
- SSRF through unvalidated URL parameters (WILD-002)
- Prompt injection via user input in system messages (WILD-006)
- Agent self-modification through dynamic code execution (WILD-003)

### Set C: Data & Auth (semantic credential analysis)

agent-audit's three-stage semantic analyzer detects hardcoded credentials in complex formats that simple pattern matching misses:

- JWT tokens embedded in configuration
- Database connection strings with inline passwords
- Multi-field credential configurations (API key + secret pairs)
- Framework schema definitions correctly suppressed (Pydantic `Field`, type annotations)

## Methodology

- **Oracle-based evaluation**: Each sample has a hand-labeled `oracle.yaml` defining expected vulnerability locations (file + line within 5-line tolerance)
- **File + line matching**: True positives require the finding to match the oracle's file path and line number (no rule_id matching required, allowing cross-tool comparison)
- **Three dataset categories**: Set A (injection/RCE), Set B (MCP/component), Set C (data/auth)
- **Noise dataset (T12)**: Validates that tools do not over-report on benign patterns

## Complementary Use

agent-audit is designed to complement, not replace, general-purpose SAST tools:

| Use Case | Recommended Tool |
|----------|-----------------|
| AI agent code, `@tool` functions, MCP configs | **agent-audit** |
| General Python security (non-agent code) | Bandit, Semgrep |
| Multi-language security scanning | Semgrep |
| Supply chain vulnerability scanning | Trivy, Snyk |

For comprehensive coverage, run agent-audit alongside your existing SAST pipeline.
