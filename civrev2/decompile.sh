#!/usr/bin/env bash
# Decompile Assembly-CSharp.dll from CivRev 2 APK using ILSpy
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APK="$SCRIPT_DIR/Civilization-Revolution-2-v1-4-4.apk"
OUT_DIR="$SCRIPT_DIR/decompiled/Assembly-CSharp"
TMP_DIR=$(mktemp -d)

trap 'rm -rf "$TMP_DIR"' EXIT

# Check prerequisites
if ! command -v dotnet &>/dev/null; then
    echo "Error: dotnet SDK not found. Install from https://dotnet.microsoft.com/download"
    exit 1
fi

if ! dotnet tool list -g 2>/dev/null | grep -q ilspycmd; then
    echo "Installing ilspycmd..."
    dotnet tool install -g ilspycmd
fi

ILSPYCMD="$HOME/.dotnet/tools/ilspycmd"
if [ ! -x "$ILSPYCMD" ]; then
    echo "Error: ilspycmd not found at $ILSPYCMD"
    exit 1
fi

if [ ! -f "$APK" ]; then
    echo "Error: APK not found at $APK"
    exit 1
fi

# Extract DLL from APK
echo "Extracting Assembly-CSharp.dll from APK..."
unzip -o "$APK" "assets/bin/Data/Managed/Assembly-CSharp.dll" -d "$TMP_DIR" >/dev/null

DLL="$TMP_DIR/assets/bin/Data/Managed/Assembly-CSharp.dll"

# Decompile to C# project
echo "Decompiling to $OUT_DIR ..."
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
"$ILSPYCMD" "$DLL" -p -o "$OUT_DIR"

COUNT=$(find "$OUT_DIR" -name "*.cs" | wc -l)
echo "Done. $COUNT C# files decompiled to $OUT_DIR"
