#!/usr/bin/env bash
#
# release_v0200.sh — take v0.20.0 from a verified branch to GitHub and PyPI.
#
# Sources:
#   RELEASE_CHECKLIST.md § 6       the six commands this stages
#   RELEASE_CHECKLIST.md § 5       the artifacts, pinned below by hash
#   NIGHT_RUN_LEDGER.md § W52      the verification set, and every expected value below
#   scripts/finalize_run7.sh       the pattern this follows: preflight everything before
#                                  the first mutation, print a before/after for each step,
#                                  have each step verify its own result, abort on mismatch
#
# Six stages. Each prints what it is about to do and whether it can be undone, then stops
# at a read -p you have to answer:
#
#   1  preflight     read-only. Nothing to undo.
#   2  merge         local only. Undo: git reset --hard <sha the stage prints>.
#   3  push master   shared. Undo: force-push, and anyone who fetched already has it.
#   4  tag + push    shared. Undo: delete here and on the remote; anyone who fetched
#                    keeps their copy, and their copy still says v0.20.0.
#   5  TestPyPI      permanent on TestPyPI — but TestPyPI is not the index anyone
#                    installs from, which is the whole point of it.
#   6  PyPI          PERMANENT. Read the comment above stage 6 before running it.
#
# WHY STAGE 5 COMES BEFORE STAGE 6, given that both upload the same two files:
#   Stage 6 cannot be undone. PyPI does not allow re-uploading a version number — not
#   after a delete, not after a yank, not ever. If 0.20.0 is wrong once it is up, the only
#   remedy is to publish 0.20.1. So stage 6 gets exactly one attempt, and everything it
#   can get wrong — rejected metadata, a long description that renders as plain text, a
#   dependency that will not resolve, a missing console entry point, a wheel that installs
#   but cannot scan — stage 5 gets wrong first, on an index nobody depends on, for free.
#   TestPyPI is the only rehearsal available for the one step that is irreversible. That is
#   the entire reason it is a stage of this script rather than an optional extra.
#
# --dry-run prints every command instead of running it. The preflight still runs for real:
# a plan built on an unverified tree is precisely what this script exists to prevent. So a
# dry run costs whatever the verification set costs — a few minutes — and tells you about a
# problem while nothing is committed to.
#
# Run it from anywhere; it cd's to the repository root. It must be run by a human:
# .claude/hooks/night-guard.sh denies push, merge, tag and package upload to an automated
# session, which is correct, and is why this file exists instead of the release being done.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- what is being released --------------------------------------------------

VERSION="0.20.0"
TAG="v${VERSION}"
BRANCH="fix/py314-blocker"
MASTER="master"
REMOTE="origin"

DIST_DIR="packages/audit/dist"
WHEEL="${DIST_DIR}/agent_audit-${VERSION}-py3-none-any.whl"
SDIST="${DIST_DIR}/agent_audit-${VERSION}.tar.gz"

# The artifacts audited in RELEASE_CHECKLIST.md § 5, by hash. A byte count identifies
# nothing — the count recorded there before RUN11 matched no build that was ever on disk.
# If either of these mismatches, the artifacts in dist/ are NOT the ones that were audited:
# rebuild and re-audit, or find out what changed. Do not upload past a hash mismatch.
WHEEL_SHA256="cff621095734b38358d80d3f98f42e7437ff95426dd3ba0c2d93d452cd5a5ee1"
SDIST_SHA256="9649f1f1b83e487e3ac10c08e5d610384176e55f6a66b5e26551b92eafeb0e8a"

# --- what the verification set must produce ----------------------------------
#
# Measured on 2026-09-12 on this branch and recorded in NIGHT_RUN_LEDGER.md § W52 and § W53
# — deliberately not stamped with a commit sha, because the commit that records a pin is the
# commit that changes it. The suite pin moved 1,904 -> 1,905 when the release notes joined
# tests/test_published_metrics.py's MUST_PRINT_A_BLOCK list. These are
# pins, not guesses: the script aborts if the tree in front of it produces anything else.
#
# They go stale on purpose. Add a test and EXP_SUITE_LINE is wrong and this script stops —
# which is the correct behaviour, because a release script that accepts any number is not
# verifying anything. Update the pin deliberately, with the measurement beside it.

EXP_SUITE_LINE="1 failed, 1905 passed, 4 skipped"
EXP_RED_TEST="tests/test_corpus_label_rules.py"
EXP_TP="199"
EXP_FP="90"
EXP_FN="37"
EXP_PRECISION="68.86%"
EXP_RECALL="84.32%"
EXP_F1="75.81%"
EXP_AVB_RECALL="100.0%"
EXP_AVB_PRECISION="88.0%"
EXP_GUARD="passed=11 failed=0"
EXP_RULES="66"
EXP_SCAN_SUMMARY="BLOCK: 1 | WARN: 5 | INFO: 0 | SUPPRESSED: 16"
SCAN_FIXTURE="tests/differential_corpus"

# Package files each artifact must contain, and the path components neither may contain.
EXP_PKG_FILES="99"
FORBIDDEN="audit-eval eval/ datasets/ knowns wilds noise/ results/ ground_truth labeled_samples NIGHT_RUN DECISIONS .claude/"

# The name-level leak check (SESSION2_REPORT.md § 6: eight target-identifying strings) is
# deliberately not reproducible from inside this repository — the strings are not written
# down here, which is the point. Export LEAK_PATTERNS_FILE=/path/to/patterns to have the
# preflight grep the unpacked artifacts against your own list; otherwise it reports the
# check as not re-run rather than as passed. A check that cannot fail is not a check.
LEAK_PATTERNS_FILE="${LEAK_PATTERNS_FILE:-}"

MERGE_MESSAGE="merge: v${VERSION} — six rules withdrawn, benchmark figures retracted, four reachability fixes

