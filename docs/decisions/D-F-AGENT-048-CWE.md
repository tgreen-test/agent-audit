# D-F: AGENT-048 CWE Assignment

**Date:** 2026-06-24
**Decision:** [A] Accept **CWE-863** (Incorrect Authorization) as the canonical CWE for AGENT-048.
**Status:** **RESOLVED IN PR #7** (branch `reconciliation/2026-06-06-paper-1-1-prep`).
**Supersedes:** Heady's earlier provisional "lock" of CWE-829 (never reflected in code).

---

## Rule under decision

- **Rule ID:** AGENT-048
- **Title:** Extension Permission Boundary Violation
- **Emit site:** `packages/audit/agent_audit/scanners/privilege_scanner.py`, `_check_extension_patterns` (~line 1049–1059).
- **Detection semantics:** Fires when extension/plugin code (inside directories matching `extensions/`, `plugins/`, `addons/`, `modules/`, `contrib/`, `third_party/`, `vendor/`) emits a relative or cross-module import that escapes the extension's root and reaches into core or sibling-extension modules.

---

## Rationale (CWE-863 vs CWE-829)

The detected failure mode is an **authorization-boundary escape**: the extension subtree is a permission boundary, and a cross-boundary import allows the extension to reach code that the extension's declared API surface is intended to gate.

- **CWE-863 (Incorrect Authorization)** describes the situation where an authorization check is performed but performed *incorrectly*, allowing the actor to bypass intended access restrictions. The extension boundary is exactly such an access restriction — declared but not enforced at the import layer — and a cross-root import is a bypass of that restriction. This matches the rule's semantics.
- **CWE-829 (Inclusion of Functionality from Untrusted Control Sphere)** describes a different failure mode: pulling functionality *from* an untrusted source into a trusted one (e.g., `eval()` of remote code, loading a remote script). AGENT-048 does not detect untrusted-source inclusion; it detects a trusted-but-sandboxed actor (the extension) escaping its own sandbox to reach trusted-core code. The control-sphere framing is the wrong direction for this rule.

The scanner has emitted CWE-863 since commit c4bc053 (2026-06-06). The earlier 829 designation was a provisional decision recorded in `HEADY_DECISIONS_NEEDED.md` (D-F) that was never written into the scanner, the YAML rule definitions, the engine mapping, or the public docs. Accepting 863 aligns with both the deployed scanner truth and the stronger semantic mapping.

---

## Inventory: all 5 value-carrying surfaces (all confirmed CWE-863)

| # | File | Line |
|---|------|------|
| 1 | `rules/builtin/asi_coverage_v030.yaml` | 482 |
| 2 | `packages/audit/agent_audit/rules/builtin/asi_coverage_v030.yaml` | 482 |
| 3 | `packages/audit/agent_audit/rules/engine.py` (RULE_CWE_MAPPING) | 97 |
| 4 | `docs/RULES.md` (Quick Reference row) | 51 |
| 5 | `packages/audit/agent_audit/scanners/privilege_scanner.py` (`_check_extension_patterns` emit) | 1059 |

Confirmed via `grep -rn "AGENT-048" --include='*.yaml' --include='*.py' --include='*.md'` and per-file reads on 2026-06-24. Zero CWE-829 occurrences in the tree.

## Files changed by this decision

**No value-changing edits.** The decision merely ratifies state already present on the `reconciliation/2026-06-06-paper-1-1-prep` branch. Only this decision-record file and `PR7_COMMENT.md` are added.

---

## Paper 1.1 sidebar

`paper/neurips/submission/supplementary/config/rule_precision.py` references AGENT-048 only as a precision number (0.82) with no CWE column. There is nothing to reconcile in the paper text right now. **If any future paper table or appendix adds a rule→CWE column, AGENT-048 MUST be cited as CWE-863** to remain consistent with the scanner truth recorded here.
