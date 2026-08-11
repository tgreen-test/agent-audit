# Phase 1 freeze smoke test — v2 judge, 2 samples

**Recorded:** 2026-06-06.
**Scope:** Gating-only. This is the **minimal 2-sample smoke test**
that gates the Phase 1 freeze of `JUDGE_PROMPT_VERSION = "v2"`. It is
**not** a Phase 2A evaluation. It does not produce per-language
precision, recall, Cohen's κ, Wilson CI, Fisher's exact, or any other
number defined in `PROTOCOL.md §4`. Phase 2A is the formal evaluation
(see `PROTOCOL.md §3` for its design).

---

## 1. Frozen judge call (recorded for replay)

| Field | Value |
|---|---|
| Backend | `SemanticJudge` (Claude API, `anthropic 0.107.0`) |
| Model | `claude-sonnet-4-6` |
| `temperature` | `0` |
| `max_tokens` | `300` |
| `JUDGE_PROMPT_VERSION` | `v2` |
| `JUDGE_PROMPT_V2` sha256 | `a40bc2194c409eecdf7af43c884ef1ffc1adea85f655b9c4660550087816e56f` |
| Key handling | sourced inline from `~/.anthropic_key.env` (perm 600); never echoed, printed, cached, written to any project file, or persisted to `/tmp`; `unset` in the shell after the call |
| Date of call | 2026-06-06 |
| Cache state | Process-local SemanticJudge cache empty before each sample (fresh `SemanticJudge()` constructor; cache populated within the run by `(sha256(description), language, JUDGE_MODEL, JUDGE_PROMPT_VERSION)` per `skill_description_judge._cache_key`) |

The frozen constants are anchored in
`agent_audit/analysis/skill_description_judge.py` and verified by
`tests/test_skill_scanner.py::TestJudgeFreeze`. Any drift from the
constants above means the smoke test in this file is **no longer
replayable** and the freeze tag must be re-validated.

---

## 2. JA sample — provenance and ground truth

### 2.1 Provenance

- **Source:** the `description:` field of the `api-design` Skill from
  `atomic-kanta-sasaki/claude-code-general-skills`.
- **Route:** **out-of-corpus.** Not from the
  `HeadyZhang/skills-crosslingual-security` corpus. The out-of-corpus
  route was forced by **corpus drift**: of the 70
  JA + `SOCIAL_ENG_VAGUE_DESCRIPTION` rows in the corpus, only 2 still
  sha256-match origin HEAD (3 %), and neither matched the user's
  selection rule of "sha256-MATCH ∩ annotator note indicates clear
  JA description". The closure of the corpus-locked route is
  documented in `findings/F-002_corpus_drift_survey.md` (the formal
  drift survey for this freeze).
- **Vouched by:** a Japanese native-speaker collaborator. Recorded
  here, in the freeze artifact, as **"a Japanese native-speaker
  collaborator"** — anonymity preserved per the collaborator's
  preference. If the collaborator later opts in to attribution, this
  field is the one to amend.
- **Sample supply path:** the verbatim text was provided by the
  user (in the prompt that authorized this smoke test). It was not
  fetched from origin during the freeze run. No network call was
  made to retrieve this description.

### 2.2 Ground truth

> The ground truth for `verdict = clear` on this sample is **the
> native-speaker collaborator's judgment that the description
> contains a clear functional Japanese sentence**. It is **not**
> the v2 judge's own verdict. Using the judge's own verdict as the
> ground truth it is then evaluated against would be a circular
> ground truth (PLAN §0 constraint #3, the CAIS rejection lesson).
> The smoke test's pass criterion is therefore "the judge's verdict
> agrees with the native speaker's, on this one sample" — a sanity
> check, not a precision measurement.

### 2.3 Verbatim input fed to the frozen judge

`language = "ja"`. The bytes below are the exact `description` string
constructed in the smoke-test script via `\u…` escapes (so nothing
got normalized in transit) and passed as `description` to
`SemanticJudge.judge`:

```
RESTful API の設計とドキュメント生成。
エンドポイント設計、リクエスト/レスポンス定義、OpenAPI仕様出力。
API設計、エンドポイント作成、APIドキュメント生成時に使用。
```

The trailing newline status, whitespace, and full-width punctuation
above are preserved exactly as fed to the judge.

### 2.4 Verdict (verbatim, as returned)

```
verdict: clear
reason : The description clearly states the skill designs RESTful APIs, defines endpoints and request/response structures, and outputs OpenAPI specifications.
```

**Match with native-speaker ground truth: YES.** The judge identified
the description's functional content (API design, endpoint and
request/response definition, OpenAPI output) in language consistent
with the native-speaker collaborator's "clear JA functional
description" assessment.

