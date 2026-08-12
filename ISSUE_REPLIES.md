# Issue replies — final text, ready to paste

**Nothing here has been posted.** The night guard blocks `gh` writes and that is the correct
setting for an unattended run. Each section below is the complete comment body; copy from
the blockquote.

Measured at `bea9901` on `fix/py314-blocker`, agent-audit 0.20.0 (unreleased), CPython
3.14.3. Every before/after in these replies was re-run this session, not quoted from an
earlier one.

| # | action | state after |
|---|---|---|
| 10 | reply, **close as fixed** | closed |
| 8 | reply, **leave open** | open — 2 of 4 fixed |
| 12 | reply, **close as won't-fix / documented limitation** | closed |
| 11 | reply, **leave open** — see § 4 for why I changed the recommendation | open |
| 5 | reply, label, **leave open** | open — `enhancement`, `needs-design`, `blocked-on-prompt-extraction` |

---

## 1. Issue #10 — AGENT-041 flags agent `.execute()` as SQL injection

**Action: post the reply, then close.** Fixed in `9b366fc`, ships in v0.20.0.

> Fixed. Your two files at HEAD now produce two AGENT-041 findings instead of three —
> `target_agent.execute(task)` is gone, and both of the true positives survive:
>
> ```
> BEFORE (0.19.2, your report)
>   AGENT-041  tp_control.py  BLOCK  1.0   cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
>   AGENT-041  tp_control.py  BLOCK  1.0   cursor.execute(query)          # SQL built upstream
>   AGENT-041  fp_case.py     BLOCK  1.0   return target_agent.execute(task)
>
> AFTER (bea9901, v0.20.0)
>   total findings: 2
>   AGENT-041  tp_control.py:7   BLOCK  1.0   cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
>   AGENT-041  tp_control.py:14  BLOCK  1.0   cursor.execute(query)
> ```
>
> Your root-cause analysis was exact, including the line numbers. The fix is option (a) from
> my last reply — the receiver heuristic — built so that it fails in the safe direction:
> `_check_sql_tainted_param` now requires **positive evidence** that the receiver is a
> database handle, from either
>
> * **the name**, matched per underscore-separated token, so `db_conn`, `cur`, and
>   `self.session` qualify and `target_agent` does not; or
> * **an assignment in the same file** that gives it one — `cur = conn.cursor()`,
>   `with sqlite3.connect(...) as h`, `create_engine(url)`.
>
> Positive evidence rather than an exclusion list, so a receiver we do not recognise produces
> silence rather than a BLOCK-tier accusation. An incomplete vocabulary costs us a detection
> instead of handing you a confident wrong one, and there is no list of agent-framework names
> to keep current — which would have been the wrong shape, since the next framework to ship
> an `.execute()` is not on any list I could write today.
>
> **What this does and does not cover, measured rather than asserted.** The receiver
> requirement applies only where the SQL is *not* visible at the call site. Both cases, at
> HEAD:
>
> ```
> zz.execute(f"SELECT * FROM users WHERE name = '{name}'")   ->  AGENT-041 BLOCK 1.0   (still fires)
> zz.execute(query)                                          ->  nothing
> cursor.execute(query)                                      ->  AGENT-041 BLOCK 1.0
> ```
>
> So if you have a database cursor under a name we do not recognise, you still get the
> finding whenever the SQL string is at the call site, and you now get **nothing** when the
> query was built elsewhere. That is a real loss of coverage and it is the price of not
> guessing. If you hit it, the fastest fix on your side is a recognisable name; tell me the
> name and I will add the token, because the vocabulary is the part that should grow from
> reports rather than from my imagination.
>
> Pinned by `tests/test_agent041_receiver.py` — 25 tests, both directions, including your
> `fp_case.py` shape and the upstream-SQL case (KNOWN-008) that a blunter fix would have
> taken with it.
>
> One thing worth saying plainly: **our benchmark did not move at all.** It contains no
> `.execute()` on a non-database receiver, so it could not have caught this and cannot show
> the fix. Your report is the measurement. That gap is now written down in
> `CAPABILITY_BOUNDARIES.md` § 6 rather than left for the next person to discover.
>
> Thanks for the precision of the report — the line numbers and the paired control file are
> what made this a same-day diagnosis.

---

## 2. Issue #8 — test files at CRITICAL, and config-derived values treated as user input

