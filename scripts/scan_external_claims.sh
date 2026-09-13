#!/usr/bin/env bash
#
# scan_external_claims.sh — find retracted and stale agent-audit figures in
# external material: papers, slide decks, outreach archives, anything.
#
#   ./scripts/scan_external_claims.sh ~/Documents/papers
#   ./scripts/scan_external_claims.sh --list                 # just print the table
#   ./scripts/scan_external_claims.sh --strict DIR           # exit 1 if anything matches
#
# Why this exists. docs/decisions/METRICS_RETRACTION.md section 5 step 1 is the release
# blocker for v0.20.0: the in-repo half of the retraction is done, and the published half
# cannot start until someone knows which external surfaces carry the retracted 98.51%.
# Only Heady can search a paper, a slide deck or an outreach archive. This narrows that
# from an afternoon to a few minutes.
#
# It reads. It never writes, never edits, never uploads. Run it wherever you like.
#
# Binary formats are handled, because that is where the risk actually is: a PDF preprint
# and a .pptx deck are the two most likely carriers, and plain grep is blind to both.
#   PDF          -> pdftotext if installed (brew install poppler), else reported as UNREAD
#   pptx/docx    -> unzipped in a temp dir and searched as XML
#   key/pages    -> reported as UNREAD; Keynote stores a binary plist that grep cannot read
#
# Exit status: 0 if the scan completed, 2 on usage error. Matches do not change it unless
# --strict is given. A finding here is not a failure; it is a to-do.

set -uo pipefail

SELF="$(basename "$0")"
STRICT=0
LIST_ONLY=0
ALLOWLIST=""
DIRS=()

