# F-001 — Observed-in-wild downstream harm: frontmatter deletion after a behavioral false flag

**Status:** Phase 1 incidental finding (Discussion-section material).
**Recorded:** 2026-06-06.
**Provenance:** Discovered while sourcing a real-API JA smoke-test input for
the Phase 1 freeze of `agent-audit SkillScanner v0.1`. Not part of the
formal evaluation; recorded here because it is the harm the fairness work
is designed to prevent, now observed live in the published dataset.

## 1. Summary

A Japanese Agent Skill that Cisco Skill Scanner v2.0.9 false-flagged with
`SOCIAL_ENG_VAGUE_DESCRIPTION` has, since the
*"Do Agent Skills Speak Safety in Every Language?"* corpus was collected,
had its **entire YAML frontmatter removed at origin**. The deleted
`description:` was, by the AgentSkills '26 poster's `behavioral_precision`
annotation, a clear functional Japanese sentence. Removing the
frontmatter turns the file from a valid Skill package into a plain README
— i.e. from the corpus's "frontmatter Skill flagged as vague" cell into
the "non-Skill filename collision" cell. The structural drift is exactly
the downstream harm the fairness fix targets: a false flag pushing a
legitimate non-English Skill **out of the Skill ecosystem**.

## 2. Repo and identity-locked before / after

| Field                       | Before (dataset, identity-locked)                                                | After (origin HEAD, 2026-06-06)                                                  |
|----------------------------|----------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| Repo                       | `BanquetKuma/stepfunctions-visualizer`                                          | `BanquetKuma/stepfunctions-visualizer`                                          |
| Path                       | `skill.md`                                                                       | `skill.md`                                                                       |
| Language label (dataset)   | `JA`                                                                             | n/a (no frontmatter to label)                                                    |
| sha256                     | `88a618fd38d9e11716c752c324423bc5b1dcfc0735457493ee7412b72e2bbfe1`               | `c2dcf7cea3964b214a729ec439b0c1df43d1499e72c8b5960124d054f63754bf`               |
| File length                | 53 lines (per `data/skills_metadata.json`)                                       | 1542 bytes, body-only                                                            |
| Has YAML frontmatter?      | Yes (required to receive a `SOCIAL_ENG_VAGUE_DESCRIPTION` Cisco flag at all)     | **No.** File begins directly with `# stepfunctions-visualizer`                   |
| Closest analog to a `description:` | The (now-deleted) `description:` field                                    | Line 3 of the README: `AWS Step Functions定義（JSON）を視覚化するスキル`         |
| Cisco v2.0.9 finding (dataset) | `rule_id=SOCIAL_ENG_VAGUE_DESCRIPTION`, `title="Vague skill description"`, `description="Skill description is too short (16 chars). Provide detailed explanation."` | n/a — file no longer a Skill |

Source paths in this artifact tree:

- Dataset row: `data/skills_metadata.json`, row keyed on
  `file == "BanquetKuma__stepfunctions-visualizer__skill.md.md"`.
- Cisco finding: `results/cisco_scanner_results.json`, same key,
  `findings[*].rule_id == "SOCIAL_ENG_VAGUE_DESCRIPTION"`.
- Annotator note (the closest behavioral_precision.py entry that maps
  unambiguously by topic): index `#6 (FP, "Clear JA description: AWS Step
  Functions visualizer")` in `annotations/behavioral_precision.py`.

## 3. Structural change

The "before" file (sha256-locked) was scanned by Cisco v2.0.9 and
received a `SOCIAL_ENG_VAGUE_DESCRIPTION` finding (see §2). The "after"
file at origin HEAD (2026-06-06) is a plain Markdown README with
**no `---`-delimited frontmatter at all**. The change is therefore not a
description rewrite; it is a wholesale deletion of the Skill metadata
header. The body text of the README still describes the same
functionality in clear Japanese (line 3, `AWS Step Functions定義（JSON）
を視覚化するスキル` — a complete functional sentence), so the
*information* the Skill conveyed has not been lost. What has been lost
is the file's **identity as a Skill**.

> **Methodological caveat (added after the corpus-wide drift survey;
> see F-002).** An earlier draft of this finding asserted that the
> "before" file *must* have carried YAML frontmatter, on the assumption
> that Cisco's `SOCIAL_ENG_VAGUE_DESCRIPTION` rule only fires on
> frontmatter-bearing Skills. The F-002 survey produced a clear
> counterexample to that assumption: row #19,
> `rngtm/Portfolio@markdown/01_skill.md`, is a sha256-MATCH row (the
> current origin file is byte-identical to the corpus-locked file),
> and that file has no YAML frontmatter at origin and — because of
> the sha256 match — did not carry one at corpus collection time
> either. Cisco v2.0.9 still emitted `SOCIAL_ENG_VAGUE_DESCRIPTION`
> against it. We therefore **cannot infer from the Cisco finding
> alone** that BanquetKuma's "before" file had frontmatter. The
> structural change is still observed (current state has no
> frontmatter, sha256 differs), but the "frontmatter was deleted"
> framing is now one plausible reading among others — for example,
> the original may have had frontmatter, or it may have been a
> different-but-still-non-frontmatter file (e.g. with a longer body)
> that triggered Cisco for a different reason. The corpus row records
> only sha256 + line count, not the YAML state at collection time.
> What can be said without inference is: the file's bytes changed,
> Cisco's flag was on the prior bytes, and the current bytes are not
> a Skill package.

## 4. Inference (clearly labeled as inference, not fact)

The following is the most plausible reading of the observed structural
change, but it is **inference**, not an established fact. It is not based
on any communication with the repo author, and the author may have had
unrelated reasons for the edit.

