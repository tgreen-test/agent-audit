#!/usr/bin/env bash
#
# finalize_run7.sh — the three RUN7 changes that the night guard blocks, in one place.
#
# Sources:
#   DECISIONS.md item 39                 — the three rule_id edits (step 1)
#   RELEASE_CHECKLIST.md § 1, § 2, § 3   — the same three edits, the ratchet, the deletions
#   docs/decisions/DEAD_FILES.md         — the evidence for step 3
#
# It does exactly three things:
#   1. Applies the three item-39 rule_id edits in tests/ground_truth/labeled_samples.yaml
#   2. Sets f1_min 0.72 -> 0.73 and recall_min 0.81 -> 0.82 in tests/benchmark/gates.yaml
#   3. git rm's the two dead threshold files listed in docs/decisions/DEAD_FILES.md
#
# It does NOT run the benchmark, the suite, the quality gate, or git commit. Steps 1 and 2
# move a measured number; re-measuring is a separate, deliberate act:
#
#   cd packages/audit && python3 ../../tests/benchmark/precision_recall.py
#   python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml
#
# Each step prints a before/after diff and then verifies its own result. Any mismatch
# between what is on disk and what the documents describe aborts the whole script before
# anything else is touched — a moved line number is a reason to stop, not to guess.
#
# Run from the repository root. This must be run by a human: .claude/hooks/night-guard.sh
# denies every path below to an automated session, and that is correct.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LABELS="tests/ground_truth/labeled_samples.yaml"
GATES="tests/benchmark/gates.yaml"
DEAD_1="tests/benchmark/quality_gates.yaml"
DEAD_2="tests/benchmark/quality_gates_v2.yaml"

SNAP_DIR="$(mktemp -d)"
trap 'rm -rf "$SNAP_DIR"' EXIT

# --- helpers -----------------------------------------------------------------

step()  { printf '\n=== STEP %s: %s\n' "$1" "$2"; }
info()  { printf '    %s\n' "$1"; }
ok()    { printf '    OK   %s\n' "$1"; }
fail()  { printf '    FAIL %s\n' "$1" >&2; exit 1; }

# snapshot <file> <tag> — copy a file aside so a real before/after diff can be printed.
snapshot() { cp "$2" "$SNAP_DIR/$1"; }

# show_diff <tag> <file> — unified diff of snapshot vs current. diff exits 1 when they
# differ, which is the expected case, so the exit code is swallowed deliberately.
show_diff() {
  printf '\n--- diff: %s\n' "$2"
  diff -u --label "a/$2" --label "b/$2" "$SNAP_DIR/$1" "$2" || true
}

# line_is <file> <lineno> <expected> — exact match on one line, whitespace included.
line_is() {
  [ "$(sed -n "${2}p" "$1")" = "$3" ]
}

# --- preflight ---------------------------------------------------------------
# Every assumption the three steps rest on, checked before the first write.

printf '=== PREFLIGHT\n'

[ -d .git ] || fail "not a git repository: $REPO_ROOT"

for f in "$LABELS" "$GATES"; do
  [ -f "$f" ] || fail "missing: $f"
done
ok "target files present"

# The three item-39 edits: yaml line, old value, new value. Line numbers are from
# RELEASE_CHECKLIST.md § 1 and were re-verified at HEAD.
EDITS=(
  '1636|        rule_id: "AGENT-036"|        rule_id: "AGENT-001"|asi-02-tool-misuse/direct/subprocess_unsandboxed.py:8'
  '1669|        rule_id: "AGENT-015"|        rule_id: "AGENT-001"|asi-04-supply-chain/direct/npm_install_runtime.py:13'
  '1709|        rule_id: "AGENT-015"|        rule_id: "AGENT-034"|asi-04-supply-chain/indirect/pypi_typosquatting.py:12'
)

STEP1_PENDING=0
STEP1_DONE=0
for edit in "${EDITS[@]}"; do
  IFS='|' read -r lineno old new label <<< "$edit"
  if line_is "$LABELS" "$lineno" "$old"; then
    STEP1_PENDING=$((STEP1_PENDING + 1))
  elif line_is "$LABELS" "$lineno" "$new"; then
    STEP1_DONE=$((STEP1_DONE + 1))
  else
    printf '    on disk at %s:%s: %s\n' "$LABELS" "$lineno" "$(sed -n "${lineno}p" "$LABELS")" >&2
    fail "$LABELS:$lineno is neither the expected old nor the expected new value ($label)"
  fi
