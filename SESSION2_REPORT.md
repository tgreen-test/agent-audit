# SESSION 2 REPORT — blind audit closed, eval harness live

Target confidentiality: referred to throughout as "the audit target". No target path,
repo name, or source excerpt appears in this file, in the ledger, or in any commit.

## 1. Is the 0/6 real?

**Yes. It is real, and it is a capability gap, not an environment artifact.** The harness
reproduces the blind run exactly at `1009782` and returns the identical `recall_hit 0,
noise 1156, total 1176` at all three commits — v0.19.2, master, and HEAD with last night's
fixes — so nothing done in session 1 moved recall by a single defect.

The prior in the brief was right and my session-1 framing was too generous to the tool.
The `ast.NameConstant` crash is real but was never in play: it fires only on Python ≥3.12,
the blind run was on 3.11.14, and a crashed scan yields no findings rather than 1176. I
measured both sides on the audit target — `1009782` on 3.14 dies with zero bytes of output;
HEAD on 3.14 completes and returns **the same 0/6 and the same 1156/1176** as 3.11. The
environmental story explains the AVB 0.0% and the 3.14 crash. It does not explain this.

**Which binary the blind run used:** the 0.19.2 working tree, not the stale 0.18.2. The
frozen JSON's own `version` field reads `0.19.2`, and the run manifest records
`pip install -e .` into a *fresh venv* at commit `1009782` with an unmodified tree. That
also explains why session 1's broken system-interpreter `.pth` was irrelevant here — and
0.18.2 could not have been used even by accident, since that `.pth` pointed at a
non-existent directory and the distribution was not importable by anything.

## 2. Three-commit table

Identical target, identical dependency set, interpreter pinned to the blind run's 3.11.14.
The venv holds only third-party dependencies — never agent-audit — so the tool source is
selected purely by `PYTHONPATH`, and each run asserts which `agent_audit/__init__.py` it
imported before scanning.

| commit | isolates | recall | noise | total |
|---|---|---|---|---|
| `1009782` (v0.19.2) | the blind-audit baseline | **0/6** | **1156** | **1176** |
| `78e1337` (master) | + the SkillScanner merge | **0/6** | **1156** | **1176** |
| `2e80a59` (HEAD) | + session 1's fixes | **0/6** | **1156** | **1176** |
| `1009782` on Python 3.14 | the crash, on the real target | — | — | **scan died, 0 bytes** |
| `2e80a59` on Python 3.14 | session 1's fix, on the real target | **0/6** | **1156** | **1176** |

Not one number moves. The tool emitted findings inside the ground-truth files for only
2 of 6 defects (1 and 2 findings); both were off-anchor and asserted an unrelated
vulnerability class. Four defects have zero findings anywhere in their files.

## 3. Harness status: **reproduces the baseline exactly**

```
$ ./run_eval.sh --frozen
freeze verified: FREEZE.sha256 OK
{"recall_hit":0,"recall_total":6,"noise":1156,"total":1176,"commit":"1009782","python":"3.11.14"}
```

Required `recall_hit 0 / noise 1156 / total 1176`. Reproduced. Stronger than required: a
live re-scan at `1009782` reproduces the frozen artifact as a **multiset of all 1176
findings** with an identical summary block — only directory-walk order differs.

Two discrepancies appeared first and were fixed in the harness, not in the numbers.
(i) Recall came out **1/6** because the mechanism sweep matched keywords inside quoted
target source; fixed by scoring on what the tool *asserts* (title+description), with the
snippet corroborating only at a ground-truth anchor. (ii) Noise came out **1157/19**
because the SQL predicate was case-insensitive and could not distinguish the prose
`cannot insert into "${x}"` from `INSERT INTO "${x}"`. Both are in the ledger.

Two deviations from the brief, both forced by the guard hook and logged: the harness sits
in a sibling directory rather than inside the guarded eval directory, and the six defects
live in `score.py` behind a drift assertion rather than in a standalone ground-truth file.
I did not rename files or switch tools to get around the hook.

