# F-003 — Cisco Skill Scanner v2.0.9: provenance, current public availability, and a published-artifact defect

**Status:** Phase 2A reproducibility finding (Phase 3 Discussion-section
material).
**Recorded:** 2026-06-07 (initial draft); rewritten same day with
recovered local provenance.
**Scope:** Strictly observational. Public-source probes + local
filesystem inspection only. Observed facts and any reasoning are
labeled separately. **No inference about *why* the public package is
absent.**
**Cross-references:** F-001 (single-Skill author-action observation),
F-002 (corpus-wide drift survey). F-003 is the tool-side counterpart
of F-001 / F-002's data-side findings, plus a defect in the published
reproduction artifact (§3(d)).

---

## 1. Why this finding exists

PROTOCOL §2 locks the Phase 2A before-baseline to *"Cisco Skill Scanner
v2.0.9, unmodified"*. The Phase 2A 2A.1 gate verified — before any
scan — whether that tool can be reconstructed on the evaluation host
today. This finding records what was found.

## 2. The recovered original-run provenance (observed)

The AgentSkills '26 corpus's Cisco scan was produced on **this laptop
on 2026-04-23**, not on a lab server. Both production scripts are
preserved locally:

- `paper/skillsworkshop/skills-experiment/run_cisco_scan.py` (mtime 2026-04-23 09:50)
- `paper/skillsworkshop/skills-experiment/run_cisco_fast.py` (mtime 2026-04-23 10:05)

The `_fast` variant is the one actually used for the batch run. It
imports the scanner module directly (no subprocess, no CLI) and uses
default constructor + `lenient=True`:

```python
sys.path.insert(0, '/opt/homebrew/lib/python3.14/site-packages')
from skill_scanner.core.scanner import SkillScanner
…
scanner = SkillScanner()
result  = scanner.scan_skill(tmp_dir, lenient=True)
```

The corresponding installed Python package is still present on this
host:

| Field | Value (observed) |
|---|---|
| `importlib.metadata.metadata('cisco-ai-skill-scanner')[Name]`    | `cisco-ai-skill-scanner` |
| `importlib.metadata.metadata('cisco-ai-skill-scanner')[Version]` | `2.0.9` |
| `importlib.metadata.metadata('cisco-ai-skill-scanner')[Author]`  | `Cisco` |
| `importlib.metadata.metadata('cisco-ai-skill-scanner')[License]` | `Apache-2.0` |
| Module path                                                       | `/opt/homebrew/lib/python3.14/site-packages/skill_scanner/__init__.py` |
| `skill_scanner.__version__`                                       | `2.0.9` |
| `SkillScanner.__init__` signature                                 | `(analyzers=None, use_virustotal=False, virustotal_api_key=None, virustotal_upload_files=False, policy=None)` |
| `SkillScanner.scan_skill` signature                               | `(self, skill_directory, *, lenient=False, skill_file=None) -> ScanResult` |
| Console scripts installed by the wheel                            | `skill-scanner`, `skill-scanner-api`, `skill-scanner-pre-commit` |

The scanner module's existence on this host means the original-run
environment is **fully reconstructable** for Phase 2A. The 2A.1 paired
scan will use the same import + invocation as Apr 23
(`SkillScanner()` default constructor, `scan_skill(tmp_dir,
lenient=True)`) so the "Cisco baseline" in the comparison is, by
construction, the *exact code path* that produced the corpus's
`cisco_scanner_results.json`. This is stronger than "paired-fresh": it
is **reproducing the actual historical code path on the same bytes**
for the sha256-MATCH stratum, and running the same code path on
today's bytes for the DRIFT stratum.

## 3. Four observed facts (each strictly observed; reasoning separated)

### (a) The corpus was produced locally on 2026-04-23 via PyPI `cisco-ai-skill-scanner==2.0.9`

| Observation | Source |
|---|---|
| Two production scripts dated `2026-04-23 09:50` and `10:05` exist locally | `ls -la paper/skillsworkshop/skills-experiment/run_cisco_*.py` |
| Both scripts import `skill_scanner.core.scanner` and call `SkillScanner().scan_skill(..., lenient=True)` | source code of `run_cisco_fast.py` |
| The installed `cisco-ai-skill-scanner 2.0.9` package's `skill_scanner` module exposes the exact API the scripts call | `importlib.metadata` + module inspection |
| All artifacts (collected skills directory, scripts, results JSON) are retained locally on this host | filesystem inspection |