---

## 3. EN sample — provenance and ground truth

### 3.1 Provenance

- **Source:** the poster's documented EN genuine TP case, recorded in
  `paper/skillsworkshop/skills-crosslingual-security/annotations/behavioral_precision.py`
  as index #18: `"TP, Genuinely vague: description is literally
  'build' with no detail"`.
- **Route:** in-corpus (the poster's annotated EN sample), but the
  literal string `"build"` is short enough that no network fetch was
  needed — the value is the description in full.
- **Ground truth:** the AgentSkills '26 poster's human annotator
  labeled this sample TP (genuinely vague). The judge's verdict is
  evaluated against the poster's TP label, not against itself.

### 3.2 Verbatim input fed to the frozen judge

`language = "en"`. `description = "build"`. No surrounding whitespace.

### 3.3 Verdict (verbatim, as returned)

```
verdict: vague
reason : The description contains only a single placeholder word with no functional sentence describing what the skill does, its inputs, or its outputs.
```

**Match with poster's annotator ground truth: YES.** The judge called
the input vague with rationale consistent with the rubric (no
functional sentence; single placeholder word).

---

## 4. Pass criteria

| Sample | Independent ground truth | Judge verdict | Match? |
|---|---|---|---|
| JA (api-design, out-of-corpus, native-speaker-vouched) | `clear` | `clear` | **YES** |
| EN (`"build"`, poster TP) | `vague` | `vague` | **YES** |

**Smoke test outcome: PASS.**

---

## 5. What the smoke test does NOT establish

- Not per-language precision. n = 1 per language is not a sample;
  it is one example each.
- Not generalization across JA Skills. The JA sample is a single
  out-of-corpus description that the native-speaker collaborator
  considered clearly functional. Other JA descriptions — especially
  the borderline ones that drive cross-lingual precision deltas in
  Phase 2A — were not tested here.
- Not robustness under prompt-injection input, off-language
  contamination, very long descriptions, or other adversarial
  stress. Those are Phase 2A / Phase 3 concerns.
- Not Cisco-comparable. Cisco v2.0.9 was not run here; nothing in
  this file is a head-to-head measurement.

The freeze gates on this smoke test being PASS (the judge is
demonstrably functional on at least one canonical example in each
direction). Anything stronger than "functional on these two samples"
is reserved for Phase 2A.

---

## 6. Replay

```python
# Assumes: anthropic SDK installed (poetry install --extras judge),
#          ANTHROPIC_API_KEY in the env this Python process inherits.
from agent_audit.analysis.skill_description_judge import (
    SemanticJudge, JUDGE_MODEL, JUDGE_PROMPT_VERSION,
)
assert JUDGE_MODEL == "claude-sonnet-4-6"
assert JUDGE_PROMPT_VERSION == "v2"

sj = SemanticJudge()

ja = (
    "RESTful API の設計とドキュメント生成。\n"
    "エンドポイント設計、リクエスト/レスポンス定義、OpenAPI仕様出力。\n"
    "API設計、エンドポイント作成、APIドキュメント生成時に使用。"
)
print(sj.judge(ja, "ja"))           # expect verdict='clear'
print(sj.judge("build", "en"))      # expect verdict='vague'
```

A future replay that returns `cannot_judge` with reason `judge_error`
on either sample indicates an upstream API / billing / SDK issue, not
a judge logic change. A future replay that returns a different
`clear` / `vague` verdict than the table in §4 — assuming the same
model id, the same prompt sha256, and `temperature = 0` — is the
condition under which the freeze tag's pass invariant is in
question. The judge prompt sha256 is the canary; the smoke test is
the live check.