Merges ${BRANCH} into ${MASTER}: the span from the Python 3.14 blocker through the
pre-release audit. Six advertised rules withdrawn because no code path could construct
them; the 98.51%/100%/99.25% benchmark figures retracted as targets that were published
as measurements; MCP config discovery, AI-tool hook discovery and the TypeScript
AGENT-034 tool boundary made reachable; Layer 1 given one threshold and a provenance
stamp. Measured at merge: TP ${EXP_TP} / FP ${EXP_FP} / FN ${EXP_FN}, F1 ${EXP_F1};
suite ${EXP_SUITE_LINE}; ${EXP_RULES} advertised rules, each with a producer."

TAG_MESSAGE="v${VERSION} — a correction release

Withdrawn: AGENT-003, -011, -013, -015, -016, -036. Six advertised rules with no producer;
the count is ${EXP_RULES}, guarded by tests/test_rule_producers.py.

Retracted: 98.51% precision / 100% recall / 99.25% F1 / 1.49% FP rate. Never measured —
copied from a development brief's target block. Reproducible value, from
tests/benchmark/precision_recall.py: TP ${EXP_TP} / FP ${EXP_FP} / FN ${EXP_FN},
P ${EXP_PRECISION} / R ${EXP_RECALL} / F1 ${EXP_F1}, stated as a floor.

Fixed: MCP config discovery and AI-tool hook discovery did not recurse; the TypeScript
AGENT-034 boundary gate was imported by nothing; the quality gate could pass without
measuring anything; two reported false-positive classes.

What it does not do: CAPABILITY_BOUNDARIES.md."

# --- flags -------------------------------------------------------------------

DRY_RUN=0

usage() {
  cat <<'USAGE'
usage: scripts/release_v0200.sh [--dry-run] [--help]

  --dry-run   print every command instead of running it. The preflight still runs for
              real, so this takes a few minutes and can still abort.
  --help      this text.

Stages, in order: preflight, merge, push master, tag + push tag, TestPyPI, PyPI.
Each stops at a confirmation stating whether it can be undone. Stage 6 cannot.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown argument: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

# --- helpers -----------------------------------------------------------------

stage()  { printf '\n\n=== STAGE %s: %s\n' "$1" "$2"; }
sect()   { printf '\n--- %s\n' "$1"; }
info()   { printf '    %s\n' "$1"; }
ok()     { printf '    OK    %s\n' "$1"; }
warn()   { printf '    NOTE  %s\n' "$1"; }
fail()   { printf '    ABORT %s\n' "$1" >&2; exit 1; }

# Problems are counted and collected in a string, not an array: /bin/bash on macOS is 3.2,
# where ${#arr[@]} on an empty array is an unbound-variable error under `set -u`, and this
# script would then abort inside its own success path.
PROBLEM_COUNT=0
PROBLEM_LIST=""
bad() {
  printf '    FAIL  %s\n' "$1" >&2
  PROBLEM_COUNT=$((PROBLEM_COUNT + 1))
  PROBLEM_LIST="${PROBLEM_LIST}      - ${1}
"
}

# run <command...> — execute it, or under --dry-run print it and do nothing.
run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '    +  %s\n' "$*"
    return 0
  fi
  printf '    $  %s\n' "$*"
  "$@"
}

# dry_only <what> — the verification a stage would run once its command had actually run.
dry_only() {
  [ "$DRY_RUN" -eq 1 ] || return 1
  printf '    ~  would verify: %s\n' "$1"
  return 0
}

# confirm <stage> <undo> <line...> — the gate in front of every mutating stage. It states
# what happens and whether it can be undone, then blocks on read -p. Answer exactly "yes".
confirm() {
  local label="$1" undo="$2"; shift 2
  printf '\n'
  printf '    ┌─ ABOUT TO: %s\n' "$label"
  local line
  for line in "$@"; do printf '    │  %s\n' "$line"; done
  printf '    │\n'
  printf '    │  UNDO: %s\n' "$undo"
  printf '    └─\n'
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '    (dry run — not prompting, nothing will be executed)\n'
    return 0
  fi
  local reply=""
  read -r -p "    Type yes to proceed, anything else to stop: " reply
  if [ "$reply" != "yes" ]; then
    printf '\nStopped before %s. Nothing in this stage ran.\n' "$label"
    exit 0
  fi
}

http_status() {
  curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$1" 2>/dev/null || printf 'ERR'
}

# wait_for_index <url> <label> — an upload is visible to the JSON API a moment after twine
# returns; poll rather than sleep-and-hope, and say how long it took.
wait_for_index() {
  local url="$1" label="$2" i status
  for i in $(seq 1 30); do
    status="$(http_status "$url")"
    if [ "$status" = "200" ]; then
      ok "$label answered 200 after ${i}0s"
      return 0
    fi
    sleep 10
  done
  return 1
}

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

# ==============================================================================
stage 1 "PREFLIGHT — the full verification set, before anything is touched"
# ==============================================================================
# Nothing below writes. Every check is either a read or a command that produces a number,
# and every number is compared against a pin. Problems are collected rather than thrown at
# the first one, so a single run tells you everything that is wrong.
#
# results/layer1.json is deliberately NOT regenerated here. It is a tracked file, so
# rewriting it inside a release preflight would dirty the tree being released; and since
# v0.20.0 it carries a provenance stamp over the labels, the corpus and the scanner source,
# which quality_gate_check.py recomputes and refuses to score if it does not describe this
# tree. Letting the gate read the committed file IS the check — a stale one now fails.

sect "1.1  repository, branch, working tree"

[ -d .git ] || fail "not a git repository: $REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" = "$BRANCH" ]; then
  ok "on $BRANCH"
else
  bad "on '$CURRENT_BRANCH', expected '$BRANCH' — this script releases $BRANCH and nothing else"
fi

HEAD_SHA="$(git rev-parse HEAD)"
info "HEAD $(git log --oneline -1 HEAD)"

if git diff --quiet && git diff --cached --quiet; then
  ok "no modified or staged tracked files"
else
  bad "the working tree has uncommitted changes to tracked files — commit or stash them"
  git status --short -- . | sed 's/^/          /'
fi