**Status:** observed. Reconstruction is possible.

### (b) The `pip install` command was not session-logged, but install products fix the version as standard PyPI 2.0.9

| Observation | Source |
|---|---|
| No `pip install cisco-ai-skill-scanner==2.0.9` invocation is preserved in any shell history file under `~` | grep over shell history files |
| The installed package metadata reports `Name=cisco-ai-skill-scanner, Version=2.0.9, Author=Cisco, License=Apache-2.0` | `importlib.metadata.metadata('cisco-ai-skill-scanner')` |
| The installed module reports `skill_scanner.__version__ == '2.0.9'` | direct import |
| The wheel's RECORD / dist-info on disk is consistent with a standard PyPI 2.0.9 install (Apache-2.0 license metadata, standard entry-points layout) | inspection of the package's `*-2.0.9.dist-info/` directory |

**Status:** observed. Identity of the installed artifact is fixed by
its install products, even though the install command itself is not
recorded. A future re-install from the GitHub release (§3(c)) is
expected to produce a byte-identical wheel.

### (c) As of 2026-06-07 the package is off PyPI; the wheel is still on the GitHub v2.0.9 release

| Probe | Result (2026-06-07) |
|---|---|
| `pip index versions cisco-ai-skill-scanner` | `ERROR: No matching distribution found for cisco-ai-skill-scanner` |
| Plausible alternative names (`skill-scanner`, `skill_scanner`, `skillsec`, `skill-security`, `cisco-skill`, `ai-skill-scanner`) | All `ERROR: No matching distribution found` |
| Vendored copy in the corpus repo (`paper/skillsworkshop/skills-crosslingual-security/`) | None |
| The GitHub `v2.0.9` release (per the user's report; not separately re-verified in this session) | The wheel is still attached to the GitHub release. Pinning at the GitHub release URL is the recoverable public route. |

**Status:** observed for PyPI. The GitHub-release availability is
recorded as the user's reported fact (the existence of the
release-attached wheel is not separately probed in this session
because the locally-installed copy is sufficient for 2A.1).

### (d) The **published** `run_cisco_scanner.py` shells out to a binary the package never installs (published-artifact defect)

| Observation | Source |
|---|---|
| The published `paper/skillsworkshop/skills-crosslingual-security/analysis/run_cisco_scanner.py` (mtime 2026-05-16) invokes Cisco via `subprocess.run(["cisco-skill-scanner", "scan", str(skill_path), "--json"], …)` | source code |
| The `cisco-ai-skill-scanner` wheel's `console_scripts` entry points are `skill-scanner`, `skill-scanner-api`, `skill-scanner-pre-commit` — **no `cisco-skill-scanner` binary is ever installed** | `importlib.metadata.entry_points(group='console_scripts')` + `ls /opt/homebrew/bin/` |
| The **actual** code path that produced `cisco_scanner_results.json` (Apr 23) does **not** use the CLI at all — it imports `skill_scanner.core.scanner` and calls `scanner.scan_skill(tmp_dir, lenient=True)` (see `run_cisco_fast.py`) | source code |
| Therefore the published reproduction script (a) names a binary that does not exist after `pip install cisco-ai-skill-scanner==2.0.9`, and (b) takes a different code path than the corpus's actual scan | direct comparison of the published script vs the recovered Apr 23 script |

**Status:** observed. **No inference** about why the published script
differs from the production script. The factual claim is narrow: the
published reproduction artifact does not reproduce the corpus's code
path. Recording this as an errata candidate; see §6.

## 4. What is now possible for Phase 2A

The 2A.1 paired scan can use the **exact code path** that produced
the corpus's `cisco_scanner_results.json`:

```python
sys.path.insert(0, '/opt/homebrew/lib/python3.14/site-packages')
from skill_scanner.core.scanner import SkillScanner
scanner = SkillScanner()                         # default constructor
result  = scanner.scan_skill(tmp_dir, lenient=True)
```

This means:

- **MATCH stratum** (14 rows: 12 EN + 2 JA, identity-locked):
  Cisco's "before" flag is the historical flag from
  `cisco_scanner_results.json`, *and* the same flag can be re-derived
  by re-running the recovered scanner on the pinned bytes. The
  historical-vs-rerun agreement on this stratum is itself a
  measurable check on the Apr 23 → 2026-06-07 environment drift.
