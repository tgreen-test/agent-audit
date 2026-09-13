# NIGHT RUN REPORT — 2026-08-11

> **2026-09-11 — the paper correction, authorised mid-session by Heady.** Supersedes the RUN10
> brief's "no edits outside the repository" for four named items in `paper/`. One was an edit,
> two were verifications that correctly changed nothing, and the fourth is blocked.
>
> **Edited — `paper/main.tex:325`.** "achieves 98.51\% precision at 100\% recall" replaced with
> the measured "68.86\% precision at 84.32\% recall (F1 0.758), measured at agent-audit
> v0.20.0", plus a footnote stating the mechanism (false negatives assumed zero rather than
> counted) and naming the producing script, corpus version and counts. Heady's supplied wording
> ended mid-word; the footnote was completed and the completion flagged.
>
> **Verified and deliberately NOT changed — `main.tex:395` and `:408`.** "perfect recall on
> Set~A and Set~B" and "100\% recall on injection/RCE and MCP" are **true**: re-measured at
> v0.20.0, Set A 100.0% (19/19), Set B 100.0% (9/9), with Set C's "two false negatives" also
> matching (12/14, both in the T12 noise sample). Layer 1's 98.51% was never measured; AVB's
> 100% is oracle-backed. Retracting the second with the first would have been an error in the
> opposite direction.
>
> **NOT done — `main.pdf` is still the old build and still carries the retracted sentence.**
> This machine runs TeX Live 2026 *basic* and lacks `pgfplots`, `acmart` and `placeins`;
> `tlmgr` cannot write to the root-owned tree and no `sudo` was run. **The source and the build
> now disagree, and the build is the file a reader opens** — so the paper is not corrected until
> Heady rebuilds it. The command to do so is in `RUN10_REPORT.md`.
>
> **`paper/` is not under version control, and that nearly cost the paper.** Both files were
> backed up before the edit (`*.pre-retraction-20260911.bak`). The failed `pdflatex` run
> **deleted `main.pdf`** while printing *"no output PDF file produced"*; it was restored from
> the backup, byte-identical. Without the backup the only compiled copy would have been
> destroyed by a command that reported producing nothing.


> **RUN 10 ADDENDUM — 2026-09-10. Three release blockers; the full write-up is
> `RUN10_REPORT.md`, evidence in the `NIGHT_RUN_LEDGER.md` RUN 10 entry.**
>
> **Nothing below changes.** No detection code, threshold, oracle, fixture or dataset was
> touched, and Layer 1 is unmoved: **TP 199 / FP 90 / FN 37, P 68.86% / R 84.32% / F1
> 0.7581**, gate exit 0. Nothing pushed, merged, tagged or published; HEAD is still
> `dbae329`.
>
> **The finding that matters most is about an instrument, not a number.**
> `scripts/scan_external_claims.sh` — the tool RUN9 built to find retracted figures on
> external surfaces, and the tool the release blocker depends on — **had never worked**. It
> cut each pattern's regex at the first `|`, turning every alternation into an unbalanced
> parenthesis; `grep -E` rejected them and the error went to `/dev/null`. **18 of its 34
> patterns silently matched nothing**, including every form of "100% recall" and "0 false
> negatives", the 80%-precision pattern, and all three count patterns. Same command, same
> specimen: **1 match before the fix, 11 after.** `EXTERNAL_CLAIMS_CHECKLIST.md` § 4 had
> certified the tool under the heading *"so you know the tool works"* — using the broken
> tool's own output as the evidence. Fixed, plus a `validate_patterns()` pass that exits 2
> rather than under-reporting. **Any external sweep run before 2026-09-10 must be re-run.**
>
> **What the fixed scan found outside the repository** (read-only; nothing outside this
> repository was edited, verified by unchanged mtimes): the retracted set is live on
> `agent-audit-slides.html` (a public deck — precision 98.51%, recall 100%, F1 99.25%, FP
> rate 1.49%, plus four wrong rule counts and five stale versions), in `paper/main.tex:325`
> **and the compiled `paper/main.pdf`**, and across five `docs/cais-2026/` files — one of
> which, `PAPER_DATA_SUMMARY.md`, is not a stale figure but a **standing instruction**: a
> column of paste-ready `LaTeX (v0.16.0)` macros under "Recommend reporting v0.16.0 Layer 1
> metrics in the paper". Clean, and both verified: `paper/neurips/submission/` (0 matches)
> and the SkillScanner camera-ready.
>
> **Two other blockers closed.** `docs/COMPETITIVE-COMPARISON.md` re-measured with all three
> tools on one corpus at v0.20.0 — and the baselines beat agent-audit on precision (100% vs
> 86.96%) and FPR (0% vs 13.04%), which the table now states. `README.md:147`'s "18,899
> ClawHub skills at 80% precision" cut and guarded by
> `tests/test_unsubstantiated_metrics.py`; the 80% was a 20-sample draw (16/20, Wilson
> 58.4–91.9%) attached to an 18,899 denominator.
>
> **Suite moved 1,891 → 1,895** (four new guard tests), corrected on every current-state
> surface; three further stale counts surfaced only because the scanner was fixed.
>
> **One expected command does not exist.** `./run_eval.sh --commit HEAD` has never been
> tracked and belongs to a gitignored corpus directory this run may not touch, so the 2.2:1
> signal-to-noise figure has **no producer in the repository**. Recorded UNVERIFIED and not
> restated. `DECISIONS.md` item 52.
>
> **Blocking, and it is a decision rather than a task:** has any of the external material
> been submitted, uploaded to arXiv, or presented? No command answers it, and it decides both
> the remedy and the ordering (`METRICS_RETRACTION.md` § 4). `RELEASE_CHECKLIST.md` steps
> A–C.


