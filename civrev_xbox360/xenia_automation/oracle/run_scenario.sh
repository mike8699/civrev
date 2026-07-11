#!/usr/bin/env bash
# H5 — scenario runner with watchdog and machine-readable result.
#
# Boots the game in the oracle container, executes a scenario script (waits,
# screenshots, input), watches for crash/hang/timeout, then emits result.json.
# This is the loop the porting agent (and capture_reference.sh) drive — no human
# needed to interpret a run.
#
# Usage:
#   run_scenario.sh <scenario> [--out DIR] [--game-dir DIR] [--keep] [--display MODE]
#     <scenario>   name under scenarios/ (boot, menu, newgame_20turns, save_load)
#     --out DIR    where to write screenshots + result.json (default output/<scenario>)
#     --game-dir   game tree to mount (default: extracted tree)
#     --keep       leave the container running after the scenario (for debugging)
#     --display    VULKAN_DISPLAY mode (default: lavapipe)
#
# result.json: { scenario, status, checkpoints{}, crash{}, started, ended, seconds,
#                log, xenia_exited }
#   status: title|completed|crash|hang|timeout|boot_fail|error
# Exit: 0 if status is a "healthy" terminal (completed/title), else nonzero.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/shlib/common.sh"
source "$HERE/shlib/container.sh"
source "$HERE/shlib/gpu_lock.sh"

scenario="${1:-}"; [ -n "$scenario" ] || die "usage: run_scenario.sh <scenario> [opts]"
shift || true
out_dir=""; game_dir="$EXTRACTED_TREE"; keep=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --out) out_dir="$2"; shift 2 ;;
        --game-dir) game_dir="$2"; shift 2 ;;
        --keep) keep=1; shift ;;
        --display) export VULKAN_DISPLAY="$2"; shift 2 ;;
        *) die "unknown arg: $1" ;;
    esac
done

script="$SCENARIOS_DIR/$scenario/script.txt"
[ -f "$script" ] || die "scenario script not found: $script"
[ -z "$out_dir" ] && out_dir="$OUTPUT_DIR/$scenario"
mkdir -p "$out_dir"

# --- run state ---------------------------------------------------------------
declare -A CHECKPOINTS
STATUS="error"
STARTED="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo n/a)"
START_EPOCH="$(date +%s)"
CRASH_FOUND=0

log_path_host="$out_dir/run.log"

crash_seen() { oracle_exec sh -c 'grep -qE "==== CRASH DUMP ====|Access Violation|SIGSEGV" /output/run.log 2>/dev/null'; }

do_shot() {
    local name="$1"
    if bash "$HERE/screenshot.sh" "$name" --dir "$out_dir" >/dev/null 2>&1; then
        CHECKPOINTS["$name"]="$out_dir/$name.png"
        log_ok "checkpoint $name"
    else
        log_warn "checkpoint $name FAILED to capture"
        CHECKPOINTS["$name"]="MISSING"
    fi
}

# wait_stable <idle_secs> [timeout] : wait until the SCREEN stops changing for
# idle_secs (and is non-black). Robustly detects the end of the intro logos+CG —
# the title "Press START" screen is static, the intro is a moving video — without
# pressing anything (skipping mid-CG can freeze Xenia's Bink decode).
do_wait_stable() {
    local idle="$1"; local timeout="${2:-120}"; local waited=0 stable=0
    local prev="$out_dir/.ws_prev.png" cur="$out_dir/.ws_cur.png"; rm -f "$prev"
    local step=3
    while [ "$waited" -lt "$timeout" ]; do
        oracle_exec import -window root /tmp/ws.png >/dev/null 2>&1
        docker cp "$ORACLE_CONTAINER:/tmp/ws.png" "$cur" >/dev/null 2>&1 || { sleep "$step"; waited=$((waited+step)); continue; }
        if [ -f "$prev" ]; then
            local sim nb
            sim="$(python3 "$HERE/compare_screens.py" "$prev" "$cur" --threshold 0 2>/dev/null | grep -oE 'combined=[0-9.]+' | cut -d= -f2)"
            nb="$(python3 -c "from PIL import Image;import numpy as np;a=np.asarray(Image.open('$cur').convert('L'));print(1 if float((a>16).mean())>0.25 else 0)" 2>/dev/null)"
            if python3 -c "exit(0 if ${sim:-0}>0.985 and ${nb:-0}==1 else 1)" 2>/dev/null; then
                stable=$((stable+step)); [ "$stable" -ge "$idle" ] && { rm -f "$prev" "$cur"; log_info "screen stable (${idle}s)"; return 0; }
            else stable=0; fi
        fi
        cp "$cur" "$prev"; sleep "$step"; waited=$((waited+step))
    done
    rm -f "$prev" "$cur"; log_warn "wait_stable timed out"; return 0
}