UNTRACKED_COUNT="$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')"
if [ "$UNTRACKED_COUNT" != "0" ]; then
  warn "$UNTRACKED_COUNT untracked file(s) present; they are not part of the merge and will not be released"
  git ls-files --others --exclude-standard | sed 's/^/          /'
fi

sect "1.2  version, on all three files and the two distribution surfaces"

for f in packages/audit/pyproject.toml packages/audit/agent_audit/version.py packages/audit/agent_audit/__init__.py; do
  if grep -qE "(^version = \"${VERSION}\"|^__version__ = \"${VERSION}\")" "$f"; then
    ok "$f says $VERSION"
  else
    bad "$f does not say $VERSION"
  fi
done

if grep -q "${EXP_RULES} rules mapped to OWASP Agentic Top 10" packages/audit/pyproject.toml; then
  ok "pyproject description says $EXP_RULES rules (this is the PyPI summary line)"
else
  bad "packages/audit/pyproject.toml description does not say '$EXP_RULES rules mapped to OWASP Agentic Top 10'"
fi

if grep -q "${EXP_RULES} rules" packages/audit/README.md; then
  ok "packages/audit/README.md says $EXP_RULES rules (this is the PyPI project page)"
else
  bad "packages/audit/README.md does not say '$EXP_RULES rules' — it is the wheel's long description"
fi

for py in 3.9 3.10 3.11 3.12 3.13 3.14; do
  grep -q "Programming Language :: Python :: ${py}\"" packages/audit/pyproject.toml \
    || bad "pyproject is missing the classifier for Python $py"
done
ok "classifiers cover 3.9 through 3.14"

sect "1.3  the advertised rule set"

RULES_COUNT="$(python3 -c "import sys;sys.path.insert(0,'tests');from test_rule_producers import advertised_rules;print(len(advertised_rules()))" 2>/dev/null || echo ERR)"
if [ "$RULES_COUNT" = "$EXP_RULES" ]; then
  ok "advertised rules = $RULES_COUNT"
else
  bad "advertised rules = $RULES_COUNT, expected $EXP_RULES"
fi

sect "1.4  the suite"

# The count alone is not the check. What matters is WHICH tests fail, so this compares the
# failure set: exactly one deliberate red, nothing else, and 1910 tests accounted for.
#
# One exception, named rather than tolerated silently. TestThroughput::test_consistent_-
# performance asserts three wall-clock timings of a 20-file scan stay within 50% of their
# own average. The scan takes ~0.06s, so a scheduling hiccup anywhere in a 45-second suite
# run breaks it: measured on 2026-09-12 it failed 1 of 4 whole-suite runs and passed 10 of
# 10 run on its own. If it is the only extra failure, this re-runs it rather than either
# ignoring a red suite or refusing to release over a stopwatch.
KNOWN_TIMING_TESTS="tests/benchmark/performance_test.py::TestThroughput::test_consistent_performance"

SUITE_RAW="$(python3 -m pytest tests/ packages/audit/tests/ -q 2>&1 || true)"
SUITE_TAIL="$(printf '%s\n' "$SUITE_RAW" | tail -1)"
SUITE_FAILED="$(printf '%s\n' "$SUITE_RAW" | grep '^FAILED ' | awk '{print $2}' || true)"
info "$SUITE_TAIL"

is_known_timing() {
  local candidate="$1" known
  for known in $KNOWN_TIMING_TESTS; do
    if [ "$candidate" = "$known" ]; then return 0; fi
  done
  return 1
}

RED_SEEN=0
UNEXPECTED=""
TIMING_HITS=""
for t in $SUITE_FAILED; do
  info "FAILED $t"
  case "$t" in
    "$EXP_RED_TEST"*) RED_SEEN=1; continue ;;
  esac
  if is_known_timing "$t"; then TIMING_HITS="$TIMING_HITS $t"; else UNEXPECTED="$UNEXPECTED $t"; fi
done

if [ "$RED_SEEN" -eq 1 ]; then
  ok "$EXP_RED_TEST is red, as it is committed to be (docs/decisions/AGENT-015_RESOLUTION.md § 4)"
else
  bad "$EXP_RED_TEST did NOT fail. It is committed red because three corpus labels cite a rule with no producer; if it now passes, the corpus or the rule set changed and this release is not the one that was audited."
fi

for t in $UNEXPECTED; do
  bad "unexpected test failure: $t"
done

TIMING_RECOVERED=0
if [ -n "$TIMING_HITS" ]; then
  warn "a timing-dependent test failed:$TIMING_HITS — re-running just it, twice, before deciding"
  RETRY1="$(python3 -m pytest $TIMING_HITS -q 2>&1 | tail -1 || true)"
  RETRY2="$(python3 -m pytest $TIMING_HITS -q 2>&1 | tail -1 || true)"
  info "re-run 1: $RETRY1"
  info "re-run 2: $RETRY2"
  if printf '%s' "$RETRY1" | grep -q "passed" && printf '%s' "$RETRY2" | grep -q "passed"; then
    TIMING_RECOVERED=1
    warn "it passes in isolation: a stopwatch, not a regression. Not treated as a release problem."
  else
    bad "$TIMING_HITS fails on its own too — that is a real failure, not a timing artefact"
  fi
fi

num_from() { printf '%s' "$SUITE_TAIL" | grep -oE "[0-9]+ $1" | head -1 | awk '{print $1}' || true; }
N_PASS="$(num_from passed)"; N_FAIL="$(num_from failed)"; N_SKIP="$(num_from skipped)"
TOTAL=$(( ${N_PASS:-0} + ${N_FAIL:-0} + ${N_SKIP:-0} ))
if [ "$TOTAL" -eq 1910 ]; then
  ok "1910 tests accounted for (${N_PASS:-0} passed, ${N_FAIL:-0} failed, ${N_SKIP:-0} skipped)"
else
  bad "$TOTAL tests accounted for, expected 1910 — a test was added or removed since this pin was set"
fi

if printf '%s' "$SUITE_TAIL" | grep -q "$EXP_SUITE_LINE"; then
  ok "suite: $EXP_SUITE_LINE"