> **SUPERSEDED IN PART — read SESSION2_REPORT.md.** Session 2 measured the blind audit
> directly and settled the open question below: **the 0/6 is real.** It reproduces
> identically at all three commits and on both interpreters, so it is a capability gap,
> not an environment artifact. The environmental story in §1 explains the AVB 0.0% and the
> Python 3.14 crash — it does not explain the blind audit, which ran on 3.11 where that
> crash cannot fire. Session 2 also corrected §2's claim that `results/layer1.json` was a
> broken-environment artifact; it was the v0.5.2 measurement, six months stale.
> Everything else below stands as written.

> **SESSION 8 ADDENDUM — 2026-08-11, scope was one file.** This session was given an explicit
> scope by Heady — read `RELEASE_CHECKLIST.md` and `DECISIONS.md` item 39, write one script
> doing the three guard-blocked changes and nothing else, do not run it — and it did exactly
> that and stopped. **No fix was made, so nothing below changes and no number moved.**
> `scripts/finalize_run7.sh` now exists: it applies the three item-39 `rule_id` edits, raises
> `f1_min` to 0.73 and `recall_min` to 0.82, and `git rm`s the two dead threshold files, each
> step printing a before/after diff and verifying itself. It is **unrun** — `bash -n`-clean
> and its embedded Python compiles, which proves it parses, not that it behaves. Evidence and
> design notes in `NIGHT_RUN_LEDGER.md` § W33. Nothing was committed, pushed, merged, tagged
> or published, and no oracle, dataset, ground-truth label, fixture or threshold was edited —
> the script that would edit two of those is precisely what was left unrun.

## 1. The headline

**The 0.0% was a broken environment, not a capability gap.** The editable install's `.pth`
still pointed at `Documents/agent-audit/...` from before the repo moved under
`Documents/Research/`, so `python3 -m agent_audit` raised `ModuleNotFoundError`, the benchmark
adapter turned that empty stdout into `return []`, and 12/12 KNOWN samples scored as false
negatives in 0.0s each — recall went **0.0% → 100.0%** with zero source changes.

**For the blind audit, the answer is "probably the environment, but I can't close it from
here."** TypeScript scanning is byte-identical on 3.11/3.12/3.13/3.14 (same 4 findings on a
4-defect probe), so 3.14 does not break TS scanning as such — *but* the `ast.NameConstant`
bug aborts the entire scan process, not just the offending file: a directory with one Python
file containing `while running:` went **8 findings on 3.11 → 0 findings (traceback, no JSON)
on 3.14**, taking the TypeScript findings down with it. If the audited codebase contained even
one `.py` file with a non-literal `while` test or `shell=` kwarg, that alone explains 0 of 6;
if it was pure TypeScript, the crash cannot have fired and 0/6 is a real capability gap.
**Re-run the blind audit at `0f321ff` to settle it — it is one command and it decides the
roadmap.**

## 2. Status

| W | status | the check that now passes |
|---|---|---|
| W0 — AVB 0.0% | **FIXED** | `cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" --tool agent-audit --dataset knowns --output /tmp/avb_after.json` → **R 100.0% / P 88.0% / F1 0.9362**, 0.2s per sample (was 0.0% / 0.0% / 0.0000, 0.0s) |
| W0b — adapter can't hide a dead scanner | **FIXED** | `pytest tests/test_benchmark_adapter_guard.py -q` → 8 passed; 6 of the 8 fail on the old adapter |
| W0c — 10 async tests silently failing | **FIXED** | `pytest tests/ -q` → 1574 passed (was 10 failed / 1539 passed; `pytest-asyncio` was declared but not installed) |
| W1 — NameConstant edits | **FIXED**, one sub-goal **UNVERIFIED** | `pytest tests/test_scanners/test_py314_ast_constant.py -q` → 25 passed; 12 fail on master's code. UNVERIFIED: no test can distinguish the naive swap from the correct one — they are the same program (the extra branch is unreachable). Shipped as deletions. Full reasoning in the ledger. |
| W2 — packages/audit/tests | **FIXED** | `pytest packages/audit/tests/ -q` → 32 passed (was 3 collection errors). Proved with the install *deliberately re-broken*, so the new `pytest.ini` is doing the work |
| W3 — loud CI | **FIXED** | every changed step run in a shell, exit 0; all 7 `continue-on-error` occurrences audited, 4 removed / 3 kept with reasons; one extra mask found and fixed (`ci.yml` self-scan `\|\| true`) |
| W4 — real baseline | **FIXED** | `results/baseline.json` exists with 21/22 passing samples; `quality_gate_check.py ... --results results/` → exit 1, real verdict. Regression path falsified: a synthetic baseline yields `newly_failing: ["T12"]` and the gate reports it |
| W5 — version matrix | **FIXED** (measurement) | 3.11 / 3.12 / 3.13 / 3.14 all: import OK, KNOWN-004 7 findings, TS probe 4 findings, AVB knowns R 100% / P 88%. **Zero divergence.** 3.9 and 3.10 are not installed |