done
ok "step 1 labels: $STEP1_PENDING to apply, $STEP1_DONE already applied"

grep -qE '^    recall_min: 0\.(81|82)$' "$GATES" || fail "$GATES: layer1 recall_min is not 0.81 or 0.82"
grep -qE '^    f1_min: 0\.(72|73)$'     "$GATES" || fail "$GATES: layer1 f1_min is not 0.72 or 0.73"
grep -qE '^    precision_min: 0\.66$'   "$GATES" || fail "$GATES: layer1 precision_min is not 0.66 — do not touch it, but it should be there"
ok "step 2 thresholds are at a known value"

for f in "$DEAD_1" "$DEAD_2"; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    info "step 3: $f is tracked, will be removed"
  else
    info "step 3: $f is not tracked, already removed"
  fi
done

# ==============================================================================
step 1 "the three item-39 rule_id edits in $LABELS"
# ==============================================================================
# Zero detection code changes. The scan is byte-identical either side; only the scoring
# key moves. Each label corrects three counters at once, because a mislabelled detection
# is scored as a miss AND as a false alarm.

snapshot labels.before "$LABELS"

for edit in "${EDITS[@]}"; do
  IFS='|' read -r lineno old new label <<< "$edit"
  if line_is "$LABELS" "$lineno" "$new"; then
    info "SKIP $LABELS:$lineno already reads the corrected value"
    continue
  fi
  info "edit $LABELS:$lineno  ($label)"
  python3 - "$LABELS" "$lineno" "$old" "$new" <<'PY'
import sys

path, lineno, old, new = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
with open(path, encoding="utf-8") as fh:
    lines = fh.readlines()

idx = lineno - 1
if lines[idx].rstrip("\n") != old:
    sys.exit(f"{path}:{lineno} changed under us: {lines[idx]!r}")

# Rewrite the one line, preserving its exact line ending. No other byte moves.
lines[idx] = new + lines[idx][len(lines[idx].rstrip("\n")):]
with open(path, "w", encoding="utf-8") as fh:
    fh.writelines(lines)
PY
done

show_diff labels.before "$LABELS"

printf '\n    verify:\n'
for edit in "${EDITS[@]}"; do
  IFS='|' read -r lineno old new label <<< "$edit"
  line_is "$LABELS" "$lineno" "$new" || fail "$LABELS:$lineno is not the corrected value"
  ok "$LABELS:$lineno  ->  $(sed -n "${lineno}p" "$LABELS" | sed 's/^ *//')"
done

CHANGED=$(diff "$SNAP_DIR/labels.before" "$LABELS" | grep -c '^[<>]' || true)
[ "$CHANGED" -le 6 ] || fail "expected at most 3 changed lines (6 diff lines), got $CHANGED"
ok "no adjacent line touched — owasp_id on line 1670 deliberately left alone (RELEASE_CHECKLIST.md § 1)"

python3 -c "import sys,yaml;yaml.safe_load(open(sys.argv[1],encoding='utf-8'))" "$LABELS" 2>/dev/null \
  && ok "$LABELS still parses as YAML" \
  || info "NOTE could not parse-check $LABELS (PyYAML not importable here); the edit is one token on one line"

# ==============================================================================
step 2 "the ratchet in $GATES: recall_min 0.81 -> 0.82, f1_min 0.72 -> 0.73"
# ==============================================================================
# Derived in RELEASE_CHECKLIST.md § 2: measured (after step 1) minus a zero run-to-run
# spread minus a 0.02 margin, truncated. precision_min stays at 0.66.

snapshot gates.before "$GATES"

python3 - "$GATES" <<'PY'
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    text = fh.read()