elif [ -z "$UNEXPECTED" ] && [ "$TIMING_RECOVERED" -eq 1 ] && [ "$RED_SEEN" -eq 1 ]; then
  ok "suite: '$SUITE_TAIL' — the shortfall against '$EXP_SUITE_LINE' is the timing test above and nothing else"
else
  bad "suite reported '$SUITE_TAIL', expected '$EXP_SUITE_LINE'"
fi

sect "1.5  Layer 1"

L1_OUT="$( (cd packages/audit && python3 ../../tests/benchmark/precision_recall.py 2>&1) || true )"
printf '%s\n' "$L1_OUT" | grep -E "True Positives|False Positives|False Negatives|Precision:|Recall:|F1-Score:" | sed 's/^/          /' || true
check_l1() {
  if printf '%s' "$L1_OUT" | grep -qE "$1[[:space:]]+$2([^0-9]|$)"; then
    ok "$1 $2"
  else
    bad "Layer 1: $1 is not $2"
  fi
}
check_l1 "True Positives:"  "$EXP_TP"
check_l1 "False Positives:" "$EXP_FP"
check_l1 "False Negatives:" "$EXP_FN"
check_l1 "Precision:"       "$EXP_PRECISION"
check_l1 "Recall:"          "$EXP_RECALL"
check_l1 "F1-Score:"        "$EXP_F1"

sect "1.6  the quality gate"

GATE_OUT="$(python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml 2>&1)" && GATE_EXIT=0 || GATE_EXIT=$?
printf '%s\n' "$GATE_OUT" | tail -3 | sed 's/^/          /'
if [ "$GATE_EXIT" -eq 0 ]; then
  ok "quality_gate_check.py exit 0"
else
  bad "quality_gate_check.py exit $GATE_EXIT"
fi
printf '%s' "$GATE_OUT" | grep -q "0 failures" || bad "the gate did not report 0 failures"

sect "1.7  agent-vuln-bench, knowns"

AVB_OUT="$( (cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" --tool agent-audit --dataset knowns --output "$TMP_DIR/avb.json" 2>&1) || true )"
printf '%s\n' "$AVB_OUT" | grep -E "Recall:|Precision:|Set A" | tail -4 | sed 's/^/          /' || true
if printf '%s' "$AVB_OUT" | grep -q "Recall: $EXP_AVB_RECALL"; then
  ok "AVB recall $EXP_AVB_RECALL"
else
  bad "AVB recall is not $EXP_AVB_RECALL"
fi
if printf '%s' "$AVB_OUT" | grep -q "Precision: $EXP_AVB_PRECISION"; then
  ok "AVB precision $EXP_AVB_PRECISION"
else
  bad "AVB precision is not $EXP_AVB_PRECISION"
fi

sect "1.8  the night guard's own self-test"

GUARD_OUT="$(bash .claude/hooks/test-guard.sh 2>&1 | tail -1 || true)"
if [ "$GUARD_OUT" = "$EXP_GUARD" ]; then
  ok "guard self-test: $GUARD_OUT"
else
  bad "guard self-test says '$GUARD_OUT', expected '$EXP_GUARD'"
fi

sect "1.9  ./run_eval.sh"

# The RUN11 brief lists `./run_eval.sh --commit HEAD` in the verification set. There is no
# such file in this repository and there was none in RUN10 either — DECISIONS.md item 52.
# The honest report is that the check does not exist, not that it passed.
if [ -x ./run_eval.sh ]; then
  run ./run_eval.sh --commit HEAD
else
  warn "./run_eval.sh does not exist — UNVERIFIED, unchanged since RUN10 (DECISIONS.md item 52)"
fi

sect "1.10  the artifacts"

for f in "$WHEEL" "$SDIST"; do
  [ -f "$f" ] || bad "missing artifact: $f"
done

if [ -f "$WHEEL" ] && [ -f "$SDIST" ]; then
  GOT_WHEEL_SHA="$(shasum -a 256 "$WHEEL" | awk '{print $1}')"
  GOT_SDIST_SHA="$(shasum -a 256 "$SDIST" | awk '{print $1}')"
  if [ "$GOT_WHEEL_SHA" = "$WHEEL_SHA256" ]; then ok "wheel sha256 matches the audited build"; else
    bad "wheel sha256 $GOT_WHEEL_SHA != audited $WHEEL_SHA256 — this is not the artifact that was audited"; fi
  if [ "$GOT_SDIST_SHA" = "$SDIST_SHA256" ]; then ok "sdist sha256 matches the audited build"; else
    bad "sdist sha256 $GOT_SDIST_SHA != audited $SDIST_SHA256 — this is not the artifact that was audited"; fi

  ART_OUT="$(FORBIDDEN="$FORBIDDEN" EXP_PKG_FILES="$EXP_PKG_FILES" EXP_RULES="$EXP_RULES" \
    VERSION="$VERSION" WHEEL="$WHEEL" SDIST="$SDIST" python3 - <<'PY' 2>&1 || true
import os, sys, tarfile, zipfile

forbidden = os.environ["FORBIDDEN"].split()
version = os.environ["VERSION"]
problems, notes = [], []

zf = zipfile.ZipFile(os.environ["WHEEL"])
wheel_names = zf.namelist()
tf = tarfile.open(os.environ["SDIST"])
sdist_names = tf.getnames()

def pkg_files(names, strip):
    out = set()
    for n in names:
        n = n[len(strip):] if strip and n.startswith(strip) else n
        if n.startswith("agent_audit/") and not n.endswith("/"):
            out.add(n)
    return out

wheel_pkg = pkg_files(wheel_names, "")
sdist_pkg = pkg_files(sdist_names, f"agent_audit-{version}/")

notes.append(f"wheel package files: {len(wheel_pkg)}   sdist package files: {len(sdist_pkg)}")
if wheel_pkg != sdist_pkg:
    problems.append(f"sdist and wheel differ: {len(wheel_pkg ^ sdist_pkg)} package file(s) in one and not the other")
if len(wheel_pkg) != int(os.environ["EXP_PKG_FILES"]):
    problems.append(f"wheel holds {len(wheel_pkg)} package files, expected {os.environ['EXP_PKG_FILES']}")