# wait_text <pattern> [timeout] : wait until OCR of the screen matches <pattern>
# (case-insensitive regex). Robustly detects a specific UI state (e.g. the
# "Press START" title) regardless of boot speed. OCR runs host-side (tesseract).
do_wait_text() {
    local pattern="$1"; local timeout="${2:-90}"; local waited=0
    local shot="$out_dir/.ocr.png"
    # Prefer OCR inside the container (self-contained); fall back to host
    # tesseract for images predating the Dockerfile's tesseract-ocr.
    local in_container=0
    oracle_exec sh -c 'command -v tesseract' >/dev/null 2>&1 && in_container=1
    while [ "$waited" -lt "$timeout" ]; do
        oracle_exec import -window root /tmp/ocr.png >/dev/null 2>&1
        if [ "$in_container" = 1 ]; then
            if oracle_exec python3 /oracle/ocr.py /tmp/ocr.png "$pattern" >/dev/null 2>&1; then
                log_ok "OCR matched '$pattern'"; return 0
            fi
        elif docker cp "$ORACLE_CONTAINER:/tmp/ocr.png" "$shot" >/dev/null 2>&1 \
             && python3 "$HERE/ocr.py" "$shot" "$pattern" >/dev/null 2>&1; then
            log_ok "OCR matched '$pattern'"; rm -f "$shot"; return 0
        fi
        sleep 2; waited=$((waited + 2))
    done
    rm -f "$shot"; log_warn "wait_text '$pattern' timed out (${timeout}s)"; return 0
}

# wait until the log stops growing for <idle> secs, or <maxwait> elapses.
do_wait_idle() {
    local idle="$1"; local maxwait="${2:-60}"; local waited=0 last=-1 stable=0
    while [ "$waited" -lt "$maxwait" ]; do
        local sz; sz="$(oracle_exec sh -c 'wc -c </output/run.log 2>/dev/null' 2>/dev/null | tr -d ' \r' || echo 0)"
        [ -z "$sz" ] && sz=0
        if [ "$sz" = "$last" ]; then
            stable=$((stable + 1)); [ "$stable" -ge "$idle" ] && return 0
        else
            stable=0; last="$sz"
        fi
        if crash_seen; then CRASH_FOUND=1; return 0; fi
        sleep 1; waited=$((waited + 1))
    done
    return 0
}

run_script() {
    local n=0
    while IFS= read -r raw || [ -n "$raw" ]; do
        n=$((n + 1))
        local line="${raw%%#*}"; line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"          # rstrip
        [ -z "$line" ] && continue
        local cmd="${line%% *}"                           # first token
        local rest=""; [ "$line" != "$cmd" ] && rest="${line#"$cmd"}"
        rest="${rest#"${rest%%[![:space:]]*}"}"           # lstrip (handle aligned cols)
        case "$cmd" in
            wait)
                # pattern may contain spaces; the LAST token is the timeout.
                local pat="$rest" to=60
                if [[ "$rest" == *" "* ]]; then pat="${rest% *}"; to="${rest##* }"; fi
                local res; res="$(wait_for_log "$pat" "$to")"
                log_info "wait '$pat' (${to}s) -> $res"
                if [ "$res" = xenia_exit ]; then CRASH_FOUND=1; STATUS="crash"; return 0; fi
                if [ "$res" = timeout ]; then STATUS="timeout"; return 0; fi
                ;;
            wait_idle)
                local idle="${rest%% *}" maxw="${rest##* }"
                [ "$idle" = "$maxw" ] && maxw=60
                do_wait_idle "$idle" "$maxw" ;;
            wait_stable)
                local sidle="${rest%% *}" smax="${rest##* }"
                [ "$sidle" = "$smax" ] && smax=120
                do_wait_stable "$sidle" "$smax" ;;
            wait_text)
                # pattern may contain spaces; the LAST token is the timeout.
                local tpat="$rest" tto=90
                if [[ "$rest" == *" "* ]]; then tpat="${rest% *}"; tto="${rest##* }"; fi
                do_wait_text "$tpat" "$tto" ;;
            sleep) sleep "$rest" ;;
            shot)  do_shot "$rest" ;;
            input) bash "$HERE/input.sh" "$rest" >/dev/null 2>&1 || log_warn "input $rest failed" ;;
            raw)   bash "$HERE/input.sh" --raw "$rest" >/dev/null 2>&1 || log_warn "raw $rest failed" ;;
            hold)  local ha="${rest%% *}" hs="${rest##* }"; bash "$HERE/input.sh" --hold "$ha" "$hs" >/dev/null 2>&1 || true ;;
            expect_no_crash) if crash_seen; then CRASH_FOUND=1; fi ;;
            *) log_warn "unknown scenario command: $cmd" ;;
        esac
        if crash_seen; then CRASH_FOUND=1; fi
    done < "$script"
}

