#!/usr/bin/env bash
# Extract and decompile Civilization Revolution iOS IPA
# Idempotent - safe to run multiple times
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IPA="$SCRIPT_DIR/Civilization Revolution for iPad (v2.4.6)-mrYODA.rc302.ipa"
EXTRACT_DIR="$SCRIPT_DIR/extracted"
DECOMPILED_DIR="$SCRIPT_DIR/decompiled"
NATIVE_DIR="$SCRIPT_DIR/native_analysis"
STRUCTURE_FILE="$SCRIPT_DIR/file_structure.txt"

# ── Prerequisites ────────────────────────────────────────────────────────────

echo "=== Checking prerequisites ==="

# unzip (should already exist)
if ! command -v unzip &>/dev/null; then
    echo "Installing unzip..."
    sudo apt-get update -qq && sudo apt-get install -y -qq unzip
fi

# .NET SDK (for ilspycmd)
if ! command -v dotnet &>/dev/null; then
    echo "Error: dotnet SDK not found. Install from https://dotnet.microsoft.com/download"
    exit 1
fi

# ilspycmd for C# decompilation
if ! dotnet tool list -g 2>/dev/null | grep -q ilspycmd; then
    echo "Installing ilspycmd..."
    dotnet tool install -g ilspycmd
fi

ILSPYCMD="$HOME/.dotnet/tools/ilspycmd"
if [ ! -x "$ILSPYCMD" ]; then
    echo "Error: ilspycmd not found at $ILSPYCMD"
    exit 1
fi

# binutils for Mach-O analysis (strings, nm)
if ! command -v strings &>/dev/null; then
    echo "Installing binutils..."
    sudo apt-get update -qq && sudo apt-get install -y -qq binutils
fi

# file command
if ! command -v file &>/dev/null; then
    echo "Installing file..."
    sudo apt-get update -qq && sudo apt-get install -y -qq file
fi

# radare2 for binary analysis
if ! command -v r2 &>/dev/null; then
    echo "Installing radare2..."
    sudo apt-get update -qq && sudo apt-get install -y -qq radare2
fi

# class-dump or jtool2 alternatives - we'll use nm/strings/r2 which work on Linux
# (class-dump is macOS-only; we rely on radare2 + ObjC metadata extraction instead)

# ── Verify IPA exists ────────────────────────────────────────────────────────

if [ ! -f "$IPA" ]; then
    echo "Error: IPA not found at $IPA"
    exit 1
fi

echo "IPA: $(basename "$IPA") ($(du -h "$IPA" | cut -f1))"

# ── Step 1: Extract IPA ──────────────────────────────────────────────────────

if [ -d "$EXTRACT_DIR" ]; then
    echo "=== Extraction directory already exists, skipping extract ==="
else
    echo "=== Extracting IPA ==="
    mkdir -p "$EXTRACT_DIR"
    unzip -q "$IPA" -d "$EXTRACT_DIR"
    echo "Extracted to $EXTRACT_DIR"
fi

# Find the .app bundle
APP_BUNDLE=$(find "$EXTRACT_DIR/Payload" -maxdepth 1 -name "*.app" -type d | head -1)
if [ -z "$APP_BUNDLE" ]; then
    echo "Error: No .app bundle found in Payload/"
    exit 1
fi
APP_NAME=$(basename "$APP_BUNDLE" .app)
echo "App bundle: $APP_NAME"

# ── Step 2: Generate file structure report ────────────────────────────────────

