# Outreach drafts — every number, and the command that produces it

**Scope:** `blog_post.md`, `twitter_thread.md`, `chinese_summary.md` — the three untracked
outreach drafts at the repository root.
**Measured:** 2026-08-11, `bea9901` on `fix/py314-blocker`, `agent_audit.__version__ == 0.20.0`,
CPython 3.14.3. All commands run from the repository root unless noted.

Three classes of claim, and the class is the whole point:

* **REPRODUCED** — a command in this repository produces the figure. The command is given.
* **THIRD PARTY** — someone else's published measurement, attributed in the text. Not
  re-run by us; a reader verifies at the source.
* **REMOVED** — no command produces it, in this repository or anywhere reachable from it.
  Cut from the draft, preserved verbatim in § 3 with the one condition that restores it.

Nothing was hedged. A number a reader cannot check is not softened in the prose; it is gone.

---

## 1. REPRODUCED — surviving numbers, with their commands

| figure | where it now appears | command |
|---|---|---|
| **66** detection rules | all three drafts | `python3 -c "import sys;sys.path.insert(0,'tests');from test_rule_producers import advertised_rules;print(len(advertised_rules()))"` |
| **7** OpenClaw rules, AGENT-058 – AGENT-064, all able to fire | all three drafts | same command; all seven appear in `advertised_rules()` |
| **10/10** OWASP Agentic category coverage | blog, thread | `python3 -m pytest tests/test_owasp_agentic.py -q` |
| AGENT-058 at **0.92**, BLOCK, on `curl … \| bash` in a `SKILL.md` | all three drafts | `agent-audit scan <dir containing the SKILL.md quoted in the draft> --format json` |
| AGENT-059 at **0.88**, WARN, on `update your SOUL.md` | blog, thread, CN | same scan |
| AGENT-058 at **0.95**, BLOCK, on `base64 -d \| sh` | all three drafts | `agent-audit scan <dir containing that one line in a SKILL.md>` |
| Risk score **3.2/10** on the demo skill | blog | same scan |
| **TP 199 / FP 90 / FN 37** | blog, thread, CN | `cd packages/audit && python3 ../../tests/benchmark/precision_recall.py` |
| **P 68.86% / R 84.32% / F1 0.7581** | blog, thread, CN | same |
| **238 annotations across 81 files** | blog | same command, first two log lines |
| **at least 21 of the 90 FPs are unlabelled true positives** | blog, thread, CN | `docs/decisions/METRICS_RETRACTION.md` § 3(b); 18 MCP + 3 AGENT-120, itemised there |
| **0 of 6** on the blind audit, 0 files skipped, 0 parse failures | blog, thread, CN | `CAPABILITY_BOUNDARIES.md` § 2 |
| tree-sitter differential: **2 TPs lost, 8 added, 6 of them known FPs, 42 test regressions** | blog | `CAPABILITY_BOUNDARIES.md` § 4; `python3 tests/test_treesitter_differential.py` |
| the retracted **98.51% / 100% / 99.25%**, and **124 FN / 47.46% recall** measured beside it | blog, thread, CN | `git show a65b341:results/layer1.json`; full trace in `docs/decisions/METRICS_RETRACTION.md` § 1 |
| **1,905** tests passing, 1 red by design | blog footer | `python3 -m pytest tests/ packages/audit/tests/ -q` |
| language coverage table (Python AST+taint; TS/JS, Go, Solidity regex; `.sh` unread) | blog | `CAPABILITY_BOUNDARIES.md` § 4 |
| version **0.20.0** | blog footer | `python3 -c "import agent_audit;print(agent_audit.__version__)"` |

### One reproduction the drafts show but this run could not re-derive

The original drafts printed a decoded payload for a base64 blob attributed to a live C2 host.
**This run did not decode it** — the environment declined to run a base64 decode of a
live-C2 string, which is the correct default. The drafts no longer assert what that blob
decodes to. The demo in the corrected drafts uses `ZWNobyBoaQ==` instead, which is inert and
whose only purpose is to make AGENT-058 fire at 0.95, which was reproduced.