emit_result() {
    cp_json="$(for k in "${!CHECKPOINTS[@]}"; do printf '%s\t%s\n' "$k" "${CHECKPOINTS[$k]}"; done)"
    ENDED="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo n/a)"
    SECONDS_ELAPSED=$(( $(date +%s) - START_EPOCH ))
    python3 - "$out_dir/result.json" <<PY
import json, sys
cps = {}
for line in """$cp_json""".splitlines():
    if '\t' in line:
        k, v = line.split('\t', 1); cps[k] = v
res = {
  "scenario": "$scenario",
  "status": "$STATUS",
  "crash": {"detected": bool($CRASH_FOUND)},
  "checkpoints": cps,
  "started": "$STARTED",
  "ended": "$ENDED",
  "seconds": $SECONDS_ELAPSED,
  "log": "run.log",
  "xenia_exited": $XENIA_EXITED,
}
json.dump(res, open(sys.argv[1], "w"), indent=2)
print(json.dumps(res, indent=2))
PY
}

# --- execute under the GPU lock ----------------------------------------------
main() {
    require_docker_image
    log_info "scenario '$scenario' -> $out_dir  (display=${VULKAN_DISPLAY:-$ORACLE_DISPLAY_MODE})"

    start_oracle_container "$out_dir" "$game_dir"
    # Wait for the supervisor to finish bringing up the pad and actually launch
    # Xenia (can take ~20s if evdev is apt-installed at start on a non-rebuilt
    # image), so the script's first liveness/log checks are meaningful.
    for _ in $(seq 1 60); do xenia_started && break; sleep 1; done
    sleep 2

    # The first scenario 'wait' establishes boot; if it never matches we call it boot_fail.
    STATUS="running"
    run_script

    # Pull the log out for offline analysis regardless of outcome.
    docker cp "$ORACLE_CONTAINER:/output/run.log" "$log_path_host" >/dev/null 2>&1 || true

    XENIA_EXITED=0; xenia_alive || XENIA_EXITED=1

    # Final status resolution (unless a wait already set crash/timeout).
    if [ "$CRASH_FOUND" = 1 ]; then
        STATUS="crash"
        python3 "$HERE/trace/extract_crash.py" "$log_path_host" --context 30 \
            --out "$out_dir/crash.txt" >/dev/null 2>&1 || true
    elif [ "$STATUS" = running ]; then
        # Completed the script with no crash. Did we get past boot at all?
        if [ -n "${CHECKPOINTS[*]:-}" ]; then STATUS="completed"; else STATUS="boot_fail"; fi
    fi

    # Always extract the file trace for diffing against the port.
    python3 "$HERE/trace/extract_file_trace.py" "$log_path_host" --unique \
        --out "$out_dir/file_trace.txt" >/dev/null 2>&1 || true
    python3 "$HERE/trace/extract_kernel_trace.py" "$log_path_host" \
        --out "$out_dir/kernel_trace.txt" >/dev/null 2>&1 || true

    emit_result

    if [ "$keep" = 1 ]; then
        log_warn "leaving container '$ORACLE_CONTAINER' running (--keep); stop with: docker rm -f $ORACLE_CONTAINER"
    else
        stop_oracle_container
    fi

    case "$STATUS" in
        completed|title) return 0 ;;
        *) return 1 ;;
    esac
}

# Serialize GPU access: even 'software' lavapipe here touches the host GPU via
# /dev/dri, so always take the lock.
with_gpu_lock main
rc=$?
log_info "scenario '$scenario' final status: $STATUS (rc=$rc)"
exit "$rc"
