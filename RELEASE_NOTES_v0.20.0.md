# agent-audit v0.20.0

**This is a correction release.** The improvements are real and they are at the bottom. What
an existing user needs first is the list of things this project published that were wrong,
because two of them change what you should believe about output you already have, and two
of them need a change on your side.

**Retracted — the benchmark figures.** Any figure of **98.51% precision, 100% recall, 99.25%
F1 or 1.49% false-positive rate** you have seen for this project is retracted, and there is
nothing to correct it *to*. Those were never measurements: they were copied out of a
development brief's *target* block and published as achievements, while the
`results/layer1.json` committed in the same commit measured 124 false negatives and 47.46%
recall. No commit exists at which any script produced them.

What stands in their place is one figure with the command that produces it. Against a ground
truth of 81 sample files and 238 labels, `python3 tests/benchmark/precision_recall.py`
prints:

```
TP 199   FP 90   FN 37
Precision 68.86%   Recall 84.32%   F1 75.81%   FP rate 31.14%
```

Read that precision as a floor, not a point estimate: at least 21 of those 90 false
positives are correct findings that the corpus simply does not label, and precision fell
since 0.19.0 partly *because* discovery bugs were fixed and the tool started finding correct
things nobody had labelled. It is published as a bound rather than quietly adjusted upward.
`docs/decisions/METRICS_RETRACTION.md` has the derivation, the per-surface record, and the
reason no adjusted headline figure is offered.

**Withdrawn — six rules, and one honest count.** `AGENT-003`, `AGENT-011`, `AGENT-013`,
`AGENT-015`, `AGENT-016` and `AGENT-036` are removed from the advertised set. What remains is
**66 rules** mapped to the OWASP Agentic Top 10, where the published figure was 72. No code path in the package could construct any of them at any commit:
five had their detection written out in full as a YAML `detection.patterns` block — the place
the contributor checklist says to write it — and the only code that can execute such a block
has never had a caller outside a unit test. **If you filter, suppress, or report on any of
those six IDs, that configuration has been matching nothing and can be deleted.** Two of the
six describe risks that are still covered under a surviving ID (`AGENT-013` by `AGENT-004`,
`AGENT-015` by `AGENT-030`); the other four leave real gaps — exfiltration chains, goal
boundaries, RAG provenance, tool-output trust — and those are written down in `docs/RULES.md`
under *Withdrawn Rules* instead of being dropped quietly. Separately, five different rule
counts had been published for one set of rules — 40, 49, 53, 60+ and 72 — including two on
distribution surfaces. Every published count now says 66, `tests/test_rule_producers.py`
fails the build if an advertised rule has no producer (no allow-list, deliberately), and
`tests/test_published_rule_count.py` fails it if any published count disagrees with the rule
set or a page quietly stops stating one.

**Fixed — rules that only worked if you named the file yourself.** MCP configuration
discovery used a non-recursive directory listing where nine other scanners recurse, so **six
MCP rules had a directory-scan count of exactly zero**: they fired when you pointed the
scanner straight at a config file, and never during an ordinary project scan. AI-tool hook
discovery (`AGENT-120`) had the same defect. On TypeScript, `AGENT-034`'s tool-boundary gate
— 325 lines with a full test file of its own — was imported by nothing, so the rule fired
outside tool entry points on every TypeScript scan since it shipped. **If you have scanned a
project whose MCP configuration lives in a subdirectory and got a clean report, scan it
again with this version.** A rule that never fires and a clean codebase produce identical
output, which is why none of this was visible from the test suite; `tests/test_rule_reachability.py`
now fails the build when a rule that fires on a single file does not fire on a directory scan.

**Fixed — the quality gate could pass without measuring anything, and this one needs a change
in your CI.** `quality_gate_check.py` decided the build by reading `results/layer1.json` and
nothing else, so a committed stale file cleared the ratchet, and an empty results directory
produced SKIP — not failure — for layers declared blocking. Layer 1 results now carry a
provenance stamp over the labels, the corpus and the scanner source, which the gate
recomputes and refuses to score if it does not describe the tree being checked; a missing
results file for an enabled blocking layer is now a failure. **If you run the gate in your
own CI, add `--layers` naming the layers that job actually measures**, or a layer you do not
produce results for will fail your build instead of being silently skipped. Layer 1 also had
*two* thresholds — a hard-coded `f1 < 0.75` inside the measuring script alongside the 0.72 in
`gates.yaml`, which calls itself the single source of truth — so the same build could pass
the documented gate and fail the undocumented one. The hard-coded floor is gone; no threshold
was lowered.

