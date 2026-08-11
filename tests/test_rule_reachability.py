"""Directory-scan reachability for every advertised rule.

Twice in a row the defect in this repository was the same shape: a mechanism that
exists, is tested in isolation, and is never reached in real use.

* `MCPConfigScanner._find_config_files` discovered configs with a non-recursive
  `iterdir()` while nine other scanners use `rglob`, so six rules had a
  directory-scan count of exactly zero (fixed in `f649dcc`).
* `typescript_scanner` never called `context_classifier`, which the Python path
  does use.

Neither was visible in the unit tests, because a unit test calls the mechanism
directly. Neither was visible in the output, because a rule that never fires
looks exactly like a clean codebase.

This module is the guard. For each probe input it records two numbers per rule:

    file  — the rule fired when the probe file was passed to `run_scan` directly
    dir   — the rule fired when the probe's *ancestor directory* was scanned

Directory scanning is how the tool is normally invoked. A rule with
``file > 0 and dir == 0`` is therefore unreachable in ordinary use, however
green its unit tests are, and `test_no_rule_is_reachable_only_by_file_argument`
fails on it.

Two companion tests cover the failure modes this one cannot see:

* `test_every_advertised_rule_has_a_producer` — a rule that fires for *nobody*
  has ``file == 0`` as well, so the comparison above is silent on it. This test
  walks the two production paths (a direct ``rule_id=`` construction, or a
  ``pattern_type`` some scanner emits that `PATTERN_TYPE_TO_RULE_MAP` maps) and
  pins the set with no path at all.
* `test_known_unreachable_registry_is_accurate` — mechanisms already known to be
  dead are listed with a reason, so wiring one up makes this test fail and the
  registry gets updated rather than quietly rotting.

Every probe is built from a synthetic literal or copied into `tmp_path`. No
fixture, oracle or dataset file is written to.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Set, Tuple

import pytest

from agent_audit.cli.commands.scan import run_scan
from agent_audit.rules.engine import RuleEngine

REPO_ROOT = Path(__file__).resolve().parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "audit" / "agent_audit"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# AGENT-090..109 are the DeFi profile. They only run under `--profile defi`, so a
# plain directory scan is not expected to reach them and they are audited apart.
DEFI_RULES = {"AGENT-%03d" % n for n in range(90, 110)}


# ---------------------------------------------------------------------------
# The advertised rule set
# ---------------------------------------------------------------------------

def advertised_rules() -> Set[str]:
    """The 66 rules a normal directory scan advertises.

    `RULE_CWE_MAPPING` carries 92 IDs; removing the 20 DeFi profile rules gives a
    set that is *equal* — not merely equal in size — to the IDs published in
    `docs/RULES.md`. That equality is asserted below, so the two lists cannot
    drift apart unnoticed.
    """
    engine_src = (PKG_ROOT / "rules" / "engine.py").read_text(encoding="utf-8")
    start = engine_src.index("RULE_CWE_MAPPING")
    end = engine_src.index("\n}", start)
    ids = set(re.findall(r'["\'](AGENT-\d+)["\']', engine_src[start:end]))
    return ids - DEFI_RULES


def documented_rules() -> Set[str]:
    """Rule IDs `docs/RULES.md` publishes as available.

    Everything from the "Withdrawn Rules" heading onwards is a record of rules that
    were removed from the advertised set, so it is excluded — those IDs are named
    there precisely so they are *not* offered.
    """
    text = (REPO_ROOT / "docs" / "RULES.md").read_text(encoding="utf-8")
    marker = text.find("## Withdrawn Rules")
    if marker != -1:
        text = text[:marker]
    return set(re.findall(r"(AGENT-\d+)", text))


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

# Synthetic probes for languages and file types the fixture corpus does not
# cover. Each is deliberately, obviously vulnerable; the point is reachability,
# not realism.
SYNTHETIC_PROBES: Dict[str, str] = {
    "vuln.sol": (
        "// SPDX-License-Identifier: MIT\n"
        "pragma solidity ^0.8.0;\n"
        "contract Vault {\n"
        "    address public owner;\n"
        "    function withdraw(address target, bytes memory data) public {\n"
        '        require(tx.origin == owner, "not owner");\n'
        "        (bool ok, ) = target.delegatecall(data);\n"
        "        require(ok);\n"
        "    }\n"
        "}\n"
    ),
    "srv.go": (
        "package main\n\n"
        "import (\n"
        '    "database/sql"\n'
        '    "math/rand"\n'
        '    "net/http"\n'
        '    "os/exec"\n'
        ")\n\n"
        "func run(userCmd string, db *sql.DB, name string) {\n"
        '    exec.Command("sh", "-c", userCmd).Run()\n'
        "    db.Query(\"SELECT * FROM users WHERE name = '\" + name + \"'\")\n"
        "    _ = rand.Intn(100)\n"
        '    http.Get("http://" + name)\n'
        "}\n"
    ),
    "unsafe.ts": (
        'import { exec } from "child_process";\n'
        'import * as yaml from "js-yaml";\n\n'
        "export function handler(req: any) {\n"
        "  exec(`ls ${req.query.dir}`);\n"
        "  const cfg = yaml.load(req.body.doc);\n"
        "  eval(req.query.code);\n"
        "  return fetch(`http://internal/${req.query.host}`);\n"
        "}\n"
    ),
    "package.json": json.dumps(
        {
            "name": "probe-pkg",
            "version": "1.0.0",
            "main": "dist/index.js",
            "files": ["dist", "dist/index.js.map", ".env"],
        },
        indent=2,
    ),
    ".mcp.json": json.dumps(
        {
            "mcpServers": {
                "risky": {
                    "command": "npx",
                    "args": ["-y", "some-mcp-server", "/"],
                    "env": {"GITHUB_TOKEN": "ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"},
                },
                "remote": {"url": "http://example.com/mcp"},
            }
        },
        indent=2,
    ),
}


def _scan_rule_ids(path: Path) -> Set[str]:
    """Rule IDs produced by a real `run_scan` of `path`."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "findings.json"
        run_scan(
            path=path,
            output_format="json",
            output_path=out,
            min_severity="info",
            additional_rules=[],
            fail_on_severity="none",
            quiet=True,
        )
        if not out.exists():
            return set()
        data = json.loads(out.read_text(encoding="utf-8"))
    return {f.get("rule_id", "") for f in data.get("findings", [])}