# layer1.thresholds only — the target block below it keeps its aspirational numbers, and
# per_asi_recall_min is untouched. Anchored on the exact four-space indent of that block.
targets = (("recall_min", "0.81", "0.82"), ("f1_min", "0.72", "0.73"))
for key, old, new in targets:
    pattern = re.compile(rf"^(    {key}: ){re.escape(old)}$", re.MULTILINE)
    updated, count = pattern.subn(rf"\g<1>{new}", text)
    if count == 1:
        text = updated
    elif count == 0 and re.search(rf"^    {key}: {re.escape(new)}$", text, re.MULTILINE):
        pass  # already applied
    else:
        sys.exit(f"{path}: expected exactly one '    {key}: {old}', found {count}")

with open(path, "w", encoding="utf-8") as fh:
    fh.write(text)
PY

show_diff gates.before "$GATES"

printf '\n    verify:\n'
python3 - "$GATES" <<'PY'
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not importable — cannot verify gates.yaml; install it and re-check")

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    cfg = yaml.safe_load(fh)

thresholds = cfg["layer1"]["thresholds"]
expected = {"precision_min": 0.66, "recall_min": 0.82, "f1_min": 0.73}
for key, want in expected.items():
    got = thresholds[key]
    if got != want:
        sys.exit(f"    FAIL layer1.thresholds.{key} = {got}, expected {want}")
    print(f"    OK   layer1.thresholds.{key} = {got}")

target = cfg["layer1"]["target"]
if (target["precision_min"], target["recall_min"], target["f1_min"]) != (0.90, 0.85, 0.87):
    sys.exit("    FAIL layer1.target moved — it is aspirational and must not be ratcheted")
print("    OK   layer1.target unchanged (0.90 / 0.85 / 0.87)")

if len(cfg["layer1"]["per_asi_recall_min"]) != 10:
    sys.exit("    FAIL per_asi_recall_min no longer has ten categories")
print("    OK   per_asi_recall_min untouched (10 categories)")
PY

# ==============================================================================
step 3 "git rm the two dead threshold files (docs/decisions/DEAD_FILES.md)"
# ==============================================================================
# Nothing in the repository loads either one. Every surviving mention is a comment, an
# assertion message, or a path string used as guard test data.

git ls-files tests/benchmark/ > "$SNAP_DIR/tracked.before"

for f in "$DEAD_1" "$DEAD_2"; do
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    info "git rm $f"
    git rm --quiet "$f"
  else
    info "SKIP $f already untracked"
  fi
done

git ls-files tests/benchmark/ > "$SNAP_DIR/tracked.after"

printf '\n--- diff: git ls-files tests/benchmark/\n'
diff -u --label "a/tracked" --label "b/tracked" "$SNAP_DIR/tracked.before" "$SNAP_DIR/tracked.after" || true

printf '\n    verify:\n'
for f in "$DEAD_1" "$DEAD_2"; do
  git ls-files --error-unmatch "$f" >/dev/null 2>&1 && fail "$f is still tracked"
  [ -e "$f" ] && fail "$f still exists in the working tree"
  ok "$f removed from the index and the working tree"
done
[ -f "$GATES" ] || fail "$GATES was removed — only the two quality_gates* files should go"
ok "$GATES untouched by step 3"

# ==============================================================================
printf '\n=== DONE — three steps applied, nothing committed.\n'
printf '\nStaged and unstaged changes:\n'
git status --short -- "$LABELS" "$GATES" "$DEAD_1" "$DEAD_2"
cat <<'NEXT'

Not done by this script, on purpose:

  # re-measure Layer 1 (RELEASE_CHECKLIST.md § 1 predicts F1 0.746667 -> 0.758095)
  cd packages/audit && python3 ../../tests/benchmark/precision_recall.py

  # the raised ratchet must still pass
  python3 tests/benchmark/quality_gate_check.py --config tests/benchmark/gates.yaml

  # the deletions must not disturb these (docs/decisions/DEAD_FILES.md)
  bash .claude/hooks/test-guard.sh
  python3 -m pytest tests/test_layer1_gate_singleton.py -q

  # tests/README.md:40 still lists quality_gates.yaml — that edit is RELEASE_CHECKLIST.md § 4

Three labels still cite a rule with no producer, so tests/test_corpus_label_rules.py
stays red. That is item 39's open half; see docs/decisions/AGENT-015_RESOLUTION.md § 4.
NEXT