for label, names in (("wheel", wheel_names), ("sdist", sdist_names)):
    hits = [n for n in names for f in forbidden if f in n]
    notes.append(f"{label}: {len(hits)} forbidden path component(s)")
    for h in sorted(set(hits)):
        problems.append(f"{label} ships {h}")

meta = zf.read(f"agent_audit-{version}.dist-info/METADATA").decode("utf-8", "replace")
summary = next((l for l in meta.splitlines() if l.startswith("Summary:")), "")
notes.append(summary[:110])
if f"{os.environ['EXP_RULES']} rules" not in summary:
    problems.append("wheel METADATA Summary does not carry the rule count")
if f"{os.environ['EXP_RULES']} rules" not in meta:
    problems.append("wheel long description does not carry the rule count (this is the PyPI project page)")
if f"Version: {version}" not in meta:
    problems.append(f"wheel METADATA is not version {version}")

ep = zf.read(f"agent_audit-{version}.dist-info/entry_points.txt").decode()
notes.append("entry point: " + " ".join(ep.split()))
if "agent-audit" not in ep or "agent_audit.cli.main:cli" not in ep:
    problems.append("console entry point agent-audit = agent_audit.cli.main:cli is missing")

for n in notes:
    print("NOTE " + n)
for p in problems:
    print("PROBLEM " + p)
PY
)"
  printf '%s\n' "$ART_OUT" | sed 's/^/          /'
  if printf '%s' "$ART_OUT" | grep -q '^PROBLEM'; then
    while IFS= read -r line; do
      case "$line" in PROBLEM*) bad "artifact: ${line#PROBLEM }";; esac
    done <<< "$ART_OUT"
  else
    ok "artifacts clean: identical package content, no local evaluation data, rule count and entry point present"
  fi

  if [ -n "$LEAK_PATTERNS_FILE" ] && [ -r "$LEAK_PATTERNS_FILE" ]; then
    LEAK_DIR="$TMP_DIR/leak"; mkdir -p "$LEAK_DIR"
    (cd "$LEAK_DIR" && unzip -qq -o "$REPO_ROOT/$WHEEL" && tar xzf "$REPO_ROOT/$SDIST")
    if grep -rniFf "$LEAK_PATTERNS_FILE" "$LEAK_DIR" >/dev/null 2>&1; then
      bad "a pattern from $LEAK_PATTERNS_FILE appears inside the artifacts"
      grep -rniFf "$LEAK_PATTERNS_FILE" "$LEAK_DIR" | head -20 | sed 's/^/          /'
    else
      ok "no pattern from $LEAK_PATTERNS_FILE appears in either artifact"
    fi
  else
    warn "name-level leak check NOT re-run — the strings are deliberately not in this repository (SESSION2_REPORT.md § 6). Set LEAK_PATTERNS_FILE to a file of patterns to re-run it."
  fi
fi

sect "1.11  the tools stages 5 and 6 need"

for t in git curl python3 shasum; do
  command -v "$t" >/dev/null 2>&1 && ok "$t: $(command -v "$t")" || bad "$t is not on PATH"
done

TWINE=""
if command -v twine >/dev/null 2>&1; then
  TWINE="twine"
elif python3 -m twine --version >/dev/null 2>&1; then
  TWINE="python3 -m twine"
fi
if [ -n "$TWINE" ]; then
  ok "twine: $TWINE"
  if [ -f "$WHEEL" ] && [ -f "$SDIST" ]; then
    if $TWINE check "$WHEEL" "$SDIST" >/dev/null 2>&1; then
      ok "twine check passes on both artifacts (the long description will render)"
    else
      bad "twine check failed — PyPI would render the long description as plain text or reject it"
      $TWINE check "$WHEEL" "$SDIST" 2>&1 | sed 's/^/          /' || true
    fi
  fi
else
  bad "twine is not installed — stages 5 and 6 cannot run. Install it in a venv (python3 -m venv ~/.venvs/rel && ~/.venvs/rel/bin/pip install twine) and re-run."
  TWINE="twine"   # so the dry-run plan below still prints a readable command
fi

sect "1.12  the remote, and what a push would actually publish"

REMOTE_URL="$(git remote get-url "$REMOTE" 2>/dev/null || echo '')"
[ -n "$REMOTE_URL" ] && ok "$REMOTE -> $REMOTE_URL" || bad "no remote named $REMOTE"

REMOTE_MASTER="$( (git ls-remote "$REMOTE" "refs/heads/$MASTER" 2>/dev/null || true) | awk '{print $1}')"
if [ -z "$REMOTE_MASTER" ]; then
  bad "could not read $REMOTE/$MASTER — no network, or no such branch on the remote"
else
  info "$REMOTE $MASTER is at $REMOTE_MASTER"
  TRACKING="$(git rev-parse "$REMOTE/$MASTER" 2>/dev/null || echo '')"
  if [ "$TRACKING" = "$REMOTE_MASTER" ]; then
    ok "the remote-tracking ref agrees with the remote"
  else
    bad "$REMOTE/$MASTER locally is $TRACKING but the remote says $REMOTE_MASTER — run: git fetch $REMOTE, then re-run this script"
  fi
fi

if git merge-base --is-ancestor "$MASTER" "$BRANCH" 2>/dev/null; then
  ok "$MASTER is an ancestor of $BRANCH — the merge cannot conflict"
else
  bad "$MASTER is not an ancestor of $BRANCH — the merge may conflict; resolve it by hand before using this script"
fi

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  bad "tag $TAG already exists locally — delete it or stop, but do not tag twice"
else
  ok "tag $TAG does not exist locally"
fi
if [ -n "$(git ls-remote "$REMOTE" "refs/tags/$TAG" 2>/dev/null || true)" ]; then
  bad "tag $TAG already exists on $REMOTE — this release has already been tagged"
else
  ok "tag $TAG does not exist on $REMOTE"
fi