@pytest.fixture(scope="module")
def reachability(tmp_path_factory) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, Set[str]]]:
    """Return (file_counts, dir_counts, rule -> probe names that reached it by file).

    The corpus is laid out under ``root/proj/src/deep/`` — three levels below the
    scan root — because the bug class this guards against is discovery that does
    not recurse. A probe sitting at the root would not have caught `f649dcc`.
    """
    root = tmp_path_factory.mktemp("reachability")
    deep = root / "proj" / "src" / "deep"
    deep.mkdir(parents=True)

    probes: Dict[str, Path] = {}
    for name, body in SYNTHETIC_PROBES.items():
        target = deep / name
        target.write_text(body, encoding="utf-8")
        probes[f"synthetic:{name}"] = target

    if FIXTURES.is_dir():
        for src in sorted(p for p in FIXTURES.rglob("*") if p.is_file()):
            if "__pycache__" in src.parts or src.suffix == ".pyc":
                continue
            rel = src.relative_to(FIXTURES)
            target = deep / "fixtures" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            probes[f"fixture:{rel}"] = target

    file_counts: Dict[str, int] = {}
    by_probe: Dict[str, Set[str]] = {}
    for label, target in probes.items():
        for rule in _scan_rule_ids(target):
            file_counts[rule] = file_counts.get(rule, 0) + 1
            by_probe.setdefault(rule, set()).add(label)

    dir_counts: Dict[str, int] = {r: 1 for r in _scan_rule_ids(root)}
    return file_counts, dir_counts, by_probe


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_advertised_set_matches_the_published_rule_list() -> None:
    """`RULE_CWE_MAPPING` minus DeFi is exactly what `docs/RULES.md` publishes."""
    engine_side = advertised_rules()
    docs_side = documented_rules()
    assert engine_side == docs_side, (
        "the engine's rule table and docs/RULES.md have drifted:\n"
        f"  engine only: {sorted(engine_side - docs_side)}\n"
        f"  docs only  : {sorted(docs_side - engine_side)}"
    )
    assert len(engine_side) == 66


def test_no_rule_is_reachable_only_by_file_argument(reachability) -> None:
    """The guard that `f649dcc` needed.

    A rule that fires when its own probe is named directly, but not when an
    ancestor directory is scanned, is unreachable the way users actually invoke
    the tool.
    """
    file_counts, dir_counts, by_probe = reachability
    unreachable = {
        rule: sorted(by_probe.get(rule, ()))
        for rule, count in sorted(file_counts.items())
        if count > 0 and dir_counts.get(rule, 0) == 0
    }
    assert not unreachable, (
        "rules fire on a file-argument scan but not on a directory scan, so they "
        "are dead in normal use:\n"
        + "\n".join(f"  {r}: reached by {p}" for r, p in unreachable.items())
    )


