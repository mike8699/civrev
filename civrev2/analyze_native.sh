#!/usr/bin/env bash
# Analyze libTkNativeDll.so - extract symbols and strings related to spawn/map placement
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APK="$SCRIPT_DIR/Civilization-Revolution-2-v1-4-4.apk"
OUT_DIR="$SCRIPT_DIR/native_analysis"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Install radare2 if not present
if ! command -v r2 &>/dev/null; then
    echo "Installing radare2..."
    sudo apt-get update -qq && sudo apt-get install -y -qq radare2
fi

# Install arm cross-objdump if not present
if ! command -v arm-linux-gnueabihf-objdump &>/dev/null; then
    echo "Installing ARM cross tools..."
    sudo apt-get update -qq && sudo apt-get install -y -qq binutils-arm-linux-gnueabihf
fi

if [ ! -f "$APK" ]; then
    echo "Error: APK not found at $APK"
    exit 1
fi

# Extract .so from APK
echo "Extracting libTkNativeDll.so from APK..."
unzip -o "$APK" "lib/armeabi-v7a/libTkNativeDll.so" -d "$TMP_DIR" >/dev/null
SO="$TMP_DIR/lib/armeabi-v7a/libTkNativeDll.so"

mkdir -p "$OUT_DIR"

# 1. Export all symbols
echo "Dumping symbols..."
nm -DC "$SO" 2>/dev/null > "$OUT_DIR/symbols_demangled.txt" || true
nm -D "$SO" > "$OUT_DIR/symbols_raw.txt" || true
readelf -Ws "$SO" > "$OUT_DIR/symbols_elf.txt"

# 2. Extract all strings
echo "Dumping strings..."
strings "$SO" > "$OUT_DIR/all_strings.txt"

# 3. Filter for spawn/placement-related symbols and strings
echo "Filtering for spawn/map/placement related content..."

grep -iE "spawn|start.*pos|place.*civ|place.*settler|init.*map|gen.*map|map.*gen|find.*land|find.*tile|find.*start|starting|position.*player|player.*position|place.*player|random.*pos|setup.*game|new.*game|begin.*game" \
    "$OUT_DIR/symbols_demangled.txt" > "$OUT_DIR/spawn_symbols.txt" 2>/dev/null || true

grep -iE "spawn|start.*pos|place.*civ|place.*settler|init.*map|gen.*map|map.*gen|find.*land|find.*tile|find.*start|starting|position.*player|player.*position|place.*player|random.*pos|setup.*game|new.*game|begin.*game" \
    "$OUT_DIR/all_strings.txt" > "$OUT_DIR/spawn_strings.txt" 2>/dev/null || true

# 4. Also grab all CsToCpp / CppToCs exported functions (the C#/native bridge)
grep -E "CsToCpp_|CppToCs_" "$OUT_DIR/symbols_demangled.txt" > "$OUT_DIR/bridge_functions.txt" 2>/dev/null || true

# 5. Broader game logic symbols - map, tile, terrain, city, unit creation
grep -iE "map|tile|terrain|city|unit|combat|settler|civ" \
    "$OUT_DIR/symbols_demangled.txt" > "$OUT_DIR/game_logic_symbols.txt" 2>/dev/null || true

# 6. Use radare2 to get function list with sizes
echo "Running radare2 analysis (this may take a minute)..."
r2 -q -e anal.timeout=120 -c "aaa; aflj" "$SO" > "$OUT_DIR/r2_functions.json" 2>/dev/null || true
r2 -q -e anal.timeout=120 -c "aaa; afl" "$SO" > "$OUT_DIR/r2_functions.txt" 2>/dev/null || true

# 7. Filter r2 functions for spawn-related
grep -iE "spawn|start.*pos|place|settler|gen.*map|map.*gen|find.*land|find.*tile|setup|begin.*game|new.*game" \
    "$OUT_DIR/r2_functions.txt" > "$OUT_DIR/r2_spawn_functions.txt" 2>/dev/null || true

echo ""
echo "=== Analysis complete. Results in $OUT_DIR/ ==="
echo ""
echo "Key files:"
echo "  spawn_symbols.txt      - Symbols matching spawn/placement patterns"
echo "  spawn_strings.txt      - Strings matching spawn/placement patterns"
echo "  bridge_functions.txt   - All C#<->C++ bridge functions"
echo "  game_logic_symbols.txt - Broader game logic symbols"
echo "  r2_spawn_functions.txt - radare2 functions matching spawn patterns"
echo "  symbols_demangled.txt  - All demangled symbols"
echo "  all_strings.txt        - All strings in the binary"
echo ""

# Print summary
echo "=== Quick summary ==="
echo "Total symbols: $(wc -l < "$OUT_DIR/symbols_demangled.txt")"
echo "Bridge functions: $(wc -l < "$OUT_DIR/bridge_functions.txt")"
echo "Spawn-related symbols: $(wc -l < "$OUT_DIR/spawn_symbols.txt")"
echo "Spawn-related strings: $(wc -l < "$OUT_DIR/spawn_strings.txt")"
echo "Game logic symbols: $(wc -l < "$OUT_DIR/game_logic_symbols.txt")"
echo ""
echo "=== Spawn-related symbols ==="
cat "$OUT_DIR/spawn_symbols.txt"
echo ""
echo "=== Spawn-related strings ==="
cat "$OUT_DIR/spawn_strings.txt"