# ---------------------------------------------------------------------------
# The patterns.
#
# Format: LABEL|CLASS|REGEX|WHAT IS TRUE NOW
#
# CLASS is the correction that applies, and it is not cosmetic — it decides what you
# write when you find one:
#   RETRACT  the figure was never a measurement. It is withdrawn with a stated mechanism,
#            not updated, because there is no commit to update it to.
#   UPDATE   a real measurement that has drifted. Restate it, with the causal note.
#   UNSUB    never reproducible from the repository. Commit the data or drop the claim.
#   COUNT    a stale count. Mechanical.
#
# Regexes are extended POSIX (grep -E) and deliberately loose: a slide will not use the
# repository's wording, and a false hit costs one glance while a miss costs a correction.
# ---------------------------------------------------------------------------
PATTERNS=(
# --- the four retracted figures, and every numeric form they take -----------
'P-98.51|RETRACT|98[.,]51|no current equivalent — the figure is withdrawn. Measured precision today is 68.86%'
'P-98.51-dec|RETRACT|0[.,]9851|as above'
'P-98.5-round|RETRACT|(precision|Precision|准确率|精确率)[^0-9]{0,24}98[.,]5([^0-9]|$)|as above'
'R-100|RETRACT|(recall|Recall|召回率)[^0-9%]{0,24}(100([.,]0+)?[[:space:]]*%|1[.,]00?([^0-9]|$))|recall was never measured; it was set to 1.0. Measured recall today is 84.32%'
'R-100-alt|RETRACT|100[[:space:]]*%[[:space:]]*(recall|Recall)|as above'
'R-0FN|RETRACT|(0|zero|no)[[:space:]]+(false[[:space:]]+negatives?|FNs?)([^a-zA-Z]|$)|the FN=0 assumption itself. Measured FN today is 37'
'F1-99.25|RETRACT|99[.,]2[45]|no current equivalent. Measured F1 today is 0.7581'
'F1-99-dec|RETRACT|0[.,]992[45]|as above'
'F1-100|RETRACT|(F1|F-1|F score|F1-Score)[^0-9]{0,20}(100[[:space:]]*%|1[.,]00?([^0-9]|$))|CHANGELOG 0.4.1. Never measured. Today 0.7581'
'FPR-1.49|RETRACT|1[.,]49[[:space:]]*%|the complement of 98.51. Measured FP rate today is 31.14%'
'P-100|RETRACT|(precision|Precision)[^0-9]{0,24}100[[:space:]]*%|the *target* block of the v0.4.1 brief, published as a result. Today 68.86%'
'ARROW|RETRACT|98[.,]51[[:space:]]*%?[[:space:]]*(->|-->|→|to)[[:space:]]*100|CHANGELOG.md:175. A delta between an assumed figure and a goal, presented as a result'
# --- the corpus description that made 198 look like a measured denominator --
'GT-198|RETRACT|198[[:space:]]*(annotations?|labels?|标注)|the corpus is v2.2, 81 files, 238 labels'
'GT-201|RETRACT|201[[:space:]]*(total|samples?|annotations?)|as above; 201 was 198+3 and is not a corpus size'
'GT-v2.1|UPDATE|v2[.,]1[^0-9]{0,30}(42|corpus|ground)|corpus is v2.2 / 81 files / 238 labels'
'GT-42|UPDATE|42[[:space:]]*(sample[[:space:]]*files?|samples?)([^0-9]|$)|81 sample files'
# --- the drifted 0.778 family: update, do not retract ----------------------
'F1-0.778|UPDATE|0[.,]778[0-9]*|F1 0.7581 today. The drop is NOT a regression — see METRICS_RETRACTION section 3(a)'
'F1-77.8|UPDATE|77[.,]8[[:space:]]*%|as above'
'P-73.58|UPDATE|73[.,]58|precision 68.86% today, and it fell because discovery bugs were FIXED'
'R-82.63|UPDATE|82[.,]63|recall 84.32% today'
'TPFP-195|UPDATE|195[^0-9]{1,12}(70|41)|TP 199 / FP 90 / FN 37'
'F1-0.84adj|UPDATE|0[.,]84[0-6]|the ADJUSTED F1. Never a headline figure. If it is being used as one, that is the 98.51 again in the other direction'
# --- the RUN6-era interim figures, if any of those escaped -----------------
'F1-0.7467|UPDATE|0[.,]746[0-9]*|superseded. F1 0.7581 today, after three ground-truth label corrections'
'P-67.82|UPDATE|67[.,]82|precision 68.86% today'
'R-83.05|UPDATE|83[.,]05|recall 84.32% today'
# --- claims with no data in the repository --------------------------------
'CLAWHUB|UNSUB|18[.,]?899|no committed data reproduces the ClawHub scan. See OUTREACH_CLAIMS.md section 3'
'PREC-80|UNSUB|80[[:space:]]*%[^.]{0,30}(precision|Precision)|the 20-sample manual draw. No data, no methodology in the repo'
'PREC-80r|UNSUB|(precision|Precision)[^0-9]{0,30}80[[:space:]]*%|as above'
'WILSON|UNSUB|Wilson|the 58.4-91.9 CI travels with the unsubstantiated 80%'
'FINDINGS|UNSUB|13[.,]?355|ClawHub scan total. Unsubstantiated'
'BLOCKN|UNSUB|1[.,]?492[[:space:]]*(BLOCK|critical)|as above'
# --- rule counts: one set, nine numbers ------------------------------------
'RULES-N|COUNT|(^|[^0-9])(40|49|52|53|56|63|72|92)[[:space:]]*\+?[[:space:]]*(detection[[:space:]]+)?(rules|Rules|条规则|条检测规则)|66 rules. The one-line check is in the legend printed after a scan'
# --- test counts -----------------------------------------------------------
'TESTS-N|COUNT|(1,?14[12]|1,?322|1,?54[12]|1,?748|1,?796|1,?808|1,?88[37]|1,?891|1,?895|1,?904|1,?905)[[:space:]]*\+?[[:space:]]*(tests?|passing|passed)|1,924 passing (pytest tests/ packages/audit/tests/), 1 red on purpose'
# --- version -----------------------------------------------------------
'VER|COUNT|v?0[.,](4[.,]1|5[.,]2|16[.,]0|18[.,]2|19[.,][02])([^0-9]|$)|current version is 0.20.0'
)

