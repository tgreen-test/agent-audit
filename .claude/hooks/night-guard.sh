#!/usr/bin/env bash
command -v python3 >/dev/null 2>&1 || { echo "BLOCKED: guard 需要 python3" >&2; exit 2; }
D=$(cat)
CMD=$(printf '%s' "$D" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
FP=$(printf '%s' "$D" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
deny(){ echo "BLOCKED: $1。写进 DECISIONS.md 由 Heady 处理,不要绕过。" >&2; exit 2; }

PROTECTED='(^|/)(oracle[^/]*\.ya?ml|quality_gates[^/]*\.ya?ml)$|(^|/)datasets/(knowns|wilds|noise)/|(^|/)tests/ground_truth/|(^|/)tests/fixtures/|(^|/)eval/'

check_path(){ printf '%s' "$1" | grep -qE "$PROTECTED" && deny "$1 属于基准/语料。修工具,不要修基准"; }
[ -n "$FP" ] && check_path "$FP"
[ -z "$CMD" ] && exit 0

if printf '%s' "$CMD" | grep -qE '(>|tee[[:space:]]|sed[[:space:]]+-i|cp[[:space:]]|mv[[:space:]]|dd[[:space:]]|truncate[[:space:]])'; then
  for tok in $(printf '%s' "$CMD" | tr '|;&()<>"'"'"'' '\n' | tr -s ' \t' '\n' | grep -E '/|\.ya?ml$|\.json$'); do
    check_path "$tok"
  done
fi

printf '%s' "$CMD" | grep -qE '(^|[;&|[:space:]])git[[:space:]]+(push|merge|rebase|tag)' && deny "git push/merge/rebase/tag"
printf '%s' "$CMD" | grep -qE 'git[[:space:]]+(reset[[:space:]]+--hard|clean[[:space:]]+-[a-z]*f|branch[[:space:]]+-D|checkout[[:space:]]+\.)' && deny "破坏性 git 操作"
printf '%s' "$CMD" | grep -qE 'gh[[:space:]]+(pr|issue|release)[[:space:]]+(create|merge|close|edit|delete|comment)' && deny "gh 写操作"
printf '%s' "$CMD" | grep -qE '(twine[[:space:]]+upload|npm[[:space:]]+publish|poetry[[:space:]]+publish)' && deny "包发布"
printf '%s' "$CMD" | grep -qE 'rm[[:space:]]+-[a-z]*r[a-z]*f' && deny "rm -rf"
printf '%s' "$CMD" | grep -qE '(^|[[:space:]])pip[[:space:]]+install[^|]*agent-audit' && deny "重装 agent-audit 会掩盖 0.18.2 线索"
exit 0