**Action: post the reply, leave open.** Two of four claims fixed, one downgraded, one
improved. Retitle to what is left if you want the tracker to be accurate: *"No provenance
model: configuration and internal computation are treated as untrusted input"*.

> v0.20.0 moves two more of your four problems. Re-running all of your shapes at HEAD:
>
> | your problem | at 0.18.2 | at v0.20.0 |
> |---|---|---|
> | 1. test files reported CRITICAL | AGENT-017/001/020/053, up to ×30 | **fixed** — everything under `tests/` lands in tier `SUPPRESSED`, hidden by default |
> | 2a. credentials in an f-string | AGENT-004 WARN 0.70 | **fixed** — no finding |
> | 2b. config-derived SQL | AGENT-041 BLOCK 1.00 | **unchanged** |
> | 3. internal template variables | AGENT-010 BLOCK 1.00 | **downgraded** to INFO 0.50 |
> | 4. fixed container argv | AGENT-047 HIGH ×13 | **improved** — one AGENT-047 WARN 0.80 |
>
> **Problem 2, the credential half — fixed.** `f"email={email}\npassword={password}"` no
> longer produces AGENT-004. Your suggestion was the right one and is what we implemented: a
> hardcoded credential is by definition a literal in the source, and the "value" our regex
> captured was `{password}\n`, which is nothing but interpolation. The rule is narrower than
> "the line contains an f-string" — `f"sk-{suffix}"` keeps a real prefix and is still
> analysed.
>
> **Problem 3 — downgraded, not fixed.** Your `<skill_system>` case drops from BLOCK/1.00 to
> INFO/0.50. We can now tell "an inbound parameter goes straight into the prompt" from "a
> local that some computation produced", which is one step of distance and about as far as a
> single-file pass can honestly see. We did **not** suppress it, because `skills_list` really
> is derived from `config`, which really is a parameter. The thing that makes it safe is that
> `config` is *configuration* — and that is a provenance model, not a heuristic. Suppressing
> would have required a hardcoded list of parameter names that are "probably config", which
> is the kind of fix that works on your file and fails on the next one.
>
> **Problem 4 — improved, and the measurement is the part worth sharing.** Your line no
> longer carries a taint flow claiming `cmd` reached a shell from user input, and no longer
> reports *Tool Function Without Input Validation* about a function that is not a tool. But
> it still produces a finding. Chasing it down:
>
> ```
> gate the subprocess taint sink   ->  AGENT-034 drops 0.85 -> 0.65, still fires
> gate subprocess_expanded         ->  still fires, now via eval_exec_expanded
> gate eval_exec_expanded          ->  still fires, now AGENT-047 at 0.80
> ```
>
> **Three separate producers report that one line, and silencing two of them relocated the
> finding to the third.** That is our defect, not a disagreement with you: nothing in the
> codebase can currently answer "which producers claim this line", which makes every report
> like yours harder to act on than it should be. It is written up and scheduled.
>
> **Problem 2's SQL half — not fixed.** `conn.execute(f'CREATE DATABASE "{db_name}"')` still
> fires at BLOCK/1.00. `db_name` comes from `urlparse(config_url)` and `config_url` is a
> parameter, so the analyser sees a parameter reaching a SQL sink and has no notion of
> "configuration" as a provenance distinct from "user input". Fixing that properly is a taint
> **source taxonomy**, not another heuristic, and it is scoped as its own release rather than
> a rider on this one.
>
> One caveat on problem 1 that I would rather state than let you find: a suppressed finding
> still carries `severity: critical` in the JSON. `severity` is the rule's intrinsic rating
> and `tier` is the confidence-adjusted verdict — `tier` is what the CLI, the exit code and
> the risk score use. If you were consuming `severity` directly, say so and I will treat that
> as its own issue, because it is a reporting-surface problem rather than a false-positive
> one.
>
> **Leaving this open.** Two of four is not a closure, and the two that remain are the tool's
> largest measured false-positive source. `tests/test_issue8_provenance_shapes.py` asserts the
> *remaining* defects, so each of those tests fails the day it is fixed — the issue cannot
> quietly stop being true.
>
> Your report is the most useful this project has had, and it caused something bigger than
> the fixes: `CAPABILITY_BOUNDARIES.md`, new in v0.20.0, states the limits behind problems
> 2–4 up front rather than leaving them to be discovered at a 70% false-positive rate on
> someone's real codebase. You were right, and about the parts that are still broken you are
> still right.