usage() {
    cat <<'HELPTEXT'
scan_external_claims.sh — find retracted and stale agent-audit figures in external material.

USAGE
    scan_external_claims.sh [options] DIR [DIR...]
    scan_external_claims.sh --list

OPTIONS
    --list              print the pattern table and exit; scan nothing
    --strict            exit 1 if any match is found (for CI); default exit is 0
    --allowlist FILE    skip paths whose text appears in FILE, one substring per line.
                        Use scripts/external_claims_allowlist.txt when scanning this
                        repository, which is full of documents whose job is to quote
                        these figures.

WHAT TO DO WITH A HIT — the class in brackets decides it:
    [RETRACT]  the figure was never a measurement. Withdraw it with the mechanism stated;
               do NOT quietly update it. Draft wording: METRICS_RETRACTION.md section 4.
    [UPDATE]   a real measurement that drifted. Restate it WITH the causal note, or the
               restatement reads as a quality regression that did not happen.
    [UNSUB]    nothing in the repository can reproduce it. Commit the data or cut the
               claim. See OUTREACH_CLAIMS.md.
    [COUNT]    mechanical. Substitute the current value.

Reads only. Never writes, edits, or uploads anything.
HELPTEXT
}

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --list) LIST_ONLY=1; shift ;;
        --strict) STRICT=1; shift ;;
        --allowlist)
            [ $# -ge 2 ] || { echo "$SELF: --allowlist needs a file" >&2; exit 2; }
            ALLOWLIST="$2"; shift 2 ;;
        -*) echo "$SELF: unknown option $1" >&2; usage >&2; exit 2 ;;
        *) DIRS+=("$1"); shift ;;
    esac
done

if [ "$LIST_ONLY" -eq 1 ]; then
    printf '%-14s %-8s %s\n' "LABEL" "CLASS" "WHAT IS TRUE NOW"
    printf '%-14s %-8s %s\n' "-----" "-----" "----------------"
    for entry in "${PATTERNS[@]}"; do
        label="${entry%%|*}"; rest="${entry#*|}"
        class="${rest%%|*}";  rest="${rest#*|}"
        truth="${rest##*|}"
        printf '%-14s %-8s %s\n' "$label" "$class" "$truth"
    done
    exit 0
fi

# ---------------------------------------------------------------------------
# Validate every pattern before scanning.
#
# Why this exists. Until 2026-09-10 the scan loop extracted the regex by cutting the
# entry at its FIRST '|'. Every pattern using alternation was therefore truncated
# mid-group -- 'R-100' became '(recall', an unbalanced parenthesis. grep rejected
# each one, the error went to /dev/null, and the scan reported 0 matches for it. 18
# of 34 patterns were dead for the tool's entire life, including every form of the
# retracted "100% recall" and "0 false negatives" claims, and the 80%-precision
# pattern this release was written to catch.
#
# The bug was invisible because a broken pattern and a clean surface produce the
# same output: nothing. So the tool now proves its instrument works before trusting
# it, and fails loudly rather than quietly under-reporting.
# ---------------------------------------------------------------------------
validate_patterns() {
    local bad=0 entry label rest regex status
    for entry in "${PATTERNS[@]}"; do
        label="${entry%%|*}"; rest="${entry#*|}"
        rest="${rest#*|}"
        regex="${rest%|*}"
        # grep exits 0 on match, 1 on no match, >=2 on a malformed pattern.
        printf '' | grep -qE -e "$regex" >/dev/null 2>&1
        status=$?
        if [ "$status" -ge 2 ]; then
            echo "$SELF: pattern '$label' is not a valid regex: $regex" >&2
            bad=$((bad + 1))
        fi
    done
    if [ "$bad" -gt 0 ]; then
        echo "$SELF: $bad of ${#PATTERNS[@]} patterns are invalid. Refusing to present a" >&2
        echo "$SELF: partial scan as a complete one -- fix the patterns and re-run." >&2
        exit 2
    fi
}

