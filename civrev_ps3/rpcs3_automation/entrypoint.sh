#!/bin/bash
set -e

# Always use Xvfb so that xdotool key input works reliably.
# In GUI mode (DISPLAY was set), also run x11vnc to mirror to host.
HOST_DISPLAY="$DISPLAY"
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1280x720x24 -ac &
sleep 1
export DISPLAY=:99

# Create writable copy of disc game (mounted read-only)
echo "Creating writable disc copy..."
cp -a /game_disc_src /game_disc_rw
# Point /game_disc symlink at the writable copy
ln -sfn /game_disc_rw /game_disc

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

# If DLC EBOOT.BIN is a patched ELF (not encrypted SELF), also copy it
# to the disc game location so RPCS3 actually boots the patched version.
# RPCS3 boots from the disc EBOOT, not the HDD one.
DLC_EBOOT="$DLC_DEST/USRDIR/EBOOT.BIN"
DISC_EBOOT="/game_disc_rw/PS3_GAME/USRDIR/EBOOT.BIN"
if [ -f "$DLC_EBOOT" ]; then
    MAGIC=$(head -c4 "$DLC_EBOOT" | od -A n -t x1 | tr -d ' ')
    if [ "$MAGIC" = "7f454c46" ]; then
        echo "Patched EBOOT detected (ELF), copying to disc location..."
        mkdir -p "$(dirname "$DISC_EBOOT")"
        cp "$DLC_EBOOT" "$DISC_EBOOT"
    fi
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

# --- RPCS3 patch installation ---
# Install patches for multiplayer or autoplay modes
if [ "${1:-}" = "multiplayer" ] || [ "${1:-}" = "autoplay" ]; then
    echo "Installing RPCS3 patches..."
    mkdir -p /root/.config/rpcs3/patches
    cp /civrev/custom_server/rpcs3_patch.yml /root/.config/rpcs3/patches/imported_patch.yml

    if [ "${1:-}" = "autoplay" ]; then
        cat > /root/.config/rpcs3/patch_config.yml << 'PATCHEOF'
PPU-5de8c820d75c2c72f3405cf4353d015c50e1e5ea:
  Enable AutoPlay:
    Sid Meier's Civilization Revolution:
      BLUS30130:
        01.30:
          Enabled: true
PATCHEOF
        echo "  AutoPlay patch enabled"
    else
        cat > /root/.config/rpcs3/patch_config.yml << 'PATCHEOF'
PPU-5de8c820d75c2c72f3405cf4353d015c50e1e5ea:
  Bypass PSN Check:
    Sid Meier's Civilization Revolution:
      BLUS30130:
        01.30:
          Enabled: true
  AutoEnd Turns:
    Sid Meier's Civilization Revolution:
      BLUS30130:
        01.30:
          Enabled: true
PATCHEOF
        echo "  Multiplayer patches enabled"
    fi
fi
# --- End patch installation ---

# --- Custom GameSpy server setup (multiplayer only) ---
if [ "${1:-}" = "multiplayer" ]; then
    echo "Multiplayer mode: redirecting GameSpy DNS to localhost..."
    cat >> /etc/hosts << 'HOSTSEOF'
# CivRev custom server - redirect GameSpy to localhost
127.0.0.1 gpcm.gamespy.com
127.0.0.1 gpsp.gamespy.com
127.0.0.1 peerchat.gamespy.com
127.0.0.1 natneg1.gamespy.com
127.0.0.1 natneg2.gamespy.com
127.0.0.1 natneg3.gamespy.com
127.0.0.1 civconps3.available.gamespy.com
127.0.0.1 civconps3.master.gamespy.com
127.0.0.1 civconps3.ms1.gamespy.com
127.0.0.1 civconps3.ms2.gamespy.com
127.0.0.1 civconps3.ms3.gamespy.com
127.0.0.1 civconps3.ms4.gamespy.com
127.0.0.1 civconps3.ms5.gamespy.com
127.0.0.1 civconps3.ms6.gamespy.com
127.0.0.1 civconps3.ms7.gamespy.com
127.0.0.1 civconps3.ms8.gamespy.com
127.0.0.1 civconps3.ms9.gamespy.com
127.0.0.1 civconps3.ms10.gamespy.com
127.0.0.1 civconps3.ms11.gamespy.com
127.0.0.1 civconps3.ms12.gamespy.com
127.0.0.1 civconps3.ms13.gamespy.com
127.0.0.1 civconps3.ms14.gamespy.com
127.0.0.1 civconps3.ms15.gamespy.com
127.0.0.1 civconps3.ms16.gamespy.com
127.0.0.1 civconps3.ms17.gamespy.com
127.0.0.1 civconps3.ms18.gamespy.com
127.0.0.1 civconps3.ms19.gamespy.com
127.0.0.1 civconps3.ms20.gamespy.com
127.0.0.1 civconps3.auth.pubsvs.gamespy.com
127.0.0.1 civconps3.comp.pubsvs.gamespy.com
127.0.0.1 civconps3.sake.gamespy.com
127.0.0.1 gamespy.com
# End CivRev
HOSTSEOF
    echo "  /etc/hosts: $(grep -c gamespy.com /etc/hosts) entries added"

    # Enable RPCS3 networking. Copy host config if available, then patch network settings.
    echo "Configuring RPCS3 network settings..."
    RPCS3_CFG="/root/.config/rpcs3/config.yml"
    mkdir -p /root/.config/rpcs3

    # Copy host config if mounted (provides complete valid config)
    if [ -f /civrev/rpcs3_automation/rpcs3_config_template.yml ]; then
        cp /civrev/rpcs3_automation/rpcs3_config_template.yml "$RPCS3_CFG"
    elif [ -f /root/.config/rpcs3/config.yml ]; then
        : # Already exists
    fi

    # Patch network settings in-place
    if [ -f "$RPCS3_CFG" ]; then
        sed -i 's/Internet enabled: .*/Internet enabled: Connected/' "$RPCS3_CFG"
        sed -i 's/DNS address: .*/DNS address: 127.0.0.1/' "$RPCS3_CFG"
        echo "  Updated config.yml network settings"
    fi
    grep -E "Internet|DNS|PSN" "$RPCS3_CFG" 2>/dev/null | head -5 || echo "  Warning: no config.yml"
fi
# --- End custom server setup ---

cd /civrev/rpcs3_automation

# Route to the appropriate test script
if [ "${1:-}" = "autoplay" ]; then
    shift
    exec python3 test_autoplay.py "$@"
elif [ "${1:-}" = "multiplayer" ]; then
    shift
    exec python3 test_multiplayer.py "$@"
elif [ "${1:-}" = "korea" ]; then
    shift
    exec python3 test_korea.py "$@"
else
    exec python3 test_map.py "$@"
fi
