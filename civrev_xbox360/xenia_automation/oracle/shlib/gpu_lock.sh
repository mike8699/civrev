#!/usr/bin/env bash
# H8 — GPU session lock.
#
# Two concurrent GPU-using processes starve the GPU on this host (verified with
# RPCS3: both fail RSX init). Every GPU-consuming run — Xenia reference capture
# AND the ReXGlue port under test — must hold this exclusive lock. Software
# (lavapipe/llvmpipe) runs are CPU-only and are exempt.
#
# Usage:
#   As a wrapper (recommended):
#     gpu_lock.sh [--timeout N] [--exempt] -- <command> [args...]
#   Sourced, for finer control inside another script:
#     source lib/gpu_lock.sh
#     with_gpu_lock <command> [args...]
#
# The lock is an flock(2) on a fixed lockfile. Because flock is tied to the file
# descriptor, the OS releases it automatically if the holder dies — so a crashed
# run never wedges the lock (no manual stale-lock cleanup needed). The holder's
# PID + start time are written into the lockfile purely for diagnostics.

GPU_LOCK_FILE="${CIVREV_GPU_LOCK_FILE:-/tmp/civrev_gpu.lock}"
GPU_LOCK_TIMEOUT="${CIVREV_GPU_LOCK_TIMEOUT:-1800}"   # seconds to wait for the lock

# with_gpu_lock <command...> : run command while holding the GPU lock.
with_gpu_lock() {
    [ "$#" -ge 1 ] || { echo "with_gpu_lock: no command given" >&2; return 2; }

    local holder_file="${GPU_LOCK_FILE}.holder"

    # fd 200 held for the lifetime of the subshell that runs the command.
    # Open with >> (append) so that a waiter opening the same file does NOT
    # truncate the current holder's diagnostics. flock works on append-mode fds.
    exec 200>>"$GPU_LOCK_FILE" || { echo "cannot open lock file $GPU_LOCK_FILE" >&2; return 2; }

    if ! flock --exclusive --timeout "$GPU_LOCK_TIMEOUT" 200; then
        local holder; holder="$(cat "$holder_file" 2>/dev/null)"
        echo "GPU lock busy after ${GPU_LOCK_TIMEOUT}s; holder: ${holder:-unknown}" >&2
        exec 200>&-
        return 75   # EX_TEMPFAIL
    fi

    # Record holder diagnostics in a side file (advisory only). Written after the
    # lock is held, cleared on release, so a waiter that times out can read who
    # currently holds it.
    printf 'pid=%s host_started=%s cmd=%s\n' "$$" \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo n/a)" "$*" >"$holder_file"

    local rc=0
    "$@" || rc=$?

    : >"$holder_file"    # clear diagnostics
    exec 200>&-          # drop the fd → release the lock
    return $rc
}

# Allow running directly as a wrapper script.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    exempt=0
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --timeout) GPU_LOCK_TIMEOUT="$2"; shift 2 ;;
            --exempt)  exempt=1; shift ;;          # software render: skip locking
            --)        shift; break ;;
            *)         break ;;
        esac
    done
    [ "$#" -ge 1 ] || { echo "usage: gpu_lock.sh [--timeout N] [--exempt] -- <command...>" >&2; exit 2; }
    if [ "$exempt" = 1 ]; then
        exec "$@"
    fi
    with_gpu_lock "$@"
fi
