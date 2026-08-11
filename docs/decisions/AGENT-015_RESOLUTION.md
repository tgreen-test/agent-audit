# AGENT-015 — collapsing a three-way conflict

**Status:** decision required (ground truth is not the scanner author's to edit)
**Date:** 2026-08-11 · RUN6 / W23
**Measured at:** `78d8fe5` on `fix/py314-blocker`
**Guard:** `tests/test_corpus_label_rules.py` — currently failing, by design

---

## The conflict in one paragraph

One identifier carries three incompatible meanings. **Published**, AGENT-015 is an MCP
rule, "Untrusted MCP Server Source". **Implemented**, it is nothing: no code path in the
package could construct it at any commit, and v0.19.3 withdrew it as a duplicate of
AGENT-030 — same severity, same CWE-494, same ASI-04 category, same detection content.
**Labelled**, it is a third thing again: five corpus labels for `npm install`,
`curl | bash`, `git clone` + exec, install-from-remote-requirements and PyPI
typosquatting, not one of which involves an MCP server. Layer 1 keys a detection to a
label on `file:line:rule_id`, so all five are unmatchable by construction — a false
negative on every input at every commit, forever, and where the tool *does* detect the
defect under a different ID, a false positive at the same time. A single identifier is
corrupting the published rule list, the corpus and the ASI-04 coverage figure
simultaneously.

The mechanism generalises and is the reason this document exists rather than a patch:
**a rule that never fires can be labelled to mean anything, because no output ever
contradicts the label.** Nothing was ever emitted under AGENT-015 to anchor its meaning.

**A sixth label has the same defect.** AGENT-036 ("Tool Output Trusted Without
Sanitization") was withdrawn in the same commit and carries one corpus label. It is
included throughout, because it is the same defect and separating them would leave the
guard failing after AGENT-015 was fixed.

---

## 1. The six labels, and what actually fires at each line

Measured with the same scan Layer 1 runs (`precision_recall.run_scan` over
`tests/fixtures`, 289 findings), cross-checked against a single-file scan of each fixture.
Both scan modes agree on all six.

| # | labelled file | line | label | GT line | rule ID actually emitted at that line | Layer 1 match? |
|---|---|---|---|---|---|---|
| 1 | `asi-04-supply-chain/direct/npm_install_runtime.py` | 13 | AGENT-015 | 1669 | **AGENT-001** at line 13 — exact | no: ID differs |
| 2 | `asi-04-supply-chain/direct/curl_pipe_bash.sh` | 11 | AGENT-015 | 1679 | **nothing**, at any line | no |
| 3 | `asi-04-supply-chain/direct/git_clone_exec.py` | 14 | AGENT-015 | 1689 | **nothing**, at any line | no |
| 4 | `asi-04-supply-chain/indirect/dynamic_requirements.py` | 14 | AGENT-015 | 1699 | **nothing**, at any line | no |
| 5 | `asi-04-supply-chain/indirect/pypi_typosquatting.py` | 12 | AGENT-015 | 1709 | **AGENT-034** at line 14 — within the 3-line tolerance | no: ID differs |
| 6 | `asi-02-tool-misuse/direct/subprocess_unsandboxed.py` | 8 | AGENT-036 | 1636 | **AGENT-001** at line 9 — within tolerance | no: ID differs |

"GT line" is the line of `tests/ground_truth/labeled_samples.yaml` that declares the rule
ID, so each row is directly actionable.

### Correction to RUN5

RUN5's report and `NIGHT_RUN_LEDGER.md § W19.5` state that `git_clone_exec.py:14` emits
AGENT-034 at the exact line, and conclude that **three** of the five AGENT-015 labels are
detected under a different ID. That is wrong. `git_clone_exec.py` produces no finding at
all, in either scan mode, and it produced none at `e4a939d` either — verified by scanning
the file from a worktree at that commit, so this is a transcription error in RUN5 and not
a behaviour change since. The row appears to have duplicated the `pypi_typosquatting.py`
result.

**Two** of the five are detected under a different ID, and **three** are genuine misses.
The corrected arithmetic is below and is the arithmetic used throughout this document.

### Why the three silent files are silent

None of the three is a detection regression, and each is silent for its own reason:

* `curl_pipe_bash.sh` is a **shell script**. No scanner in the package reads `.sh` — the
  file is never opened, so no rule of any kind could fire on it. This is a language-coverage
  gap, not a rule gap.
* `git_clone_exec.py:14` is `subprocess.run(["git", "clone", repo_url, "/tmp/repo"])` —
  argument-list form, no `shell=True`, fixed non-shell program. RUN4's
  fixed-non-shell-program predicate suppresses it deliberately, and correctly: `git clone`
  cannot be turned into arbitrary command execution by `repo_url`. The supply-chain risk is
  real (the *next* line executes the cloned code) but it is not a command-injection risk,
  which is the only thing any live rule is looking at.
* `dynamic_requirements.py:14` is `subprocess.run(["pip", "install", "-r", url])` — the
  same shape, suppressed for the same reason and equally correctly.

The two that *are* detected are detected because they contain a second, different defect:
`npm_install_runtime.py:13` passes `shell=True`, which is genuine command injection, and
`pypi_typosquatting.py` pipes `input()` into a subprocess argument list.

---

## 2. Does an existing rule already cover the described defect?

Answered per label from the rule's own published definition, not from what happens to
fire.

| # | what the label describes | covered today? | by what |
|---|---|---|---|
| 1 | "Runtime npm install without verification" | **partially** | AGENT-001 covers the `shell=True` command injection on the same line. It does **not** cover installing an unverified package — the same line without `shell=True` would be silent, as rows 3 and 4 demonstrate. |
| 2 | "Curl pipe to bash — arbitrary code execution" | **no** | No scanner reads shell scripts. |
| 3 | "Git clone and execute untrusted repo" | **no** | Nothing looks at fetch-then-execute as a sequence. |
| 4 | "Install from remote requirements file" | **no** | Nothing looks at package-install provenance. |
| 5 | "User input to pip install — typosquatting risk" | **partially** | AGENT-034 fires on the untrusted-input-to-subprocess shape. Typosquatting itself — an attacker-controlled *package name* — is not modelled. |
| 6 | "subprocess `shell=True`" | **yes** | AGENT-001 is exactly this, and the fixture's own docstring says `Expected: AGENT-047`, a third opinion. The label, the fixture and the tool disagree three ways; the tool is right. |

**The gap is a real one and it is not small.** The advertised set of 66 rules contains
nothing that covers untrusted package or code acquisition in general application code. The
three CWE-494 rules are all narrow: AGENT-005 and AGENT-030 are MCP server sources,
AGENT-062 is fake dependencies declared in OpenClaw skill metadata. AGENT-083 (CWE-829) is
Solidity `delegatecall`. Rows 2, 3 and 4 describe ASI-04 "Supply Chain" defects that
agent-audit does not detect, and withdrawing AGENT-015 already recorded that as a known
gap in `docs/RULES.md`.

---

## 3. The Layer 1 arithmetic, if the labels were retargeted

Simulated, not calculated on paper: the corpus was copied to a scratch directory, the
labels retargeted in the copy, and `precision_recall.evaluate` run against the copy with
the same 289 findings. **The corpus itself was not modified.**

Baseline, as labelled today:

```
TP=196  FP=93  FN=40   P=0.678201  R=0.830508  F1=0.746667
```

Per label, each applied on its own:

| # | retarget | ΔTP | ΔFP | ΔFN | resulting F1 |
|---|---|---|---|---|---|
| 1 | `npm_install_runtime.py:13` AGENT-015 → **AGENT-001** | +1 | −1 | −1 | 0.750476 |
| 2 | `curl_pipe_bash.sh:11` AGENT-015 → *nothing to retarget to* | 0 | 0 | 0 | 0.746667 |
| 3 | `git_clone_exec.py:14` AGENT-015 → *nothing to retarget to* | 0 | 0 | 0 | 0.746667 |
| 4 | `dynamic_requirements.py:14` AGENT-015 → *nothing to retarget to* | 0 | 0 | 0 | 0.746667 |
| 5 | `pypi_typosquatting.py:12` AGENT-015 → **AGENT-034** | +1 | −1 | −1 | 0.750476 |
| 6 | `subprocess_unsandboxed.py:8` AGENT-036 → **AGENT-001** | +1 | −1 | −1 | 0.750476 |

All three retargetable labels applied together:

```
TP=199  FP=90  FN=37   P=0.688581  R=0.843220  F1=0.758095

total delta:  ΔTP +3   ΔFP −3   ΔFN −3
              P  0.6782 -> 0.6886
              R  0.8305 -> 0.8432
              F1 0.7467 -> 0.7581
```

Each retargetable label moves three counters at once, which is the signature of this
defect class: one detection scored as a miss *and* as a false alarm because only the
identifier disagreed. Three labels, nine counter corrections, and **not one line of
detection code changed.**

Two things worth noting about that number.

* **0.7581 is above 0.75.** Had these labels been correct, the hard-coded floor that made
  CI red (W24, `precision_recall.py:503`) would never have fired. The contradiction between
  two thresholds and the mislabelling were, in the end, the same bill arriving twice.
* **Rows 2–4 contribute nothing.** They are unaffected by any retargeting, because there is
  no finding on those lines under any ID. They stay false negatives until a rule exists that
  detects what they describe — which is precisely the difference between the two options
  below.

---

## 4. Two options

These are **not** two ways of doing the same thing, and presenting them side by side
should not obscure that.

### Option A — retarget the labels to the rule that fires

**This is an accounting correction.** It changes no behaviour of the tool. It asserts that
three labels named the wrong rule for a defect the tool was already reporting, and it makes
the corpus say what the tool was already right about.

* Scope: three `rule_id` values in `tests/ground_truth/labeled_samples.yaml` — lines
  **1669** (→ `AGENT-001`), **1709** (→ `AGENT-034`), **1636** (→ `AGENT-001`). The
  `owasp_id` on each should be reviewed at the same time: row 1 moves from an ASI-04 label
  to an ASI-02 rule, which shifts one expectation between per-ASI recall buckets.
* Effect: Layer 1 F1 0.7467 → 0.7581, measured above.
* Leaves behind: rows 2, 3 and 4 remain false negatives, and the guard test still fails
  because those three labels still cite AGENT-015. **Option A alone does not clear the
  guard.** Those three must additionally be either retargeted to a rule that will exist
  (Option B) or removed from the corpus as labels for a capability the tool does not claim
  — and removing a label is a decision about what the benchmark measures, not a correction.
* Risk: low, and the failure mode is visible. If a retarget is wrong, the label stops
  matching and reappears as a false negative.

### Option B — introduce a supply-chain rule that matches what the labels describe

**This is a capability change,** and it carries the full cost of one. A new rule needs a
producer in a scanner, a published definition in `rules/builtin/*.yaml` **and**
`docs/RULES.md`, an entry in `RULE_CWE_MAPPING` and `PATTERN_TYPE_TO_RULE_MAP`, a fixture,
and tests — the checklist in `CLAUDE.md`. It is not a relabelling with a different name.

* What it would have to detect, to earn rows 2–4: package or code acquisition from a source
  the code does not verify — `pip install` / `npm install` from a runtime-supplied name or
  URL, `git clone` followed by execution of the cloned tree, `curl … | bash`. Rows 1 and 5
  would then also match it, and would match it *better* than AGENT-001 and AGENT-034 do,
  because it is the defect the labels actually describe.
* Blocking sub-decision: `curl_pipe_bash.sh` is a shell script and **no scanner in the
  package reads `.sh` at all**. Row 2 cannot be earned by a rule; it needs a shell-script
  scanner first. So even Option B, fully executed, leaves one of the six labels unmatchable
  unless a language is added.
* Cost of getting it wrong: this is the exact hazard `docs/RULES.md` records for the six
  withdrawn rules — "a rule implemented from a guess at its intended semantics is worse than
  an absent one". "Installs a package without verification" has no operational threshold
  until someone defines what verification counts. A hash-pin? A lockfile? A non-parameterised
  package name? Written loosely it will fire on every `subprocess.run(["pip", …])` in every
  repository, and the tool has already been through one round of exactly that with AGENT-034.
* Effect on Layer 1: unknown until built, and **not** simply +3. A new rule fires on
  unlabelled code too, which is how the last three precision drops in this project happened.

---

## 5. Recommendation

**Do Option A now. Treat Option B as a separate, scoped piece of product work, and do not
let A wait on B.**

The reasoning is that the two options answer different questions, and only one of them is
currently blocking a number.

Rows 1, 5 and 6 are **not detection gaps at all** — the tool sees those defects today and is
penalised twice each for naming them differently from a rule that does not exist. That is a
bookkeeping error in the measuring instrument, and it is corrupting a published F1. It costs
three lines to fix, the fix is measured (+3 TP, −3 FP, −3 FN), and nothing about it commits
the project to a design decision.

Rows 2, 3 and 4 are a **genuine capability gap**, already recorded as such in
`docs/RULES.md`'s known-gaps section when AGENT-015 was withdrawn. They should be resolved by
building the capability if the capability is wanted — with a stated operational threshold,
a fixture, and a published definition — and not by moving a label onto whichever rule
happens to be nearby. There is no rule nearby, which is the honest answer and also the
correct one.

The failure mode to avoid is the one that produced this situation: retargeting rows 2–4 onto
an approximately-related rule to make a guard go green would recreate exactly the drift that
let AGENT-015 mean three things. **A label should name the defect, and a rule should detect
what it says it detects.** Where those cannot be made to meet, the label is a recorded gap,
not a scoring adjustment.

### Suggested sequence

1. Retarget rows 1, 5 and 6 (three `rule_id` edits, plus an `owasp_id` review on row 1).
   Re-run `python3 tests/benchmark/precision_recall.py` and confirm F1 0.7581.
2. Re-derive the Layer 1 ratchet from the new measurement using the method in
   `NIGHT_RUN_LEDGER.md § W24` — measured minus observed spread minus 0.02, truncated — and
   **raise** it. 0.7581 − 0.02 → `f1_min: 0.73`.
3. Decide rows 2–4 explicitly and record the decision: build the supply-chain rule, or mark
   the three labels as known-uncovered in the corpus. Either closes the guard honestly.
   Whichever is chosen, row 2 additionally needs shell-script support or it stays open.

---

## 6. The guard

`tests/test_corpus_label_rules.py`. No allow-list. It fails the suite when any corpus label
cites a rule ID that no code path in the package can construct, and its message names each
label, the fixture line and the ground-truth line to edit.

```
$ python3 tests/test_corpus_label_rules.py
corpus labels: 238
labels citing a rule with NO producer: 6
    AGENT-036  asi-02-tool-misuse/direct/subprocess_unsandboxed.py:8  (labeled_samples.yaml:1636)  'subprocess shell=True AGENT-047/036'
    AGENT-015  asi-04-supply-chain/direct/npm_install_runtime.py:13  (labeled_samples.yaml:1669)  'Runtime npm install without verification'
    AGENT-015  asi-04-supply-chain/direct/curl_pipe_bash.sh:11  (labeled_samples.yaml:1679)  'Curl pipe to bash - arbitrary code execution'
    AGENT-015  asi-04-supply-chain/direct/git_clone_exec.py:14  (labeled_samples.yaml:1689)  'Git clone and execute untrusted repo'
    AGENT-015  asi-04-supply-chain/indirect/dynamic_requirements.py:14  (labeled_samples.yaml:1699)  'Install from remote requirements file'
    AGENT-015  asi-04-supply-chain/indirect/pypi_typosquatting.py:12  (labeled_samples.yaml:1709)  'User input to pip install - typosquatting risk'
labels citing a rule not in the advertised set: 6
    ... the same six
script exit = 1
```

It is committed failing. That is deliberate: the labels cannot be edited by the scanner
author, and a guard that passes while the defect is present is the thing this project keeps
finding. `tests/test_rule_producers.py` did the same on the rule side in v0.19.3 — it failed
on HEAD, named six rules, and the rules came out of the published list. This is the corpus
half of that check, and it is the one that would have caught AGENT-015 before the identifier
reached a published rule list, a published coverage figure and 238 labels at once.

---

## Related

* `docs/RULES.md` § Withdrawn Rules — the six withdrawn IDs and the gaps they leave
* `DECISIONS.md` item 9 — the nine known corpus mislabels, of which rows 1, 5 and 6 are three
* `NIGHT_RUN_LEDGER.md § W19.5` — the original diagnosis (see the correction in § 1 above)
* `NIGHT_RUN_LEDGER.md § W23` — the measurements in this document
* `tests/test_rule_producers.py` — the same guard on the rule side