---

## 3. Issue #12 — TS AST path silently disabled by a stale language-module API

**Action: post the reply, close as won't-fix / documented limitation.**

> Closing as won't-fix with the measurement attached, because your diagnosis led somewhere
> neither of us expected.
>
> Your finding is exact: `tree_sitter_typescript` exposes only `language_tsx()` and
> `language_typescript()`, and `_init_tree_sitter` recognises neither. It covers **one of
> three** independent reasons that path is dead:
>
> 1. the missing accessor — yours;
> 2. `tree_sitter.Parser(lang)` is handed the raw `language()` return, which on grammar
>    packages ≥0.23 is a `PyCapsule` and needs `tree_sitter.Language(...)` around it. The
>    `TypeError` is caught and logged at **debug**, so **no language activates — not
>    TypeScript, not JavaScript, not Python**;
> 3. `tree-sitter = "^0.22.0"` resolves to `<0.23`, and a 0.22 core cannot consume a 0.23
>    grammar capsule at all. **The declared extra is inoperable regardless of the parser
>    code** — `poetry install -E tree-sitter` gets you 0.22.3.
>
> ```
> core 0.22.3  ->  a.py=False  a.js=False  a.ts=False  a.tsx=False
> core 0.23.2  ->  a.py=True   a.js=True   a.ts=True   a.tsx=True
> core 0.26.0  ->  a.py=True   a.js=True   a.ts=True   a.tsx=True
> ```
>
> I fixed all three on a scratch build, the AST path came alive for all four languages, and
> then I measured it against the regex path on the same corpus:
>
> ```
> agreed on by both paths ................................. 20
> present with regex, ABSENT with tree-sitter .............. 2
>     AGENT-034  cp.execSync(cmd) inside a vercel-ai tool()
>     AGENT-034  cp.execSync(req.body.cmd) in an express handler
> present with tree-sitter only ............................ 8
>     six of them the exact false positives the regex path
>     was fixed to suppress — the .fetch-on-a-receiver family,
>     and template strings that are not system prompts
> ```
>
> and the suite, same environment either side:
>
> ```
> tree-sitter absent ................ 8 failed, 1787 passed
> tree-sitter present, path dead .... 8 failed, 1788 passed
> tree-sitter present, path LIVE .... 50 failed, 1746 passed    <- 42 regressions
> ```
>
> Every regression is a finding disappearing (`assert 0 >= 1`): 40 in the TypeScript scanner,
> 2 in the Python parser.
>
> So the line in your own "user impact" section turns out to be the conclusion rather than
> the caveat: **the regex path is not a fallback, it is the implementation**, and the AST path
> is a worse second one. A path that parses but detects less is worse than one that never ran,
> because it looks like an upgrade. I reverted the fix — `git diff` on `treesitter_parser.py`
> is empty.
>
> What landed instead:
>
> * `CAPABILITY_BOUNDARIES.md` § 4 documents TypeScript/JavaScript as **regex-level, by
>   decision**, with this measurement as the reason. It is stated in the same table as
>   "shell scripts are not read at all", so nobody has to infer it.
> * `tests/test_treesitter_differential.py` and `tests/differential_corpus/` stand between the
>   next person and the same mistake. It **skips loudly rather than passing** when the AST
>   path is inactive, because an empty differential over a dead path looks exactly like
>   agreement — which is the failure mode that produced this issue in the first place.
>
> **Your point 2 — that the downgrade is silent — is the part I still want to fix**, and it
> is the part I have no good answer for. A per-file `logger.warning` is noise; a startup
> banner is noise on every run; and saying nothing is what we do now. If you have an opinion
> on where that belongs, open a follow-up and I will take it — it is a better issue than this
> one turned out to be.
>
> Thanks for this. It is unusual to get a bug report whose accepted resolution is "you found
> a third of a bigger problem and the answer is to document the whole thing".

---

## 4. Issue #11 — CI should install the `tree-sitter` extra so Codecov measures the AST paths

**Action: post the reply, leave open.** *This reverses the recommendation in
`ISSUE_TRIAGE.md`, which said "blocked, and its premise is gone".*

