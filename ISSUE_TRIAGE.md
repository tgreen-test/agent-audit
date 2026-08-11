# Issue triage for v0.20.0 — reproduced at HEAD, not assumed

**Measured at:** `ec0a29b` on `fix/py314-blocker`, CPython 3.14.3
**Scope:** the five open issues on `HeadyZhang/agent-audit` as of this run — #5, #8, #10, #11, #12

Every issue below was re-run from the reporter's own case at HEAD. **Nothing is marked fixed
on the strength of a related change having landed.** Closing an issue that is not actually
fixed is worse than leaving it open: a reporter who comes back and finds the bug still there
stops believing every other closure, including the correct ones.

**The replies are drafted, not posted.** The night guard blocks `gh issue comment` and that is
the right setting for an unattended run.

---

## Summary

| # | title | verdict | can it close? |
|---|---|---|---|
| 10 | AGENT-041 flags agent `.execute()` as SQL injection | **NOT FIXED** — reproduces exactly | no |
| 8 | test files CRITICAL + config-derived values as user input | **PARTIALLY FIXED** — claim 1 fixed, claims 2–4 live | no |
| 12 | TS AST path silently disabled | **ANSWERED, won't fix** — with a measurement that supersedes the proposed fix | yes, as won't-fix |
| 11 | CI should install the `tree-sitter` extra | **BLOCKED** on #12's outcome, and its premise is gone | no |
| 5 | integrate system-prompt defence scanning | **DEFERRED** — out of scope, reason below | no, label and leave |

Two of five could close. One of those two closes as "won't fix, documented", which is a real
answer and not a dodge. **Three stay open, and two of those three are the tool's largest
measured false-positive sources.**

---

## #10 — AGENT-041 flags agent `.execute()` as SQL injection

**Verdict: NOT FIXED.** The brief's expectation — that RUN3's SQL-sink requirement would
cover this — does not hold. The finding reproduces at full confidence.

### Reproduction

The reporter's two files, verbatim:

```bash
mkdir -p /tmp/issue10 && cd /tmp/issue10
# fp_case.py and tp_control.py exactly as in the issue body
cd packages/audit && python3 -m agent_audit scan /tmp/issue10 --format json
```

### Before — the reporter's output on 0.19.2

```
AGENT-041  @ tp_control.py:10  tier=BLOCK  conf=1.0  snippet='cursor.execute(f"SELECT * FROM users WHERE name = \'{name}\'")'
AGENT-041  @ fp_case.py:11     tier=BLOCK  conf=1.0  snippet='return target_agent.execute(task)'
```

### After — HEAD, this run

```
total findings: 2
AGENT-041  tp_control.py:8  tier=BLOCK  conf=1.0  sev=critical
AGENT-041  fp_case.py:8     tier=BLOCK  conf=1.0  sev=critical
```

Identical: two findings, both BLOCK, both confidence 1.0. The line numbers differ only
because the repro files here have no leading blank line.

### Why it still fires

`_check_sql_tainted_param` in `packages/audit/agent_audit/scanners/python_scanner.py:3597`
is unchanged. The receiver-side gate is still a bare method-name test at line 3610:

```python
if simple_name not in ('execute', 'executemany', 'executescript'):
    return None
```

and the `sink_type` is still hard-coded to `'sql_execution'` at line 3629. The reporter's
root-cause analysis is correct in every particular, including the line numbers.

### The honest framing

This is not a missing special case. It is section 4 of `CAPABILITY_BOUNDARIES.md`: a
**syntactic signal used as a proxy for a semantic property**. `.execute` and "is a DB cursor"
coincide for DB-API objects and diverge for everything else, and agent frameworks are full of
everything else. Resolving it properly needs receiver-type information the analyser does not
have; resolving it approximately means another receiver heuristic like the ones already
carried for `.eval` and `.fetch`.

Both are legitimate. Neither has been done, so the issue stays open.

### Draft reply

