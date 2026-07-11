#!/usr/bin/env bash
# H6 — capture a committed reference bundle for a scenario.
#
# Runs the scenario N times (default 2), checks self-consistency (the file trace
# must match run-to-run; checkpoint screenshots are compared and reported), then
# promotes one run's artifacts into references/<scenario>/ as the milestone
# baseline the porting agent diffs against.
#
# Self-consistency is the H2 acceptance gate: two runs from the pinned config
# must agree. The file trace is the authoritative signal (deterministic);
# screenshot scores are reported and gate only if --strict-shots is given (frames
# with nondeterministic overlays — e.g. a crash dialog — legitimately vary).
#
# Usage:
#   capture_reference.sh <scenario> [--runs N] [--strict-shots] [--display MODE]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/shlib/common.sh"

scenario="${1:-}"; [ -n "$scenario" ] || die "usage: capture_reference.sh <scenario> [--runs N]"
shift || true
runs=2; strict_shots=0; display_args=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        --runs) runs="$2"; shift 2 ;;
        --strict-shots) strict_shots=1; shift ;;
        --display) display_args=(--display "$2"); shift 2 ;;
        *) die "unknown arg: $1" ;;
    esac
done
[ -f "$SCENARIOS_DIR/$scenario/script.txt" ] || die "no such scenario: $scenario"

work="$(mktemp -d)";
log_info "capturing '$scenario' x$runs for self-consistency (work: $work)"

statuses=()
for i in $(seq 1 "$runs"); do
    log_info "--- run $i/$runs ---"
    bash "$HERE/run_scenario.sh" "$scenario" --out "$work/run$i" "${display_args[@]}" >/dev/null 2>&1 || true
    st="$(python3 -c "import json;print(json.load(open('$work/run$i/result.json'))['status'])" 2>/dev/null || echo error)"
    statuses+=("$st")
    log_info "run $i status: $st"
done

# --- self-consistency: file traces must match across runs --------------------
consistent=1
for i in $(seq 2 "$runs"); do
    if ! python3 "$HERE/trace/diff_trace.py" "$work/run1/file_trace.txt" "$work/run$i/file_trace.txt" >/dev/null 2>&1; then
        log_warn "file trace run1 vs run$i DIVERGED"
        consistent=0
    else
        log_ok "file trace run1 == run$i"
    fi
done

# --- screenshot comparison (reported; gates only with --strict-shots) --------
shot_ok=1
if [ "$runs" -ge 2 ]; then
    for shot in "$work/run1"/*.png; do
        [ -e "$shot" ] || continue
        name="$(basename "$shot")"
        other="$work/run2/$name"
        [ -e "$other" ] || { log_warn "shot $name missing in run2"; continue; }
        if python3 "$HERE/compare_screens.py" "$shot" "$other" >/tmp/cmp.$$ 2>&1; then
            log_ok "shot $name consistent ($(grep -o 'combined=[0-9.]*' /tmp/cmp.$$))"
        else
            log_warn "shot $name differs ($(grep -o 'combined=[0-9.]*' /tmp/cmp.$$))"
            shot_ok=0
        fi
        rm -f /tmp/cmp.$$
    done
fi

gate_ok=$consistent
[ "$strict_shots" = 1 ] && [ "$shot_ok" = 0 ] && gate_ok=0

# --- promote run1 as the committed reference ---------------------------------
dest="$REFERENCES_DIR/$scenario"
if [ "$gate_ok" = 1 ]; then
    mkdir -p "$dest"
    rm -f "$dest"/*.png "$dest"/*.txt "$dest"/*.json 2>/dev/null || true
    cp "$work/run1"/*.png "$dest"/ 2>/dev/null || true
    cp "$work/run1"/file_trace.txt "$work/run1"/kernel_trace.txt "$work/run1"/result.json "$dest"/ 2>/dev/null || true
    [ -f "$work/run1/crash.txt" ] && cp "$work/run1/crash.txt" "$dest"/
    # keep the log gzipped (it can be large)
    gzip -c "$work/run1/run.log" > "$dest/run.log.gz" 2>/dev/null || true
    printf 'scenario=%s\nruns=%s\nstatuses=%s\nfile_trace_consistent=%s\nshots_consistent=%s\n' \
        "$scenario" "$runs" "${statuses[*]}" "$consistent" "$shot_ok" > "$dest/CONSISTENCY.txt"
    log_ok "reference promoted -> $dest (status: ${statuses[0]})"
else
    log_err "NOT promoting: self-consistency failed (file_trace=$consistent shots=$shot_ok)"
fi

rm -rf "$work"
[ "$gate_ok" = 1 ]
