#!/usr/bin/env python3
"""Provenance stamping for benchmark results — what a number is a number *about*.

Why this module exists
----------------------

`quality_gate_check.py` decides whether a build passes by reading `results/layer1.json`.
It read that file and nothing else. Two consequences, both measured on 2026-08-11 and
both exit code 0:

  A. A `layer1.json` describing a corpus that no longer exists passes the gate. The file
     is committed to the repository, so it is present in every checkout whether or not
     anything measured it. `gates.yaml` already records the historical case — the
     `results/layer1.json` committed at `a65b341` reported R 0.4746 and sat in the tree
     for six months.

  B. An absent `layer1.json` passes the gate. Both enabled, `blocking: true` layers
     reported SKIP and the run exited 0.

That is the eighth instance of this repository's recurring defect shape, stated in
`CAPABILITY_BOUNDARIES.md` § 3:

    A detector that cannot fire and a target with no defects produce identical output.

Here the detector is the gate. A gate evaluating a stale file and a gate evaluating a
passing build produce identical output — `exit 0` — and so do a gate evaluating nothing
and a gate evaluating a passing build. Nothing that observes the exit code can tell them
apart, which is why the fix cannot be another assertion about the numbers. It has to be a
statement about *where the numbers came from*, carried in the file and checked against
the tree.

What a stamp commits to
-----------------------

A Layer 1 measurement is a function of exactly three things: the labels, the corpus the
labels point at, and the scanner that reads it. The stamp fingerprints all three, so the
gate can ask "is this file about this tree?" without re-running a five-minute benchmark.

Deliberately *not* time-based. In CI the gate runs in a different job from the
measurement and the artifact is minutes old by the time it is read; an age limit would
fail correct builds and be switched off within a week. Content answers the question that
was actually being asked.

Deliberately fails **loud**. A fingerprint mismatch blocks. If that ever fires spuriously
— a stray file under `tests/fixtures/`, a `.pyc` this module failed to exclude — the cost
is a red build with an exact command in the message, which is the direction this project
has repeatedly chosen: see `PROGRESS.md`, "the false-positive direction remains the safe
one".

Used by `precision_recall.py` (writes the stamp) and `quality_gate_check.py` (checks it).
Both are run as scripts out of this directory, which puts it on `sys.path`; there is no
package here to import from.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# Bump when the *meaning* of a field changes. A stamp written under a different schema
# version is treated as absent rather than silently compared field by field.
SCHEMA_VERSION = 1

REPO_ROOT = Path(__file__).resolve().parents[2]

# The three inputs a Layer 1 number is a function of.
GROUND_TRUTH = REPO_ROOT / "tests" / "ground_truth" / "labeled_samples.yaml"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
SOURCE_DIR = REPO_ROOT / "packages" / "audit" / "agent_audit"

# Extensions that can change what the scanner does. Everything else under SOURCE_DIR is
# packaging noise. Under FIXTURES_DIR nothing is filtered by extension: a `.sh`, a
# `.mcp.json` and a `.claude/settings.json` are all corpus.
SOURCE_SUFFIXES = frozenset({".py", ".yaml", ".yml"})

# Never content: build artifacts and editor droppings that appear and vanish without
# changing a measurement. Kept small on purpose — every entry here is a way for a real
# change to slip past the fingerprint.
EXCLUDED_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})
EXCLUDED_FILE_NAMES = frozenset({".DS_Store"})
EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})


class ProvenanceError(RuntimeError):
    """A fingerprint could not be computed because an input is missing."""


def _iter_files(root: Path, suffixes: Optional[frozenset] = None) -> Iterable[Path]:
    """Every content file under `root`, in a deterministic order."""
    if not root.exists():
        raise ProvenanceError(f"cannot fingerprint a path that does not exist: {root}")
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.name in EXCLUDED_FILE_NAMES or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if suffixes is not None and path.suffix not in suffixes:
            continue
        yield path


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint_tree(root: Path, suffixes: Optional[frozenset] = None) -> str:
    """A content hash of a directory: sorted `relpath\\0sha256` lines, hashed.

    Path-sensitive as well as content-sensitive, so moving a fixture is a change and
    deleting one is a change — not only editing one.
    """
    lines: List[str] = []
    for path in _iter_files(root, suffixes):
        rel = path.relative_to(root).as_posix()
        lines.append(f"{rel}\0{_digest_file(path)}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def fingerprint_file(path: Path) -> str:
    if not path.is_file():
        raise ProvenanceError(f"cannot fingerprint a file that does not exist: {path}")
    return _digest_file(path)


def corpus_fingerprint(
    ground_truth: Path = GROUND_TRUTH, fixtures: Path = FIXTURES_DIR
) -> str:
    """The labels and the files they point at, together.

    One hash rather than two: a label edit and a fixture edit are the same kind of event
    for the gate's purposes, and one field is one thing to keep in sync.
    """
    return hashlib.sha256(
        (fingerprint_file(ground_truth) + "\n" + fingerprint_tree(fixtures)).encode("utf-8")
    ).hexdigest()


def source_fingerprint(source: Path = SOURCE_DIR) -> str:
    """The scanner source tree that a measurement should have been produced by."""
    return fingerprint_tree(source, SOURCE_SUFFIXES)


def resolve_runtime_package(python_cmd: str) -> Dict[str, Optional[str]]:
    """Ask the interpreter that ran the scan where its `agent_audit` actually is.

    `precision_recall.py` measures by shelling out to `<python> -m agent_audit`, so the
    build being measured is whichever `agent_audit` that interpreter imports — which is
    not necessarily the one in this checkout. An editable install points back at
    `packages/audit/agent_audit` and the two agree; a wheel install in an active venv does
    not, and the resulting number describes a build nobody is looking at.

    Returns the package path and version, or an `error` string. Never raises: failing to
    resolve the runtime is worth recording, not worth losing the measurement over.
    """
    probe = (
        "import json,agent_audit;"
        "print(json.dumps({'path': agent_audit.__file__, "
        "'version': getattr(agent_audit, '__version__', None)}))"
    )
    try:
        proc = subprocess.run(
            [python_cmd, "-c", probe], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"path": None, "version": None, "error": f"{type(exc).__name__}: {exc}"}
    if proc.returncode != 0:
        return {"path": None, "version": None, "error": proc.stderr.strip()[:400]}
    try:
        info = json.loads(proc.stdout.strip())
    except ValueError as exc:
        return {"path": None, "version": None, "error": f"unparseable probe output: {exc}"}

    package_dir = str(Path(info["path"]).resolve().parent)
    return {
        "path": package_dir,
        "version": info.get("version"),
        "error": None,
        "is_this_checkout": package_dir == str(SOURCE_DIR.resolve()),
    }


def _git_rev() -> Optional[str]:
    """Best effort, for forensics only. Nothing is compared against it."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def current_stamp(
    *,
    python_cmd: Optional[str] = None,
    ground_truth: Path = GROUND_TRUTH,
    fixtures: Path = FIXTURES_DIR,
    source: Path = SOURCE_DIR,
    generated_at: Optional[str] = None,
) -> Dict[str, object]:
    """Build the stamp for the tree as it is right now.

    `generated_at` is recorded and never compared — see the module docstring on why
    staleness here is a content question, not an age question. It is a parameter so a
    caller with a real clock can supply one and this module stays free of one.
    """
    stamp: Dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "corpus_fingerprint": corpus_fingerprint(ground_truth, fixtures),
        "source_fingerprint": source_fingerprint(source),
        "git_rev": _git_rev(),
        "generated_at": generated_at,
    }
    if python_cmd is not None:
        stamp["runtime_package"] = resolve_runtime_package(python_cmd)
    return stamp


