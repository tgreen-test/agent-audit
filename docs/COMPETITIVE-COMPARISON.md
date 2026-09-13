# Competitive Comparison: agent-audit vs Bandit vs Semgrep

**All three tools below were run on the same corpus, on the same day, by the same command.**
That was not true of this document before 2026-09-10 — see the correction note in § 5.

Reproduce every number on this page with one command:

```bash
cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" --tool all --dataset all --output ../../results/avb_tool_comparison
```

Its output is committed at [`results/avb_tool_comparison_v0.20.0.json`](../results/avb_tool_comparison_v0.20.0.json)
and [`results/avb_tool_comparison_v0.20.0.md`](../results/avb_tool_comparison_v0.20.0.md).

---

## 1. Head-to-head (Agent-Vuln-Bench 1.0, 22 samples, 42 oracle labels)

Measured 2026-09-10 at agent-audit 0.20.0 (commit `dbae329`), Bandit 1.8.0, Semgrep 1.99.0.

| Tool | Recall | Precision | F1 | FPR | TP | FN | FP |
|------|-------:|----------:|---:|----:|---:|---:|---:|
| **agent-audit** 0.20.0 | **95.24%** | 86.96% | **0.9091** | 13.04% | 40 | 2 | 6 |
| Bandit 1.8.0 | 26.19% | **100.00%** | 0.4151 | **0.00%** | 11 | 31 | 0 |
| Semgrep 1.99.0 | 23.81% | **100.00%** | 0.3846 | **0.00%** | 10 | 32 | 0 |

**Read the precision column before the recall column.** Bandit and Semgrep are *more precise
than agent-audit on this corpus* — perfectly precise, in fact: neither produced a single false
positive across 22 samples, while agent-audit produced six. They achieve that by reporting only
what they are confident about, which is also why they miss 31 and 32 of the 42 labelled
vulnerabilities respectively. That is a defensible engineering position and this table should
not be read as saying otherwise.

The honest summary is a trade, not a ranking: **agent-audit finds 3.6× as many of the labelled
vulnerabilities as Bandit and 4.0× as many as Semgrep, and pays for it with a 13%
false-positive rate.** If your tolerance
for false positives is zero, the baselines are the better tools by that criterion.

### Per-set recall

| Set | Description | agent-audit | Bandit | Semgrep |
|-----|-------------|------------:|-------:|--------:|
| **A** | Injection & RCE (19 labels) | **100.0%** (19/19) | 57.9% (11/19) | 47.4% (9/19) |
| **B** | MCP & Component (9 labels) | **100.0%** (9/9) | 0.0% (0/9) | 0.0% (0/9) |
| **C** | Data & Auth (14 labels) | **85.7%** (12/14) | 0.0% (0/14) | 7.1% (1/14) |

Set B is the structural difference rather than a tuning difference: Bandit and Semgrep do not
parse MCP JSON configuration at all, so their 0/9 is a scope boundary, not a miss.

### Scan time

| Tool | Total | Avg per sample |
|------|------:|---------------:|
| agent-audit | 5.78s | 0.26s |
| Bandit | 3.32s | 0.15s |
| Semgrep | 134.64s | 6.12s |

Bandit is the fastest tool here.

---

## 2. Why agent-audit's headline F1 (0.7581) is deliberately not in the table above

agent-audit's published Layer 1 figure — **P 68.86% / R 84.32% / F1 0.7581, TP 199 / FP 90 /
FN 37**, over 238 labels in 81 files of ground truth v2.2 — is produced by a different
evaluator:

```bash
cd packages/audit && python3 ../../tests/benchmark/precision_recall.py
```

**That evaluator cannot score Bandit or Semgrep, and no amount of re-running will change
that.** It credits a detection as a true positive only when the finding's *rule ID* equals the
label's rule ID (`precision_recall.py`, the `e_rule == d_rule` condition in `evaluate()`).
Ground-truth labels carry agent-audit rule IDs such as `AGENT-034`. Bandit emits `B102`;
Semgrep emits `python.lang.security.…`. Neither can ever match a label, so both would score a
structural 0.0 that measures the identifier scheme rather than the tool.

The Agent-Vuln-Bench oracle used in § 1 matches on **file and line only, within a ±5-line
tolerance, with no rule-ID check** (`harness/oracle_eval.py`) — which is precisely what makes
it usable for cross-tool comparison.

So the two numbers answer different questions, and this is the reason they must not share a
table:

| figure | corpus | matching | what it measures |
|---|---|---|---|
| F1 0.7581 | GT v2.2, 81 files, 238 labels | file + line + **rule ID** | agent-audit against its own rule taxonomy |
| F1 0.9091 | AVB 1.0, 22 samples, 42 labels | file + line only | any tool, comparably |

Two qualifications travel with the 0.7581 figure (`docs/decisions/METRICS_RETRACTION.md` § 3):

* **68.86% precision is a floor, not a point estimate.** At least 21 of the 90 false positives
  are correct by their own rule's definition and simply unlabelled. § 3(b).
* **Precision fell from the 73.58% this document used to print, and that is not a detection
  regression.** It fell in three steps, each a file-discovery bug being *fixed*: the scanner
  began finding things the corpus never labelled. Recall rose over the same period,
  82.63% → 84.32%. § 3(a) has the per-step table.

A post-hoc adjusted F1 of 0.84 is documented as a footnote in
[`docs/F1_REPRODUCTION.md`](F1_REPRODUCTION.md) and is **not** a headline figure, because it is
not directly reproducible by the included script.

---

## 3. Key differentiators

### Set B: MCP configuration (agent-audit exclusive)

Bandit and Semgrep cannot parse MCP JSON configurations — 0/9 on Set B. agent-audit's
MCPConfigScanner detects:

- Overly broad filesystem access (`"args": ["/"]`)
- Wildcard command grants
- Unpinned NPX packages (`npx -y @some/package` without version lock)
- Hardcoded credentials in MCP server configs
- Missing authentication on MCP transports

### Set A: Injection / RCE (@tool context awareness)

Bandit detects basic `eval()`/`exec()`/`subprocess` calls but lacks `@tool` decorator context
awareness. agent-audit's tool-boundary-aware taint analysis identifies LLM-controllable input
flowing to dangerous sinks: SQL injection via f-string in tool functions, SSRF through
unvalidated URL parameters, prompt injection via user input in system messages, and agent
self-modification through dynamic code execution.

### Set C: Data & Auth (semantic credential analysis)

agent-audit's three-stage semantic analyzer detects hardcoded credentials in formats simple
pattern matching misses — JWT tokens in configuration, connection strings with inline
passwords, multi-field credential pairs — while suppressing framework schema definitions
(Pydantic `Field`, bare type annotations).

---

## 4. Complementary use

agent-audit is designed to complement, not replace, general-purpose SAST tools. The § 1 numbers
support that reading directly: the baselines' perfect precision and agent-audit's Set B
coverage are not in competition.

| Use case | Recommended tool |
|----------|-----------------|
| AI agent code, `@tool` functions, MCP configs | **agent-audit** |
| General Python security (non-agent code) | Bandit, Semgrep |
| Multi-language security scanning | Semgrep |
| Supply chain vulnerability scanning | Trivy, Snyk |

---

## 5. Correction note, 2026-09-10 (v0.20.0)

**What was wrong.** Between 2026-08-11 and 2026-09-10 this page carried a "Current Snapshot"
table whose three rows were measured on two different corpora: agent-audit on GT v2.2
(81 samples), Bandit and Semgrep on AVB-19 (19 samples). A caveat under the table said so, but
a caveat under a three-row table with a bolded winner is not how a table is read, and the row
labels invited exactly the head-to-head reading the caveat disclaimed.

**Why the caveat was also wrong.** It said the baselines "have not been re-run against the
81-sample GT; until they are, the honest reading …", which implied that re-running them was the
missing step. It was not possible: § 2 shows the GT v2.2 evaluator requires a rule-ID match and
therefore cannot score a third-party tool at all. The fix was to move the comparison to the
corpus that was built for it, not to re-run the baselines on the corpus that was not.

**What replaced it.** All three tools re-measured on Agent-Vuln-Bench 1.0 at v0.20.0 by a
single command, with the raw output committed.

**Prior corrections to this page, retained for the audit trail.** On 2026-08-11 this section
published F1 0.778 / P 73.58% / R 82.63% (TP 195 / FP 70 / FN 41) at "v0.19.0, 2026-05-30", and
a label count of 218 where the corpus has 238. It was missed by the v0.20.0 claims sweep — it
appeared in neither the location table of `CLAIMS_RECONCILIATION.md` § 2 nor that of
`METRICS_RETRACTION.md` § 2, while `docs/F1_REPRODUCTION.md` listed this file among those
already carrying the corrected headline. It was found by `scripts/scan_external_claims.sh`.

---

## 6. Historical: Agent-Vuln-Bench v1.0 at 19 samples (2026-02-19, v0.15.1/v0.16.0)

Kept as the audit trail. **These numbers are superseded by § 1** and should not be quoted.

Two reasons they are not directly comparable to § 1, beyond the version change: the corpus has
since grown from 19 samples to 22, and the tool versions recorded here — Bandit 1.8.6 and
Semgrep 1.136.0 — are not the versions installed on the machine that produced § 1 (Bandit 1.8.0,
Semgrep 1.99.0), so this row cannot be re-derived here even in principle.

| Metric | agent-audit | Bandit 1.8.6 | Semgrep 1.136.0 |
|--------|------------|-------------|-----------------|
| Recall | 94.6% | 29.7% | 27.0% |
| Precision | 87.5% | 100.0% | 100.0% |
| F1 Score | 0.909 | 0.458 | 0.426 |
| True Positives | 35 | 11 | 10 |
| False Negatives | 2 | 26 | 27 |
| False Positives | 5 | 0 | 0 |
| Scan time | 2.9s | 1.7s | 55.4s |

### Per-sample detail (historical, 19 samples)

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

---

## 7. Methodology and its limits

- **Oracle-based evaluation.** Each sample has a hand-labelled `oracle.yaml` defining expected
  vulnerability locations.
- **File + line matching, ±5-line tolerance, no rule-ID check** — this is what permits
  cross-tool comparison, and is the difference from the Layer 1 evaluator described in § 2.
- **Three sets**: A (injection/RCE), B (MCP/component), C (data/auth), plus a noise sample
  (T12) that checks tools do not over-report on benign patterns. All three tools score 0 on
  T12's 2 labels, which is counted in the recall denominators above.

Three limits worth stating, because they bound how far § 1 can be pushed:

1. **22 samples and 42 labels is a small corpus.** Differences of one or two detections move
   the percentages by several points. Treat the Set-level figures as indicative.
2. **The corpus was built by this project.** It is oracle-labelled and tool-agnostic in its
   matching, but a benchmark authored by one of the tools under test is not a neutral corpus,
   and Sets B and C cover agent-specific and credential patterns that the baselines do not
   claim to detect.
3. **The Semgrep row is not deterministic over time.** The adapter runs `semgrep
   --config=auto`, which resolves rules from the Semgrep registry at scan time, so re-running
   this command in six months may produce a different Semgrep row from the same source tree.
   Bandit and agent-audit use only rules shipped in their own distributions.