echo "=== Generating file structure report ==="
{
    echo "=== Civilization Revolution iOS - File Structure ==="
    echo "Generated: $(date -Iseconds)"
    echo ""

    echo "--- IPA info ---"
    echo "File: $(basename "$IPA")"
    echo "Size: $(du -h "$IPA" | cut -f1)"
    echo "Total files in IPA: $(unzip -l "$IPA" 2>/dev/null | tail -1 | awk '{print $2}')"
    echo ""

    echo "--- App bundle: $APP_NAME ---"
    echo ""

    echo "--- Info.plist summary ---"
    if [ -f "$APP_BUNDLE/Info.plist" ]; then
        # Try to read plist (binary or XML)
        if command -v plutil &>/dev/null; then
            plutil -p "$APP_BUNDLE/Info.plist" 2>/dev/null || echo "(binary plist, plutil failed)"
        elif command -v plistutil &>/dev/null; then
            plistutil -i "$APP_BUNDLE/Info.plist" 2>/dev/null || echo "(plistutil failed)"
        else
            file "$APP_BUNDLE/Info.plist"
            echo "(install plistutil to read binary plists: sudo apt-get install libplist-utils)"
        fi
    fi
    echo ""

    echo "--- Top-level app bundle contents ---"
    ls -la "$APP_BUNDLE/" 2>/dev/null || true
    echo ""

    echo "--- Main executable ---"
    # The main executable is usually named same as the app
    MAIN_EXEC=""
    for candidate in "$APP_BUNDLE/$APP_NAME" "$APP_BUNDLE/CivRev" "$APP_BUNDLE/CivilizationRevolution"; do
        if [ -f "$candidate" ]; then
            MAIN_EXEC="$candidate"
            break
        fi
    done
    # Fallback: find Mach-O executables
    if [ -z "$MAIN_EXEC" ]; then
        MAIN_EXEC=$(find "$APP_BUNDLE" -maxdepth 1 -type f -executable | head -1)
    fi
    if [ -z "$MAIN_EXEC" ]; then
        # Try finding by file type
        MAIN_EXEC=$(find "$APP_BUNDLE" -maxdepth 1 -type f | while read f; do
            if file "$f" 2>/dev/null | grep -q "Mach-O"; then
                echo "$f"
                break
            fi
        done)
    fi
    if [ -n "$MAIN_EXEC" ]; then
        echo "Found: $(basename "$MAIN_EXEC")"
        file "$MAIN_EXEC"
        echo "Size: $(du -h "$MAIN_EXEC" | cut -f1)"
    else
        echo "WARNING: Could not identify main executable"
        echo "Files in app root:"
        find "$APP_BUNDLE" -maxdepth 1 -type f -exec file {} \;
    fi
    echo ""

    echo "--- Frameworks/ ---"
    if [ -d "$APP_BUNDLE/Frameworks" ]; then
        ls -la "$APP_BUNDLE/Frameworks/" 2>/dev/null || true
        # List dylibs/frameworks
        find "$APP_BUNDLE/Frameworks" -name "*.dylib" -o -name "*.framework" 2>/dev/null | sort
    else
        echo "(no Frameworks/ directory)"
    fi
    echo ""

    echo "--- Unity check ---"
    # Check for Unity Data directory
    UNITY_DATA=""
    for candidate in "$APP_BUNDLE/Data" "$APP_BUNDLE/data"; do
        if [ -d "$candidate" ]; then
            UNITY_DATA="$candidate"
            break
        fi
    done
    if [ -n "$UNITY_DATA" ]; then
        echo "Unity Data directory found: $(basename "$UNITY_DATA")/"
        echo "Contents:"
        ls -la "$UNITY_DATA/" 2>/dev/null || true
        echo ""

        # Check for Managed/ (Mono backend)
        if [ -d "$UNITY_DATA/Managed" ]; then
            echo "--- Managed/ (Mono scripting backend) ---"
            ls -la "$UNITY_DATA/Managed/" 2>/dev/null || true
            echo ""
            echo "DLL files:"
            find "$UNITY_DATA/Managed" -name "*.dll" -exec du -h {} \; | sort -rh
        else
            echo "No Managed/ directory - may use IL2CPP backend"
        fi
        echo ""

        # Check for il2cpp
        if [ -d "$UNITY_DATA/il2cpp" ] || [ -f "$UNITY_DATA/Metadata/global-metadata.dat" ]; then
            echo "--- IL2CPP backend detected ---"
            find "$UNITY_DATA" -name "global-metadata.dat" -exec du -h {} \;
        fi

        # Unity serialized assets
        echo ""
        echo "--- Unity serialized assets ---"
        find "$UNITY_DATA" -maxdepth 1 -type f | while read f; do
            echo "$(du -h "$f" | cut -f1)  $(basename "$f")"
        done | sort -rh | head -30
        echo ""

        # Asset bundles
        echo "--- Asset bundles (hash-named files) ---"
        HASH_COUNT=$(find "$UNITY_DATA" -maxdepth 1 -type f -regex '.*/[a-f0-9]\{32\}' 2>/dev/null | wc -l)
        echo "Hash-named files: $HASH_COUNT"
        if [ "$HASH_COUNT" -gt 0 ]; then
            echo "Largest:"
            find "$UNITY_DATA" -maxdepth 1 -type f -regex '.*/[a-f0-9]\{32\}' -exec du -h {} \; | sort -rh | head -10
        fi
        echo ""

        # Streaming assets
        echo "--- .resS streaming resources ---"
        find "$UNITY_DATA" -name "*.resS" -exec du -h {} \; | sort -rh | head -10
        RESS_COUNT=$(find "$UNITY_DATA" -name "*.resS" 2>/dev/null | wc -l)
        echo "Total .resS files: $RESS_COUNT"
    else
        echo "No Unity Data directory found - may not be a Unity game"
    fi
    echo ""

    echo "--- Game data files ---"
    # Look for common game data patterns
    find "$APP_BUNDLE" -type f \( \
        -name "*.xml" -o -name "*.json" -o -name "*.plist" -o -name "*.ini" -o \
        -name "*.csv" -o -name "*.txt" -o -name "*.bin" -o -name "*.dat" -o \
        -name "*.map" -o -name "*.civscen" -o -name "*.lua" -o -name "*.cfg" \
    \) 2>/dev/null | sort | head -100
    echo ""

    echo "--- File type summary ---"
    find "$APP_BUNDLE" -type f | while read f; do
        ext="${f##*.}"
        if [ "$ext" != "$f" ]; then
            echo ".$ext"
        else
            echo "(no extension)"
        fi
    done | sort | uniq -c | sort -rn
    echo ""

    echo "--- Directory tree (depth 3) ---"
    find "$APP_BUNDLE" -maxdepth 3 -type d | sort
    echo ""

    echo "--- Total file count ---"
    find "$APP_BUNDLE" -type f | wc -l
    echo ""

    echo "--- Total size ---"
    du -sh "$APP_BUNDLE"

} > "$STRUCTURE_FILE" 2>&1
echo "Structure report: $STRUCTURE_FILE"