> Reproduced at HEAD (`ec0a29b`, unreleased v0.20.0) with your two files unchanged — still two
> AGENT-041 findings, both `BLOCK`, both confidence 1.0, on `target_agent.execute(task)` and
> `cursor.execute(f"...")` alike. Your root-cause analysis is exact, including the line
> numbers: `_check_sql_tainted_param` (python_scanner.py:3597) gates only on the method name
> at line 3610 and hard-codes `sink_type: 'sql_execution'` at line 3629.
>
> Leaving this open rather than folding it into the v0.20.0 release notes, because it is not
> fixed and I would rather it stay visible. We have now written down the general shape it
> belongs to — `CAPABILITY_BOUNDARIES.md` §1, "no type resolution" — since `.eval` on a Redis
> client and `.fetch` on a request handler were the same bug with different names, and each
> got its own receiver heuristic. A fourth one-off is not obviously the right answer.
>
> The two candidate fixes: (a) another receiver heuristic — require the receiver to look like
> a cursor/connection/session, by assignment origin within the file; (b) require a SQL
> statement to be visible in the argument, which is what the f-string branch already does and
> would cost the "SQL built upstream" case the check was added for (KNOWN-008, v0.15.1).
> Thoughts welcome on which you would rather have — (a) keeps recall, (b) is principled.

---

## #8 — test files flagged CRITICAL, and config-derived values treated as user input

**Verdict: PARTIALLY FIXED.** The issue makes four separate claims. One is fixed. Three are
live. Assessed separately, and the fixed one does not carry the others.

### Reproduction

The reporter's five shapes, reconstructed from the issue body into a tree mirroring the
described layout (`tests/`, `persistence/`, `gateway/auth/`, `agents/lead_agent/`,
`aio_sandbox/`):

```bash
cd packages/audit && python3 -m agent_audit scan /tmp/issue8
```

### Claim 1 — test files reported at CRITICAL: **FIXED**

**Before**, 0.18.2, as reported:

```
AGENT-017 (CRITICAL) tests/test_deferred_tool_promotion_real_llm.py:68 — eval(expression, ...)
AGENT-001 (CRITICAL) same file, same line
AGENT-020 (HIGH) x30  tests/test_remote_sandbox_backend.py:35 — RemoteSandboxBackend("http://provisioner:8002")
AGENT-053 (CRITICAL) x12 tests/conftest.py:53 — importlib.util.spec_from_file_location(...)
```

**After**, HEAD:

```
⬛ SUPPRESSED — Tier 4 (hidden, use --verbose to show) — 4 findings

📊 Summary:
  BLOCK: 2 | WARN: 2 | INFO: 0 | SUPPRESSED: 4
```

and with suppressed findings shown:

```
AGENT-053  tests/conftest.py:7  sev=critical  tier=SUPPRESSED  conf=0.25
AGENT-053  tests/conftest.py:8  sev=critical  tier=SUPPRESSED  conf=0.25
AGENT-053  tests/conftest.py:9  sev=critical  tier=SUPPRESSED  conf=0.25
AGENT-001  tests/test_deferred_tool_promotion_real_llm.py:9  sev=critical  tier=SUPPRESSED  conf=0.2
```

Every finding in `tests/` is now tier `SUPPRESSED` and hidden by default. AGENT-017 and
AGENT-020 do not fire at all. The context classifier the reporter identified as present but
unapplied is applied.

One caveat worth stating in the reply rather than glossing: the `severity` field still reads
`critical`. Severity is the rule's intrinsic rating; `tier` is the confidence-adjusted verdict
and is what the terminal, the exit code and the risk score use. A JSON consumer keying on
`severity` alone will still see `critical` — that is a reporting-surface question, not a
false-positive one.

### Claim 2 — config-derived values treated as user input: **LIVE**

```
AGENT-041  persistence/engine.py:10  sev=critical  tier=BLOCK  conf=1.0
    conn.execute(f'CREATE DATABASE "{db_name}"')

AGENT-004  gateway/auth/credential_file.py:9  sev=high  tier=WARN  conf=0.7
    handle.write(f"email={email}\npass**************}\n")
```

Both unchanged in substance. `db_name` comes from `urlparse(config_url)` and is still treated
as user input; the AGENT-004 match is still an f-string containing the word `password` whose
values are function parameters, not literals. This is a **taint-source classification**
question — the tool has no notion of "configuration" as a provenance distinct from "user
input" — and it is genuinely open.

### Claim 3 — internal template variables flagged as prompt injection: **LIVE**

```
AGENT-010  agents/lead_agent/prompt.py:10  sev=critical  tier=BLOCK  conf=1.0
    return f"""<skill_system>
```

`skills_list` is built by `get_enabled_skills_for_config()` two lines above and is still
reported as a system-prompt injection vector at BLOCK. Same root cause as claim 2: no
provenance distinction between internal computation and untrusted input.