# What stage 3 publishes is everything on master that the remote has not seen, which is
# NOT the same as the branch's own commits. Print both, because they differ here.
BRANCH_COMMITS="$(git rev-list --count "$MASTER..$BRANCH" 2>/dev/null || echo '?')"
PRE_EXISTING="$(git rev-list --count "$REMOTE/$MASTER..$MASTER" 2>/dev/null || echo '?')"
info "$BRANCH is $BRANCH_COMMITS commit(s) ahead of $MASTER"
if [ "$PRE_EXISTING" != "0" ] && [ "$PRE_EXISTING" != "?" ]; then
  warn "local $MASTER is already $PRE_EXISTING commit(s) ahead of $REMOTE/$MASTER — these predate the branch and stage 3 publishes them too:"
  git log --oneline "$REMOTE/$MASTER..$MASTER" | sed 's/^/          /'
  warn "read that list. If any of it should not be public, stop now: after stage 3 it is."
fi

sect "1.13  the version is not already on either index"

TESTPYPI_URL="https://test.pypi.org/pypi/agent-audit/${VERSION}/json"
PYPI_URL="https://pypi.org/pypi/agent-audit/${VERSION}/json"

TESTPYPI_BEFORE="$(http_status "$TESTPYPI_URL")"
PYPI_BEFORE="$(http_status "$PYPI_URL")"
info "TestPyPI $VERSION -> HTTP $TESTPYPI_BEFORE"
info "PyPI     $VERSION -> HTTP $PYPI_BEFORE"

case "$TESTPYPI_BEFORE" in
  404) ok "TestPyPI has no $VERSION — stage 5 can upload" ;;
  200) bad "TestPyPI already has $VERSION. TestPyPI will reject a re-upload; stage 5 will fail. Rehearse under a local version suffix or skip stage 5 knowingly." ;;
  *)   bad "could not reach TestPyPI (HTTP $TESTPYPI_BEFORE)" ;;
esac
case "$PYPI_BEFORE" in
  404) ok "PyPI has no $VERSION — stage 6 can upload, once" ;;
  200) bad "PyPI ALREADY HAS $VERSION. It cannot be replaced. Stop, and release 0.20.1 instead." ;;
  *)   bad "could not reach PyPI (HTTP $PYPI_BEFORE)" ;;
esac

# --- preflight verdict --------------------------------------------------------

sect "preflight verdict"

if [ "$PROBLEM_COUNT" -eq 0 ]; then
  ok "every check passed. $HEAD_SHA is releasable."
else
  printf '\n    %s problem(s):\n' "$PROBLEM_COUNT"
  printf '%s' "$PROBLEM_LIST"
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '\n    DRY RUN: a real run would stop here and release nothing.\n'
    printf '    Continuing only to print the plan for stages 2-6.\n'
  else
    printf '\n'
    fail "preflight failed. Nothing was merged, pushed, tagged or uploaded."
  fi
fi

# ==============================================================================
stage 2 "MERGE $BRANCH into $MASTER (--no-ff)"
# ==============================================================================
# Local only. Nothing leaves this machine until stage 3.

sect "before"
MASTER_BEFORE="$(git rev-parse "$MASTER")"
info "$MASTER      $(git log --oneline -1 "$MASTER")"
info "$BRANCH  $(git log --oneline -1 "$BRANCH")"
info "commits the merge brings in: $BRANCH_COMMITS"

confirm "merge $BRANCH into $MASTER with --no-ff" \
  "YES, completely, and only until stage 3. On $MASTER, git reset --hard $MASTER_BEFORE puts it back exactly. Nothing has left this machine yet." \
  "git checkout $MASTER" \
  "git merge --no-ff $BRANCH  (message names the span of work)" \
  "$MASTER moves from $MASTER_BEFORE" \
  "to a merge commit containing $BRANCH_COMMITS commit(s)"

run git checkout "$MASTER"
run git merge --no-ff "$BRANCH" -m "$MERGE_MESSAGE"

sect "after"
if [ "$DRY_RUN" -eq 1 ]; then
  dry_only "$MASTER moved; the merge commit has two parents; git diff $MASTER $BRANCH is empty; the tree is clean"
else
  MASTER_AFTER="$(git rev-parse "$MASTER")"
  info "$MASTER  $(git log --oneline -1 "$MASTER")"
  printf '    %s\n' "before: $MASTER_BEFORE"
  printf '    %s\n' "after:  $MASTER_AFTER"

  [ "$MASTER_AFTER" != "$MASTER_BEFORE" ] || fail "$MASTER did not move"
  PARENTS="$(git rev-list --parents -n1 "$MASTER_AFTER" | wc -w | tr -d ' ')"
  [ "$PARENTS" = "3" ] || fail "the tip of $MASTER has $((PARENTS - 1)) parent(s); --no-ff should have produced 2"
  ok "merge commit with two parents"
  git merge-base --is-ancestor "$BRANCH" "$MASTER" || fail "$BRANCH is not an ancestor of $MASTER"
  ok "$BRANCH is contained in $MASTER"
  if git diff --quiet "$MASTER" "$BRANCH"; then
    ok "git diff $MASTER $BRANCH is empty — $MASTER now has exactly the tree that was verified"
  else
    fail "$MASTER and $BRANCH have different trees after the merge"
  fi
  git diff --quiet && git diff --cached --quiet || fail "the working tree is dirty after the merge"
  ok "working tree clean"
fi

# ==============================================================================
stage 3 "PUSH $MASTER to $REMOTE"
# ==============================================================================
# The first irreversible-in-practice step. A force-push can move the branch back, but it
# cannot un-fetch: anyone who pulled in between keeps what they got.

sect "before"
info "$REMOTE $MASTER: $REMOTE_MASTER"
if [ "$DRY_RUN" -eq 0 ]; then
  PUBLISHING="$(git rev-list --count "$REMOTE_MASTER..$MASTER" 2>/dev/null || echo '?')"
