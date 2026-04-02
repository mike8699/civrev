#!/bin/bash
set -e

echo "=== CivRev Xbox 360 (Xenia) ==="

# ---------------------------------------------------------------------------
# Display mode: VULKAN_DISPLAY controls how Vulkan presents to VNC.
#
#   lavapipe  (default) - Xvfb + lavapipe software Vulkan.
#                         Mesa WSI skips DRI3 check for sw drivers and falls
#                         back to xcb_put_image(). Slow but reliable.
#
#   weston              - Weston headless compositor + Xwayland.
#                         Xwayland provides real DRI3. Can use host GPU via
#                         /dev/dri if available, or lavapipe for sw rendering.
#                         VNC served by Weston's built-in VNC backend.
#
#   xorg-dummy          - Xorg with dummy video driver + DRI3 extension.
#                         DRI3 is advertised but dri3_open may fail without
#                         a real DRM device. Only works with lavapipe (sw=true
#                         bypasses DRI3 requirement anyway).
# ---------------------------------------------------------------------------
VULKAN_DISPLAY="${VULKAN_DISPLAY:-lavapipe}"

case "$VULKAN_DISPLAY" in
    lavapipe)
        echo "Display mode: Xvfb + lavapipe (software Vulkan, no DRI3 needed)"
        echo ""

        # Force lavapipe as the only Vulkan ICD
        export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json
        export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json

        # Software OpenGL fallback for any GL usage
        export LIBGL_ALWAYS_SOFTWARE=1

        # Start Xvfb - lavapipe's WSI will use xcb_put_image() (no DRI3 needed)
        export DISPLAY=:99
        Xvfb :99 -screen 0 1280x720x24 +extension GLX +extension RENDER &
        sleep 1
        echo "Xvfb started on $DISPLAY"

        # Start VNC server on port 5900
        x11vnc -display :99 -forever -nopw -shared -rfbport 5900 &
        sleep 1
        echo "VNC server started on port 5900"
        ;;

    weston)
        echo "Display mode: Weston headless + Xwayland (DRI3 available)"
        echo ""

        # Determine if we should use GPU or software rendering
        if [ -e /dev/dri/renderD128 ]; then
            echo "  GPU detected at /dev/dri/renderD128"
            WESTON_RENDERER="gl"
        else
            echo "  No GPU detected, using pixman software renderer"
            WESTON_RENDERER="pixman"
            export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json
            export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
        fi

        # Create Weston config for headless + VNC + Xwayland
        export XDG_RUNTIME_DIR=/tmp/weston-runtime
        mkdir -p "$XDG_RUNTIME_DIR"
        chmod 0700 "$XDG_RUNTIME_DIR"

        cat > "$XDG_RUNTIME_DIR/weston.ini" <<'WEOF'
[core]
xwayland=true

[output]
name=headless
mode=1280x720

[libinput]
enable-tap=true
WEOF

        # Start Weston with VNC backend
        weston \
            --backend=vnc \
            --renderer="$WESTON_RENDERER" \
            --width=1280 --height=720 \
            --config="$XDG_RUNTIME_DIR/weston.ini" \
            --socket=wayland-0 &
        WESTON_PID=$!
        sleep 2

        if ! kill -0 $WESTON_PID 2>/dev/null; then
            echo "ERROR: Weston failed to start. Falling back to lavapipe mode."
            exec env VULKAN_DISPLAY=lavapipe "$0" "$@"
        fi

        export WAYLAND_DISPLAY=wayland-0
        for i in $(seq 1 10); do
            if [ -e "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; then
                break
            fi
            sleep 0.5
        done

        # Xwayland sets DISPLAY; find it
        export DISPLAY=:0
        for i in $(seq 1 10); do
            if xdpyinfo -display :0 >/dev/null 2>&1; then
                break
            elif xdpyinfo -display :1 >/dev/null 2>&1; then
                export DISPLAY=:1
                break
            fi
            sleep 0.5
        done

        echo "Weston started (PID $WESTON_PID)"
        echo "Xwayland DISPLAY=$DISPLAY"
        echo "VNC served by Weston on port 5900"
        ;;

    xorg-dummy)
        echo "Display mode: Xorg dummy driver (DRI3 advertised, sw rendering)"
        echo ""

        export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json
        export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
        export LIBGL_ALWAYS_SOFTWARE=1

        cat > /tmp/xorg-dummy.conf <<'XEOF'