# ── Step 3: Read Info.plist ───────────────────────────────────────────────────

echo "=== Reading app metadata ==="

# Install plistutil if needed (for reading binary plists on Linux)
if ! command -v plistutil &>/dev/null; then
    echo "Installing plistutil..."
    sudo apt-get update -qq && sudo apt-get install -y -qq libplist-utils
fi

PLIST_XML="$SCRIPT_DIR/Info.plist.xml"
if [ -f "$APP_BUNDLE/Info.plist" ] && [ ! -f "$PLIST_XML" ]; then
    if command -v plistutil &>/dev/null; then
        plistutil -i "$APP_BUNDLE/Info.plist" -o "$PLIST_XML" 2>/dev/null || true
        echo "Converted Info.plist to XML: $PLIST_XML"
    fi
fi

# ── Step 4: Decompile C# assemblies (if Mono backend) ────────────────────────

echo "=== Decompiling C# assemblies ==="

# Find Unity Data/Managed directory
UNITY_DATA=""
for candidate in "$APP_BUNDLE/Data" "$APP_BUNDLE/data"; do
    if [ -d "$candidate" ]; then
        UNITY_DATA="$candidate"
        break
    fi
done

if [ -n "$UNITY_DATA" ] && [ -d "$UNITY_DATA/Managed" ]; then
    MANAGED_DIR="$UNITY_DATA/Managed"

    # Decompile Assembly-CSharp.dll
    if [ -f "$MANAGED_DIR/Assembly-CSharp.dll" ]; then
        DECOMPILED_CSHARP="$DECOMPILED_DIR/Assembly-CSharp"
        if [ -d "$DECOMPILED_CSHARP" ]; then
            echo "Assembly-CSharp already decompiled, skipping"
        else
            echo "Decompiling Assembly-CSharp.dll..."
            mkdir -p "$DECOMPILED_CSHARP"
            "$ILSPYCMD" "$MANAGED_DIR/Assembly-CSharp.dll" -p -o "$DECOMPILED_CSHARP"
            COUNT=$(find "$DECOMPILED_CSHARP" -name "*.cs" | wc -l)
            echo "Decompiled $COUNT C# files to $DECOMPILED_CSHARP"
        fi
    else
        echo "No Assembly-CSharp.dll found"
    fi

    # Decompile Assembly-CSharp-firstpass.dll if it exists
    if [ -f "$MANAGED_DIR/Assembly-CSharp-firstpass.dll" ]; then
        DECOMPILED_FP="$DECOMPILED_DIR/Assembly-CSharp-firstpass"
        if [ -d "$DECOMPILED_FP" ]; then
            echo "Assembly-CSharp-firstpass already decompiled, skipping"
        else
            echo "Decompiling Assembly-CSharp-firstpass.dll..."
            mkdir -p "$DECOMPILED_FP"
            "$ILSPYCMD" "$MANAGED_DIR/Assembly-CSharp-firstpass.dll" -p -o "$DECOMPILED_FP"
            COUNT=$(find "$DECOMPILED_FP" -name "*.cs" | wc -l)
            echo "Decompiled $COUNT C# files to $DECOMPILED_FP"
        fi
    fi

    # Decompile Assembly-UnityScript-firstpass.dll if it exists
    if [ -f "$MANAGED_DIR/Assembly-UnityScript-firstpass.dll" ]; then
        DECOMPILED_US="$DECOMPILED_DIR/Assembly-UnityScript-firstpass"
        if [ -d "$DECOMPILED_US" ]; then
            echo "Assembly-UnityScript-firstpass already decompiled, skipping"
        else
            echo "Decompiling Assembly-UnityScript-firstpass.dll..."
            mkdir -p "$DECOMPILED_US"
            "$ILSPYCMD" "$MANAGED_DIR/Assembly-UnityScript-firstpass.dll" -p -o "$DECOMPILED_US"
            COUNT=$(find "$DECOMPILED_US" -name "*.cs" | wc -l)
            echo "Decompiled $COUNT C# files to $DECOMPILED_US"
        fi
    fi

    # List all other DLLs for reference
    echo ""
    echo "All managed DLLs:"
    find "$MANAGED_DIR" -name "*.dll" -exec du -h {} \; | sort -rh
