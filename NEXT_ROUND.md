# v0.21.0 — scope, decided before v0.20.0 closes

v0.20.0 is a correction release: six withdrawn rules, a retracted metrics claim, four
reachability fixes, one rule count where there were four, and a quality gate that can no
longer pass on numbers it cannot account for. Everything in it is about making existing
claims true.

**v0.21.0 should be the opposite: one capability that does not exist yet, built the way
the last seven runs learned to build things.** This document says which one, why that one,
and what would make it finished.

It is deliberately short and deliberately singular. The failure mode this project has
demonstrated eight times is a mechanism that ships, is unit-tested, and is never reached.
The defence is not more process — it is fewer things per release, each with an input that
makes it fire and a measurement that would notice if it stopped.

---

## The one thing: untrusted code acquisition at runtime

**Rule shape:** a program that decides *at runtime* which code to run — `pip install`
with a non-literal package name, runtime `npm install`, `curl … | bash`, `git clone`
followed by execution, `requirements.txt` assembled from a variable.

Not "is this package name real" — that needs a registry, and
`docs/decisions/SLOPSQUATTING.md` sets out why scanning will not make network calls. This
is the half that is a property of the file.

### Why this one, in order of how much each reason weighs

1. **The corpus already asks for it, and the suite is red because it is missing.**
   `tests/test_corpus_label_rules.py` fails at HEAD. Three ground-truth labels cite
   AGENT-015 with the meaning "untrusted code fetched at runtime", no code path can emit
   it, and a label naming an unproducible rule is a false negative on every input at every
   commit, forever. `docs/decisions/AGENT-015_RESOLUTION.md` § 4 gives the two honest ways
   to close it. This is the only open item in the repository that is currently failing a
   test on purpose.

2. **It has an input before it has an implementation**, which inverts the defect this
   project keeps finding. Three fixtures exist and are labelled; the rule is the thing
   that is missing, not the corpus. Whether it fires is measurable on day one.

3. **Slopsquatting makes it current.** A newly published attack class whose detectable
   half is exactly this shape. See `docs/decisions/SLOPSQUATTING.md` — including why the
   answer to "add a slopsquatting rule" is no.

4. **It closes a naming defect as a side effect.** AGENT-015 currently means three things:
   a withdrawn YAML rule about MCP sources, a duplicate of AGENT-030, and the corpus's
   "runtime code acquisition". One identifier, three meanings, is what `DECISIONS.md` item
   39 is about. A new ID for the third meaning ends it.

### What "done" requires, and one of these is larger than it looks

* A rule ID that is **not** AGENT-015 — reusing it would preserve the ambiguity that made
  this an item.
* A producer, a YAML definition and an entry in both `RULE_CWE_MAPPING` and
  `PATTERN_TYPE_TO_RULE_MAP`. Item 36 (AGENT-049) is the cautionary tale: detection that
  works at confidence 0.85 and is then discarded because the rule has no YAML block.
* Corpus labels retargeted onto the new ID — a **ground-truth edit, so Heady's**, and the
  measured effect on Layer 1 stated before it is applied, per W27's method.
* **A scanner that opens `.sh` files.** `curl_pipe_bash.sh` is one of the three labels and
  `CAPABILITY_BOUNDARIES.md` § 4 states plainly that no scanner opens a shell script. This
  is a new file-type path, not a new pattern, and it is most of the work. If it is not in
  scope, say so *and* leave that label uncovered rather than retargeting it onto a Python
  rule to make the guard green — that is the drift this whole sequence has been undoing.
* The corpus-label guard green **for the right reason**, and `tests/test_rule_producers`
  and `tests/test_rule_fixture_coverage` still passing.

### What would make it a failure even if it ships

A rule that fires on its three fixtures and on nothing else in the world. Every guard in
this repository asks "can this fire at all?"; none asks "does it fire on the code people
actually write" (`CAPABILITY_BOUNDARIES.md` § 3). Before calling it done, run it against
real agent repositories and record what it found and what it did not — the blind-audit
0/6 is what skipping that step looks like.

---

## Carried, not scheduled

Ordered by whether the next person can act on them alone.

**Needs a decision from Heady before anything can move:**

* `METRICS_RETRACTION.md` § 5 step 1 — **which external surfaces carry the 98.51%.** Every
  in-repo surface is now corrected; the public half of the retraction is blocked on a list
  only Heady can produce.
* The five issue replies in `ISSUE_TRIAGE.md`, updated by W40/W41. #12 can close as
  won't-fix. #10 is now **fixed** and can close. #8 stays open with two of four claims
  fixed. #11 and #5 stay open.
* `DECISIONS.md` items 35, 36, 38, and item 39 rows 2–4 — all ground-truth or rule-set
  decisions.

**Actionable without a decision, in rough value order:**

* **Issue #8's remaining half: a provenance model.** Configuration and internal
  computation are not untrusted input. This is the tool's largest measured false-positive
  source and the honest fix for two live claims. It is a real piece of work — a taint
  source taxonomy, not a heuristic — and it should be its own release rather than a rider
  on the supply-chain rule.
* **AVB results carry no provenance stamp.** Layer 1's staleness hole is closed and this
  one is not; the gate reports it as `INFO`. Stamping it is a change to the AVB harness.
  Same design as `tests/benchmark/provenance.py` — content, not time.
* **`.agent-audit.yaml` at the repository root has been renamed to `.bak` since 2026-02-03
  and committed in that state.** A benchmark run did not reach its restore, so the
  project's own ignore rules have not applied to any scan of this repository for six
  months. Ledger § W39. One `git mv` plus a guard so the rename cannot be committed again.
* **The dead tree-sitter AST branches.** v0.20.0 decided the path stays unreached
  (`CAPABILITY_BOUNDARIES.md` § 4). Issue #11 notes the coherent follow-up is to delete
  the branches rather than measure them, at which point that issue resolves by the code
  disappearing.
* **A per-line view of the producer set.** W41 found that one `subprocess.run` line is
  reported by three separate producers, and gating two of them relocated the finding to
  the third. Nothing today can answer "which producers claim this line", which makes every
  false-positive report harder than it needs to be.

---

## Explicitly not in scope, with the reason

* **A slopsquatting / hallucinated-package rule.** `docs/decisions/SLOPSQUATTING.md`. The
  distinguishing test is a registry lookup; scanning makes no network calls by design; a
  bundled name list is a mechanism that decays into silence.
* **Issue #5, prompt-defence scoring.** Unchanged from RUN7's reasoning: it needs reliable
  prompt *extraction* first, and #8's problem 3 is a live example of the tool getting that
  distinction wrong. Extraction with its own fixtures and its own measured precision
  before anything scores what it extracts.
* **Re-enabling Layer 2.** `results/layer2.json` describes February. Re-enable it together
  with a regenerated file and a provenance stamp, or not at all.
* **Raising the ratchet again.** It moved this release, to R 0.82 / F1 0.73. A floor that
  rises every release stops being a regression detector and becomes a target.