---

## 2. THIRD PARTY — attributed, not ours, not re-run

Kept in the drafts because each is published under its author's name and a reader can check
it at the source. **The drafts now say so explicitly** — the originals presented them in the
same voice as our own findings.

| claim | source as cited | status |
|---|---|---|
| 400+ malicious skills on ClawHub | Koi Security | not re-run; confirm the citation is still live before publishing |
| 1-click RCE in the platform | CVE-2026-25253 | not re-run; confirm the CVE ID and its description |
| 26% of skills contain vulnerabilities | Cisco AI Defense | not re-run. See `docs/skillscanner/findings/F-003_cisco_scanner_unobtainable.md` — the Cisco scanner's published reproduction path does **not** reproduce on a clean machine. If you cite the 26%, cite it as their published figure and do not imply we replicated it |
| 181 leaked secrets, 65 still valid | GitGuardian | not re-run |
| "From Magic to Malware" | 1Password security blog | quotation only, no figure |

### Third-party figures that were removed rather than kept

| removed | why |
|---|---|
| "196k GitHub stars" | unattributed, changes weekly, wrong by the time anyone reads it |
| "over 13,700 skills" on ClawHub | unattributed, and it **contradicted the draft's own 18,899** in the paragraph above it. Two counts of one marketplace, 5,199 apart, in one post |

---

## 3. REMOVED — the ClawHub scan, verbatim, with restore conditions

Every figure below traces to one 18,899-skill ClawHub scan. **The scan data is not in this
repository**, no committed artifact records it, and `grep` for its totals across the tree
returns only the drafts themselves and the documents that flag them. `CLAIMS_RECONCILIATION.md`
§ 7 already recorded two of these as "not wrong; unfalsifiable from this repository", and
`METRICS_RETRACTION.md` § 2 classes them as needing **their data committed, not a
retraction**. That distinction is preserved here: these are not withdrawn claims, they are
unsubstantiated ones.

**There is a second problem, and it is the harder one.** The drafts state the scan was run by
a scanner evaluating **56 detection rules**. 56 is not any count this project has ever been
able to attribute — the known set is 66 (today), and historically 72, 92, 63, 53, 52, 49 and
40+ (`CLAIMS_RECONCILIATION.md` § 3). So the scan ran against a rule set nobody can now
reconstruct. Since then v0.20.0 has **withdrawn six rules that could never fire**, gated
AGENT-034 on a tool boundary, and narrowed AGENT-004. AGENT-034 alone accounts for 3,129 of
the 18,294 rule triggers the draft's own table reports. **A re-run would not return these
numbers**, and publishing them beside a v0.20.0 announcement would attribute one scanner's
output to a different scanner — which is the shape of the 98.51%, in a new place.

### Restore condition, for every row below

Exactly one of:

* **(a)** Re-run the scan at v0.20.0 over the same corpus, commit the raw output under
  `results/` with a provenance stamp in the manner of `tests/benchmark/provenance.py`
  (content, not time), and paste the new figures back. This is the only option that makes
  the numbers checkable by a reader.
* **(b)** Commit the *original* scan's raw output plus the scanner revision that produced
  it, and state the version and date inline with every figure — "at v0.1x, on 2026-06-25",
  not "Agent Audit identified". This preserves the numbers as a dated result rather than a
  property of the current tool.

**Option (c), publishing them as they stand, is the one this document exists to rule out.**

### 3.1 Scope and headline totals

> We scanned all 18,899 skills on ClawHub. To our knowledge, this is the largest public security audit of the OpenClaw skill ecosystem to date.

> Across 18,899 skills, Agent Audit identified **13,355 security findings**. Of these, **1,492 were BLOCK-tier critical vulnerabilities** spread across 859 skills — meaning **4.5% of all ClawHub skills have at least one critical security issue**. When including WARN-tier findings, 2,487 skills are affected: **13.2% of the ecosystem**.

