# RUN 8 REPORT

Target confidentiality: the audit target is referred to only as "the audit target". No
target path, repository name or source excerpt appears in this file, in the ledger, in any
fixture, or in any commit message.

W38 through W43 are complete. **v0.20.0's corrections are applied, and the release is now
staged with every published number matching what the tool does.**

Six commits, `fda9f06` through this one. The run's result is that the release's own
premise — that a claim should be checkable — is now enforced by three tests rather than by
attention.

---

## 0. The headline: the gate that decided the build could not tell it had measured nothing

`quality_gate_check.py` reads `results/layer1.json` and reads nothing else. Two ways it
exited 0 while proving nothing, both measured before anything was changed:

```
$ ... --results <the previous commit's layer1.json>
  ℹ️ Layer 1 precision 67.8% below target 90% (aspirational, non-blocking)
Summary: 0 failures, 0 warnings, 1 skipped, 3 below target
exit=0

$ ... --results <an empty directory>
  ⏭️ [SKIP] Layer 1 results not found
  ⏭️ [SKIP] Agent-Vuln-Bench results not found
Summary: 0 failures, 0 warnings, 2 skipped, 0 below target
exit=0
```

Both layers are `enabled: true, blocking: true`. `SKIP` is not counted as a failure.

**What the first one would have hidden is specific.** The stale file reads F1 0.746667 and
R 0.830508, which clear the ratchet raised in the same commit to `f1_min: 0.73` and
`recall_min: 0.82`. Running the gate to confirm that raise — exactly what
`RELEASE_CHECKLIST.md` § 2 instructs — would have returned PASS against the measurement the
raise was supposed to be checked against. Nothing in the output distinguishes that from a
real pass.

This is the eighth instance of `CAPABILITY_BOUNDARIES.md` § 3, with the gate in the
detector's place. A gate that evaluated the wrong corpus, a gate that evaluated nothing,
and a gate that evaluated a passing build all print the same exit code.

**No assertion about the numbers could have caught it**, because no statement about a value
distinguishes a value with the wrong referent from one with the right one. So the fix is a
statement about where the numbers came from: `tests/benchmark/provenance.py` fingerprints
the labels, the corpus, the scanner source, and which `agent_audit` the interpreter that ran
the scan actually imported. Content, never time — in CI the gate runs in a different job and
the artifact is minutes old when it is read, so an age limit would fail correct builds and
be switched off inside a week. No `--allow-stale`, because that would be the next place the
contradiction hides.

It then caught two real stalenesses during this run's own scanner work, which is the only
kind of evidence that matters for a guard.

---

## 1. W40/W41 — two bug reports, and a measurement that says "no" again

**Issue #10 is fixed.** `_check_sql_tainted_param` now requires the receiver to look like a
database handle — named like one, or given one by an assignment in the same file. Positive
evidence, so an unrecognised receiver is silence rather than a BLOCK-tier accusation, and
there is no list of agent framework names to keep current.

```
BEFORE  3 AGENT-041, all BLOCK/1.0, including  return target_agent.execute(task)
AFTER   2 AGENT-041 — the false positive gone, both true positives kept
```

Both survive, including KNOWN-008 (`cursor.execute(query)`, SQL built upstream), which is
the one a blunter fix takes with it.

**Issue #8 has two of four claims fixed, one downgraded, one improved, and stays open.** The
credential half of claim 2 is fixed — a value that is entirely interpolation is not a
hardcoded credential. Claim 3 drops from BLOCK/1.0 to INFO/0.50 rather than being
suppressed, because `skills_list` really is parameter-derived and the distinction a
single-file pass can draw is one step wide.

**Claim 4 is where the finding is.** Gating the subprocess taint sink moved AGENT-034 from
0.85 to 0.65; gating `subprocess_expanded` left it firing via `eval_exec_expanded`; gating
that one left AGENT-047 at 0.80.

> **Three separate producers report that one line, and gating two of them relocated the
> finding to the third.**

That is the "one thing in several places" shape of W24's duplicate thresholds and this
release's four rule counts, relocated into the detection path. `CLAUDE.md` warns that three
*pattern types* map to AGENT-034; the producer set for a single call is wider again, and
nothing enumerates it.

**Layer 1 did not move across any of the four scanner changes.** TP 199 / FP 90 / FN 37 on
both sides. The graded corpus contains none of these shapes, so it could not have caught
the defects and cannot show the fixes. `CAPABILITY_BOUNDARIES.md` § 6 already says these
numbers do not transfer to real code; this is what that looks like from the inside.

---

## 2. W42 — four numbers for one set, and the guard that ends it

The rule count is **66**, and it is checkable. Eighteen in-repo surfaces corrected from 40,
49, 53 and 72 — including `packages/audit/pyproject.toml`, the PyPI description and the only
rule count on a distribution surface.

`tests/test_published_rule_count.py` relates the published numbers to
`advertised_rules()` rather than to each other, and fails **per surface** if a page stops
stating a count at all. That second half is the load-bearing one: a phrasing change quietly
removing a file from the guard is precisely how `docs/index.html` came to publish 49 while
the README published 72.