Section "Device"
    Identifier "DummyGPU"
    Driver     "dummy"
    VideoRam   256000
EndSection

Section "Screen"
    Identifier "DummyScreen"
    Device     "DummyGPU"
    Monitor    "DummyMonitor"
    DefaultDepth 24
    SubSection "Display"
        Depth  24
        Modes  "1280x720"
    EndSubSection
EndSection

Section "Monitor"
    Identifier "DummyMonitor"
    HorizSync  28.0-80.0
    VertRefresh 48.0-75.0
EndSection

Section "Extensions"
    Option "DRI3" "Enable"
EndSection
XEOF

        export DISPLAY=:99
        Xorg :99 -config /tmp/xorg-dummy.conf -noreset +extension GLX +extension RENDER &
        XORG_PID=$!
        sleep 2

        if ! kill -0 $XORG_PID 2>/dev/null; then
            echo "Xorg dummy failed, falling back to Xvfb + lavapipe..."
            Xvfb :99 -screen 0 1280x720x24 +extension GLX +extension RENDER &
            sleep 1
        fi
        echo "Display started on $DISPLAY"

        x11vnc -display :99 -forever -nopw -shared -rfbport 5900 &
        sleep 1
        echo "VNC server started on port 5900"
        ;;

    *)
        echo "ERROR: Unknown VULKAN_DISPLAY mode: $VULKAN_DISPLAY"
        echo "Valid options: lavapipe, weston, xorg-dummy"
        exit 1
        ;;
esac

# Verify /dev/shm has exec permission (required for Xenia JIT)
SHM_OPTS=$(mount | grep '/dev/shm' | head -1)
echo "SHM mount: $SHM_OPTS"
if echo "$SHM_OPTS" | grep -q 'noexec'; then
    echo "WARNING: /dev/shm is mounted with noexec - Xenia JIT will SIGBUS!"
    echo "Attempting remount with exec..."
    mount -o remount,exec /dev/shm 2>/dev/null || echo "  remount failed (need --privileged)"
fi

# Diagnostic: verify Vulkan is working
echo ""
echo "--- Vulkan diagnostics ---"
echo "VK_DRIVER_FILES=${VK_DRIVER_FILES:-<not set, using system default>}"
vulkaninfo --summary 2>/dev/null | head -20 || echo "vulkaninfo not available or failed"
echo "--- end diagnostics ---"
echo ""

# Set library path for Xenia
export LD_LIBRARY_PATH=/opt/xenia/usr/lib:$LD_LIBRARY_PATH

# If arguments given, run them (e.g. bash for interactive shell)
if [ $# -gt 0 ]; then
    exec "$@"
fi

# Find game file in /game_data mount
GAME_FILE=""
if [ -d /game_data ]; then
    # Look for default.xex first, then any xex, then any file (XBLA package)
    if [ -f /game_data/default.xex ]; then
        GAME_FILE="/game_data/default.xex"
    else
        GAME_FILE=$(find /game_data -maxdepth 2 -type f \( -name "*.xex" -o -name "*.iso" \) | head -1)
        if [ -z "$GAME_FILE" ]; then
            # Might be an XBLA package (single file, no extension)
            GAME_FILE=$(find /game_data -maxdepth 1 -type f | head -1)
        fi
    fi
fi

if [ -n "$GAME_FILE" ]; then
    echo "Launching Xenia with: $GAME_FILE"
    exec xenia \
        --apu=sdl \
        --license_mask=-1 \
        --log_file=/output/xenia.log \
        "$GAME_FILE"
fi

echo "No game file found in /game_data. Starting shell..."
exec /bin/bash