else
    echo "No Managed/ directory found - skipping C# decompilation"
    if [ -n "$UNITY_DATA" ]; then
        echo "Unity data dir exists but no Mono assemblies - likely IL2CPP or non-Unity native"
    fi
fi

# ── Step 5: Analyze native binaries ──────────────────────────────────────────

echo ""
echo "=== Analyzing native binaries ==="
mkdir -p "$NATIVE_DIR"

# Find the main executable
MAIN_EXEC=""
for candidate in "$APP_BUNDLE/$APP_NAME" "$APP_BUNDLE/CivRev" "$APP_BUNDLE/CivilizationRevolution"; do
    if [ -f "$candidate" ]; then
        MAIN_EXEC="$candidate"
        break
    fi
done
# Fallback: find Mach-O executables
if [ -z "$MAIN_EXEC" ]; then
    while IFS= read -r f; do
        if file "$f" 2>/dev/null | grep -q "Mach-O"; then
            MAIN_EXEC="$f"
            break
        fi
    done < <(find "$APP_BUNDLE" -maxdepth 1 -type f)
fi

if [ -n "$MAIN_EXEC" ]; then
    echo "Main executable: $(basename "$MAIN_EXEC")"
    file "$MAIN_EXEC" | tee "$NATIVE_DIR/executable_info.txt"

    # Extract all strings
    if [ ! -f "$NATIVE_DIR/all_strings.txt" ]; then
        echo "Dumping strings from main executable..."
        strings "$MAIN_EXEC" > "$NATIVE_DIR/all_strings.txt"
        echo "  $(wc -l < "$NATIVE_DIR/all_strings.txt") strings extracted"
    fi

    # Extract symbols (nm may work on Mach-O if binutils supports it)
    if [ ! -f "$NATIVE_DIR/symbols_raw.txt" ]; then
        echo "Dumping symbols..."
        nm "$MAIN_EXEC" > "$NATIVE_DIR/symbols_raw.txt" 2>/dev/null || \
            echo "nm failed (may need Mach-O support)" > "$NATIVE_DIR/symbols_raw.txt"
        nm -D "$MAIN_EXEC" > "$NATIVE_DIR/symbols_dynamic.txt" 2>/dev/null || true
    fi

    # Filter for game-related strings
    if [ ! -f "$NATIVE_DIR/game_strings.txt" ]; then
        echo "Filtering for game-related strings..."
        grep -iE "spawn|map|tile|terrain|city|unit|combat|settler|civ|tech|wonder|building|leader|victory|save|load|scenario|dlc|native" \
            "$NATIVE_DIR/all_strings.txt" > "$NATIVE_DIR/game_strings.txt" 2>/dev/null || true
        echo "  $(wc -l < "$NATIVE_DIR/game_strings.txt") game-related strings"
    fi

    # Filter for bridge/interop functions
    if [ ! -f "$NATIVE_DIR/bridge_functions.txt" ]; then
        grep -iE "CsToCpp_|CppToCs_|DllImport|P.Invoke|native|TkNative" \
            "$NATIVE_DIR/all_strings.txt" > "$NATIVE_DIR/bridge_functions.txt" 2>/dev/null || true
    fi

    # Run radare2 analysis
    if [ ! -f "$NATIVE_DIR/r2_functions.txt" ]; then
        echo "Running radare2 analysis (this may take a while)..."
        r2 -q -e anal.timeout=180 -c "aaa; afl" "$MAIN_EXEC" > "$NATIVE_DIR/r2_functions.txt" 2>/dev/null || \
            echo "radare2 analysis failed" > "$NATIVE_DIR/r2_functions.txt"
        echo "  $(wc -l < "$NATIVE_DIR/r2_functions.txt") functions found"
    fi
