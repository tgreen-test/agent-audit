# `tests/rule_fixtures/` — one trigger per rule, and nothing else

This tree exists to answer one question for every advertised rule: **does anything in
this repository make it fire?**

It is deliberately **not** `tests/fixtures/`, and the distinction is load-bearing.

| | `tests/fixtures/` | `tests/rule_fixtures/` |
|---|---|---|
| purpose | the labelled benchmark corpus | reachability triggers |
| graded by | Layer 1 precision/recall, against `tests/ground_truth/labeled_samples.yaml` | `tests/test_rule_fixture_coverage.py`, rule by rule |
| an unlabelled file here | counts as a false positive and depresses published precision | costs nothing |
| answers | "how accurate is the tool on realistic code?" | "can this rule fire at all?" |

Mixing the two is what produced `tests/fixtures/agent_architecture/vulnerable_hooks/`:
a fixture written for AGENT-120, which the rule could not reach for five months
because of a discovery bug, and which — once the bug was fixed — produced three
correct findings that the corpus does not label, so Layer 1 precision **fell**. A
reachability fixture placed in a graded corpus without a label is a guaranteed
precision penalty for a rule working exactly as designed.

So these files are outside the graded corpus. Layer 1 does not scan this directory
and its numbers are unaffected by anything added here — measured, not assumed:
`NIGHT_RUN_LEDGER.md § W26`.

## What belongs here

One directory per rule, named for the rule it triggers, containing the **smallest
input that satisfies that rule's producer condition** — read out of the producer's
own source, not guessed. Each directory must trigger its own rule when scanned in
isolation; incidental findings from other rules are fine and are recorded in the
ledger.

## What does not belong here

* **Labels.** Nothing in this tree is graded against ground truth, and adding a
  ground-truth entry pointing at it would move it into the benchmark corpus by the
  back door.
* **Realistic code.** These are triggers. Breadth, idiom and plausibility belong in
  `tests/fixtures/`.
* **Anything for AGENT-054.** It compares a live MCP server against a stored
  baseline and no static input can produce it. It is pinned with its reason in
  `tests/test_rule_producers.py::SCAN_UNREACHABLE_BY_DESIGN`.

## Adding a rule

`tests/test_rule_fixture_coverage.py` fails the suite when an advertised rule is
produced by neither tree. Adding a rule to `RULE_CWE_MAPPING` and `docs/RULES.md`
without adding an input that reaches it is therefore no longer possible quietly —
which is the whole point, because a rule nothing measures cannot regress.