def verify_stamp(
    stamp: Optional[dict],
    *,
    ground_truth: Path = GROUND_TRUTH,
    fixtures: Path = FIXTURES_DIR,
    source: Path = SOURCE_DIR,
    regenerate_hint: str = "python3 tests/benchmark/precision_recall.py --output-json results/layer1.json",
) -> List[str]:
    """Return one problem string per reason the stamp does not describe this tree.

    Empty list means the results file was produced from this corpus by this scanner.
    """
    if not isinstance(stamp, dict) or not stamp:
        return [
            "results file carries no provenance stamp, so nothing can say which corpus "
            f"or which scanner produced it — regenerate with: {regenerate_hint}"
        ]

    if stamp.get("schema_version") != SCHEMA_VERSION:
        return [
            f"provenance schema_version {stamp.get('schema_version')!r} is not the "
            f"expected {SCHEMA_VERSION} — regenerate with: {regenerate_hint}"
        ]

    problems: List[str] = []
    expected: Tuple[Tuple[str, str], ...] = (
        ("corpus_fingerprint", corpus_fingerprint(ground_truth, fixtures)),
        ("source_fingerprint", source_fingerprint(source)),
    )
    labels = {
        "corpus_fingerprint": "ground-truth labels and/or the fixture corpus",
        "source_fingerprint": "the scanner source under packages/audit/agent_audit",
    }
    for key, want in expected:
        got = stamp.get(key)
        if got != want:
            problems.append(
                f"{labels[key]} changed since this results file was written "
                f"({key} {str(got)[:12]}… != {want[:12]}…) — the numbers describe a "
                f"different tree. Regenerate with: {regenerate_hint}"
            )

    runtime = stamp.get("runtime_package")
    if isinstance(runtime, dict) and runtime.get("is_this_checkout") is False:
        problems.append(
            "the measurement was produced by an agent_audit outside this checkout "
            f"({runtime.get('path')}, version {runtime.get('version')}), so the numbers "
            f"describe a different build. Regenerate with: {regenerate_hint}"
        )

    return problems


def _main(argv: List[str]) -> int:
    """`python3 tests/benchmark/provenance.py` prints the current stamp.

    Useful when a gate failure needs to be told apart from a broken fingerprint.
    """
    stamp = current_stamp(python_cmd=sys.executable)
    print(json.dumps(stamp, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