else
    echo "WARNING: Could not find main executable"
fi

# Also analyze any native plugin dylibs
echo ""
echo "--- Checking for native plugin libraries ---"
find "$APP_BUNDLE" -name "*.dylib" -o -name "libTkNativeDll*" -o -name "*.so" 2>/dev/null | while read lib; do
    libname=$(basename "$lib")
    echo "Found: $libname ($(du -h "$lib" | cut -f1))"
    file "$lib"

    if [ ! -f "$NATIVE_DIR/${libname}_strings.txt" ]; then
        strings "$lib" > "$NATIVE_DIR/${libname}_strings.txt"
    fi
    if [ ! -f "$NATIVE_DIR/${libname}_symbols.txt" ]; then
        nm "$lib" > "$NATIVE_DIR/${libname}_symbols.txt" 2>/dev/null || true
    fi
done

# Check for native plugins in Frameworks/
if [ -d "$APP_BUNDLE/Frameworks" ]; then
    find "$APP_BUNDLE/Frameworks" -type f \( -name "*.dylib" -o -perm -111 \) 2>/dev/null | while read lib; do
        if file "$lib" 2>/dev/null | grep -q "Mach-O"; then
            libname=$(basename "$lib")
            echo "Framework binary: $libname ($(du -h "$lib" | cut -f1))"
            file "$lib"
            if [ ! -f "$NATIVE_DIR/${libname}_strings.txt" ]; then
                strings "$lib" > "$NATIVE_DIR/${libname}_strings.txt"
            fi
        fi
    done
fi

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "========================================="
echo "=== Extraction & Analysis Complete ==="
echo "========================================="
echo ""
echo "Outputs:"
echo "  $EXTRACT_DIR/          - Extracted IPA contents"
echo "  $STRUCTURE_FILE        - File structure report"
echo "  $SCRIPT_DIR/Info.plist.xml  - App metadata (if converted)"
if [ -d "$DECOMPILED_DIR" ]; then
echo "  $DECOMPILED_DIR/       - Decompiled C# source"
fi
echo "  $NATIVE_DIR/           - Native binary analysis"
echo ""
echo "Next steps:"
echo "  1. Read file_structure.txt for an overview"
echo "  2. Check decompiled/ for C# game logic (if Mono backend)"
echo "  3. Check native_analysis/ for binary strings and symbols"
echo "  4. Look for game data files (XML, INI, BIN) in the app bundle"