## 4. NEEDS-HEADY

1. **Layer 1 gate contradiction — forensics changed the recommendation from "probably" to
   "clearly".** `quality_gates_v2.yaml` has never been modified since `a65b341`
   (2026-02-04), and its step has carried `continue-on-error: true` from creation until
   last night — **it has never been able to fail a build**. The 0.90/0.85/0.87 floors were
   **never met, not even on the day they were written**: the `layer1.json` committed in
   that same commit reads R 0.4746 against an 0.85 floor. → **Align the v2 config to the
   inline 0.72/0.80/0.75 floors and delete the duplicate.** That is not loosening a
   standard; it was never a standard.
2. **ASI-04 — I was wrong in session 1; it does not need a new rule.** Of the 7 labels:
   **2** are detections that exist but are unreachable by directory scan (the MCP fixture
   emits AGENT-029/030/032 when scanned as a file and only AGENT-004 when scanned via its
   directory — a real bug, and Layer 1 scans by directory); **3** are rule-ID attribution
   mismatches where one detection is counted as both an FP and an FN at the same line; **2**
   are genuine gaps, one of which is a `.sh` file the scanner never reads (`scanned_files:
   0`). → Fix the directory-scan bug first; bring the labeling question to a decision.
3. **`results/layer2.json` is a v0.5.2 placeholder**, created at `a65b341` and never
   regenerated — same story as items 1 and 2. → Regenerate, or set Layer 2
   `enabled: false`; a missing file reports an honest SKIP.
4. **Guard hook blocks its own deliverable.** `eval/` matches `audit-eval/`, and
   `ground_truth` blocks *creating* the file the plan asks for. → Scope the guard to the
   repo and to modification-not-creation. Note it inspects Write but not Bash-authored
   writes, which is a gap if it is meant to be load-bearing.
5. **The noise metric is an upper bound on any commit but the frozen one.** It encodes the
   outcome of a one-time manual bucketing, so a genuinely new high-value finding scores as
   noise. Fine for P0A; must be re-adjudicated before P1, which is supposed to add
   detections. → Budget that adjudication inside P1.

**Correction to session 1.** I wrote that `results/layer1.json` was "a broken-environment
artifact". It was not: git shows it byte-identical to the file committed at `a65b341` on
2026-02-04 and untouched for six months. Regenerating it was still right and the refreshed
numbers stand; the cause I asserted was wrong.

## 5. Go / no-go for P0A

**GO** — and the go is now better founded than it was, because the premise is confirmed
rather than assumed. The roadmap is pointed at a real gap: 98.3% noise is real, 0/6 recall
is real, and neither is an artifact of a broken machine.

**The one measurement P0A is judged on:**

```
./run_eval.sh --commit <sha>   →   noise < 118   (i.e. <10% of 1176), with recall_hit still 0
```

Two conditions on that number, both from the plan and both now mechanically checkable:
recall must stay **0/6** (P0A adds no detection; if recall moves, the change exceeded
denoise scope and needs separate review), and AVB recall must not fall — session 1 left
that at R 100.0% / P 88.0% on knowns via
`python3 -m "agent-vuln-bench.harness.run_eval" --tool agent-audit --dataset knowns`.

One sequencing note: **settle NEEDS-HEADY item 1 before P0A lands**, not after. P0A's
acceptance is a threshold judgement, and it cannot be accepted against two different
definitions of pass.

## 6. Confirmation

I did NOT push, merge, tag, or publish, and I did not modify any oracle, fixture, or
threshold.

*(Scope notes: two commits to `fix/py314-blocker`, both documentation and `.gitignore` —
no scanner, rule, gate, label, or fixture was touched this session. The harness and all
its outputs live outside the repository and are gitignored defensively. The frozen
evaluation artifacts were read only, and their SHA-256 freeze verified before and after.
A leak check for eight target-identifying strings across the whole repo returns clean.)*