if [ "${#DIRS[@]}" -eq 0 ]; then
    echo "$SELF: no directory given" >&2
    usage >&2
    exit 2
fi

for d in "${DIRS[@]}"; do
    [ -d "$d" ] || { echo "$SELF: not a directory: $d" >&2; exit 2; }
done

if [ -n "$ALLOWLIST" ] && [ ! -f "$ALLOWLIST" ]; then
    echo "$SELF: allowlist not found: $ALLOWLIST" >&2
    exit 2
fi

validate_patterns

WORK="$(mktemp -d "${TMPDIR:-/tmp}/scan_external_claims.XXXXXX")" || exit 2
trap 'rm -rf "$WORK"' EXIT INT TERM

EXTRACTED="$WORK/extracted"
mkdir -p "$EXTRACTED"

is_allowed() {
    [ -n "$ALLOWLIST" ] || return 1
    while IFS= read -r pat; do
        case "$pat" in ''|'#'*) continue ;; esac
        case "$1" in *"$pat"*) return 0 ;; esac
    done < "$ALLOWLIST"
    return 1
}

# ---------------------------------------------------------------------------
# Pass 1 — extract text from container formats into $EXTRACTED, keeping a map
# back to the real path so the report names the file the reader recognises.
# ---------------------------------------------------------------------------
MAP="$WORK/map.tsv"
: > "$MAP"
UNREAD="$WORK/unread.txt"
: > "$UNREAD"

have() { command -v "$1" >/dev/null 2>&1; }

n_pdf=0; n_office=0; n_opaque=0
while IFS= read -r f; do
    is_allowed "$f" && continue
    case "$(printf '%s' "$f" | tr '[:upper:]' '[:lower:]')" in
        *.pdf)
            if have pdftotext; then
                out="$EXTRACTED/pdf_$n_pdf.txt"
                if pdftotext -q -layout "$f" "$out" 2>/dev/null && [ -s "$out" ]; then
                    printf '%s\t%s\n' "$out" "$f" >> "$MAP"
                    n_pdf=$((n_pdf + 1))
                else
                    printf 'PDF unreadable (pdftotext failed): %s\n' "$f" >> "$UNREAD"
                fi
            else
                printf 'PDF not searched (pdftotext not installed — brew install poppler): %s\n' "$f" >> "$UNREAD"
            fi
            ;;
        *.pptx|*.docx|*.xlsx|*.odp|*.odt)
            if have unzip; then
                d="$EXTRACTED/office_$n_office"
                mkdir -p "$d"
                if unzip -qq -o "$f" -d "$d" 2>/dev/null; then
                    printf '%s\t%s\n' "$d" "$f" >> "$MAP"
                    n_office=$((n_office + 1))
                else
                    printf 'Office file unreadable: %s\n' "$f" >> "$UNREAD"
                fi
            else
                printf 'Office file not searched (unzip missing): %s\n' "$f" >> "$UNREAD"
            fi
            ;;
        *.key|*.pages|*.numbers)
            printf 'Keynote/Pages/Numbers NOT SEARCHABLE by any tool here — open and check by hand: %s\n' "$f" >> "$UNREAD"
            n_opaque=$((n_opaque + 1))
            ;;
    esac
done < <(find "${DIRS[@]}" \
            \( -name .git -o -name node_modules -o -name .venv -o -name venv \
               -o -name __pycache__ -o -name dist -o -name build \) -prune -o \
            -type f -print 2>/dev/null)

# ---------------------------------------------------------------------------
# Pass 2 — grep. Plain text first, then each extracted container.
# ---------------------------------------------------------------------------
HITS="$WORK/hits.txt"
: > "$HITS"