> The single strongest predictor of vulnerability is whether a skill includes executable code. Skills with a `scripts/` directory had a **46.6% vulnerability rate**. Skills without scripts: 16.8%. That's a **2.8x risk multiplier** when a skill bundles code alongside its SKILL.md.

Internal arithmetic checks out (859/18,899 = 4.55%; 2,487/18,899 = 13.16%; 46.6/16.8 = 2.77).
The arithmetic is not the problem; the denominator's provenance is.

### 3.2 Per-rule hit counts

> **Obfuscated shell commands (AGENT-058): 641 hits.** …
> **Identity file modification (AGENT-059): 457 hits.** …
> **Fake dependency social engineering (AGENT-062): 250 hits.** … The #1 attack vector in the ecosystem.
> Five of seven new rules triggered in the wild, producing 1,845 total hits.

Note also: "The #1 attack vector in the ecosystem" is a ranking claim over the same
uncommitted data, and 641 + 457 + 250 = 1,348, so the remaining 497 of the stated 1,845 are
unattributed in the draft itself.

### 3.3 The OWASP mapping table

The full 10-row table of rule triggers, plus:

> ASI-02 (Tool Misuse) dominates at 58% of all triggers. … The top two rules are AGENT-026 (SSRF, 7,024 triggers) and AGENT-034 (tool input without validation, 3,129 triggers). Note that a single skill can trigger multiple rules, so these 18,294 total rule triggers map to 13,355 unique findings across tiers.

**This is the row most affected by (b) above.** AGENT-034's behaviour changed materially in
v0.20.0.

### 3.4 The precision validation paragraph — the highest-risk removal

> After the initial scan, we performed a 50-sample stratified code review … This revealed 5 distinct false positive patterns. We fixed all 5 (352 lines of additive-only code changes, no detection logic removed), re-scanned all 18,899 skills, and re-validated with a fresh sample.
>
> Post-fix results: **BLOCK-tier precision: 80%** (16/20 TP, 95% Wilson CI: 58.4%–91.9%). **AGENT-058 precision: 80%** (16/20 TP, same CI — both tracks happened to yield identical TP rates on 20-sample draws). All 1,322 regression tests passing.
>
> We're transparent about this because trust matters in security tooling. Our precision methodology, raw sample data, and classification rationale are all available in the repository.

**"available in the repository" is false.** No sample data, no classification rationale and
no methodology for this 50-sample review exists in this tree. This sentence is the one that
would do real damage: it invites a reader to go and check, and there is nothing there.

`1,322 regression tests` is separately stale — the measured figure is **1,905 passing, 1
failing on purpose, 4 skipped** (`python3 -m pytest tests/ packages/audit/tests/ -q`).

The same 80% appears on a **tracked, published** surface: `README.md:147`, "validated against
18,899 ClawHub skills at 80% precision". That one is on Heady's list, § 5 item 2.

### 3.5 The malware campaign section

The whole section: the named publisher accounts, the base64 blob, the decoded
`curl` to a C2 host, the C2 IP address, and:

> Agent Audit flagged every instance at 0.95 confidence.

Removed for two independent reasons, and the second is not about reproducibility:

1. "every instance at 0.95" is a claim about the uncommitted scan. The *capability* — that
   `base64 -d | sh` in a `SKILL.md` fires AGENT-058 at 0.95 — **was reproduced this run** and
   is what the corrected drafts show instead.
2. Naming publisher accounts and a C2 address in a public post is a **disclosure decision**,
   not a metrics one. It has a coordination question attached (were the accounts reported to
   ClawHub, and when) that no command answers. Heady's call, § 5 item 3.

### 3.6 Smaller removals

