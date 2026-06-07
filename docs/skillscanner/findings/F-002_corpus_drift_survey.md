# F-002 — Corpus drift survey: JA + `SOCIAL_ENG_VAGUE_DESCRIPTION` rows

**Status:** Phase 1 incidental finding (Discussion-section material).
**Recorded:** 2026-06-06.
**Provenance:** Conducted during Phase 1 freeze sample selection for the
v2 judge smoke test, when the F-001 anchor case (BanquetKuma) had
drifted and we needed to know whether *any* sha256-locked JA flagged row
was still usable for an identity-locked real-API smoke test.
**Scope:** Strictly observational. Counts are facts. Causal readings are
labeled inference and bounded.

## 1. Method

- **Population.** Every row of
  `paper/skillsworkshop/skills-crosslingual-security/results/cisco_scanner_results.json`
  with `language == "JA"` and at least one finding whose
  `rule_id == "SOCIAL_ENG_VAGUE_DESCRIPTION"`. N = 70.
- **Fetch.** One HTTP GET per row to
  `https://raw.githubusercontent.com/{repo}/HEAD/{path}` with a 0.3 s
  inter-request pause and `User-Agent: skillscanner-drift-survey/0.1`.
  No authentication, no body modification, no redirect chasing beyond
  urllib's default. Raw bytes captured.