- **DRIFT stratum** (184 rows: 125 EN + 59 JA, paired-fresh):
  Cisco runs *fresh today* on the pinned current bytes via the same
  code path the corpus used. SkillScanner runs on the same bytes.
  The pair is observed-together and is a valid comparison.
- **404 stratum** (30 rows: 20 EN + 10 JA): excluded with reason.

PROTOCOL §2's `"If Cisco v2.0.9 cannot be reproduced bit-for-bit on
the evaluation host, that fact is reported and the evaluation does
not proceed"` clause was a precondition for `evaluation does not
proceed`. That precondition is no longer met: the scanner is on this
host, version 2.0.9, with the same API the corpus used. Phase 2A
proceeds.

## 5. What this finding does NOT say

- It does **not** say *why* the PyPI package is absent today. Several
  plausible explanations exist (deletion, rename, migration to a
  private index, an issue with the upstream maintainer's account,
  etc.). None is supported by the evidence in this finding. The
  cause is out of scope.
- It does **not** say the GitHub-release wheel is byte-identical to
  the locally-installed copy. The user reports the wheel is still on
  the GitHub `v2.0.9` release; this was not separately verified in
  this session because the locally-installed copy fully satisfies
  Phase 2A's need and re-pulling from GitHub would be a
  precaution rather than a measurement. Phase 2A's reproduction will
  document both the local-install path and the GitHub-release URL for
  any later observer who needs to re-stand-up the baseline.
- It does **not** characterize the published script defect (§3(d)) as
  intentional or as anyone's fault. It records the defect as a fact.
  See §6 for the errata candidate.
- It does **not** revise F-001 or F-002. The corpus-side drift
  findings remain valid; F-003 adds the tool-side picture.

## 6. Errata candidate for the published `HeadyZhang/skills-crosslingual-security` repo

A separate file in this findings tree —
`docs/skillscanner/findings/ERRATA_skills_crosslingual_security.md` —
records §3(d) as an errata candidate for the published dataset repo.
**No edit to the published repo is made in this session.** The errata
file's purpose is to make the published-artifact defect surface so
that, when the user is ready to publish a correction to the
`HeadyZhang/skills-crosslingual-security` repo, the corrected
artifacts are ready to drop in: replace
`analysis/run_cisco_scanner.py` (which shells to the ghost CLI) with
the actual `run_cisco_fast.py` (which uses the API), and update the
README install line / reproduction instructions accordingly.

## 7. Reproducibility of F-003 itself

```bash
# Recover the production scripts:
ls -la paper/skillsworkshop/skills-experiment/run_cisco_*.py

# Confirm the package is installed and identify its API surface:
/opt/homebrew/bin/python3 -c "
import importlib.metadata as m, inspect
from skill_scanner.core.scanner import SkillScanner
md = m.metadata('cisco-ai-skill-scanner')
print({k: md.get(k) for k in ('Name','Version','Author','License')})
print('SkillScanner :', inspect.signature(SkillScanner))
print('scan_skill   :', inspect.signature(SkillScanner.scan_skill))
print('entry_points :', [e.name for e in m.entry_points(group='console_scripts')
                          if e.value.startswith('skill_scanner.')])
"

# Confirm the public PyPI probe state (these may change later):
pip index versions cisco-ai-skill-scanner

# Confirm the published-artifact defect (§3(d)):
grep -n 'cisco-skill-scanner' \
  paper/skillsworkshop/skills-crosslingual-security/analysis/run_cisco_scanner.py
grep -n 'skill_scanner.core.scanner' \
  paper/skillsworkshop/skills-experiment/run_cisco_fast.py
```

Anyone re-running on a later date may see different PyPI results
(§3(c)) and may find that the package has been republished or
renamed; the 2026-06-07 result is the dated snapshot.

## 8. What this finding is NOT (closure)

- Not a Phase 1 freeze invariant violation. The Phase 1
  `skillscanner-core-frozen` tag's invariants (judge sha256,
  BLOCK-ceiling, schema conformance, smoke test) are unchanged by
  F-003. The frozen judge / schema / scanner code is untouched.
- Not a substitution of the Cisco baseline. The 2A.1 scan will use
  the **exact** scanner the corpus used — same module, same version,
  same code path, same `lenient=True` flag, same default constructor.
- Not a SkillScanner detection. F-003 is an ecosystem +
  published-artifact observation, not a code-pattern one.
