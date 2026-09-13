# RUN 3 REPORT

Target confidentiality: referred to throughout as "the audit target". No target path,
repository name, or source excerpt appears in this file, in the ledger, in any test
fixture, or in any commit message.

W9 through W13 are complete. W14 landed all four named denoise patterns but **did not
reach its bar**, and that is the headline of section 4.

---

## 1. The MCP bug: general dispatch or MCP-specific?

**MCP-specific, and worse than reported: six rules were dead in ordinary
directory-scan use, not three.** `MCPConfigScanner._find_config_files` discovered
configs with a non-recursive `path.iterdir()` while all nine other scanners in the
package use `rglob`, so any MCP config below the scan root was invisible — and
directory scanning is how every user invokes the tool.

The six with a directory-scan count of exactly zero were AGENT-005 and the **entire**
AGENT-029 to AGENT-033 MCP configuration family. Every one of the 18 findings the fix
restored on `tests/fixtures` originates in an MCP config file, which is the positive
control for the diagnosis being MCP-specific rather than a general dispatch fault.

---

## 2. Layer 1 before → after, delta attributed

| state | scanner | evaluator | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|---|---|
| A — baseline | pre-W10 | pre-determinism | 195 *or* 196 | 72 *or* 71 | 41 | .7303–.7341 | .8263–.8270 | .7753–.7778 |
| A′ | pre-W10 | deterministic | 195 | 72 | 41 | .7303 | .8263 | .7753 |
| **C — now** | +W10 | deterministic | 196 | 91 | 40 | **.6829** | **.8305** | **.7495** |

Measured by reverting each fix independently, five runs per state.

- **MCP dispatch fix: the entire delta.** P −0.0474, R +0.0042. It made 20
  previously-impossible findings possible; 1 matches a label and becomes a true
  positive, 19 are unlabelled and become false positives. **Precision fell because the
  corpus does not label what the fixed scanner now finds** — a labelling artifact, not
  a product regression. ASI-04 recall moved 0.0000 → 0.1429.
- **Rule-ID corrections: exactly zero.** All nine mismatches are label-side and a
  ground-truth correction is not mine to make. None was applied. For reference,
  correcting all nine is worth P +0.0314 / R +0.0381 with no scanner change.
- **A third fix, not in the brief:** the evaluator was non-deterministic. It matched
  findings to labels while iterating over sets, so the same command on the same commit
  returned TP 196 or TP 197 depending on `PYTHONHASHSEED`. **Every Layer 1 figure
  recorded before commit `cca9265` carries ±1 TP of unquantified noise, including the
  P 0.734 / R 0.827 / F1 0.778 headline in `CLAUDE.md`** — that was the high end of a
  coin flip. Found because two consecutive runs during W11 disagreed. A ratchet on a
  flapping number is worthless, so this had to be fixed before W12.

W11 found **nine** rule-ID mismatches, not three: session 2 had looked only at the
ASI-04 row. All nine cite a rule whose published title and pattern types describe a
different vulnerability from the label's own `notes`. The systemic case: all five
labels citing AGENT-015 are non-MCP supply-chain issues, while AGENT-015 is "Untrusted
MCP Server Source" — that single misconception, not a detection gap, is the largest
contributor to ASI-04 reading 0.0%.

---

## 3. The ratchet and its derivation

`tests/benchmark/gates.yaml` is now the single source of truth. The inline gate in
`benchmark.yml` is deleted; `run_all.sh` and `quality_gate_check.py`'s default point at
the same file, so nothing references the old one.

The two gates had drifted to P 0.72/R 0.80/F1 0.75 inline versus P 0.90/R 0.85/F1 0.87
in the file — and the current measurement, P 0.6829, sits below **both**, so the inline
gate would have failed CI on this tree.

**Ratchet = measured − 0.02, truncated:**

| | measured | ratchet |
|---|---|---|
| precision | 0.6829 | **0.66** |
| recall | 0.8305 | **0.81** |
| F1 | 0.7495 | **0.72** |

Per-ASI floors derived the same way. The `target:` tier keeps 0.90/0.85/0.87 visible,
non-blocking, annotated with the forensics: never modified since creation, carried
`continue-on-error` from birth, and the `layer1.json` committed beside it read R 0.4746
against its own 0.85 floor. It was never a standard, and the file now says so.

**Blind spot, stated rather than buried:** the ratchet first fires only after **5** true
positives are lost. Losing 1–4 passes silently. That is the price of a floor that does
not flap, and it should tighten to 0.01 once the labels are settled.

Proof both directions: exit 0 on real results; exit 1 on four synthetic files each one
point below a single floor, including per-ASI.

---

## 4. P0A: noise 1156 → 375. **The bar was not met.**

Target `noise < 118`. Achieved **375**. That is a 67.6% reduction and it is more than
three times the target — not a near miss.

| # | pattern | commit | before | after | delta |
|---|---|---|---|---|---|
| 1 | 40-hex read as an AWS secret key | `6a5db05` | 1156 | 684 | **−472** |
| 2 | `.exec`/`.spawn` receiver resolution | `a37bfba` | 684 | 441 | **−243** |
| 3 | constant-argument suppression | `26ee49f` | 441 | 409 | −32 |
| 4 | SQL statement syntax required | `5f00398` | 409 | 375 | −34 |