else
  case "$BRANCH_COMMITS$PRE_EXISTING" in
    *\?*) PUBLISHING="unknown — the counts above could not be read" ;;
    *)    PUBLISHING="$((BRANCH_COMMITS + PRE_EXISTING + 1)) (estimate: $BRANCH_COMMITS from $BRANCH + $PRE_EXISTING already on local $MASTER + the merge commit)" ;;
  esac
fi
info "commits this publishes: $PUBLISHING"

confirm "push $MASTER to $REMOTE — it becomes public" \
  "not really. A force-push moves the ref back, but anyone who fetched in the meantime keeps the commits, and the push is visible in the repository's event log either way." \
  "git push $REMOTE $MASTER" \
  "publishes $PUBLISHING commit(s), including the $PRE_EXISTING that were already on local $MASTER" \
  "before this, $REMOTE/$MASTER is at $REMOTE_MASTER"

run git push "$REMOTE" "$MASTER"

sect "after"
if [ "$DRY_RUN" -eq 1 ]; then
  dry_only "git ls-remote $REMOTE refs/heads/$MASTER matches the local $MASTER sha"
else
  REMOTE_AFTER="$( (git ls-remote "$REMOTE" "refs/heads/$MASTER" || true) | awk '{print $1}')"
  LOCAL_AFTER="$(git rev-parse "$MASTER")"
  printf '    %s\n' "remote before: $REMOTE_MASTER"
  printf '    %s\n' "remote after:  $REMOTE_AFTER"
  printf '    %s\n' "local:         $LOCAL_AFTER"
  [ "$REMOTE_AFTER" = "$LOCAL_AFTER" ] || fail "the remote is at $REMOTE_AFTER, local $MASTER at $LOCAL_AFTER"
  ok "$REMOTE/$MASTER is the local $MASTER"
fi

# ==============================================================================
stage 4 "TAG $TAG and push it"
# ==============================================================================
# An annotated tag, so it carries a message, an author and a date. The tag is what the
# GitHub release attaches to and what anyone auditing the published wheel compares against.

sect "before"
info "local tags matching $TAG:  $(git for-each-ref --format='%(refname:short)' "refs/tags/$TAG" | tr '\n' ' ')(none if blank)"
info "remote tags matching $TAG: $( (git ls-remote "$REMOTE" "refs/tags/$TAG" || true) | awk '{print $1}' | tr '\n' ' ')(none if blank)"

confirm "create annotated tag $TAG and push it to $REMOTE" \
  "partly. git tag -d $TAG here and git push $REMOTE :refs/tags/$TAG there removes it — but a tag is what people pin to, and anyone who fetched keeps a v0.20.0 pointing at this commit forever. Moving a published tag is worse than leaving it." \
  "git tag -a $TAG -m '<the release summary>'" \
  "git push $REMOTE refs/tags/$TAG" \
  "the tag points at $MASTER, which stage 3 has already published"

run git tag -a "$TAG" -m "$TAG_MESSAGE"
run git push "$REMOTE" "refs/tags/$TAG"

sect "after"
if [ "$DRY_RUN" -eq 1 ]; then
  dry_only "$TAG is an annotated tag object, points at the tip of $MASTER, and exists on $REMOTE"
else
  TYPE="$(git cat-file -t "$TAG")"
  [ "$TYPE" = "tag" ] || fail "$TAG is a $TYPE, not an annotated tag"
  ok "$TAG is an annotated tag object"
  TAGGED="$(git rev-list -n1 "$TAG")"
  [ "$TAGGED" = "$(git rev-parse "$MASTER")" ] || fail "$TAG points at $TAGGED, not the tip of $MASTER"
  ok "$TAG points at $(git log --oneline -1 "$TAG")"
  REMOTE_TAG="$( (git ls-remote "$REMOTE" "refs/tags/$TAG" || true) | head -1 | awk '{print $1}')"
  [ -n "$REMOTE_TAG" ] || fail "$TAG is not on $REMOTE"
  ok "$TAG is on $REMOTE"
  printf '    %s\n' "GitHub release: create it from $TAG, body = RELEASE_NOTES_v${VERSION}.md"
fi

# ==============================================================================
stage 5 "TESTPYPI — the rehearsal for stage 6"
# ==============================================================================
# Everything stage 6 can get wrong, this gets wrong first, on an index nobody installs
# from. It is not a formality: the long description shipped in these artifacts was rebuilt
# during the pre-release audit because it published a wrong rule count, and the only way to
# see the page a user sees is to put it on an index and look.
#
# TestPyPI will not accept a second upload of 0.20.0 either, so this stage is also
# single-shot — but a burnt TestPyPI version costs nothing.
#
# Installing from TestPyPI needs --extra-index-url https://pypi.org/simple, because the
# dependencies (click, rich, pydantic, pyyaml, aiohttp, aiofiles, langdetect) live on real
# PyPI. Without it the install fails for a reason that has nothing to do with this package.

sect "before"
info "TestPyPI $VERSION -> HTTP $TESTPYPI_BEFORE  (404 = not there yet)"
info "uploading: $WHEEL"
info "           $SDIST"

confirm "upload $VERSION to TestPyPI" \
  "no, and it does not matter. TestPyPI never accepts the same version twice either, but nothing depends on TestPyPI. This is the rehearsal; getting it wrong here is what it is for." \
  "$TWINE upload --repository testpypi $WHEEL $SDIST" \
  "then: a fresh venv installs agent-audit==$VERSION from TestPyPI and scans $SCAN_FIXTURE"

run $TWINE upload --repository testpypi "$WHEEL" "$SDIST"

sect "after"
if [ "$DRY_RUN" -eq 1 ]; then
  dry_only "TestPyPI answers 200 for $VERSION; a clean venv installs it, reports version $VERSION, and scans $SCAN_FIXTURE to '$EXP_SCAN_SUMMARY'"
