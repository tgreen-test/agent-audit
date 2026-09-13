#!/usr/bin/env bash
# Self-test for .claude/hooks/night-guard.sh — the 11 cases from RUN3 W9.
#
# Exit 0 = every case behaves as specified. Exit 1 = the guard is weaker or
# stronger than intended. If a case fails, fix the guard, not the expectation.
#
# Run:  ./.claude/hooks/test-guard.sh              # tests the installed guard
#       ./.claude/hooks/test-guard.sh /path/to/other-guard.sh
#
# The optional argument exists so an archived pre-fix guard can be put through
# the identical 11 cases — that is how W9's BEFORE was made falsifiable after
# the hook had already been repaired by hand.
#
# Note: the protected paths live inside this file rather than on a command line,
# because the guard (correctly) blocks any Bash command that redirects onto one.
#
# Case 1/2 exist because the pattern `eval/` used to substring-match
# `audit-eval/` and blocked the entire Phase -1 deliverable.
# Cases 8/9 exist because the guard used to inspect Edit/Write file paths but
# not Bash-authored writes (`>`, `tee`, `sed -i`, `cp`, `mv`).

set -u

HERE=$(cd "$(dirname "$0")" && pwd)
GUARD="${1:-$HERE/night-guard.sh}"

[ -x "$GUARD" ] || { echo "FATAL: $GUARD is missing or not executable" >&2; exit 1; }

pass=0
fail=0

# run <expected_exit> <key: command|file_path> <value> <label>
run() {
  local expected="$1" key="$2" value="$3" label="$4"
  local payload actual
  payload=$(EK="$key" EV="$value" python3 -c '
import json, os
print(json.dumps({"tool_input": {os.environ["EK"]: os.environ["EV"]}}))')
  printf '%s' "$payload" | "$GUARD" >/dev/null 2>&1
  actual=$?
  if [ "$actual" = "$expected" ]; then
    printf 'ok    exit=%s  %-12s %s\n' "$actual" "$key" "$label"
    pass=$((pass + 1))
  else
    printf 'FAIL  exit=%s (want %s)  %-12s %s\n' "$actual" "$expected" "$key" "$label"
    fail=$((fail + 1))
  fi
}

echo "== night-guard self-test (11 cases) =="
echo "guard: $GUARD"

# --- allow: the harness deliverable must not be blocked -------------------
run 0 file_path '/repo/audit-eval/score.py'                        'audit-eval/ is not eval/'
run 0 file_path '/repo/audit-eval/run_eval.sh'                     'audit-eval/ is not eval/'

# --- block: benchmark / corpus / oracle paths -----------------------------
run 2 file_path '/repo/eval/snapshot/x.md'                         'eval/ corpus'
run 2 file_path '/repo/bench/oracle.yaml'                          'oracle file'
run 2 file_path '/repo/tests/benchmark/quality_gates_v2.yaml'      'quality gate file'
run 2 file_path '/repo/tests/fixtures/a.py'                        'frozen fixture'

# --- allow: ordinary product source ---------------------------------------
run 0 file_path '/repo/packages/audit/agent_audit/x.py'            'product source'

# --- block: Bash-authored writes onto protected paths ----------------------
run 2 command   'echo 0.9 > tests/benchmark/quality_gates_v2.yaml' 'redirect onto gate file'
run 2 command   'sed -i s/a/b/ tests/fixtures/a.py'                'sed -i onto fixture'

# --- allow: ordinary work ---------------------------------------------------
run 0 command   'python3 -m pytest tests/ -q'                      'running the suite'

# --- block: shared-state git operations ------------------------------------
run 2 command   'git push origin master'                           'git push'

echo "-----------------------------------------"
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ] || exit 1