### Claim 4 — subprocess with a fixed container-runtime argv: **CHANGED, still fires**

```
AGENT-034  aio_sandbox/local_backend.py:8  sev=high  tier=WARN  conf=0.65
    return subprocess.run(cmd, capture_output=True, check=False)
```

The reporter saw `AGENT-047 (HIGH) x13`. At HEAD the same line reports **AGENT-034 at WARN**,
one finding, confidence 0.65. Better — it is no longer a HIGH-severity block-tier result — but
the underlying complaint stands: `cmd` is `["docker", "run", ...]`, a fixed argv with no shell,
and the tool still flags it. Improved, not fixed.

### Verdict

One of four claims fixed. **Partial credit is not a closure**, and the fixed claim is the
cheapest of the four. Issue stays open, retitled in the reply to what is actually left.

### Draft reply

> Thank you for this — it is the most useful bug report the project has had, and it drove
> several of the changes in v0.20.0. Re-running all five of your shapes at HEAD, one of your
> four problems is fixed and three are not, so I am leaving this open rather than closing it
> on the one.
>
> **Problem 1 (test files at CRITICAL) — fixed.** Everything under `tests/` now lands in tier
> `SUPPRESSED` and is hidden by default; AGENT-017 and AGENT-020 no longer fire on your
> `eval()` and `http://provisioner:8002` cases at all. Summary line for your five files at
> HEAD: `BLOCK: 2 | WARN: 2 | INFO: 0 | SUPPRESSED: 4`. One caveat: the `severity` field on a
> suppressed finding still reads `critical` — `tier` is the confidence-adjusted verdict and is
> what the CLI, the exit code and the risk score use, but a JSON consumer keying on `severity`
> alone will still see the old value. If that is how you were consuming it, say so and I will
> treat it as its own issue.
>
> **Problems 2 and 3 (config-derived values; internal template variables) — not fixed.**
> `conn.execute(f'CREATE DATABASE "{db_name}"')` is still AGENT-041 BLOCK at confidence 1.0,
> and the `skills_list` prompt is still AGENT-010 BLOCK at 1.0. These are the same underlying
> gap: the analyser has no provenance model that distinguishes configuration and internal
> computation from untrusted input. That is a real piece of work, not a threshold tweak, and I
> would rather it stay open with the right label than be closed with the easy one.
>
> **Problem 4 (container-runtime subprocess) — improved, not fixed.** Your line now reports
> AGENT-034 at WARN, confidence 0.65, once — rather than AGENT-047 HIGH ×13. A fixed argv with
> no shell still should not fire at all.
>
> One thing your report caused that is worth pointing at: `CAPABILITY_BOUNDARIES.md`, new in
> v0.20.0, states the limits behind problems 2–4 up front rather than leaving them to be
> discovered at 70% FP on a real codebase. Your scan is the kind this project was not honest
> enough about.

---

## #12 — TS AST path silently disabled by a stale language-module API

**Verdict: ANSWERED — won't fix, documented, with the measurement attached.** Can close.

The diagnosis is correct and incomplete, and acting on it as written would have made
detection worse.

### What the issue reports, confirmed

```
>>> import tree_sitter_typescript as mod
>>> [x for x in dir(mod) if not x.startswith('_')]
['language_tsx', 'language_typescript']
```

Exactly so, and `_init_tree_sitter` recognises neither. Verified at HEAD.

### What the issue does not report

With the `tree-sitter` extra installed as declared, **no language activates — not TypeScript,
not JavaScript, not Python**:

```
_TREE_SITTER_AVAILABLE = True
  a.py   lang=python      tree_sitter_active=False
  a.js   lang=javascript  tree_sitter_active=False
  a.ts   lang=typescript  tree_sitter_active=False
  a.tsx  lang=typescript  tree_sitter_active=False
```

Two further defects:

1. `tree_sitter.Parser(lang)` is handed the raw `language()` return, which on grammar
   packages ≥0.23 is a `PyCapsule`. `Parser(lang)` raises `TypeError`; the `except` at line
   203 logs it at **debug**, so Python and JavaScript die as silently as TypeScript.
2. `pyproject.toml` pins `tree-sitter = "^0.22.0"` → `<0.23`, against grammars pinned
   `^0.23.0`. A 0.22 core cannot load a 0.23 capsule at all. **The declared extra is
   inoperable regardless of the parser code.**

