#!/usr/bin/env bash
# H9 — save-game / profile fixture manager.
#
# The oracle container bind-mounts a persistent Xenia content root
# ($XENIA_CONTENT_DIR -> /root/.local/share/Xenia/content), so a profile created
# once and any in-game saves survive across runs. This tool snapshots that state
# into named, committable fixtures under fixtures/saves/, and restores them — so
# a save produced in Xenia can be handed to the ReXGlue port (PRD M7: "a save
# made in Xenia loads in the port" is the strongest cross-impl correctness check).
#
# Usage:
#   fixtures.sh status                 # what profiles/saves exist right now
#   fixtures.sh export <name>          # snapshot live content dir -> fixtures/saves/<name>
#   fixtures.sh import <name>          # restore a snapshot into the live content dir
#   fixtures.sh list                   # list saved fixtures
#   fixtures.sh reset                  # wipe the live content dir (careful)
#
# See SAVES.md for the one-time profile-provisioning procedure.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/shlib/common.sh"

SAVES_DIR="$FIXTURES_DIR/saves"
cmd="${1:-status}"; shift || true

case "$cmd" in
    status)
        echo "content dir: $XENIA_CONTENT_DIR"
        if [ -d "$XENIA_CONTENT_DIR" ]; then
            local_count=$(find "$XENIA_CONTENT_DIR" -type f 2>/dev/null | wc -l)
            echo "files: $local_count"
            # Xenia lays profile/content out as content/<xuid>/<title_id>/...
            find "$XENIA_CONTENT_DIR" -maxdepth 1 -mindepth 1 -type d 2>/dev/null \
                | while read -r d; do echo "  profile/xuid dir: $(basename "$d")"; done
            find "$XENIA_CONTENT_DIR" -type d -name "$TITLE_ID" 2>/dev/null \
                | while read -r d; do echo "  save data for title $TITLE_ID: $d"; done
        else
            echo "(content dir does not exist yet — run a scenario or run_extracted.sh)"
        fi
        ;;
    export)
        name="${1:-}"; [ -n "$name" ] || die "usage: fixtures.sh export <name>"
        [ -d "$XENIA_CONTENT_DIR" ] || die "no content dir to export: $XENIA_CONTENT_DIR"
        dest="$SAVES_DIR/$name"
        mkdir -p "$dest"
        rm -rf "${dest:?}/content"
        cp -a "$XENIA_CONTENT_DIR" "$dest/content"
        printf 'exported=%s\ntitle_id=%s\nfiles=%s\n' \
            "$name" "$TITLE_ID" "$(find "$dest/content" -type f | wc -l)" > "$dest/FIXTURE.txt"
        log_ok "exported live content -> $dest ($(find "$dest/content" -type f | wc -l) files)"
        ;;
    import)
        name="${1:-}"; [ -n "$name" ] || die "usage: fixtures.sh import <name>"
        src="$SAVES_DIR/$name/content"
        [ -d "$src" ] || die "no such fixture: $SAVES_DIR/$name"
        mkdir -p "$XENIA_CONTENT_DIR"
        rm -rf "${XENIA_CONTENT_DIR:?}"/*
        cp -a "$src/." "$XENIA_CONTENT_DIR/"
        log_ok "imported fixture '$name' into live content dir ($(find "$XENIA_CONTENT_DIR" -type f | wc -l) files)"
        ;;
    list)
        [ -d "$SAVES_DIR" ] || { echo "(no fixtures yet)"; exit 0; }
        find "$SAVES_DIR" -maxdepth 1 -mindepth 1 -type d 2>/dev/null \
            | while read -r d; do echo "$(basename "$d")  ($(find "$d" -type f | wc -l) files)"; done
        ;;
    reset)
        [ -d "$XENIA_CONTENT_DIR" ] && rm -rf "${XENIA_CONTENT_DIR:?}"/* && log_ok "content dir wiped" || log_info "nothing to wipe"
        ;;
    *)
        die "unknown command '$cmd' (status|export|import|list|reset)"
        ;;
esac