AGENT-004 went 474 → 2. AGENT-041 went 39 → 5 **while keeping all 3 of its true
positives** — it is the only rule on the target carrying both.

**The four invariants, all holding at `5f00398`:**

| invariant | result |
|---|---|
| recall on the target | **0/6, unchanged in both directions** |
| AVB knowns | **R 100.0% / P 88.0% / F1 0.9362, unchanged** |
| Layer 1 ratchet | **exit 0**, P 0.6829 / R 0.8305 unchanged |
| full suite | **1671 passed, 1 skipped** — 1606 baseline + 65 new, none deleted or skipped |

All 20 high-value findings survived every pattern, verified at each of the four commits
rather than only at the end. **No threshold, tier boundary, or confidence value was
changed anywhere in the phase** — `git diff 1c297d8..5f00398` contains no confidence
table. 65 new regression tests, every set split into FP cases and true-positive
controls, matching `3d58235`'s structure.

**Why 375 and not 118.** The brief's bucketing was wrong by a factor of three on the
largest pattern — it put the `.exec`/`.spawn` families at 155 when AGENT-034 actually
emitted 466. I recorded that in W13 before starting, but my own W13 estimate of ~144 was
still optimistic, and the gap is mine, not the measurement's:

- **AGENT-034 went to 180, not 0 (+180).** The survivors are bare `spawn()`,
  `execFileSync()`, `execa()` on genuine child_process imports. By the rule's own
  definition these *are* shell execution; the rule has no input-provenance requirement.
  Receiver resolution was never going to clear them and I was wrong to assume it would.
- **AGENT-047 (+36)** is a Python-side rule; pattern 3 is TypeScript-only.
- **AGENT-026 (+84)** was correctly flagged in W13 as a required fifth pattern and was
  not reached.

---

## 5. NEEDS-HEADY

Full detail in `DECISIONS.md` items 9–21. The ones that matter:

1. **Nine ground-truth labels (item 9).** Each cites a rule contradicting its own
   description. Worth P +0.031 / R +0.038 with no scanner change. I touched none of
   them. Four are `AMBIGUOUS` because the tool's ID is also questionable — relabelling
   those to match current emission would freeze an attribution that may itself be wrong.
2. **Delete `tests/benchmark/quality_gates_v2.yaml` (item 12).** One `git rm`. The
   consolidation is done and it is now referenced by nothing, but the W9 guard protects
   that filename and **I did not bypass it** — the RUN3 rules granted a W12 exception
   the guard cannot express, so I routed the work to an unprotected path instead of
   engineering around a control. It is inert, but leaving it recreates the problem W12
   just fixed.
3. **Wire the TypeScript scanner to `context_classifier.py` (item 18).** The same shape
   as the W10 bug: the mechanism exists, the Python path uses it, the TS path never
   calls it. **174 of the remaining 375** noise findings are in test paths. Highest-value
   remaining item and not a threshold change.
4. **AGENT-034 has no input-provenance requirement (item 20).** On an agent runtime
   whose job is spawning processes, this guarantees the rule is mostly noise however
   good the predicates get. Three options in `DECISIONS.md`; I recommend splitting the
   tier using the existing `_call_args_are_constant`, then taint in P1. Not done,
   because changing tier assignment is a public behaviour change and moving findings
   between tiers sits uncomfortably close to P0A's red line.
5. **P0A's two acceptance criteria are one criterion (item 16).** With 20 high-value
   findings frozen by the recall invariant, a post-fix denominator makes "rate < 10%"
   mean `noise ≤ 2`. I adopted session 2's frozen-1176 reading and flagged it rather
   than reinterpreting silently.

---

## 6. What I would do first next, and why

**Wire `context_classifier.py` into the TypeScript scanner.** It is worth 174 of the
remaining 375 findings, it is additive, it needs no new capability, and it closes an
asymmetry of exactly the kind that made W10 valuable — a mechanism that exists and was
never connected to one path. Do it with a true-positive control that survives being in a
test path, because downweight-not-delete is the whole safety property.

Then item 19 (widen `ts_decl_signature_re` beyond `eval`/`Function`), which is small and
precedented. Those two land around 180, and the remaining distance to 118 is item 20 —
which is a rule-design decision, not a predicate, and should not be taken unilaterally.

One thing I would *not* do next: reopen the four patterns. They are done, guarded, and
each one's blast radius is visible in its diff.

---

## 7. Confirmation

**I did NOT push, merge, tag, or publish, and I did not modify any oracle, fixture, or
dataset.**

Ten commits to `fix/py314-blocker`, all local. No ground-truth label was changed — the
nine mismatches are logged, not applied. No fixture file was added or modified; every
new test builds its inputs with `tmp_path` or synthetic literals. `tests/fixtures/`,
`tests/ground_truth/`, and the frozen evaluation data were read only. No threshold, tier
boundary, or confidence value was changed. The one gate file I was authorised to edit
was protected by my own guard, and I logged that rather than bypassing it.

Actions avoided: `git push`, `git merge`, `git rebase`, `git tag`, `gh` writes, PyPI/npm
publish, `rm -rf`, anything under `eval/`, `pip install agent-audit`, and any edit to an
oracle, dataset, fixture, or confidence threshold.
