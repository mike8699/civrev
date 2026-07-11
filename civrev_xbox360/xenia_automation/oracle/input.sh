#!/usr/bin/env bash
# H4 — inject input into the running oracle container via xdotool.
#
# Delivers logical gamepad actions (mapped in input_map.conf) or raw keys/text
# to Xenia's virtual display. Without a window manager on Xvfb, keys are targeted
# at the Xenia window by id when it can be found (XSendEvent), falling back to a
# global send.
#
# Usage:
#   input.sh <ACTION>                 # e.g. input.sh START   (from input_map.conf)
#   input.sh --key <keysym>           # raw xdotool keysym, bypassing the map
#   input.sh --type "<text>"          # type a literal string
#   input.sh --script <file>          # run a timed action script (see below)
#   input.sh --list                   # print the current action map
#
# Script file lines (one per line, '#' comments, blank lines ignored):
#   ACTION            a mapped action        e.g.  DPAD_DOWN
#   key KEYSYM        a raw keysym           e.g.  key Return
#   type TEXT         type literal text      e.g.  type hello
#   sleep N           wait N seconds (float) e.g.  sleep 1.5
#   hold ACTION N     hold key for N seconds
#
# NOTE: whether an ACTION actually navigates the CivRev UI depends on the
# (currently unverified) mapping in input_map.conf — see INPUT_MAP.md.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/shlib/common.sh"
source "$HERE/shlib/container.sh"

MAP_FILE="${CIVREV_INPUT_MAP:-$HERE/input_map.conf}"

declare -A ACTION_MAP
load_map() {
    [ -f "$MAP_FILE" ] || die "input map not found: $MAP_FILE"
    while IFS='=' read -r k v; do
        k="${k%%#*}"; k="${k// /}"
        [ -z "$k" ] && continue
        v="${v%%#*}"; v="${v// /}"
        ACTION_MAP["$k"]="$v"
    done < "$MAP_FILE"
}

resolve() {
    local action="$1"
    local key="${ACTION_MAP[$action]:-}"
    [ -n "$key" ] || die "unknown action '$action' (see input.sh --list)"
    echo "$key"
}

# Find the Xenia window id once; empty if not found (then send globally).
_XENIA_WID=""
find_window() {
    # The emulator's SDL window always carries "Xenia" in its title; --onlyvisible
    # excludes the non-visible Qt selection-owner window. (This xdotool build has
    # no -i flag; the title is capital-X "Xenia" so a plain match suffices.)
    _XENIA_WID="$(oracle_exec sh -c 'xdotool search --onlyvisible --name Xenia 2>/dev/null | head -1' 2>/dev/null | tr -d "\r\n" || true)"
}

# Delivery strategy: SDL apps (Xenia) generally ignore XSendEvent synthetic
# events (what `xdotool ... --window` uses), but honor XTEST-injected events
# (what xdotool uses WITHOUT --window) since those look like real hardware input.
# So we focus the Xenia window (XSetInputFocus works even without a WM) and then
# inject globally via XTEST. CIVREV_INPUT_XSENDEVENT=1 forces the --window path
# if a future setup needs it.
_focus() { [ -n "$_XENIA_WID" ] && oracle_exec xdotool windowfocus "$_XENIA_WID" 2>/dev/null || true; }

send_key() {
    local keysym="$1"
    if [ "${CIVREV_INPUT_XSENDEVENT:-0}" = 1 ] && [ -n "$_XENIA_WID" ]; then
        oracle_exec xdotool key --window "$_XENIA_WID" --clearmodifiers "$keysym"
    else
        _focus; oracle_exec xdotool key --clearmodifiers "$keysym"
    fi
}

send_type() {
    local text="$1"
    _focus
    oracle_exec xdotool type --clearmodifiers -- "$text"
}

hold_key() {
    local keysym="$1"; local secs="$2"
    _focus
    oracle_exec xdotool keydown "$keysym"
    sleep "$secs"
    oracle_exec xdotool keyup "$keysym"
}

run_script() {
    local file="$1"; [ -r "$file" ] || die "script not readable: $file"
    local n=0
    while IFS= read -r raw || [ -n "$raw" ]; do
        n=$((n + 1))
        local line="${raw%%#*}"; line="${line#"${line%%[![:space:]]*}"}"
        [ -z "$line" ] && continue
        local cmd; cmd="$(echo "$line" | awk '{print $1}')"
        case "$cmd" in
            sleep) sleep "$(echo "$line" | awk '{print $2}')" ;;
            key)   send_key "$(echo "$line" | awk '{print $2}')" ;;
            type)  send_type "${line#type }" ;;
            hold)  hold_key "$(resolve "$(echo "$line" | awk '{print $2}')")" "$(echo "$line" | awk '{print $3}')" ;;
            *)     send_key "$(resolve "$cmd")" ;;
        esac
        log_info "input[$n]: $line"
    done < "$file"
}

main() {
    load_map
    [ "$#" -ge 1 ] || die "usage: input.sh <ACTION> | --key K | --type T | --script F | --list"

    if [ "$1" = "--list" ]; then
        for k in "${!ACTION_MAP[@]}"; do printf '%-14s %s\n' "$k" "${ACTION_MAP[$k]}"; done | sort
        return 0
    fi

    container_running || die "oracle container '$ORACLE_CONTAINER' not running (start it first)"
    find_window
    [ -n "$_XENIA_WID" ] && log_info "targeting xenia window id $_XENIA_WID" || log_warn "xenia window not found; sending keys globally"

    case "$1" in
        --key)    send_key "$2" ;;
        --type)   send_type "$2" ;;
        --script) run_script "$2" ;;
        *)        send_key "$(resolve "$1")"; log_info "sent action $1 -> $(resolve "$1")" ;;
    esac
}

main "$@"
