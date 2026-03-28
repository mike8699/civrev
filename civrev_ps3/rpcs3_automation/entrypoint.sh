#!/bin/bash
set -e

# Always use Xvfb so that xdotool key input works reliably.
# In GUI mode (DISPLAY was set), also run x11vnc to mirror to host.
HOST_DISPLAY="$DISPLAY"
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1280x720x24 -ac &
sleep 1
export DISPLAY=:99

if [ -n "$HOST_DISPLAY" ]; then
    echo "GUI mode: starting x11vnc to mirror display"
    echo "  Connect with: vncviewer localhost:5900"
    x11vnc -display :99 -nopw -forever -shared -rfbport 5900 -bg || \
        echo "  Warning: x11vnc failed to start (VNC viewing unavailable)"
fi

# Create writable copy of DLC/game data so we can inject Pak9.edat
DLC_SRC="/game_dlc"
DLC_DEST="/root/.config/rpcs3/dev_hdd0/game/BLUS30130"
mkdir -p "$DLC_DEST/USRDIR"
echo "Copying DLC/game data to writable location..."
if [ -d "$DLC_SRC/USRDIR" ]; then
    cp -a "$DLC_SRC/USRDIR/"* "$DLC_DEST/USRDIR/"
fi
cp -a "$DLC_SRC/PARAM.SFO" "$DLC_DEST/" 2>/dev/null || true
cp -a "$DLC_SRC/ICON0.PNG" "$DLC_DEST/" 2>/dev/null || true
cp -a "$DLC_SRC/PS3LOGO.DAT" "$DLC_DEST/" 2>/dev/null || true

# Copy DLC exdata (license RAP files + additional DLC packs like Pak1, Pak6)
EXDATA_SRC="/game_exdata"
EXDATA_DEST="/root/.config/rpcs3/dev_hdd0/home/00000001/exdata"
if [ -d "$EXDATA_SRC" ]; then
    mkdir -p "$EXDATA_DEST"
    cp -a "$EXDATA_SRC/"* "$EXDATA_DEST/" 2>/dev/null || true
    echo "Copied DLC exdata ($(ls "$EXDATA_DEST" | wc -l) files)"
fi

# Set up keyboard pad handler so we can send controller inputs
mkdir -p /root/.config/rpcs3/input_configs/global
cat > /root/.config/rpcs3/input_configs/global/Default.yml << 'PADEOF'
Player 1 Input:
  Handler: Keyboard
  Device: Keyboard
  Config:
    Left Stick Left: A
    Left Stick Down: S
    Left Stick Right: D
    Left Stick Up: W
    Right Stick Left: Delete
    Right Stick Down: End
    Right Stick Right: Page Down
    Right Stick Up: Home
    Start: "1"
    Select: "3"
    PS Button: ""
    Square: Z
    Cross: Return
    Circle: BackSpace
    Triangle: X
    Left: Left
    Down: Down
    Right: Right
    Up: Up
    R1: E
    R2: "."
    R3: "/"
    L1: Q
    L2: ","
    L3: ";"
    Motion Sensor X:
      Axis: ""
      Mirrored: false
      Shift: 0
    Motion Sensor Y:
      Axis: ""
      Mirrored: false
      Shift: 0
    Motion Sensor Z:
      Axis: ""
      Mirrored: false
      Shift: 0
    Motion Sensor G:
      Axis: ""
      Mirrored: false
      Shift: 0
    Pressure Intensity Button: ""
    Pressure Intensity Percent: 50
    Pressure Intensity Toggle Mode: false
    Pressure Intensity Deadzone: 0
    Left Stick Multiplier: 100
    Right Stick Multiplier: 100
    Left Stick Deadzone: 0
    Right Stick Deadzone: 0
    Left Trigger Threshold: 0
    Right Trigger Threshold: 0
    Left Pad Squircle Factor: 0
    Right Pad Squircle Factor: 0
    Color Value R: 0
    Color Value G: 0
    Color Value B: 0
    Enable LED: true
    LED Battery Indicator: false
    LED Battery Indicator Brightness: 50
    Enable Vibration: true
    Large Vibration Motor: true
    Small Vibration Motor: true
    Switch Vibration Motors: false
    Mouse Movement Mode: Relative
    Mouse Deadzone X: 60
    Mouse Deadzone Y: 60
    Mouse Acceleration X: 200
    Mouse Acceleration Y: 250
    Mouse Lerp Factor: 100
    Device Class Type: 0
    Vendor ID: 0
    Product ID: 0
PADEOF

# Register the disc game with RPCS3
echo "BLUS30130: /game_disc/" > /root/.config/rpcs3/games.yml

# Disable RPCS3 welcome dialog and update check on first run
mkdir -p /root/.config/rpcs3/GuiConfigs
cat > /root/.config/rpcs3/GuiConfigs/CurrentSettings.ini << 'EOF'
[Meta]
checkUpdateStart=false

[main_window]
infoBoxEnabledWelcome=false
EOF

cd /civrev/rpcs3_automation

# If first arg is "autoplay", run autoplay test instead
if [ "${1:-}" = "autoplay" ]; then
    shift
    exec python3 test_autoplay.py "$@"
else
    exec python3 test_map.py "$@"
fi
