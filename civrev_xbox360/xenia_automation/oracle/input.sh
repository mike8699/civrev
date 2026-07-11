#!/usr/bin/env bash
# H4 — drive Xenia's game input via the virtual gamepad (virtpad.py).
#
# Xenia's SDL HID reads game controllers, not the keyboard, so input is delivered
# through a virtual Xbox 360 pad (created by the container supervisor before Xenia
# starts). This script maps logical actions (input_map.conf) to virtpad commands
# and writes them to the pad's FIFO inside the running oracle container.
#
# Usage:
#   input.sh <ACTION>          # e.g. input.sh START   (from input_map.conf)
#   input.sh --raw "<cmd>"     # a raw virtpad command, e.g. "dpad down" / "press A 0.3"
#   input.sh --hold <ACTION> <secs>
#   input.sh --script <file>   # timed action script (see below)
#   input.sh --list            # print the action map
#
# Script lines ('#' comments, blanks ignored):
#   ACTION            a mapped action        e.g.  DPAD_DOWN
#   raw <cmd>         raw virtpad command    e.g.  raw press A 0.3
#   sleep <secs>      wait (host-side)       e.g.  sleep 1.5
#   hold <ACTION> N   hold a button N secs
#
# virtpad commands: press <BTN> [secs] | down <BTN> | up <BTN> | dpad <dir> |
#   stick <l|r> <x> <y> | trig <l|r> <0..255> | sleep <secs>
# BTN: A B X Y LB RB START BACK GUIDE LS RS
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
        v="${v%%#*}"; v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"
        ACTION_MAP["$k"]="$v"
    done < "$MAP_FILE"
}

# Send one virtpad command line to the pad FIFO in the container.
pad_send() {
    local cmd="$1"
    oracle_exec sh -c "printf '%s\n' \"$cmd\" > /tmp/virtpad.cmd" \
        || die "failed to send to virtpad (is the pad daemon running? check /output/virtpad.log)"
}

resolve() {
    local action="$1"
    local cmd="${ACTION_MAP[$action]:-}"
    [ -n "$cmd" ] || die "unknown action '$action' (see input.sh --list)"
    echo "$cmd"
}

run_script() {
    local file="$1"; [ -r "$file" ] || die "script not readable: $file"
    local n=0
    while IFS= read -r raw || [ -n "$raw" ]; do
        n=$((n + 1))
        local line="${raw%%#*}"; line="${line#"${line%%[![:space:]]*}"}"; line="${line%"${line##*[![:space:]]}"}"
        [ -z "$line" ] && continue
        local cmd="${line%% *}"; local rest=""; [ "$line" != "$cmd" ] && rest="${line#"$cmd" }"
        case "$cmd" in
            sleep) sleep "$rest" ;;
            raw)   pad_send "$rest" ;;
            hold)  local a="${rest%% *}" s="${rest##* }"; pad_send "down $(resolve "$a" | sed 's/^press //')"; sleep "$s"; pad_send "up $(resolve "$a" | sed 's/^press //')" ;;
            *)     pad_send "$(resolve "$cmd")" ;;
        esac
        log_info "input[$n]: $line"
    done < "$file"
}

main() {
    load_map
    [ "$#" -ge 1 ] || die "usage: input.sh <ACTION> | --raw <cmd> | --hold <ACTION> N | --script F | --list"
    if [ "$1" = "--list" ]; then
        for k in "${!ACTION_MAP[@]}"; do printf '%-12s %s\n' "$k" "${ACTION_MAP[$k]}"; done | sort
        return 0
    fi
    container_running || die "oracle container '$ORACLE_CONTAINER' not running"
    case "$1" in
        --raw)    pad_send "$2" ;;
        --hold)   local btn; btn="$(resolve "$2" | sed 's/^press //')"; pad_send "down $btn"; sleep "$3"; pad_send "up $btn" ;;
        --script) run_script "$2" ;;
        *)        pad_send "$(resolve "$1")"; log_info "sent $1 -> $(resolve "$1")" ;;
    esac
}

main "$@"
