# Slopsquatting: does it belong in agent-audit?

**Decision: no, not as a rule of its own. Yes, as the motivation for a rule this project
already owes its own corpus.** Measured on 2026-08-11 at v0.20.0.

---

## 1. The attack class

Slopsquatting is typosquatting without the typo. A coding agent hallucinates a plausible
package name that does not exist; an attacker registers that name; the next agent — or the
next developer following the agent's suggestion — installs it.

The term was coined by Seth Larson (Python Software Foundation) and popularised by Andrew
Nesbitt; Aikido's Charlie Eriksen documented it occurring in the wild. What makes it a
distinct class rather than a variant of typosquatting is its determinism: re-running
identical prompts, **43% of hallucinated package names recurred on every run**, so an
attacker does not need to guess a plausible misspelling — they need only sample a popular
model a few dozen times and register what it keeps inventing. One non-existent name had
already propagated to 237 repositories through forks.

It is squarely in this tool's declared territory: ASI-04, supply chain, agent-specific,
and invisible to conventional SAST.

---

## 2. What agent-audit reports on it today

Three shapes, scanned at v0.20.0. This is the measurement the decision rests on, not a
description of what the code looks like it would do.

**Shape 1 — the attack itself: a hallucinated name as a static import.**

```python
import requests
import langchain_utils_toolkit   # does not exist on PyPI
```

```
AGENT-026  a_static_import.py:7  tier=WARN  conf=0.65
```

That finding is SSRF on `requests.get(url)`. **Nothing at all is reported about the
package.** The accompanying `requirements.txt` pinning `langchain-utils-toolkit==0.1.0`
produces zero findings.

**Shape 2 — an agent installing a name a model produced.**

```python
@tool
def ensure_dependency(package_name: str) -> str:
    subprocess.run(["pip", "install", package_name], check=True)
    return __import__(package_name).__doc__ or ""
```

```
AGENT-022  :8   BLOCK  1.00      AGENT-034  :8   WARN   0.85
AGENT-035  :11  BLOCK  1.00      AGENT-053  :11  BLOCK  1.00
AGENT-034  :11  BLOCK  0.95
```

Five findings — and **not one of them is about the package name**. They are tool input
validation, dynamic import, and agent self-modification. The line is covered, for reasons
that have nothing to do with slopsquatting.

So the position today is precise: the shape the tool can see, it already sees under rules
that exist; the shape that makes slopsquatting *slopsquatting* — this name was invented —
it cannot see at all.

---

## 3. Why a rule would not close the gap

Every published detection approach for slopsquatting reduces to the same first step:
**ask the registry whether the package exists.** Aikido's scanner, Snyk's guidance and the
Cloud Security Alliance research note all begin there, and the secondary signals — naming
heuristics, curated hallucination corpora — are triage on top of that lookup.

agent-audit cannot take that step, and the reason is a design commitment rather than an
omission. `CAPABILITY_BOUNDARIES.md` § 1: *"No runtime behaviour of any kind. Nothing is
executed, no server is started, no model is called."* A scan makes no outbound request,
and the one command that does talk to a network — `agent-audit inspect` — introspects a
declared MCP interface and is not part of scanning.

The two ways to build it anyway are both worse than not building it:

* **Ship a registry client in the scan path.** That makes every scan network-dependent and
  non-deterministic, converts an offline CI step into one that can fail on a proxy, and
  leaks the dependency list of the scanned repository to two public registries. It also
  breaks the property every guard in this repository relies on — that the same tree
  produces the same findings, which is what `tests/benchmark/provenance.py` was written to
  be able to assert.

* **Ship a bundled list of known-hallucinated names.** A snapshot of somebody else's
  research, stale on the day it ships, silently decaying afterwards. This project has
  spent seven runs removing exactly that: a mechanism that looks like detection and
  produces no finding is indistinguishable from a clean codebase (§ 3 of
  `CAPABILITY_BOUNDARIES.md`). A name list is that failure mode with a maintenance
  schedule attached.

There is a third option that is neither, and it is not a rule: report the **dependency
inventory** a scan already parses and let something with a network decide. That is a
feature request for a different tool boundary, and it should be argued as one rather than
smuggled in as a detection rule.

---

## 4. What this project actually owes, and why slopsquatting sharpens it

The half of slopsquatting a static analyser *can* see is **runtime acquisition of code
whose identity is not fixed in the source** — `pip install <variable>`, `npm install`
at runtime, `curl | bash`, `git clone` then execute. Not "is this name real", which needs
a registry, but "is this program deciding at runtime what code to run", which is a
property of the file.

**That rule does not exist, and its absence is already recorded as a defect.** Three
ground-truth labels cite AGENT-015 for exactly that meaning, no code path can emit it, and
`tests/test_corpus_label_rules.py` is committed red because of them:

```
AGENT-015  asi-04-supply-chain/direct/curl_pipe_bash.sh:11
AGENT-015  asi-04-supply-chain/direct/git_clone_exec.py:14
AGENT-015  asi-04-supply-chain/indirect/dynamic_requirements.py:14
```

`docs/decisions/AGENT-015_RESOLUTION.md` § 4 sets out the two honest ways to close them:
build the rule, or mark them known-uncovered. Slopsquatting is the argument for building
it. It also names the harder half of the work — one of those three is a `.sh` file, and
**no scanner in this tool opens a shell script**, so a supply-chain rule that stops at
Python leaves the most common form of the attack unread.

That is the scope recommendation, and it is in `NEXT_ROUND.md` rather than here.

---

## 5. The decision, stated so it can be disagreed with

| question | answer |
|---|---|
| Is slopsquatting real and in scope thematically? | Yes. ASI-04, agent-specific, documented in the wild. |
| Can agent-audit detect it as published? | **No.** The distinguishing test is a registry lookup, and scanning makes no network calls by design. |
| Would a rule that skipped the lookup detect it? | No. It would detect runtime package acquisition, which is a different and already-owed rule. |
| Should v0.21.0 add an `AGENT-1xx: Hallucinated Package` rule? | **No.** A rule named for an attack it cannot test for is the defect this project spent seven runs removing. |
| Should v0.21.0 close the AGENT-015 gap? | **Yes**, and slopsquatting is the strongest current argument for it. |

Revisit if either premise changes: if agent-audit ever grows a deliberate,
opt-in, clearly-bounded online mode (`--online`, off by default, with its own
determinism story), the registry lookup becomes available and this decision should be
re-taken rather than inherited.

---

## Sources

* [Slopsquatting: The AI Package Hallucination Attack Already Happening — Aikido Security](https://www.aikido.dev/blog/slopsquatting-ai-package-hallucination-attacks)
* [Slopsquatting: When AI Agents Hallucinate Malicious Packages — Trend Micro](https://www.trendmicro.com/vinfo/us/security/news/cybercrime-and-digital-threats/slopsquatting-when-ai-agents-hallucinate-malicious-packages)
* [Slopsquatting: AI Code Hallucinations Fuel Supply Chain Risk — Cloud Security Alliance](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/04/CSA_research_note_slopsquatting-ai-supply-chain_20260419-csa-styled-1.pdf)
* [Slopsquatting: New AI Hallucination Threats & Mitigation Strategies — Snyk](https://snyk.io/articles/slopsquatting-mitigation-strategies/)
* [AI Coding Agents Skip Package Verification, and Attackers Are Exploiting It — TechTimes](https://www.techtimes.com/articles/319457/20260701/ai-coding-agents-skip-package-verification-attackers-are-exploiting-it.htm)