**Why leave it open rather than close it.** The issue's *stated* remedy is dead — installing
the extra would raise the coverage of branches that still do not execute, which is worse than
under-reporting because the number would look like progress. But the issue's *subject* is
live: there is dead code in the tree with a misleading coverage story, and v0.20.0 has just
decided it stays dead. That makes deleting the branches a real scheduled task
(`NEXT_ROUND.md`, "actionable without a decision"), and this issue is its natural tracker.
Closing it would discard the tracker and leave the work with no issue attached; a reader
arriving from #12 would find the follow-up missing. So: open, with the remedy replaced.

> Holding this one, and the reason has changed since you filed it.
>
> See #12: with the extra installed, `is_tree_sitter_available` is `False` for **every**
> language, not just TypeScript. So installing it in CI would raise the reported coverage of
> branches that still do not execute — the number would move while the behaviour did not.
> That is a worse state than under-reporting, and it is the same defect class as an
> advertised rule with no producer, relocated into a coverage report.
>
> Separately, the install would not do what the issue expects even setting coverage aside:
> `-E tree-sitter` resolves `tree-sitter 0.22.3` (the pin is `^0.22.0` → `<0.23`), which
> cannot load a 0.23 grammar capsule at all.
>
> v0.20.0 documents the TS/JS path as regex-level and keeps the AST path unreached
> deliberately, with the differential that justifies it (#12). Given that, the coherent
> follow-up is to **remove the dead AST branches** rather than to measure them — at which
> point this issue resolves by the code disappearing and the coverage question stops existing.
>
> I am leaving this open as the tracker for that removal rather than closing it, because the
> thing you were pointing at is real: there is code in the tree whose coverage story is
> misleading. The remedy changed; the observation did not. If you would rather I close it and
> open a fresh "delete the dead tree-sitter branches" issue, say so — I do not have a strong
> preference between the two, only against losing it.

---

## 5. Issue #5 — integrate system-prompt defence scanning (prompt-defense-audit)

**Action: post the reply, add labels `enhancement`, `needs-design`,
`blocked-on-prompt-extraction`, leave open.**

> Thanks for this, and for the 1,646-prompt dataset — the defence-posture numbers are the
> most interesting part of the proposal and I would like to point at them regardless of
> whether the integration happens.
>
> Deferring, with a specific reason rather than a general one.
>
> **Step 1 of your proposal — "agent-audit finds system prompt strings in agent code" — is
> the part agent-audit cannot currently do well.** It matches prompt-shaped string literals
> within a single file, with no import following and no type resolution. Issue #8 is an open
> report of exactly that going wrong: a `<skill_system>` template built entirely from internal
> metadata, reported as a user-input injection vector at BLOCK/1.00. At HEAD it is down to
> INFO/0.50, which is better and is still not "we know what this string is". A defence score
> computed over a mis-extracted prompt is a confident number about the wrong text — and
> v0.20.0 is specifically a release about withdrawing confident numbers that were not earned,
> so adding a new scoring surface in it would be self-defeating.
>
> There is also a packaging cost worth being honest about: agent-audit is pure Python with
> seven runtime wheels, and this would put a Node runtime in the install path for every user,
> for a feature some of them want.
>
> **The sequencing I would want:** prompt *extraction* as a first-class capability, with its
> own fixtures and its own measured precision, and only then scoring on top of it. That
> ordering is not bureaucracy — it is the difference between a number that means something
> and a number that has a decimal point.
>
> Where it sits: v0.21.0 is scoped to a single capability (detecting code whose identity is
> not fixed in the source — runtime package/code acquisition), chosen because our own corpus
> already contains labelled fixtures for it and our test suite is committed red until it
> exists. Prompt extraction is not in that release. It is a plausible v0.22.0 if someone
> wants to build it.
>
> **If you would like to contribute, the extraction half is the valuable half and is where I
> would take a PR** — a fixture set of real agent code with the system prompt(s) marked, plus
> a precision measurement against it, would be worth more to this project than the scoring
> integration and would unblock it. Leaving this open as the tracking issue.

---

## What was not done

* **No `gh` write of any kind** — no comment, no label, no close, no reopen. The guard blocks
  them, and drafts-for-a-human is the right output for an unattended run.
* **No code change made to render an issue closeable.** #10 closes because the reporter's own
  files stopped producing the finding; #8 stays open because two of its four claims still
  reproduce.
* **No verdict changed without re-running the case.** Every before/after above was measured
  this session at `bea9901`.