**Fixed — two reported false positives, Python 3.12–3.14, and a large TypeScript denoise.**
`AGENT-041` no longer treats every `.execute()` as a SQL sink: the receiver must now look
like a database handle by name or by an assignment in the same file, so `target_agent.execute(task)`
is silent while both true positives in the reporter's case survive (#10). `AGENT-004` no
longer reports a format string as a hardcoded credential — `f"password={password}"` is
interpolation, not a literal (#8). `AGENT-010` scores a prompt built only from locals at 0.50
rather than 1.00, and a `subprocess` call that names its own program is no longer treated as
a shell sink — both downgrades, never suppressions. The suite runs clean on 3.12, 3.13 and 3.14 — the
versions the `ast.NameConstant` removal broke — and the classifiers now declare 3.9 through
3.14. None of these moved the benchmark by a single finding,
because the graded corpus contains none of these shapes — the bug reports were the
measurement, which is itself worth knowing about the corpus. The TypeScript scanner also lost
a large volume of false positives (receiver resolution, all-literal argument lists, `AGENT-041`
requiring SQL syntax rather than a keyword); the CHANGELOG records that measurement together
with where it came from.

**What this tool does not do — please read `CAPABILITY_BOUNDARIES.md`.** No cross-file
analysis, no call graph, no import following, no type resolution, no runtime behaviour.
TypeScript and JavaScript analysis is **regex-level, not AST-level**: the tree-sitter path
exists, has never executed in a shipped environment, and stays unreached on purpose — wired
up on a scratch build it lost 2 true positives, added 6 known false positives and broke 42
tests. No scanner opens a `.sh` file. `AGENT-041` still over-triggers on non-database
`.execute()` receivers where the SQL is at the call site, and there is no provenance model
separating configuration from untrusted input. That document also carries the blind-audit
result: on a real codebase, with 0 files skipped and 0 parse failures, recall on 6 real
defects was **0**. Read it before treating a clean report as an assurance.

**Shipping as preview — SkillScanner and the PDF report.** This release publishes two
features that were merged before the branch and that no previous release note mentioned. They
are labelled preview because of what has *not* been done to them, not because of what has:
both carry tests (twenty-eight for SkillScanner, thirty-three for the report), and neither has
been measured on a graded corpus the way the core scanner has. Every figure in this document —
P 68.86% / R 84.32% / F1 0.7581, and the sixty-six rules behind it — describes `AGENT-*` rules
on the eighty-one-sample labelled corpus. It says nothing about either of these.

* **SkillScanner** analyses `SKILL.md` files and runs on every scan, no flag. Its own
  `SKILL-000` / `SKILL-010` / `SKILL-020` namespace sits deliberately outside the advertised
  `AGENT-*` set and is tier-ceilinged — `SKILL-010` cannot exceed WARN, `SKILL-000` and
  `SKILL-020` cannot exceed INFO — so **no `SKILL-*` finding can fail your build**. Rely on
  those to point at Skills worth a human read; do not read a quiet SkillScanner as evidence a
  Skill is safe. Its cross-lingual fairness evaluation is pre-registered in
  `docs/skillscanner/eval/PROTOCOL.md` and is not finished, so there is no precision or recall
  figure for it and this release publishes none.
* **One way SkillScanner *can* fail your build, and it is new behaviour.** It also extracts
  fenced `python` and `shell` blocks from a `SKILL.md` and routes them through the existing
  Python and privilege scanners, remapping the findings back onto the `SKILL.md` line. Those
  are ordinary `AGENT-*` findings and keep ordinary tiering: a Skill whose example block
  calls `eval()` on a tool argument produces **BLOCK-tier `AGENT-001` and `AGENT-034`**,
  measured on `tests/fixtures/skills/eval_python`. If you gate CI on BLOCK findings and your
  repository contains `SKILL.md` files with code in them, this release can start failing
  builds that passed under 0.19.2. That is the scanner working; it is not a `SKILL-*` finding
  and the ceiling does not apply to it.
* **One thing to check before you upgrade.** `SKILL-010`'s judge calls the Claude API. It is
  off unless *both* the `anthropic` SDK is installed and `ANTHROPIC_API_KEY` is set in the
  environment, in which case a plain `agent-audit scan` sends the `description` field of each
  `SKILL.md` it finds to `claude-sonnet-4-6`. There is no flag to turn that off, and with no
  key it never happens — `get_default_judge()` returns `NullJudge` and nothing leaves the
  machine. If the code you scan is confidential and that variable is set in your CI, unset it
  for the scan step.
* **`agent-audit report <scan.json> -o <out.pdf>`** turns `--format json` output into a PDF.
  It needs `pip install "agent-audit[report]"`; without the extra the command exits 1 and now
  says so with the extra in it, which it did not before this release — Rich was reading
  `[report]` as a style tag and printing `pip install agent-audit`, an instruction that does
  not install the dependency. One claim is hardcoded into every PDF it writes, in *Standards
  Alignment*: 10/10 coverage of the OWASP ASI Top 10. That one reproduces — the advertised set
  spans all ten ASI categories — and the check is in `NIGHT_RUN_LEDGER.md` § W56. No
  precision, recall or count figure is printed in a report.
* **`langdetect` is a new required dependency**, not optional: `0.19.2` shipped six, this
  ships seven. `pip install --upgrade agent-audit` pulls it. The other two additions are
  extras and are only installed if you ask: `[report]` (reportlab, matplotlib) and `[judge]`
  (the `anthropic` SDK).

---

Full detail in [`CHANGELOG.md`](CHANGELOG.md). The suite is 1,924 passed / 1 failed / 4
skipped, and the one failure is committed red on purpose: three ground-truth labels still
cite a rule no code path can emit, and a guard that passes while the defect is present is
exactly what this release is about.
