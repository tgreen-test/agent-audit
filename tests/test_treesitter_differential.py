"""The tree-sitter path may not become the default until this differential is empty.

## Why this test exists

`TreeSitterParser` has two implementations of the same job: a tree-sitter AST path and
a regex path, chosen at import time by whether `tree_sitter` is installed. The AST path
has been dead in every shipped environment since it was written — issue #12 — because
`tree_sitter_typescript` exposes `language_typescript()` / `language_tsx()` and
`_init_tree_sitter` only recognises a `LANGUAGE` attribute or a `language()` function.

The temptation, once that is known, is to add the missing branch and call it an upgrade.
**It is not an upgrade until it is measured.** RUN3 enabled tree-sitter and measured the
self-test going 76/76 to 6 failing, with `child_process.exec` / `spawn` findings dropping
to zero; it was reverted. A path that parses but detects less is worse than one that never
ran, because it looks like progress.

So the contract this file enforces is narrow and one-directional:

    enabling tree-sitter may ADD findings; it may not REMOVE any.

The set that must be empty is `regex_only` — findings the shipping regex path produces
that the tree-sitter path does not. `treesitter_only` is reported but not asserted on,
because genuinely better parsing is allowed to find more.

## What it measured in v0.20.0

Issue #12's proposed fix was applied to a scratch copy, plus the `tree_sitter.Language`
wrap that a 0.23+ grammar capsule needs, and the AST path activated for all four
languages. The differential over `tests/differential_corpus/` was then:

    present with regex, ABSENT with tree-sitter (must be empty): 2
        AGENT-034  ts/framework_boundaries.ts:16   cp.execSync(cmd) inside a vercel-ai tool()
        AGENT-034  ts/framework_boundaries.ts:33   cp.execSync(req.body.cmd) in an express handler
    present with tree-sitter only: 8
        AGENT-010  ts/prompt_names.ts:5     `Request to ${url} failed...`   <- negative control
        AGENT-010  ts/prompt_names.ts:9     `Operation timed out after...`  <- negative control
        AGENT-010  ts/prompt_names.ts:13    `<div>Hello, ${userName}</div>` <- negative control
        AGENT-010  ts/prompt_names.ts:18    a real system prompt            <- genuine gain
        AGENT-010  ts/receiver_shapes.ts:31 cp.execSync(`ls -la ${x}`)      <- not a prompt
        AGENT-026  ts/receiver_shapes.ts:67 handler.fetch(url)              <- negative control
        AGENT-026  ts/receiver_shapes.ts:71 provider.get().fetch(url)       <- negative control
        AGENT-026  ts/receiver_shapes.ts:75 a.b.fetch(url)                  <- negative control
    agreed on by both paths: 20

Two true positives lost, and six of the eight "gains" are the exact false positives the
regex path was fixed to suppress. The full suite told the same story: 50 failed against
a same-environment baseline of 8, i.e. **42 regressions**, spread across 40 TypeScript
scanner tests and 2 Python parser tests. The decision recorded in
`CAPABILITY_BOUNDARIES.md` is therefore to leave the AST path unreached and document
TypeScript/JavaScript analysis as regex-level.

## How it runs

Two subprocess scans of `tests/differential_corpus/`, same interpreter, same corpus,
differing only in whether `import tree_sitter` succeeds. The regex run is forced by
putting a shim package first on `PYTHONPATH` whose `tree_sitter` module raises
`ImportError` on import — no production code is modified and no environment variable is
added to the package to support testing.

Findings are keyed on `(relative path, line, rule_id)`, which is the same key Layer 1
scores on.

## Reading a skip

When `tree_sitter` is not importable the two runs are identical by construction and the
test would pass vacuously, so it **skips** instead. A skip here means the question was not
asked. It is not a green light.

Run standalone for the full symmetric difference:

    python3 tests/test_treesitter_differential.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Set, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PKG_ROOT = REPO_ROOT / "packages" / "audit"
CORPUS = REPO_ROOT / "tests" / "differential_corpus"

Key = Tuple[str, int, str]

_SHIM = (
    "raise ImportError(\n"
    "    'tree_sitter disabled by tests/test_treesitter_differential.py to force the '\n"
    "    'regex path. If you are seeing this outside that test, something is wrong '\n"
    "    'with PYTHONPATH.'\n"
    ")\n"
)


def tree_sitter_installed() -> bool:
    try:
        import tree_sitter  # noqa: F401
    except ImportError:
        return False
    return True


def _scan(env_extra: Dict[str, str]) -> Set[Key]:
    """Run one scan of the differential corpus and return its finding keys."""
    env = dict(os.environ)
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, "-m", "agent_audit", "scan", str(CORPUS), "--format", "json"],
        capture_output=True,
        text=True,
        cwd=str(PKG_ROOT),
        env=env,
        timeout=600,
    )
    if not proc.stdout.strip():
        raise AssertionError(
            f"scan produced no output (rc={proc.returncode})\n{proc.stderr[-2000:]}"
        )
    data = json.loads(proc.stdout)
    items = data.get("findings", data) if isinstance(data, dict) else data

    keys: Set[Key] = set()
    for item in items:
        if item.get("suppressed", False):
            continue
        location = item.get("location") or {}
        raw = location.get("file_path", item.get("file", ""))
        try:
            rel = str(Path(raw).resolve().relative_to(CORPUS))
        except ValueError:
            rel = raw
        keys.add((rel, location.get("start_line", item.get("line", 0)), item.get("rule_id", "")))
    return keys


def run_differential() -> Tuple[Set[Key], Set[Key], Set[Key]]:
    """Return (regex_only, treesitter_only, common)."""
    with tempfile.TemporaryDirectory() as shim_dir:
        (Path(shim_dir) / "tree_sitter.py").write_text(_SHIM, encoding="utf-8")
        existing = os.environ.get("PYTHONPATH", "")
        regex_path = f"{shim_dir}{os.pathsep}{existing}" if existing else shim_dir
        regex_keys = _scan({"PYTHONPATH": regex_path})

    treesitter_keys = _scan({})
    return (
        regex_keys - treesitter_keys,
        treesitter_keys - regex_keys,
        regex_keys & treesitter_keys,
    )


def _render(title: str, keys: Set[Key]) -> str:
    if not keys:
        return f"  {title}: (empty)"
    lines = [f"  {title}: {len(keys)}"]
    lines += [f"      {rule}  {path}:{line}" for path, line, rule in sorted(keys)]
    return "\n".join(lines)


def test_corpus_is_present_and_covers_both_language_families():
    """A differential over an empty corpus proves nothing."""
    ts = sorted(p.name for p in (CORPUS / "ts").glob("*.ts"))
    js = sorted(p.name for p in (CORPUS / "js").glob("*.js"))
    py = sorted(p.name for p in (CORPUS / "py").glob("*.py"))
    assert ts, "no TypeScript inputs in the differential corpus"
    assert js, "no JavaScript inputs in the differential corpus"
    assert py, (
        "no Python inputs in the differential corpus. semantic_analyzer builds a "
        "TreeSitterParser per file and tree_sitter_python exposes the LANGUAGE attribute "
        "the parser already recognises, so installing the extra changes Python results "
        "too — a TS-only differential answers the wrong question."
    )


def test_shim_actually_forces_the_regex_path():
    """If the shim stopped working the differential would be vacuously empty."""
    with tempfile.TemporaryDirectory() as shim_dir:
        (Path(shim_dir) / "tree_sitter.py").write_text(_SHIM, encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "from agent_audit.parsers.treesitter_parser import _TREE_SITTER_AVAILABLE;"
                "print(_TREE_SITTER_AVAILABLE)",
            ],
            capture_output=True,
            text=True,
            cwd=str(PKG_ROOT),
            env={**os.environ, "PYTHONPATH": shim_dir},
            timeout=120,
        )
    assert proc.stdout.strip() == "False", (
        "the ImportError shim no longer forces the regex path, so the differential "
        f"would compare a path against itself.\nstdout={proc.stdout!r} stderr={proc.stderr[-500:]!r}"
    )


def _any_language_activates() -> str:
    """Return a description of which languages actually reach the AST path."""
    sys.path.insert(0, str(PKG_ROOT))
    try:
        from agent_audit.parsers.treesitter_parser import TreeSitterParser
    finally:
        sys.path.pop(0)
    active = [
        suffix
        for suffix in (".py", ".js", ".ts", ".tsx")
        if TreeSitterParser("const x = 1;", file_path=f"probe{suffix}").is_tree_sitter_available
    ]
    return ", ".join(active)


@pytest.mark.skipif(
    not tree_sitter_installed(),
    reason="tree_sitter is not importable; there is no second path to compare against",
)
def test_an_empty_differential_is_not_reported_when_it_is_vacuous():
    """An empty differential means nothing if the AST path never ran.

    This is the trap the first version of this file fell into: with `tree_sitter`
    installed the differential came back empty and looked like a clean bill of health,
    while `_init_tree_sitter` was in fact failing for every language and both sides of
    the comparison were the regex path.

    This test does not require the AST path to be active — as of v0.20.0 it deliberately
    is not. It requires that its inactivity be *stated*, so nobody reads an empty
    differential as evidence the two paths agree.
    """
    active = _any_language_activates()
    if not active:
        pytest.skip(
            "tree_sitter imports but no language reaches the AST path, so the "
            "differential compares the regex path against itself and proves nothing. "
            "This is the shipping state and it is deliberate — see "
            "CAPABILITY_BOUNDARIES.md. If you have just wired the AST path, this skip "
            "turning into a pass is the signal that the differential below is now real."
        )
    assert active, "unreachable"


@pytest.mark.skipif(
    not tree_sitter_installed(),
    reason=(
        "tree_sitter is not installed, so both sides of the differential are the regex "
        "path and the comparison is vacuous. THIS SKIP IS NOT A PASS — it means the "
        "tree-sitter path was not measured. Install the extra to ask the question: "
        "poetry install -E tree-sitter"
    ),
)
def test_enabling_tree_sitter_removes_no_finding():
    """Enabling tree-sitter may add findings. It may not take any away."""
    if not _any_language_activates():
        pytest.skip(
            "the AST path is not reached for any language, so this comparison is "
            "vacuous. See test_an_empty_differential_is_not_reported_when_it_is_vacuous."
        )
    regex_only, treesitter_only, common = run_differential()

    assert not regex_only, (
        "enabling tree-sitter REMOVES findings the shipping regex path produces. "
        "That is a capability regression wearing the costume of an upgrade, and it is "
        "why the tree-sitter path was rolled back once already (RUN3: self-test 76/76 -> "
        "6 failing, child_process findings to zero).\n"
        + _render("present with regex, ABSENT with tree-sitter", regex_only)
        + "\n"
        + _render("present with tree-sitter only (allowed)", treesitter_only)
        + f"\n  agreed on by both paths: {len(common)}"
    )


def main() -> int:
    print(f"differential corpus: {CORPUS}")
    print(f"tree_sitter installed: {tree_sitter_installed()}")
    if not tree_sitter_installed():
        print(
            "\ntree_sitter is NOT installed. Both sides would be the regex path and the "
            "comparison is vacuous.\nThis is not a pass. Install the extra and re-run."
        )
        return 2

    active = _any_language_activates()
    print(f"languages reaching the AST path: {active or '(none)'}")
    if not active:
        print(
            "\ntree_sitter imports but no language reaches the AST path, so both sides "
            "are the regex path.\nThis is the shipping state and it is deliberate — see "
            "CAPABILITY_BOUNDARIES.md.\nThis is not a pass either: the question was not "
            "asked."
        )
        return 2

    regex_only, treesitter_only, common = run_differential()
    print()
    print(_render("present with regex, ABSENT with tree-sitter (must be empty)", regex_only))
    print(_render("present with tree-sitter only (allowed)", treesitter_only))
    print(f"  agreed on by both paths: {len(common)}")
    print()
    if regex_only:
        print("VERDICT: tree-sitter must NOT become the default. It loses findings.")
        return 1
    print("VERDICT: the tree-sitter-missing side is empty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