| removed | why |
|---|---|
| "the #1 ranked skill … turned out to be malware, containing 9 vulnerabilities, 2 of them critical" | our scan output, same uncommitted data; also a ranking claim with no date |
| "**56 detection rules**" (blog), "**56 rules** mapped to OWASP" (thread) | wrong. The count is 66, and 56 was a ninth number for one set. This is the only removal that is a plain error rather than an unsubstantiated claim |
| "Agent Audit performs AST-level taint analysis — tracking how data flows from tool function parameters to dangerous sinks" | **false for this post's own subject.** `SKILL.md` is analysed by parsed frontmatter plus regex over the body, and TypeScript/JavaScript is regex by decision (`CAPABILITY_BOUNDARIES.md` § 4). AST-plus-taint is the Python path only. Replaced with the per-language table rather than deleted, because the accurate version is short and is a better claim |
| "Four rules. Four BLOCK-tier findings. One scan." (closing) | asserts a scan of the founder's setup that was never run. Reworded to what is true: those risks are rules the tool carries |
| "All 1,322 regression tests passing" | stale by 568; see § 3.4 |

---

## 4. What changed in each draft

| draft | rule count | AST claim | scan figures | third-party framing | net |
|---|---|---|---|---|---|
| `blog_post.md` | 56 → **66** | replaced with the per-language table | removed, § 3 | now explicitly "not our research" | reframed from an ecosystem-survey post to a tool post with a 30-second reproduction and a stated retraction |
| `twitter_thread.md` | 56 → **66** | replaced | removed, § 3 | same | 10 tweets, same count |
| `chinese_summary.md` | carried no rule count | n/a | removed, § 3 | same | same shape as the blog |

`chinese_summary.md` was not named in the brief. It is untracked, sits beside the other two,
carries the same 18,899-scan figures, the same 80% precision and the same `1322` test count,
and is a translation of the post being corrected. Leaving it alone would have left the fifth
number's whole family intact in the one language where nobody would grep for it.

Each corrected draft opens with a non-rendering HTML comment stating the hold and pointing
here. It is a draft control, not a published caveat — it cannot reach a reader.

---

## 5. What only Heady can decide

Ordered. Item 1 gates items 2 and 3.

1. **Do the ClawHub scan figures get restored, and by which route — (a) re-run at v0.20.0, or
   (b) publish as a dated v0.1x result with the raw data committed?** Everything in § 3 turns
   on this one answer. Route (a) is the one that makes them checkable; route (b) is cheaper
   and still honest if every figure carries its version and date.
2. **`README.md:147`** — "validated against 18,899 ClawHub skills at 80% precision" is on a
   tracked, published surface and carries the § 3.4 figure. It is the only metric on an
   in-repo surface with no reproducing command, which makes it the one exception to what
   RUN8 established. Either commit the data or cut the clause; both are one-line edits, and
   which one is yours.
3. **The malware campaign section** — publishing publisher account names and a C2 address is
   a disclosure decision with a coordination question attached. Independent of item 1.
4. **Whether these drafts get published at all before
   `METRICS_RETRACTION.md` § 5 step 1 is closed.** That section's governing rule is that
   nothing new should be published on top of an external surface still carrying the retracted
   98.51%. These drafts *cite* the retraction, which is the strongest form of compliance
   available — but the external surfaces still have to be found first. See
   `EXTERNAL_CLAIMS_CHECKLIST.md` and `scripts/scan_external_claims.sh`.

---

## Related

* `docs/decisions/METRICS_RETRACTION.md` — the retraction, its mechanism, and the ordering
* `CLAIMS_RECONCILIATION.md` §§ 3, 7 — the rule-count spread and the two unverifiable claims
* `CAPABILITY_BOUNDARIES.md` §§ 2, 4 — the blind-audit result and the language coverage table
* `EXTERNAL_CLAIMS_CHECKLIST.md` — where the retracted figures may have gone
* `DECISIONS.md` item 44 — the fifth rule count, and item 45 — why no test can guard these files
