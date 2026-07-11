#!/usr/bin/env bash
# Self-test for the H7 trace extractors + diff, run against the committed
# historical Xenia log (xenia_automation/output/xenia.log). Doubles as living
# documentation of expected behavior and as a regression guard. No Docker/GPU
# needed. Exit 0 = all invariants hold.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../shlib/common.sh"

LOG="$OUTPUT_DIR/xenia.log"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
check() { if [ "$1" = "$2" ]; then log_ok "$3 ($1)"; else log_err "$3: expected $2 got $1"; fail=1; fi; }
check_ge() { if [ "$1" -ge "$2" ]; then log_ok "$3 ($1 >= $2)"; else log_err "$3: $1 < $2"; fail=1; fi; }

[ -f "$LOG" ] || die "reference log not found: $LOG"

# --- file trace ---------------------------------------------------------------
python3 "$HERE/extract_file_trace.py" "$LOG" --unique --out "$TMP/ref.txt" 2>/dev/null
n=$(grep -c . "$TMP/ref.txt")
check_ge "$n" 40 "file_trace: unique paths extracted"
grep -qxF 'default.xex' "$TMP/ref.txt" && log_ok "file_trace: default.xex present" || { log_err "default.xex missing"; fail=1; }
grep -qF 'config.ini' "$TMP/ref.txt" && log_ok "file_trace: config.ini present" || { log_err "config.ini missing"; fail=1; }
grep -q 'terrain.fxobj' "$TMP/ref.txt" && log_ok "file_trace: shader landmark present" || { log_err "shader missing"; fail=1; }

# --- diff invariants ----------------------------------------------------------
python3 "$HERE/diff_trace.py" "$TMP/ref.txt" "$TMP/ref.txt" >/dev/null 2>&1
check "$?" 0 "diff: identical trace -> PASS"

head -n -5 "$TMP/ref.txt" > "$TMP/miss.txt"
python3 "$HERE/diff_trace.py" "$TMP/ref.txt" "$TMP/miss.txt" >/dev/null 2>&1
check "$?" 2 "diff: 5 missing landmarks -> FAIL"

grep -v '^default.xex$' "$TMP/ref.txt" > "$TMP/reorder.txt"; echo 'default.xex' >> "$TMP/reorder.txt"
python3 "$HERE/diff_trace.py" "$TMP/ref.txt" "$TMP/reorder.txt" >/dev/null 2>&1
check "$?" 2 "diff: reordered landmark -> FAIL"

head -n -1 "$TMP/ref.txt" > "$TMP/1miss.txt"
python3 "$HERE/diff_trace.py" "$TMP/ref.txt" "$TMP/1miss.txt" >/dev/null 2>&1
check "$?" 0 "diff: 1 miss within tolerance -> PASS"

# --- kernel trace -------------------------------------------------------------
python3 "$HERE/extract_kernel_trace.py" "$LOG" --out "$TMP/kern.txt" 2>/dev/null
grep -q 'IoDismountVolumeByFileHandle' "$TMP/kern.txt" && log_ok "kernel_trace: runtime gap captured" || { log_err "kernel gap missing"; fail=1; }
grep -q 'xboxkrnl.exe: 350 imports' "$TMP/kern.txt" && log_ok "kernel_trace: import banner captured" || { log_err "import banner missing"; fail=1; }

# --- crash extract ------------------------------------------------------------
python3 "$HERE/extract_crash.py" "$LOG" --context 12 --out "$TMP/crash.txt" 2>/dev/null
check "$?" 0 "crash: dump detected in historical log"
grep -q 'Access Violation' "$TMP/crash.txt" && log_ok "crash: access-violation line captured" || { log_err "crash detail missing"; fail=1; }
# a clean log must report no crash (rc 1)
printf 'i> hello\ni> world\n' > "$TMP/clean.log"
python3 "$HERE/extract_crash.py" "$TMP/clean.log" >/dev/null 2>&1
check "$?" 1 "crash: clean log -> no crash (rc1)"

echo
[ "$fail" = 0 ] && log_ok "ALL TRACE SELF-TESTS PASSED" || log_err "TRACE SELF-TESTS FAILED"
exit "$fail"