```
===== tree-sitter core 0.22.3 =====  a.py=False a.js=False a.ts=False a.tsx=False
===== tree-sitter core 0.23.2 =====  a.py=True  a.js=True  a.ts=True  a.tsx=True
===== tree-sitter core 0.26.0 =====  a.py=True  a.js=True  a.ts=True  a.tsx=True
```

### What happens when all three are fixed

Applied on a scratch build; the AST path came alive for all four languages. Then:

```
present with regex, ABSENT with tree-sitter: 2
    AGENT-034  ts/framework_boundaries.ts:16   cp.execSync(cmd) inside a vercel-ai tool()
    AGENT-034  ts/framework_boundaries.ts:33   cp.execSync(req.body.cmd) in an express handler
present with tree-sitter only: 8
    six of them the exact false positives the regex path was fixed to suppress
    (.fetch on a receiver; template strings that are not system prompts)
agreed on by both paths: 20
```

and the suite, same environment either side:

```
tree-sitter absent:              8 failed, 1787 passed
tree-sitter present, path dead:  8 failed, 1788 passed
tree-sitter present, path LIVE: 50 failed, 1746 passed     <- 42 regressions
```

Every regression is a finding disappearing (`assert 0 >= 1`), across 40 TypeScript scanner
tests and 2 Python parser tests.

### Verdict

The issue's own framing — "user impact: none end-to-end, the regex fallback implements the
same detection surface" — turns out to be the answer rather than the caveat. The regex path
is not a fallback; **it is the implementation**, and the AST path is a worse second one. The
fix was written, applied, measured and reverted; `git diff` on `treesitter_parser.py` is
empty.

Landed instead: `tests/differential_corpus/` and `tests/test_treesitter_differential.py`,
which fail if anyone wires the AST path without re-running the comparison, and skip loudly
rather than passing when it is inactive.

### Draft reply

> Closing as won't-fix, with the measurement, because your diagnosis led somewhere neither of
> us expected.
>
> Your finding is exact: `tree_sitter_typescript` exposes only `language_tsx()` and
> `language_typescript()`, and `_init_tree_sitter` recognises neither. Two things it turns out
> not to cover:
>
> 1. **No language activates**, not just TypeScript. `Parser(lang)` is handed the raw
>    `language()` return, which is a `PyCapsule` on grammars ≥0.23 and needs
>    `tree_sitter.Language(...)` around it. The `TypeError` is caught and logged at debug, so
>    Python and JavaScript are dead exactly as silently.
> 2. **The declared extra cannot work at any code revision.** `tree-sitter = "^0.22.0"`
>    resolves to `<0.23`, and a 0.22 core cannot consume a 0.23 grammar capsule. `poetry
>    install -E tree-sitter` gets you `tree-sitter 0.22.3`. Version matrix: 0.22.3 → nothing
>    activates; 0.23.2 / 0.24 / 0.25 / 0.26 → all four languages activate.
>
> I fixed all three and measured. The AST path loses two true positives (`child_process.execSync`
> inside a vercel-ai `tool()` and inside an express handler) and adds eight findings, six of
> which are the false positives the regex path was fixed to suppress — the `.fetch`-on-a-receiver
> family and template strings that are not system prompts. The suite went 8 → 50 failures in the
> same environment: 42 regressions, 40 in the TypeScript scanner and 2 in the Python parser, every
> one of them a finding disappearing.
>
> So the line in your own "user impact" section is the conclusion: the regex path is not a
> fallback, it is the implementation. I reverted the fix. TypeScript/JavaScript analysis is now
> documented as regex-level in `CAPABILITY_BOUNDARIES.md` §4, and
> `tests/test_treesitter_differential.py` plus `tests/differential_corpus/` are in the tree so
> that anyone wiring the AST path has to re-run the comparison first — it skips loudly rather
> than passing when the path is inactive, because an empty differential over a dead path looks
> exactly like agreement.
>
> Your point 2 — that the downgrade is silent — is the part I would still like to fix, and it
> needs a home that is not a per-file `logger.warning`. Open a follow-up if you want to shape it.

---

## #11 — CI should install the `tree-sitter` extra so Codecov measures the AST paths

**Verdict: BLOCKED, and its premise is now gone.** Stays open.

The issue is well-reasoned on its own terms: the AST branches show as uncovered because
`poetry install` omits the extra. But installing it, given #12's measurement, would:

* raise the reported coverage of code that **does not execute** — with the extra installed and
  the shipping parser, `is_tree_sitter_available` is `False` for every language, so the AST
  branches remain unexecuted and the number would move while the behaviour does not. That is
  the same defect class as an advertised rule with no producer, relocated into a coverage
  report; and
* not even install what the issue expects — `-E tree-sitter` resolves `tree-sitter 0.22.3`,
  which cannot load a 0.23 grammar.

If the AST path stays unreached, which is this run's decision, the honest fix is to delete the
dead branches rather than to cover them. That is a larger change than v0.20.0 should carry.

### Draft reply

> Holding this one, and the reason changed since you filed it. See #12: with the extra
> installed, `is_tree_sitter_available` is `False` for **every** language, not just TypeScript
> — so installing it in CI would raise the reported coverage of branches that still do not
> execute. That is a worse state than under-reporting, because the number would look like
> progress.
>
> Separately, `-E tree-sitter` currently resolves `tree-sitter 0.22.3` (the pin is
> `^0.22.0` → `<0.23`), which cannot load a 0.23 grammar capsule at all, so the install would
> not do what the issue expects even setting coverage aside.
>
> v0.20.0 documents the TS/JS path as regex-level and keeps the AST path unreached
> deliberately. Given that, the coherent follow-up is probably to remove the dead AST branches
> rather than to measure them — at which point this issue resolves by the code disappearing.
> Leaving it open as the placeholder for that decision.

---

## #5 — integrate system-prompt defence scanning (prompt-defense-audit)

**Verdict: DEFERRED — out of scope for v0.20.0 and for the tool's current shape.** Stays open,
labelled.

Not a bug and not a wrong idea. The reason it is deferred is specific rather than a shrug:

1. **It requires a capability the tool does not have.** Step 1 of the proposal is "agent-audit
   finds system prompt strings in agent code". agent-audit finds *string literals that a
   prompt-shaped rule matches*, single-file, with no import following and no type resolution —
   see `CAPABILITY_BOUNDARIES.md` §1. Extracting *the* system prompt of an agent, reliably
   enough to score it out of 100, is a different problem from matching a template literal, and
   issue #8's problem 3 is a live example of the tool getting exactly that distinction wrong.
   A defence-posture score built on a mis-extracted prompt is a confident number about the
   wrong text.
2. **It adds a Node/npm runtime dependency** to a pure-Python package whose current install is
   seven wheels. That is a real cost to every user for a feature some want.
3. **v0.20.0 is a correction release.** Its content is six withdrawn rules, a retracted metrics
   claim, and four reachability fixes. Adding a scoring surface in the same release is exactly
   how a number nobody has validated gets published — which is the failure this release exists
   to correct.

The integration is plausible once (1) has an answer. The honest sequencing is: prompt
extraction as its own capability, with its own fixtures and its own precision measurement,
before anything scores what it extracts.

**Suggested labels:** `enhancement`, `needs-design`, `blocked-on-prompt-extraction`.

### Draft reply

> Thanks for this, and for the 1,646-prompt dataset — the defence-posture numbers are the most
> interesting part and I would like to point at them regardless of whether the integration
> happens.
>
> Deferring, with a specific reason rather than a general one. Step 1 of your proposal —
> "agent-audit finds system prompt strings in agent code" — is the part agent-audit cannot
> currently do well. It matches prompt-shaped string literals within a single file, with no
> import following and no type resolution, and #8 is an open report of it flagging a
> `<skill_system>` template built from internal metadata as a user-input injection vector. A
> defence score computed over a mis-extracted prompt is a confident number about the wrong
> text, and v0.20.0 is specifically a release about withdrawing confident numbers that were not
> earned.
>
> There is also a packaging cost — agent-audit is pure Python with seven runtime wheels, and
> this would put a Node runtime in the path for everyone.
>
> The sequencing I would want: prompt **extraction** as a first-class capability with its own
> fixtures and its own measured precision, then scoring on top of it. If you would like to
> contribute, the extraction half is the valuable half and is where I would take a PR. Leaving
> this open as the tracking issue for that.

---

## What I did not do

* **No `gh` write of any kind.** No comment, no label, no close, no reopen. The guard blocks
  those and the replies above are drafts for a human to send.
* **No code change to make an issue closeable.** #10 and #8 are open because they reproduce,
  not because the fix was out of budget.
* **No partial closure.** #8 has one of four claims fixed; that is recorded in the reply and
  the issue stays open.
