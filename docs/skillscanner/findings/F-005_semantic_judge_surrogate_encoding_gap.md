# F-005 — `SemanticJudge._cache_key` raises on descriptions containing lone surrogates (Phase 2B fix candidate)

**Status:** Recorded for Phase 2B. **Not fixed now.** The cache-key
function lives inside the frozen Phase 1 module
(`agent_audit/analysis/skill_description_judge.py`); editing it would
break the `skillscanner-core-frozen` tag's `JUDGE_PROMPT_V2` sha256
fence + the v2 → `claude-sonnet-4-6` schema pin in `finding.schema.json`.
Any fix must come with a `JUDGE_PROMPT_VERSION` bump or a separate
input-sanitization layer outside the frozen surface.
**Recorded:** 2026-06-07.
**Cross-references:** F-004 (judge robustness on *well-formed*
inputs); this finding is the boundary case where the well-formed
assumption breaks.

---

## 1. The defect (observed, narrow, code-localized)

`SemanticJudge.judge` calls `_cache_key(description, language)` before
any LLM invocation. `_cache_key` is:

```python
def _cache_key(description: str, language: str) -> str:
    """Stable cache key per Judge Freeze:
       sha256(description) | language | model | prompt_version."""
    h = hashlib.sha256(description.encode("utf-8")).hexdigest()
    return f"{h}|{language}|{JUDGE_MODEL}|{JUDGE_PROMPT_VERSION}"
```

(source: `agent_audit/analysis/skill_description_judge.py:152-155`,
frozen at tag `skillscanner-core-frozen`, commit
`05c3f98855413091f6671bb0acbd4281a59ae37d`.)

The `description.encode("utf-8")` call **has no `errors=` argument**,
so it raises `UnicodeEncodeError: 'utf-8' codec can't encode
characters in position 0-1: surrogates not allowed` on any input that
contains an unpaired surrogate (code points `U+D800`-`U+DFFF`). These
appear in real Skills via two routes observed in this evaluation:

- a text editor / build tool that emitted UTF-16 surrogates without
  re-encoding;
- a Markdown post-processor that round-tripped through a non-strict
  decode (e.g. `errors='replace'` paired with `errors='surrogatepass'`
  somewhere upstream).

## 2. The observation that produced this finding

| Field | Value |
|---|---|
| Affected row | `EN_0137` in the 2A.0/2A.1 snapshot |
| `manifest.json` `match_class` | DRIFT |
| Behaviour during 2A.1 SkillScanner run | `SkillScanner` propagated the exception as a warning (`SkillScanner error on …/SKILL.md: 'utf-8' codec can't encode characters in position 0-1: surrogates not allowed`) and emitted no finding for that row. |
| Behaviour during the silent-verdict disambiguation run | The same row was about to be re-judged; the exception fired again on the first sha256 call, halting the loop until I excluded the row. |
| Net effect on the evaluation | One row produces no `SKILL-010` finding **and** no SKILL-000 / no-op record; it simply vanishes from the SkillScanner output stream. |

## 3. Surface area at the boundary

The exception fires before any API call, so there is no spend / cost
risk. But the silent-vanish behaviour is worse than `cannot_judge`
because:

1. It leaves the row absent from `skillscanner_results.json` rather
   than present-with-a-known-fallback-verdict. Downstream stratification
   (which expects every in-snapshot row to have *some* SkillScanner
   record) has to special-case the missing key.
2. It is a different failure mode from `cannot_judge` (which is the
   documented "judge abstained" path) — annotators reading the
   intermediate artifacts could mistake a vanished row for a
   `cannot_judge` row, conflating two distinct things.
3. The error message reaches the user only via a runtime warning,
   not as a structured finding metadata field. There is no
   `judge_backend: input_error` enum value in the schema today.

## 4. Why this is NOT fixed now

The cache-key function is part of the frozen v2 surface. Touching it
implies either:

- bumping `JUDGE_PROMPT_VERSION` (which the prompt text didn't change
  → semantically wrong);
- updating the recorded `JUDGE_PROMPT_V2_SHA256` in the test fence (which
  would silently let the prompt drift if someone edited prompt + hash
  together later);
- moving the sanitization out of the frozen module into a wrapper at
  the SkillScanner boundary (the right Phase 2B answer; left to Phase
  2B because it changes the public surface area of SkillScanner).

The freeze tag's invariants explicitly include
`test_prompt_text_sha256_locked` passing; any edit to
`skill_description_judge.py` triggers that check and is therefore
part of a deliberate Phase 2B release, not an in-band fix.

## 5. Proposed Phase 2B fix (drop-in, two-option)

### Option A (minimal, in-module) — bump to v3

Edit `_cache_key`:

```python
h = hashlib.sha256(description.encode("utf-8", errors="surrogateescape")).hexdigest()
```

…paired with `JUDGE_PROMPT_VERSION = "v3"` and the matching
`JUDGE_PROMPT_V3_SHA256` recorded in `tests/test_skill_scanner.py`.
Pro: smallest patch. Con: bumps the prompt version without changing
prompt text, which is misleading for any future reader following the
version-tag trail.

### Option B (cleaner, at the boundary) — sanitize in SkillScanner

Sanitize `description` once at the SkillScanner boundary, before it
reaches `_cache_key`, using a stable transform:

```python
# in skill_scanner.py, before invoking the judge
description_clean = (description.encode("utf-8", errors="replace")
                                .decode("utf-8", errors="replace"))
```

Pro: prompt-version-stable; treats the surrogate input as a
*scanner*-side input-sanitization concern, which is where it
belongs. Con: changes the SkillScanner public surface (the description
fed to the judge is the cleaned form, which the prompt-version freeze
implicitly already assumes is well-formed UTF-8 — so this is
clarifying behavior the frozen module had relied on without enforcing).

Both options should also add a structured emit for the failure
mode: e.g., a `SKILL-011 input_error` rule_id (INFO tier, no judge
call, metadata field carries the original encode-error message),
so the row is *present* in the SkillScanner output stream with a
known reason instead of vanishing.

## 6. What this finding does NOT say

- Not a Phase 1 freeze invariant violation. The freeze's invariants
  hold; the row that triggers this bug is *outside the well-formed
  input domain* the freeze tests cover. The smoke test, the 28-test
  unit suite, and the schema all pass.
- Not common. 1 / 198 rows in the 2A.1 snapshot. Probably uncommon
  in any reasonably-curated corpus. But "uncommon" is not "zero" and
  the silent-vanish behaviour is worse than the rate suggests.
- Not a judge prompt or judge model problem. The model never sees the
  input; the exception fires inside the SDK-prep layer of the cache
  key.

## 7. Reproducibility (one-liner)

```python
# Reproduces the exact error, no API call, no network:
import hashlib
description = '\udce4\udcb8'        # a lone-surrogate pair from a real row
hashlib.sha256(description.encode("utf-8")).hexdigest()
# → UnicodeEncodeError: 'utf-8' codec can't encode characters in position 0-1:
#   surrogates not allowed
```

The row that produced this finding (`EN_0137`) is in
`eval/snapshot/private/bytes/EN/0137.md` (gitignored). Anyone with
the snapshot can reproduce; anyone without can construct the same
condition synthetically as above.

## 8. Tracking

- **Recorded:** 2026-06-07.
- **Frozen-tag impact:** none until a Phase 2B fix lands; the freeze
  invariants are unaffected by this finding.
- **Phase 2B owner:** TBD.
- **Suggested resolution path:** Option B + structured `SKILL-011
  input_error` emit + a unit test fixture under
  `tests/fixtures/skills/lone_surrogate/SKILL.md`.