Its first version failed on nine correct per-category counts in `index.html`. An over-eager
guard gets weakened, and a weakened guard is the one that stops catching things — so it now
checks only counts whose line claims to describe the whole set, and the cost is stated:
`docs/ARCHITECTURE.md:134` is a bare `(66 rules)` in an ASCII diagram that it does not see.

Every metric on every in-repo surface is now the measured value with the command beside it.
`tests/README.md` was the priority and now opens with the retraction, naming the mechanism
in three sentences. `CHANGELOG.md`'s three 100% lines are **struck rather than updated**,
because they were never measurements and there is nothing to update them *to*.

**The published half of the retraction is still blocked**, on the same thing RUN7 recorded:
which external surfaces carry the 98.51%. That list is Heady's.

---

## 3. W43 — a newly published attack class, assessed and declined

Slopsquatting: a coding agent hallucinates a plausible package name, an attacker registers
it. Real, in the wild, ASI-04, agent-specific — squarely this tool's declared territory.
43% of hallucinated names recur across identical prompts, so it is not even guesswork for
the attacker.

Scanned three shapes at v0.20.0 rather than reasoning from the rule list:

* the attack itself — a hallucinated name as a static import — produces **nothing about the
  package**. The one finding is SSRF on an unrelated line, and the `requirements.txt`
  pinning the same name produces zero.
* an agent installing a model-produced name produces **five findings, none about the
  package name** — tool input validation, dynamic import, self-modification. Already
  covered, for other reasons.

So: the shape the tool can see it already sees; the shape that makes slopsquatting
slopsquatting, it cannot see at all.

**A rule would not close that**, because every published detection begins by asking the
registry whether the package exists, and scanning makes no network calls by design. The two
ways round it are both catalogued failure modes — a registry client destroys the
determinism `provenance.py` was written this same session to assert, and a bundled list of
known-hallucinated names is a mechanism that decays into silence, which is
`CAPABILITY_BOUNDARIES.md` § 3 with a maintenance schedule attached.

**What it is an argument for** is the rule this project already owes its own corpus: runtime
acquisition of code whose identity is not fixed in the source. Three ground-truth labels
mean exactly that, `tests/test_corpus_label_rules.py` is committed red because of them, and
one of the three is a `.sh` file no scanner opens.

That is `NEXT_ROUND.md`, and it is the single thing v0.21.0 should do.

---

## 4. Invariants at the end of the run

| invariant | result |
|---|---|
| Layer 1 | **TP 199 / FP 90 / FN 37**, P 0.688581 / R 0.843220 / F1 0.758095 — unchanged by four scanner fixes |
| `results/layer1.json` | carries a provenance stamp; verified against this tree by the suite |
| `quality_gate_check.py` | **exit 0**, and now capable of exiting 1 for the right reasons |
| full suite | **1,890 passed, 1 failed, 3 skipped** — the failure is the corpus-label guard, still red on purpose |
| advertised rules | **66**, and 18 published surfaces now agree, enforced by a test |
| thresholds changed | **none by me**; the ratchet was raised by `finalize_run7.sh` in the first commit |
| new guards | `test_gate_provenance` (12), `test_published_rule_count` (7), `test_agent041_receiver` (25), `test_issue8_provenance_shapes` (18) |

**No push, merge, rebase, tag or publish. No oracle, dataset, ground-truth label, existing
fixture, confidence value or tier boundary modified by me** — the three label corrections
and the ratchet were applied by Heady before this run and committed as its first act.

---

## 5. Two defects found while looking at something else

**`.agent-audit.yaml` at the repository root has been renamed to `.bak` since 2026-02-03
and committed in that state.** A benchmark run did not reach its restore. Layer 1 is
unaffected — the benchmark disables that file on purpose, which is exactly why nothing
noticed — but every `agent-audit scan .` against this repository has silently not honoured
the project's own ignore rules for six months. `DECISIONS.md` item 41.

**Agent-Vuln-Bench results carry no provenance stamp.** Layer 1's staleness hole is closed
and the same hole one directory away is not. The gate reports it as `INFO` rather than
enforcing it, because stamping it means changing the AVB harness. `DECISIONS.md` item 40.

---

## 6. The through-line, eight runs on

RUN7 ended by saying the only defence against a mechanism that looks like success is to
measure the mechanism rather than the output. This run is what that costs when you apply it
to the instruments themselves.

The gate was the last thing in the repository still trusted rather than checked. It had
been consolidated, documented, given a single source of truth and a test asserting that
only one thing decides Layer 1 — and none of that noticed that it would pass on a file from
another commit, or on no file at all, because every one of those improvements was about
*which* numbers it read.

The pattern is now specific enough to state as a question worth asking of anything:

> **If this mechanism silently stopped working, what would be different?**

For six advertised rules, a tree-sitter path, an MCP discovery walk, a coverage report and
now a quality gate, the answer was *nothing observable*. The three guards this release adds
each make the answer to that question "the suite goes red" — and the one this run wrote
proved it by catching two real stalenesses in the same session that introduced it.