report_for() {
    # $1 = root to grep, $2 = label, $3 = regex, $4 = display-path override ("" = real path)
    local root="$1" label="$2" regex="$3" display="$4"
    grep -rnIE --binary-files=without-match \
        --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
        --exclude-dir=venv --exclude-dir=__pycache__ --exclude-dir=dist \
        --exclude-dir=build \
        -e "$regex" "$root" 2>/dev/null | while IFS= read -r line; do
            local path="${line%%:*}"
            local rest="${line#*:}"
            local lineno="${rest%%:*}"
            local text="${rest#*:}"
            if [ -n "$display" ]; then
                path="$display"
                lineno="-"
            else
                is_allowed "$path" && continue
            fi
            # squeeze whitespace, clip long lines
            text="$(printf '%s' "$text" | tr -s '[:space:]' ' ' | cut -c1-140)"
            printf '%s\t%s\t%s\t%s\n' "$label" "$path" "$lineno" "$text"
        done >> "$HITS"
}

for entry in "${PATTERNS[@]}"; do
    label="${entry%%|*}"; rest="${entry#*|}"
    class="${rest%%|*}";  rest="${rest#*|}"
    # The regex may itself contain '|' (alternation), so split from the RIGHT: the
    # last field is the truth text, everything before it is the pattern. Splitting
    # from the left truncated 18 of 34 patterns at their first alternation, leaving
    # an unbalanced paren that grep rejected -- silently, because stderr is
    # discarded. See _validate_patterns below, which now makes that loud.
    regex="${rest%|*}"
    for d in "${DIRS[@]}"; do
        report_for "$d" "$label [$class]" "$regex" ""
    done
    if [ -s "$MAP" ]; then
        while IFS="$(printf '\t')" read -r extracted real; do
            report_for "$extracted" "$label [$class]" "$regex" "$real"
        done < "$MAP"
    fi
done

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
echo "============================================================"
echo " agent-audit external claims scan"
echo " roots: ${DIRS[*]}"
[ -n "$ALLOWLIST" ] && echo " allowlist: $ALLOWLIST"
echo " patterns: ${#PATTERNS[@]} (all validated)"
echo " containers opened: $n_pdf PDF, $n_office Office"
echo "============================================================"
echo

if [ -s "$HITS" ]; then
    sort -u "$HITS" | sort -t"$(printf '\t')" -k2,2 -k3,3n | \
        awk -F'\t' '{ printf "%-22s %s:%s\n      %s\n", $1, $2, $3, $4 }'
    echo
fi

n_hits=$(sort -u "$HITS" | grep -c . 2>/dev/null || true)
n_hits=${n_hits:-0}

if [ -s "$UNREAD" ]; then
    echo "------------------------------------------------------------"
    echo " NOT SEARCHED — check these by hand:"
    echo "------------------------------------------------------------"
    sed 's/^/  /' "$UNREAD"
    echo
fi

echo "------------------------------------------------------------"
echo " $n_hits match(es)."
if [ "$n_hits" -gt 0 ]; then
    cat <<'LEGEND'

 [RETRACT] never a measurement — withdraw with the mechanism stated, do not
           update. Wording: docs/decisions/METRICS_RETRACTION.md section 4.
 [UPDATE]  drifted measurement — restate WITH the causal note, or it reads as a
           regression that did not happen. Section 3(a).
 [UNSUB]   no data in the repository — commit it or cut the claim. OUTREACH_CLAIMS.md.
 [COUNT]   mechanical substitution.

 Current values, and the commands that produce them:
   P 68.86% / R 84.32% / F1 0.7581, TP 199 / FP 90 / FN 37
     cd packages/audit && python3 ../../tests/benchmark/precision_recall.py
   66 rules
     python3 -c "import sys;sys.path.insert(0,'tests');from test_rule_producers import advertised_rules;print(len(advertised_rules()))"
   1,924 tests passing, 1 red by design
     python3 -m pytest tests/ packages/audit/tests/ -q
   AVB knowns: R 100.0% / P 88.0% / F1 0.9362  (unaffected — measured against an oracle)
     cd tests/benchmark && python3 -m "agent-vuln-bench.harness.run_eval" --tool agent-audit --dataset knowns
LEGEND
fi
echo "------------------------------------------------------------"

if [ "$STRICT" -eq 1 ] && [ "$n_hits" -gt 0 ]; then
    exit 1
fi
exit 0