else
  wait_for_index "$TESTPYPI_URL" "TestPyPI $VERSION" || fail "TestPyPI still does not serve $VERSION after 5 minutes"
  printf '    %s\n' "before: HTTP $TESTPYPI_BEFORE"
  printf '    %s\n' "after:  HTTP $(http_status "$TESTPYPI_URL")"

  TEST_VENV="$TMP_DIR/venv-testpypi"
  python3 -m venv "$TEST_VENV"
  "$TEST_VENV/bin/pip" install --quiet --upgrade pip
  "$TEST_VENV/bin/pip" install --quiet --no-cache-dir \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple \
    "agent-audit==$VERSION"

  GOT_VERSION="$("$TEST_VENV/bin/agent-audit" --version 2>&1 || true)"
  info "$GOT_VERSION"
  printf '%s' "$GOT_VERSION" | grep -q "version $VERSION" || fail "the installed CLI does not report $VERSION"
  ok "installed from TestPyPI into a clean venv, reports $VERSION"

  SCAN_OUT="$("$TEST_VENV/bin/agent-audit" scan "$SCAN_FIXTURE" 2>&1 || true)"
  printf '%s\n' "$SCAN_OUT" | grep -E "BLOCK:|Risk Score" | sed 's/^/          /' || true
  printf '%s' "$SCAN_OUT" | grep -qF "$EXP_SCAN_SUMMARY" \
    || fail "the TestPyPI build does not reproduce '$EXP_SCAN_SUMMARY' on $SCAN_FIXTURE"
  ok "scan matches: $EXP_SCAN_SUMMARY"

  DESC="$(curl -sS --max-time 20 "$TESTPYPI_URL" | python3 -c "import json,sys;print(json.load(sys.stdin)['info']['description'][:4000])" 2>/dev/null || true)"
  printf '%s' "$DESC" | grep -q "$EXP_RULES rules" \
    && ok "the project page carries '$EXP_RULES rules' — the thing the audit had to rebuild the wheel to fix" \
    || fail "the TestPyPI project page does not say '$EXP_RULES rules'"
  info "look at it: https://test.pypi.org/project/agent-audit/$VERSION/"
fi

# ==============================================================================
stage 6 "PYPI — permanent"
# ==============================================================================
# PyPI does not allow re-uploading a version number. Not after deleting the release, not
# after yanking it, not with support's help. Whatever these two files contain becomes
# agent-audit 0.20.0 for everyone, forever, and the only way to correct anything at all
# about them is to publish 0.20.1.
#
# Stage 5 has already put the identical bytes on a real index and installed them back out.
# If anything there was not exactly right, stop here.

sect "before"
info "PyPI $VERSION -> HTTP $PYPI_BEFORE  (404 = not published)"
info "uploading: $WHEEL"
info "           $SDIST"
info "these are the same two files stage 5 rehearsed with — hashes pinned in the preflight"

confirm "upload $VERSION to PyPI — PERMANENT" \
  "NO. This cannot be undone. PyPI never allows re-uploading a version number — deleting or yanking the release does not free it. If 0.20.0 turns out to be wrong, the only remedy is to fix it and publish 0.20.1." \
  "$TWINE upload $WHEEL $SDIST" \
  "agent-audit $VERSION becomes public and installable for everyone" \
  "the six-rule withdrawal and the metric retraction ship with it: RELEASE_NOTES_v${VERSION}.md" \
  "stage 5 rehearsed these exact bytes on TestPyPI and installed them back out"

run $TWINE upload "$WHEEL" "$SDIST"

sect "after"
if [ "$DRY_RUN" -eq 1 ]; then
  dry_only "PyPI answers 200 for $VERSION; a clean venv installs it, reports $VERSION, and scans $SCAN_FIXTURE to '$EXP_SCAN_SUMMARY'"
else
  wait_for_index "$PYPI_URL" "PyPI $VERSION" || fail "PyPI still does not serve $VERSION after 5 minutes — the upload may have failed; check before doing anything else"
  printf '    %s\n' "before: HTTP $PYPI_BEFORE"
  printf '    %s\n' "after:  HTTP $(http_status "$PYPI_URL")"

  PROD_VENV="$TMP_DIR/venv-pypi"
  python3 -m venv "$PROD_VENV"
  "$PROD_VENV/bin/pip" install --quiet --upgrade pip
  "$PROD_VENV/bin/pip" install --quiet --no-cache-dir "agent-audit==$VERSION"

  GOT_VERSION="$("$PROD_VENV/bin/agent-audit" --version 2>&1 || true)"
  info "$GOT_VERSION"
  printf '%s' "$GOT_VERSION" | grep -q "version $VERSION" || fail "the published CLI does not report $VERSION"
  ok "installed from PyPI into a clean venv, reports $VERSION"

  SCAN_OUT="$("$PROD_VENV/bin/agent-audit" scan "$SCAN_FIXTURE" 2>&1 || true)"
  printf '%s\n' "$SCAN_OUT" | grep -E "BLOCK:|Risk Score" | sed 's/^/          /' || true
  printf '%s' "$SCAN_OUT" | grep -qF "$EXP_SCAN_SUMMARY" \
    || fail "the published build does not reproduce '$EXP_SCAN_SUMMARY' — it is public; the remedy is 0.20.1"
  ok "scan matches: $EXP_SCAN_SUMMARY"
  info "https://pypi.org/project/agent-audit/$VERSION/"
fi

# ==============================================================================
printf '\n\n=== DONE\n'
# ==============================================================================

if [ "$DRY_RUN" -eq 1 ]; then
  cat <<'DRY'

    That was a dry run. Nothing was merged, pushed, tagged or uploaded — only the
    preflight actually ran, and it ran for real.

    Re-run without --dry-run to be asked, stage by stage.
DRY
  exit 0
fi

cat <<NEXT

    Not done by this script, on purpose:

      * the GitHub release. Create it from $TAG with RELEASE_NOTES_v${VERSION}.md as the
        body. Attaching the two dist/ files is optional; PyPI already serves them.
      * the issue replies. Five bodies in ISSUE_REPLIES.md: #10 and #12 close on posting,
        #8 and #11 stay open, #5 keeps its labels and its deferral.
      * the external surfaces. The slide deck and docs/cais-2026/ still carry the
        retracted figures; RELEASE_CHECKLIST.md rows B and C.

    You are on $MASTER. git checkout $BRANCH to get back.
NEXT
