#!/usr/bin/env bash
# H3 — capture a screenshot from the running oracle container's virtual display.
#
# Grabs the root window of the Xvfb/Xorg display (:99) with ImageMagick `import`
# (already in the image) and copies the PNG to the host output dir. Works while
# Xenia is running or after it has crashed (the container stays alive), so you
# can always capture the last frame.
#
# Usage:
#   screenshot.sh <name>              # -> <OUTPUT_DIR>/<name>.png
#   screenshot.sh <name> --dir DIR    # -> DIR/<name>.png
#
# Requires an oracle container already started (start_oracle_container / a
# scenario run). For a one-shot, use run_scenario.sh instead.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/shlib/common.sh"
source "$HERE/shlib/container.sh"

name="${1:-}"; [ -n "$name" ] || die "usage: screenshot.sh <name> [--dir DIR]"
shift || true
dest_dir="$OUTPUT_DIR"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --dir) dest_dir="$2"; shift 2 ;;
        *) die "unknown arg: $1" ;;
    esac
done
name="${name%.png}"
mkdir -p "$dest_dir"

container_running || die "oracle container '$ORACLE_CONTAINER' is not running (start it first)"

# Capture inside the container to /tmp, then copy out with `docker cp` so this
# works regardless of where /output happens to be mounted.
in_path="/tmp/oracle_shot_${name}.png"
if ! oracle_exec import -window root "$in_path" 2>/dev/null; then
    # Fallback: xwd + convert, in case import can't grab the root directly.
    oracle_exec sh -c "xwd -root -silent | convert xwd:- '$in_path'" \
        || die "screenshot capture failed (import and xwd both failed)"
fi

out="$dest_dir/${name}.png"
docker cp "$ORACLE_CONTAINER:$in_path" "$out" >/dev/null 2>&1 \
    || die "docker cp of screenshot failed"
[ -s "$out" ] || die "screenshot produced no data: $out"
log_ok "screenshot -> $out ($(stat -c%s "$out") bytes)"
echo "$out"