Commits on `fix/py314-blocker`: `279082a`, `0f321ff`, `7a79d28`, `363cfa3`, `d95b62d`.
Full evidence with pasted before/after output: `NIGHT_RUN_LEDGER.md`.

**Two numbers worth noticing.** The repo's committed `results/layer1.json` was from
2026-07-04 and claimed R 47.5% / F1 63.6%. A real run gives **P 73.41% / R 82.70% /
F1 77.78%** — reproducing the CLAUDE.md v0.19.0 headline to within one finding. The
documented metric was right; the file in the repo was another broken-environment artifact.

## 3. NEEDS-HEADY (detail in `DECISIONS.md`)

1. **Layer 1 thresholds contradict each other, and CI will go red on merge.**
   `quality_gates_v2.yaml` demands P≥0.90 / R≥0.85 / F1≥0.87; `benchmark.yml`'s inline gate
   uses 0.72 / 0.80 / 0.75; reality is 0.734 / 0.827 / 0.778. The same layer passes one gate
   and fails the other. This was invisible only because the v2 step was masked. **Recommend:**
   align `quality_gates_v2.yaml` to the inline floors and delete the duplicate — those are the
   numbers CI has actually been enforcing since `1009782`. I changed no threshold.
2. **ASI-04 detects nothing — 0.0% recall, 0 true positives.** Not a threshold problem, a
   coverage hole. ASI-03 is also weak at 37.5%. **Recommend:** treat ASI-04 as a P0A input.
3. **`results/layer2.json` is fabricated** — one target named `test1`, round 150.0s, tool
   version 0.5.0, timestamp `2026-02-04T12:00:00`. It is the only source of both Layer 2
   warnings. **Recommend:** regenerate on a networked machine, or set Layer 2
   `enabled: false`; a missing file reports an honest SKIP, a fake one reports fiction.
4. **Two test roots.** Both work and both now run in CI, but the split is arbitrary.
   **Recommend:** `git mv packages/audit/tests/test_report tests/test_report`. Not done —
   architecture-level.
5. **CI matrix stops at 3.12 while the dev machine runs 3.14.** That is exactly why the
   `ast.NameConstant` removal shipped undetected. **Recommend:** add 3.13 and 3.14.
6. **Dev environment isn't reproducible from the repo** — three separate breakages tonight
   were drift (stale editable install, missing `pytest-asyncio`, missing tree-sitter extras),
   and each degraded a *number* rather than erroring. **Recommend:** a documented setup step.

## 4. What I would do first tomorrow

**Re-run the blind audit at `0f321ff` and diff it against the original.** It is cheap, and it
is the only thing standing between you and knowing whether the roadmap's premise — "we miss
real defects in large TypeScript codebases" — is true or was an artifact. Everything in
`docs/overhaul/` is prioritised off that conclusion, and P0A denoise is the wrong first move
if the tool was simply crashing. Check first whether that codebase contains any `.py` files;
that single fact decides which branch of the headline applies.

Then, in order: settle the Layer 1 threshold contradiction (item 1) so CI has one honest
gate, and look at ASI-04's flat zero (item 2), which is a genuine detection gap that no
amount of denoise work will fix.

## 5. Confirmation

I did NOT push, merge, tag, or publish, and I did not modify any oracle, fixture, or
threshold.

*(Scope notes, stated plainly: I committed five times to `fix/py314-blocker`, as instructed.
I regenerated and committed `results/layer1.json` and added `results/baseline.json` — both
are generated result files, not ground truth, and W4 asked for the latter. I edited
`tests/benchmark/agent-vuln-bench/harness/adapters/agent_audit_adapter.py` and
`tests/benchmark/scripts/save_avb_baseline.py`, which are harness code, not oracle, dataset,
or fixture files; both changes make failures louder and detection stricter, never looser.
Outside the repo I fixed the editable install, installed `pytest-asyncio` and Python 3.13,
and built throwaway venvs under `/tmp` — all listed and reversible in `DECISIONS.md`.
Nothing under `eval/` was touched.)*
