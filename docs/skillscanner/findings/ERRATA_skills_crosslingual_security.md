# ERRATA candidate — `HeadyZhang/skills-crosslingual-security` dataset repo

**Status:** Not applied. Recorded so that, when the user is ready to
publish a correction to the dataset repo, the corrected artifacts are
ready to drop in. **The published repo is not edited in this session.**
**Recorded:** 2026-06-07.
**Discovered while:** sourcing the recovered Cisco scanner provenance
for Phase 2A 2A.1; see `findings/F-003_cisco_scanner_unobtainable.md`
§3(d).

---

## 1. The defect (observed, no inference)

The published `paper/skillsworkshop/skills-crosslingual-security/analysis/run_cisco_scanner.py`
(mtime 2026-05-16) is documented in the dataset README as the script
that reproduces the Cisco run:

> ```bash
> python analysis/run_cisco_scanner.py --input data/skills_metadata.json --output results/cisco_scanner_results.json
> ```

That published script invokes the Cisco scanner via a shell
subprocess to a binary named `cisco-skill-scanner`:

```python
proc = subprocess.run(
    ["cisco-skill-scanner", "scan", str(skill_path), "--json"],
    capture_output=True, text=True, timeout=60,
)
```

The `cisco-ai-skill-scanner 2.0.9` PyPI wheel does **not** install a
binary by that name. The wheel's `console_scripts` entry points are:

- `skill-scanner` → `skill_scanner.cli.cli:main`
- `skill-scanner-api` → `skill_scanner.api.api_cli:main`
- `skill-scanner-pre-commit` → `skill_scanner.hooks.pre_commit:main`

(verified by `importlib.metadata.entry_points(group='console_scripts')`
on the local install).

As a result, anyone following the published README's reproduction
instructions on a clean machine would (a) successfully `pip install
cisco-ai-skill-scanner==2.0.9` if the package is still on PyPI, and
then (b) get `FileNotFoundError: [Errno 2] No such file or directory:
'cisco-skill-scanner'` the moment `run_cisco_scanner.py` invokes the
subprocess. The published reproduction path does not, on any host,
reproduce the corpus.

Independent confirmation: the **actual** scan that produced
`cisco_scanner_results.json` was performed by
`paper/skillsworkshop/skills-experiment/run_cisco_fast.py` (mtime
2026-04-23 10:05) — a local, **unpublished** script that imports the
scanner module directly:

```python
sys.path.insert(0, '/opt/homebrew/lib/python3.14/site-packages')
from skill_scanner.core.scanner import SkillScanner
scanner = SkillScanner()
result  = scanner.scan_skill(tmp_dir, lenient=True)
```

The published `run_cisco_scanner.py` and the actual `run_cisco_fast.py`
are two different code paths to (intended) similar output; the
published one references a CLI that does not exist; only the
unpublished one is what actually generated the corpus.

## 2. Proposed corrected artifacts (drop-in ready)

When the user is ready to publish a correction to
`HeadyZhang/skills-crosslingual-security`, the following two changes
will close the defect:

### 2.1 Replace `analysis/run_cisco_scanner.py`

- Drop in the corpus's actual production script — a cleaned form of
  `paper/skillsworkshop/skills-experiment/run_cisco_fast.py` —
  renamed to `analysis/run_cisco_scanner.py` so existing README
  references continue to resolve. Strip the absolute path
  (`/opt/homebrew/lib/python3.14/site-packages`) so the script
  doesn't hard-depend on one machine's filesystem layout; let the
  standard import resolution find the installed package.
- Keep `lenient=True` and the default `SkillScanner()` constructor;
  these are what produced the corpus's flags.

### 2.2 Update `README.md` reproduction instructions

- Reproduction install: the README currently says
  `pip install cisco-ai-skill-scanner==2.0.9`. **As of 2026-06-07
  this package is no longer on PyPI**, but a wheel for v2.0.9 is
  still attached to the upstream GitHub `v2.0.9` release. The
  reproduction line should be replaced with whichever route the user
  considers durable, e.g.:
  ```bash
  pip install <github-release-url>/cisco_ai_skill_scanner-2.0.9-py3-none-any.whl
  ```
  Add a one-line note that the PyPI package was reachable when the
  corpus was collected (Apr 23 2026) and may or may not be reachable
  at later times.
- Reproduction command: keep
  `python analysis/run_cisco_scanner.py --input data/skills_metadata.json --output results/cisco_scanner_results.json`,
  pointing at the corrected (API-based) script.
- Add the recovered date stamp: *"Corpus produced 2026-04-23
  on a personal MacBook via the API path; this script reproduces
  that code path."*

## 3. Why this errata is worth publishing

- Reproducibility is the dataset's first promise. The published
  script not reproducing the corpus undermines the rest of the
  artifact's value.
- A future reader who hits the missing-binary error has no way to
  know that the API path exists or that the GitHub release wheel is
  the recoverable install route. Publishing the corrected
  `run_cisco_scanner.py` + a 2-line README note resolves both gaps
  in one PR.
- The Phase 3 narrative will record the Cisco-tool unavailability
  observation honestly (per F-003). Publishing this errata *first*
  means the Phase 3 paper isn't relying on a published dataset that
  is itself broken at the reproduction layer.

## 4. What this errata candidate is NOT

- Not a claim about cause. F-003 §3(d) records the defect as
  observed fact only; this file does the same. The corrected
  artifacts in §2 are forward-looking remedies, not retrospective
  reattribution.
- Not a Phase 2A blocker. Phase 2A's evaluation will use the
  **recovered local** production code path, not the published one
  (see F-003 §4). The errata is for the *dataset repo*'s reproduction
  promise to external readers; Phase 2A's internal reproduction is
  satisfied by the local artifact.
- Not edited or pushed in this session. The dataset repo is
  unmodified. This file lives only inside `agent-audit`'s findings
  tree as a parked draft.

## 5. Ready-to-execute checklist (for when the user runs it later)

- [ ] In a clean checkout of `HeadyZhang/skills-crosslingual-security`,
      replace `analysis/run_cisco_scanner.py` with a cleaned form of
      the local `run_cisco_fast.py` (strip absolute path; keep
      `lenient=True` + default `SkillScanner()` + the metadata-driven
      fetch loop the existing script uses).
- [ ] Update `README.md`'s "Reproducing the analysis" section per §2.2
      above.
- [ ] Commit with a message that names this as an errata: e.g.
      *"errata: replace ghost-CLI reproduction script with the actual
      API-based production script; update README install path to the
      GitHub-release wheel; recovered provenance 2026-04-23 (this
      laptop)."*
- [ ] Open a release on the dataset repo noting the errata (so users
      who pinned the prior commit can see it).
- [ ] Cite this errata in the Phase 3 paper's reproducibility paragraph.
