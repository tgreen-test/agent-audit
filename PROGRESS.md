# PROGRESS

**Session 10 state: COMPLETE. W44–W47 all done.** Read `RUN9_REPORT.md` first (one page),
then § 6 of it — **six decisions, all yours, ordered, with the first gating three others.**

**Every mechanical gap before v0.20.0 is now closed.** Nothing pushed, merged, tagged or
published.

## Start here

`RUN9_REPORT.md` § 6. Then, in this order:

1. **`EXTERNAL_CLAIMS_CHECKLIST.md`** + `scripts/scan_external_claims.sh` — the release
   blocker, and the kit that turns it from an afternoon into minutes.
2. **`ISSUE_REPLIES.md`** — five complete comment bodies, paste-ready. Nothing posted.
3. **`OUTREACH_CLAIMS.md`** — the three outreach drafts: every number with its command, and
   everything removed with the one condition that restores it.

## What this session did

| W | what |
|---|---|
| W44 | **the fifth rule count, in three drafts rather than two.** 56 → 66; every unsubstantiated figure removed rather than hedged; the guard now covers the drafts once they are tracked |
| W45 | **the external-claims search kit** — 35 patterns, PDF and Office support, a destination checklist. It found a 22nd location of the drifted F1 nobody had catalogued |
| W46 | **five issue replies, final text.** #10 closes as fixed, #12 as won't-fix. One recommendation reversed: #11 stays open |
| W47 | **the full verification sweep**, recorded as release evidence. Four more mechanical corrections found and applied |

## The three things a reader needs

1. **The catalogue of wrong numbers was itself incomplete.** Two sessions catalogued the
   0.778 family by hand under a heading reading *"Every location the affected figures
   appear"*. A script written for a different purpose found a twenty-second location in under
   a second — `docs/COMPETITIVE-COMPARISON.md`, a head-to-head table against Bandit and
   Semgrep by name — and `docs/F1_REPRODUCTION.md` listed that very file among the ones
   already corrected. **A claim about which claims are correct is still a claim, and it
   drifts the same way.** Fixed.

2. **The drafts' problem is not the rule count.** Their whole evidentiary base is one
   18,899-skill scan whose data is not committed, produced by a scanner advertising a count
   that matches no set the project has ever had — and v0.20.0 has since withdrawn six rules
   and gated AGENT-034, so a re-run would not return those numbers. Everything unreproducible
   is removed from the prose and preserved verbatim with its restore condition. What replaced
   it is a 30-second reproduction a reader can run.

3. **The test count drifted, and then drifted again inside the fix for it.** Four surfaces
   said 1,883 where the command produces 1,890 — a gap of exactly seven, being the seven-test
   guard RUN8 added in the same session. Correcting them to 1,890 went stale before this
   session ended, because this session added two more tests. Final: **1,891**. Deliberately
   not guarded; `DECISIONS.md` item 46 says why the obvious guard is a trap and what shape
   would work.

## Current commit

`fix/py314-blocker`.

## Invariants at the end of the run

| invariant | result |
|---|---|
| Layer 1 | **TP 199 / FP 90 / FN 37**, P 0.688581 / R 0.843220 / F1 0.758095 — unchanged; no detection code touched |
| `quality_gate_check.py` | **exit 0** — 0 failures, 0 warnings, **0 skipped** |
| gate provenance | current for this tree: `bea9901`, 0.20.0, `is_this_checkout: true` |
| full suite | **1,891 passed, 1 failed, 4 skipped** (`pytest tests/ packages/audit/tests/`) |
| the one failure | `tests/test_corpus_label_rules.py`, committed red on purpose |
| AVB `knowns` | **R 100.0% / P 88.0% / F1 0.9362** |
| AVB `all` | **R 95.24% / P 86.96% / F1 0.9091** — re-run and **byte-identical on every metric** to the file the gate reads |
| advertised rules | **66**, and the guard now extends to the outreach drafts once tracked |
| built wheel | carries the corrected 66-rule PyPI description; 0 of 103 entries match the leakage exclusion list |
| guard self-test | 11/11 |
| thresholds changed | **none** |
| detection code changed | **none** — the only code edit is `tests/test_published_rule_count.py` |

## Still open

**Yours, and blocking — the full table is `RUN9_REPORT.md` § 6:**

1. **Which external surfaces carry the 98.51%** — `EXTERNAL_CLAIMS_CHECKLIST.md`. Gates 2, 3
   and 6.
2. **`README.md:147`** — "18,899 ClawHub skills at 80% precision". The only metric on an
   in-repo surface with no reproducing command. Commit the data or cut the clause.
3. **The ClawHub scan figures** — re-run at v0.20.0, or republish as a dated v0.1x result
   with the raw output committed. `OUTREACH_CLAIMS.md` § 3.
4. **The malware-campaign section** — a disclosure decision, not a metrics one.
5. **`RELEASE_CHECKLIST.md` steps 6–7** — merge, tag, publish; post the five replies.
6. **Whether the drafts go out at all before 1 closes.**

**Carried, not blocking:** `DECISIONS.md` items 35, 36, 38, 39 rows 2–4, 40 (AVB provenance
stamp — verified current by re-run, still unstamped), 41 (`git mv .agent-audit.yaml.bak`),
43 (a per-line producer view), 46 (test-count guard shape, if ever wanted).
`NEXT_ROUND.md` is v0.21.0 and needs no decision to start.

## Environment

`python` is NOT on PATH — use `python3` (3.14.3). Run the benchmark from `packages/audit`:

```bash
cd packages/audit && python3 ../../tests/benchmark/precision_recall.py --output-json ../../results/layer1.json
python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml --results results/ --layers layer1
```

The `--output-json` matters: without it the results file is not rewritten, and the gate will
refuse the stale one rather than quietly scoring it.

`pdftotext` is **not** installed. `scripts/scan_external_claims.sh` will list PDFs as unread
rather than searching them — `brew install poppler` before running it over a papers
directory, or the most likely carrier of a retracted figure is the one thing it skips.

## Guard-hook friction

Three denials, none bypassed, all the same mechanism as last session: a command is refused
whole when it contains a protected path or a destructive verb, even when the path is only
being read (`grep ... eval/`) or the target is a scratchpad directory (`rm -rf $SCRATCH/x`).
Each was solved by rewriting the command — a fresh scratch directory instead of removing one,
and dropping the protected path from a `grep` path list.

One further denial came from the environment rather than the hook: decoding the base64 payload
quoted in the outreach drafts was refused, correctly, because the string points at a live C2
host. The consequence is recorded rather than worked around — the corrected drafts do not
assert what it decodes to, and `OUTREACH_CLAIMS.md` § 1 says so.