- **Identity check.** sha256 of fetched bytes compared to the
  `sha256` column of the corresponding row in
  `data/skills_metadata.json` (the corpus's identity lock).
- **Frontmatter check.** A row is recorded as "has YAML frontmatter at
  origin" iff the fetched bytes, decoded as UTF-8 (errors=replace),
  have `---` as the first non-empty line **and** at least one
  subsequent line equal to `---`. Anything else is recorded as "no
  frontmatter". Errored fetches are recorded as `has_fm = None`.
- **Date.** All 70 fetches completed on **2026-06-06**.
- **Output.** Per-row results cached at `/tmp/drift_survey_results.json`
  during the freeze run; the aggregates below are derived from that
  file and are the only numbers used in this document.

## 2. Observed counts (facts)

| Bucket | n | % of 70 |
|---|---:|---:|
| **Total rows surveyed** | 70 | 100% |
| sha256 MATCH (file byte-identical to corpus identity lock) | **2** | 3% |
| sha256 MISMATCH (file fetched, but bytes differ) | 58 | 83% |
| Error (file or repo unreachable at fetch time) | 10 | 14% |
| YAML frontmatter present at origin (today) | 16 | 23% |
| YAML frontmatter absent at origin (today) | 44 | 63% |
| Frontmatter state not determined (fetch error) | 10 | 14% |

Crossing match-state with frontmatter-state:

| | has FM today | no FM today | FM not determined | row total |
|---|---:|---:|---:|---:|
| **sha256 MATCH** | 1 | 1 | 0 | 2 |
| **sha256 MISMATCH** | 15 | 43 | 0 | 58 |
| **ERROR** | 0 | 0 | 10 | 10 |
| **column total** | 16 | 44 | 10 | 70 |

## 3. The two sha256-MATCH rows (full identity)

These are the only two rows whose origin bytes today are identical to
the bytes Cisco v2.0.9 scanned at corpus collection time. Both are
recorded here in full because they are individually load-bearing for
both F-001's softening and the Phase 1 freeze sample-selection process.

| # | repo | path | has FM today | corpus sha256 |
|---|---|---|---|---|
| 19 | `rngtm/Portfolio` | `markdown/01_skill.md` | **No** | `…` (see `data/skills_metadata.json`) |
| 30 | `Mnbee33/Mnbee33.github.io` | `docs/skill.md` | **Yes** | `…` (see `data/skills_metadata.json`) |

Row 19 (`rngtm/Portfolio`) is the **counterexample** that softens
F-001's earlier "Cisco needs frontmatter to fire" claim: this row's
bytes have not changed since corpus collection, the bytes have no
frontmatter, and Cisco v2.0.9 nonetheless emitted
`SOCIAL_ENG_VAGUE_DESCRIPTION` against it. Therefore Cisco's
`SOCIAL_ENG_VAGUE_DESCRIPTION` rule **can** fire on a no-frontmatter
file. F-001 has been edited (see F-001 §3 caveat and §4) to reflect
this.

## 4. The 10 unreachable rows

| # | repo | path | failure mode |
|---|---|---|---|
| 5 | `sc30gsw/claude-code-customes` | `docs/skills/serena-skill.md` | HTTP 404 |
| 15 | `sc30gsw/claude-code-customes` | `docs/skills/okr-skill.md` | HTTP 404 |
| 16 | `wwulfric/peeka` | `gh-pages/ja/ai-skill.md` | HTTP 404 |
| 22 | `takarki/vibecoding` | `DesignSKILL.md` | HTTP 404 |
| 38 | `hackenbacker/job-offers` | `files/old_skill.md` | HTTP 404 |
| 40 | `hackenbacker/job-offers` | `files/future_skill.md` | HTTP 404 |
| 50 | `openclaw/skills` | `skills/sa9saq/persona/SKILL.md` | HTTP 404 |
| 51 | `sc30gsw/claude-code-customes` | `docs/skills/team-builder-skill.md` | HTTP 404 |
| 65 | `kawaken/dotfiles` | `claude/skills/kickoff/SKILL.md` | HTTP 404 |
| 69 | `SekiroResurrection/mod-files` | `Strings/Items/Mibu Balloon of Skill.md` | URL encoding (control char in path) — not retried |

Nine of the ten errors are HTTP 404 (file or repo deleted, or moved
beyond `HEAD` resolution). The tenth (row 69) is a urllib limitation
on the file path, not a real fetch failure — manual fetch with proper
URL encoding would likely succeed but was not performed. **Three of
the four `sc30gsw/claude-code-customes` paths 404**, suggesting that
repo's `docs/skills/` tree has been substantially restructured rather
than that individual files were deleted; one repo / one event, not
three independent author actions.

## 5. The 15 MISMATCH-with-frontmatter rows (still Skills today)

These are rows whose bytes have changed since corpus collection but
which **still carry YAML frontmatter at origin**. They are the
candidates for the "author rewrote the description rather than
remove the metadata" reading — the alternative to the F-001 pattern.

```
 6  majiayu000/claude-skill-registry@skills/data/tech-blog/SKILL.md
29  Pokeyama/portfolio-jekyll@skill.md
32  RyosukeDTomita/myblog@posts/my_skill.md
35  yoshida55/skills@auto-class/skill.md
48  yasuhito/zenn@articles/pai-art-skill.md
49  myuon/harness@skills/list/SKILL.md
52  Hiroshiba/hiho_ai_coding@base/commands/write-skill.md
53  yasuhito/zenn@articles/pai-council-skill.md
54  annenpolka/zenn-articles@articles/debug-mode-skill.md
55  fdshg693/ZENN@articles/use_tavily_skill.md
60  yasuhito/zenn@articles/pai-research-skill.md
61  yasuhito/zenn@articles/pai-prompting-skill.md
63  fairy-pitta/claude-dotfiles@skills/plan-impl/SKILL.md
64  fairy-pitta/claude-dotfiles@skills/codex-plan/SKILL.md
68  infinith4/dev-pm@.claude/skills/commit/SKILL.md
```

Observed: **5 of these 15 rows are from `yasuhito/zenn`** — one repo
contributing five distinct flagged Skills. This is a single-author
cluster, not five independent observations; any inference drawn from
this row population should weight repo-level edits accordingly.

## 6. The 43 MISMATCH-without-frontmatter rows (counts only)

43 rows have changed since corpus collection **and** currently have no
frontmatter at origin. Per the published corpus README,
*"23% of Japanese entries lack YAML frontmatter and may be non-Skill
files (game documentation, portfolio pages) that reuse the SKILL.md
filename"* — i.e. some rows had no frontmatter at corpus collection
time and still don't today. The 43-row count is therefore an
**upper bound** on the population "rows that lost frontmatter between
collection and 2026-06-06". The actual deletion count cannot be
computed from this survey: the corpus does not record the
collection-time YAML state per row, and we declined to extract the
2-MATCH rows' contents on this pass.

Listing of all 43 row identifiers is preserved in
`/tmp/drift_survey_results.json`; not duplicated here.

## 7. Interpretation — what the counts support, and what they don't

**Supported by the counts alone (facts):**

1. The corpus's identity lock is, at the time of this survey, a
   near-total wall against re-using sha256-matched rows for any
   purpose. **2 / 70 = 3 %.**
2. At least one corpus row (`rngtm/Portfolio`, MATCH + no FM)
   demonstrates that Cisco v2.0.9's `SOCIAL_ENG_VAGUE_DESCRIPTION`
   rule can fire on a file without YAML frontmatter. F-001 §3's
   earlier assumption is falsified by this single observation.
3. The `sc30gsw/claude-code-customes` repo accounts for three of ten
   404s; the `yasuhito/zenn` repo accounts for five of fifteen
   MISMATCH-with-FM rows. Per-repo concentration is non-trivial in
   both buckets; the surveyed population is not 70 independent author
   actions.
4. The maximum possible *new* frontmatter-deletions between corpus
   collection and 2026-06-06 is **bounded above by the 43
   MISMATCH-no-FM rows**. The minimum is zero. Without a per-row
   collection-time YAML state, the survey alone cannot place the
   true value inside that band.

**Not supported by the counts alone (would require further work):**

- That a meaningful fraction of those 43 rows are *Cisco-induced*
  frontmatter deletions. The F-001 inference chain — Cisco false flag
  → author notified → author removes frontmatter — is plausible for
  some subset, but the survey gives no causal handle. Resolving this
  would require either (a) per-row collection-time YAML state (not
  in the corpus), or (b) `git log` evidence per repo that the edit
  was timed to Cisco's collection or to a downstream registry
  rejection.
- That JA Skills suffer this kind of drift at a higher rate than EN
  Skills. The poster's recorded EN behavioral precision (10 %) vs JA
  (0 %) predicts that more JA flags are false positives, so if
  authors respond to false positives by mutating files, JA should
  show more drift than EN. **F-003 (proposed, Phase 2A or 3)** is
  the same survey applied to the EN
  `SOCIAL_ENG_VAGUE_DESCRIPTION` rows: a within-corpus control.
  Until F-003 lands, the JA-only number is suggestive at best.

## 8. Effect on Phase 1 freeze sample selection

The intersection of the user's selection rule —
`sha256-MATCH ∩ "Clear JA description" annotator note` — is empty
across the surveyed population:

- The matched subset has 2 rows.
- The `annotations/behavioral_precision.py` annotator notes that
  begin *"Clear JA description: …"* (13 of the 20 indices) cannot be
  mapped to `skill_id` from the published artifacts.
- The one unambiguous mapping that did exist (`#6 → BanquetKuma`) has
  drifted (F-001).
- Of the 2 sha256-MATCH rows: row 19 maps best to annotator note
  `#3 "Not an agent Skill: portfolio website"` — the wrong test
  target; row 30 has no unambiguous annotator mapping.

The Phase 1 freeze therefore used an **out-of-corpus, native-speaker-
vouched** JA sample (see `eval/SMOKE_TEST_v2_freeze.md`). F-002 is the
formal record of why that out-of-corpus route was necessary: the
corpus-locked route is closed by drift.

## 9. Reproducibility

The survey is deterministic given (i) the fetched bytes on a given
date and (ii) the corpus's sha256 column. Anyone re-running on a later
date will see further drift; the MATCH count is monotonically
non-increasing as origin HEAD drifts further. The 2026-06-06 numbers
above are a dated snapshot.

```bash
# Re-derive the survey aggregates from the cached per-row results:
python3 -c '
import json
d = json.load(open("/tmp/drift_survey_results.json"))
m   = sum(1 for r in d if r["match"] is True)
mm  = sum(1 for r in d if r["match"] is False)
err = sum(1 for r in d if r["err"])
fm  = sum(1 for r in d if r["has_fm"] is True)
nfm = sum(1 for r in d if r["has_fm"] is False)
print(dict(total=len(d), match=m, mismatch=mm, err=err, has_fm=fm, no_fm=nfm))
'
```

`/tmp/drift_survey_results.json` is the local cache. It is NOT
committed (the freeze tag does not depend on it); it is reproducible
by running the survey itself from the same fixed input.

## 10. What this finding is NOT

- Not a SkillScanner detection. SkillScanner does not look at corpus
  drift; that's an evaluation-side concern.
- Not a corpus criticism. The poster's published artifact does
  exactly what it says it does (metadata-only, redistribute by
  reference). Drift is a property of the *origin*, not of the corpus.
- Not a Phase 1 deliverable in the strict sense. F-002 became
  necessary only because F-001's anchor case had drifted and the
  Phase 1 smoke test needed sourcing. It is recorded here so the
  Phase 2A evaluation team does not have to re-run the survey to
  re-derive the same negative result.