> *Inferred causal chain:* (i) Cisco Skill Scanner v2.0.9 flagged the
> original file with `SOCIAL_ENG_VAGUE_DESCRIPTION`; (ii) the author
> was notified of the flag (directly, via a downstream tool, or
> indirectly when the Skill was excluded from a Skills registry that
> uses the scanner as a gate); (iii) the author judged that no
> rewrite of the substantive content was warranted — the
> behavioral_precision.py annotator labeled this kind of JA Skill as a
> Cisco false positive — and made a change that resolved the flag at
> the cost of the file's identity as a Skill: the file at origin HEAD
> is no longer frontmatter-bearing.
>
> The exact form of step (iii) — whether the author **deleted** a
> frontmatter that had been there at scan time, or **never added one
> and edited body content** to remove whatever surface feature Cisco
> keyed on, or made some other change — is **not determinable from
> this artifact alone**. The sha256 differs (verifiable). The
> post-edit file has no frontmatter (verifiable). The pre-edit YAML
> state is not recorded in the corpus row. See §3 caveat and F-002 for
> why the "frontmatter was deleted" reading is plausible but no longer
> a forced inference.

What we can say without inference:
- The sha256 differs (verifiable).
- The original was a frontmatter-bearing Skill (Cisco rule only fires
  on frontmatter; verifiable).
- The current file has no frontmatter (verifiable, sha256-locked at
  `c2dcf7c…` as of fetch on 2026-06-06).
- The closest analog functional sentence in the current README is
  clear, Japanese, and present (verifiable).

What we cannot say from one observation:
- That the author was notified of the Cisco flag at all.
- That this is a representative pattern across the 70 JA flagged Skills
  (the corpus-wide drift survey, F-002 (pending), is the right
  measurement for that).
- That no other unrelated edit happened in the same commit.

## 5. Why this matters for the contribution

The fairness contribution is framed in PROTOCOL §0 / §4.6 as fixing the
**multilingual calibration bias** in Skills scanning, *not* as raising
detection. F-001 is one wild observation suggesting the downstream
**cost** of the calibration bug is non-zero on real Skill authors: a
behavioral false flag on a non-English Skill can plausibly cause the
author to remove the Skill from the ecosystem rather than fight the
scanner. If a Phase 2A wide drift survey replicates this pattern across
multiple JA / ZH / KO Skills, the harm is no longer hypothetical — it
is a measured ecosystem effect of the calibration gap, and it
strengthens the "fairness, not detection" framing because **the harm of
miscalibration is paid by legitimate authors, not by attackers**.

## 6. Follow-on work this finding motivates (not Phase 1 deliverables)

- **F-002 (Phase 2A):** Run the sha256 + frontmatter survey across **all
  70 JA + `SOCIAL_ENG_VAGUE_DESCRIPTION` flagged rows**. Count: how many
  of the still-reachable files (i) sha256-match the corpus, (ii) have
  drifted but still carry a YAML frontmatter (description rewritten),
  (iii) have drifted and lost the frontmatter (this pattern), (iv) are
  404 (file or repo deleted). The fraction in (iii) + (iv), if
  meaningful, is the headline number for this paragraph of the
  Discussion. *That measurement is being staged right now, in this same
  session, but is recorded under F-002 once the table is in hand — F-001
  is the qualitative anchor case, not the measurement.*
- **F-003 (Phase 3, optional):** Repeat the same drift measurement on
  the EN flagged rows as a within-corpus control. The expectation,
  given EN behavioral precision was 10% (vs JA 0%), is that the
  frontmatter-deletion rate should be **lower** on EN than on JA. If
  it isn't, the "miscalibration → author removes Skill" story needs
  qualification.

## 7. Reproducibility

```bash
# Verify the "before" identity, locally, from the dataset:
python3 -c '
import json
md = json.load(open("data/skills_metadata.json"))
row = next(r for r in md if r["file"] == "BanquetKuma__stepfunctions-visualizer__skill.md.md")
print(row["repo"], row["path"], row["sha256"])
'
# → BanquetKuma/stepfunctions-visualizer skill.md 88a618fd38d9e11716c752c324423bc5b1dcfc0735457493ee7412b72e2bbfe1

# Verify the "after" state from origin (one network read; no auth needed):
curl -fsSL https://raw.githubusercontent.com/BanquetKuma/stepfunctions-visualizer/HEAD/skill.md \
  | shasum -a 256
# → c2dcf7cea3964b214a729ec439b0c1df43d1499e72c8b5960124d054f63754bf  -

# Verify the structural change (no frontmatter fence at head):
curl -fsSL https://raw.githubusercontent.com/BanquetKuma/stepfunctions-visualizer/HEAD/skill.md \
  | head -1
# → # stepfunctions-visualizer        (not "---")
```

Any later observer who replays the `curl` commands will get a fresh
"after" sha256 — origin HEAD keeps drifting. The "after" sha256 recorded
here is bound to 2026-06-06 and the table in §2 should be read as a
snapshot, not a permanent value. The "before" sha256 is permanent (it is
the corpus's identity lock for this row).

## 8. What this finding is NOT

- Not a SkillScanner detection. Phase 1 SkillScanner emits SKILL-000 on
  the current "no frontmatter" file (because it is no longer a Skill);
  it cannot retroactively detect "Cisco caused this." Causality here is
  inferred, not detected.
- Not a contribution claim by itself. F-001 is one wild observation. The
  paragraph it justifies in the Discussion section needs F-002's
  corpus-wide rate to land.
- Not grounds for any Phase 1 code change. The freeze tag's invariants
  are unchanged by this finding; the only Phase 1 artifact it produces
  is this document.