def test_every_advertised_rule_has_a_producer() -> None:
    """No advertised rule may lose its last production path unnoticed.

    Two paths can construct a finding: a literal ``rule_id="AGENT-0XX"`` in a
    scanner, or a ``pattern_type`` that some scanner emits and that
    `PATTERN_TYPE_TO_RULE_MAP` maps to the rule. A rule with neither can never
    fire on any input, which the file-vs-directory comparison cannot detect
    because both of its counts are zero.
    """
    sources = {
        p: p.read_text(encoding="utf-8")
        for p in PKG_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
    }
    pattern_map = RuleEngine.PATTERN_TYPE_TO_RULE_MAP

    def emitted(pattern_type: str) -> bool:
        needle_a, needle_b = f"'{pattern_type}'", f'"{pattern_type}"'
        return any(
            needle_a in src or needle_b in src
            for path, src in sources.items()
            if path.name != "engine.py"
        )

    def constructed(rule_id: str) -> bool:
        for path, src in sources.items():
            if path.name == "ignore.py":
                continue  # references rule IDs as configuration keys, not findings
            if path.name == "engine.py":
                if re.search(r'rule_id\s*=\s*["\']' + rule_id + r'["\']', src):
                    return True
            elif rule_id in src:
                return True
        return False

    orphans = set()
    for rule in advertised_rules():
        if constructed(rule):
            continue
        if any(emitted(pt) for pt, rid in pattern_map.items() if rid == rule):
            continue
        orphans.add(rule)

    assert orphans == KNOWN_ORPHAN_RULES, (
        "the set of advertised-but-unproducible rules changed:\n"
        f"  newly orphaned: {sorted(orphans - KNOWN_ORPHAN_RULES)}\n"
        f"  now producible: {sorted(KNOWN_ORPHAN_RULES - orphans)} "
        "(delete these from KNOWN_ORPHAN_RULES)"
    )


# RUN4 pinned six advertised-but-unproducible rules here so the set could not grow.
# RUN5 removed them from the advertised set instead — see `WITHDRAWN_RULES` in
# `rules/engine.py` and the Withdrawn Rules section of `docs/RULES.md`. The set is
# now empty and must stay empty: `tests/test_rule_producers.py` enforces that with
# no allow-list at all, and this assertion is the second lock on the same door.
KNOWN_ORPHAN_RULES: Set[str] = set()


# Mechanisms that exist, have passing unit tests, and are not reached by any
# directory scan. Listed with the reason so that wiring one up fails this test
# and forces the list to be updated rather than left to rot.
#
# RUN5 correction: AGENT-056 and AGENT-057 were listed here on the grounds that
# `mcp_config_scanner._detect_tool_poisoning` has no callers. That method does have
# no callers — but it is not the producer. `_check_tool_poisoning_in_config` is a
# different method, is called from `mcp_config_scanner.py` on every config scan,
# and emits both rules; a designed trigger fires them (see NIGHT_RUN_LEDGER § W19.3).
# The RUN4 trigger missed them because it used the phrase "ignore all previous
# instructions", and the analyzer's regex requires the noun straight after the first
# qualifier, so it matches "ignore previous instructions" and not that phrasing.
# Both rules are removed from this registry; they are unfixtured, not unreachable.
KNOWN_UNREACHABLE_MECHANISMS = {
    # AGENT-054 (MCP baseline drift) compares a live server against a stored
    # baseline. `MCPBaselineManager` is constructed only in `cli/commands/inspect.py`,
    # so no static input can produce it during `scan`. Unreachable by design rather
    # than by defect — but advertised beside 65 rules a scan does reach.
    "AGENT-054",
}


def test_known_unreachable_registry_is_accurate(reachability) -> None:
    """A mechanism recorded as dead must still be dead.

    The probe corpus contains a `.mcp.json` declaring a server; extending it with
    a `tools` array whose descriptions carry blatant injection text still yields
    no AGENT-056/057, which is what pins these two. If wiring lands, this test
    fails and the registry entry gets deleted along with it.
    """
    file_counts, dir_counts, _ = reachability
    revived = {
        rule
        for rule in KNOWN_UNREACHABLE_MECHANISMS
        if file_counts.get(rule, 0) or dir_counts.get(rule, 0)
    }
    assert not revived, (
        f"{sorted(revived)} now fire on a scan — remove them from "
        "KNOWN_UNREACHABLE_MECHANISMS and record what wired them up"
    )


def test_probe_corpus_reaches_a_documented_share_of_the_rule_set(reachability) -> None:
    """Coverage is recorded, not assumed.

    The guard above is only as good as the corpus feeding it, so the reached set
    is pinned. Reaching *more* rules is always fine; reaching fewer means a probe
    stopped working and the guard quietly lost teeth.
    """
    file_counts, _, _ = reachability
    reached = {r for r in file_counts if r in advertised_rules()}
    assert len(reached) >= 52, (
        f"probe corpus reaches only {len(reached)} of 66 advertised rules "
        f"(was 52); missing: {sorted(advertised_rules() - reached)}"
    )
