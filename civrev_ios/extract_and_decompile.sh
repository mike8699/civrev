#!/usr/bin/env bash
# Extract and decompile Civilization Revolution iOS IPA
# Idempotent - safe to run multiple times
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IPA="$SCRIPT_DIR/Civilization Revolution for iPad (v2.4.6)-mrYODA.rc302.ipa"
EXTRACT_DIR="$SCRIPT_DIR/extracted"
NATIVE_DIR="$SCRIPT_DIR/native_analysis"
GHIDRA_DIR="$SCRIPT_DIR/ghidra_decompiled"
STRUCTURE_FILE="$SCRIPT_DIR/file_structure.txt"

# Ghidra version to install if missing
GHIDRA_VERSION="11.3.1"
GHIDRA_DATE="20250219"
GHIDRA_INSTALL_DIR="$HOME/ghidra"

# ── Prerequisites ────────────────────────────────────────────────────────────

echo "=== Checking prerequisites ==="

# Check required tools, suggest apt install if missing
MISSING=()
command -v unzip &>/dev/null || MISSING+=(unzip)
command -v wget &>/dev/null || MISSING+=(wget)
command -v strings &>/dev/null || MISSING+=(binutils)
command -v file &>/dev/null || MISSING+=(file)
command -v r2 &>/dev/null || MISSING+=(radare2)
command -v java &>/dev/null || MISSING+=(default-jdk)

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "Error: Missing required tools. Install with:"
    echo "  sudo apt-get install -y ${MISSING[*]}"
    exit 1
fi

# plistutil is optional (nice to have for Info.plist conversion)
HAS_PLISTUTIL=false
command -v plistutil &>/dev/null && HAS_PLISTUTIL=true
if ! $HAS_PLISTUTIL; then
    echo "Note: plistutil not found (optional). Install with: sudo apt-get install -y libplist-utils"
fi

# Ghidra (headless decompiler) - install to ~/ghidra if not found
ANALYZE_HEADLESS=""
for candidate in \
    "$GHIDRA_INSTALL_DIR/support/analyzeHeadless" \
    "$GHIDRA_INSTALL_DIR"/ghidra_*/support/analyzeHeadless \
    "$HOME/ghidra_"*/support/analyzeHeadless \
    /opt/ghidra/support/analyzeHeadless \
    /opt/ghidra_*/support/analyzeHeadless \
    /opt/ghidra/ghidra_*/support/analyzeHeadless \
    /usr/share/ghidra/support/analyzeHeadless; do
    if [ -x "$candidate" ] 2>/dev/null; then
        ANALYZE_HEADLESS="$candidate"
        break
    fi
done

if [ -z "$ANALYZE_HEADLESS" ]; then
    echo "Ghidra not found. Installing Ghidra ${GHIDRA_VERSION} to $GHIDRA_INSTALL_DIR ..."
    GHIDRA_ZIP="ghidra_${GHIDRA_VERSION}_PUBLIC_${GHIDRA_DATE}.zip"
    GHIDRA_URL="https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/${GHIDRA_ZIP}"

    TMP_DL=$(mktemp -d)
    trap 'rm -rf "$TMP_DL"' EXIT

    echo "  Downloading from GitHub (~500 MB)..."
    wget -q --show-progress -O "$TMP_DL/$GHIDRA_ZIP" "$GHIDRA_URL"

    echo "  Extracting..."
    unzip -q "$TMP_DL/$GHIDRA_ZIP" -d "$TMP_DL/"
    # The zip extracts to ghidra_VERSION_PUBLIC/
    EXTRACTED=$(find "$TMP_DL" -maxdepth 1 -type d -name "ghidra_*" | head -1)
    if [ -z "$EXTRACTED" ]; then
        echo "Error: Could not find extracted Ghidra directory"
        exit 1
    fi
    mv "$EXTRACTED" "$GHIDRA_INSTALL_DIR"

    rm -rf "$TMP_DL"
    trap - EXIT

    ANALYZE_HEADLESS="$GHIDRA_INSTALL_DIR/support/analyzeHeadless"
    if [ ! -x "$ANALYZE_HEADLESS" ]; then
        echo "Error: Ghidra analyzeHeadless not found after install at $ANALYZE_HEADLESS"
        exit 1
    fi
    echo "  Ghidra installed to $GHIDRA_INSTALL_DIR"
fi
echo "Ghidra analyzeHeadless: $ANALYZE_HEADLESS"

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

# Find the main executable
MAIN_EXEC=""
for candidate in "$APP_BUNDLE/$APP_NAME" "$APP_BUNDLE/CivRev" "$APP_BUNDLE/CivilizationRevolution"; do
    if [ -f "$candidate" ]; then
        MAIN_EXEC="$candidate"
        break
    fi
done
if [ -z "$MAIN_EXEC" ]; then
    while IFS= read -r f; do
        if file "$f" 2>/dev/null | grep -q "Mach-O"; then
            MAIN_EXEC="$f"
            break
        fi
    done < <(find "$APP_BUNDLE" -maxdepth 1 -type f)
fi
if [ -z "$MAIN_EXEC" ]; then
    echo "Error: Could not find main Mach-O executable in app bundle"
    exit 1
fi
echo "Main executable: $(basename "$MAIN_EXEC") ($(du -h "$MAIN_EXEC" | cut -f1))"
file "$MAIN_EXEC"

# ── Step 2: Generate file structure report ────────────────────────────────────

if [ ! -f "$STRUCTURE_FILE" ]; then
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
            if command -v plistutil &>/dev/null; then
                plistutil -i "$APP_BUNDLE/Info.plist" 2>/dev/null || echo "(plistutil failed)"
            else
                file "$APP_BUNDLE/Info.plist"
            fi
        fi
        echo ""

        echo "--- Main executable ---"
        echo "$(basename "$MAIN_EXEC")"
        file "$MAIN_EXEC"
        echo "Size: $(du -h "$MAIN_EXEC" | cut -f1)"
        echo ""

        echo "--- Frameworks/ ---"
        if [ -d "$APP_BUNDLE/Frameworks" ]; then
            ls -la "$APP_BUNDLE/Frameworks/" 2>/dev/null || true
        else
            echo "(no Frameworks/ directory)"
        fi
        echo ""

        echo "--- Game data files ---"
        find "$APP_BUNDLE" -type f \( \
            -name "*.xml" -o -name "*.json" -o -name "*.plist" -o -name "*.ini" -o \
            -name "*.csv" -o -name "*.txt" -o -name "*.bin" -o -name "*.dat" -o \
            -name "*.map" -o -name "*.civscen" -o -name "*.lua" -o -name "*.cfg" \
        \) 2>/dev/null | sort | head -100
        echo ""

        echo "--- File type summary ---"
        find "$APP_BUNDLE" -type f | while read f; do
            ext="${f##*.}"
            if [ "$ext" != "$f" ]; then echo ".$ext"; else echo "(no extension)"; fi
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
else
    echo "=== Structure report already exists, skipping ==="
fi

# ── Step 3: Read Info.plist ───────────────────────────────────────────────────

PLIST_XML="$SCRIPT_DIR/Info.plist.xml"
if [ -f "$APP_BUNDLE/Info.plist" ] && [ ! -f "$PLIST_XML" ]; then
    echo "=== Converting Info.plist to XML ==="
    plistutil -i "$APP_BUNDLE/Info.plist" -o "$PLIST_XML" 2>/dev/null || true
fi

# ── Step 4: Native binary analysis (radare2) ─────────────────────────────────

echo ""
echo "=== Analyzing native binary with radare2 ==="
mkdir -p "$NATIVE_DIR"

# 4a. Basic info
file "$MAIN_EXEC" > "$NATIVE_DIR/executable_info.txt" 2>&1

# 4b. Extract all strings
if [ ! -f "$NATIVE_DIR/all_strings.txt" ]; then
    echo "Dumping strings..."
    strings "$MAIN_EXEC" > "$NATIVE_DIR/all_strings.txt"
    echo "  $(wc -l < "$NATIVE_DIR/all_strings.txt") strings extracted"
fi

# 4c. Filtered string sets
if [ ! -f "$NATIVE_DIR/game_strings.txt" ]; then
    echo "Filtering game-related strings..."
    grep -iE "spawn|map|tile|terrain|city|unit|combat|settler|civ|tech|wonder|building|leader|victory|save|load|scenario|dlc|native" \
        "$NATIVE_DIR/all_strings.txt" > "$NATIVE_DIR/game_strings.txt" 2>/dev/null || true
    echo "  $(wc -l < "$NATIVE_DIR/game_strings.txt") game-related strings"
fi

# 4d. Full radare2 analysis (functions, imports, exports, sections, ObjC classes)
if [ ! -f "$NATIVE_DIR/r2_functions.txt" ]; then
    echo "Running radare2 full analysis (this takes a few minutes)..."
    r2 -q -e anal.timeout=300 -c "aaa; afl" "$MAIN_EXEC" \
        > "$NATIVE_DIR/r2_functions.txt" 2>/dev/null || true
    echo "  $(wc -l < "$NATIVE_DIR/r2_functions.txt") functions found"
fi

if [ ! -f "$NATIVE_DIR/r2_imports.txt" ]; then
    echo "Extracting imports..."
    r2 -q -c "ii" "$MAIN_EXEC" > "$NATIVE_DIR/r2_imports.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_exports.txt" ]; then
    echo "Extracting exports..."
    r2 -q -c "iE" "$MAIN_EXEC" > "$NATIVE_DIR/r2_exports.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_sections.txt" ]; then
    echo "Extracting sections..."
    r2 -q -c "iS" "$MAIN_EXEC" > "$NATIVE_DIR/r2_sections.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_objc_classes.txt" ]; then
    echo "Extracting Objective-C classes..."
    r2 -q -c "ic" "$MAIN_EXEC" > "$NATIVE_DIR/r2_objc_classes.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_objc_methods.txt" ]; then
    echo "Extracting Objective-C methods..."
    r2 -q -c "icj" "$MAIN_EXEC" > "$NATIVE_DIR/r2_objc_methods.json" 2>/dev/null || true
    # Also a readable list: filter function list for method. entries
    grep "method\." "$NATIVE_DIR/r2_functions.txt" > "$NATIVE_DIR/r2_objc_methods.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_strings_data.txt" ]; then
    echo "Extracting data-section strings via r2..."
    r2 -q -c "iz" "$MAIN_EXEC" > "$NATIVE_DIR/r2_strings_data.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_entrypoints.txt" ]; then
    echo "Extracting entrypoints..."
    r2 -q -c "ie" "$MAIN_EXEC" > "$NATIVE_DIR/r2_entrypoints.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_relocations.txt" ]; then
    echo "Extracting relocations..."
    r2 -q -c "ir" "$MAIN_EXEC" > "$NATIVE_DIR/r2_relocations.txt" 2>/dev/null || true
fi

# 4e. Derived analysis files
if [ ! -f "$NATIVE_DIR/class_list.txt" ]; then
    echo "Building class list..."
    # Extract unique class names from ObjC method entries
    grep "method\." "$NATIVE_DIR/r2_functions.txt" 2>/dev/null \
        | sed 's/.*method\.//' | cut -d. -f1 | sort -u \
        > "$NATIVE_DIR/class_list.txt" || true
    # Also extract from ic output
    grep "^class " "$NATIVE_DIR/r2_objc_classes.txt" 2>/dev/null \
        | awk '{print $2}' | sort -u \
        >> "$NATIVE_DIR/class_list.txt" || true
    sort -u -o "$NATIVE_DIR/class_list.txt" "$NATIVE_DIR/class_list.txt"
    echo "  $(wc -l < "$NATIVE_DIR/class_list.txt") classes found"
fi

if [ ! -f "$NATIVE_DIR/game_functions.txt" ]; then
    echo "Filtering game-related functions..."
    grep -iE "city|unit|combat|tech|map|terrain|tile|wonder|leader|civ|save|load|game|turn|victory|scenario|barbar|diplo|trade|settler|spawn|generate" \
        "$NATIVE_DIR/r2_functions.txt" > "$NATIVE_DIR/game_functions.txt" 2>/dev/null || true
    echo "  $(wc -l < "$NATIVE_DIR/game_functions.txt") game-related functions"
fi

# ── Step 5: Ghidra headless decompilation ─────────────────────────────────────

echo ""
echo "=== Decompiling with Ghidra (headless mode) ==="

GHIDRA_PROJECT_DIR="$SCRIPT_DIR/.ghidra_project"
GHIDRA_PROJECT_NAME="CivRevIOS"

if [ -d "$GHIDRA_DIR" ] && [ "$(find "$GHIDRA_DIR" -name '*.c' 2>/dev/null | head -1)" != "" ]; then
    echo "Ghidra decompilation already exists, skipping"
    echo "  $(find "$GHIDRA_DIR" -name '*.c' | wc -l) C files in $GHIDRA_DIR"
else
    mkdir -p "$GHIDRA_DIR"
    mkdir -p "$GHIDRA_PROJECT_DIR"

    # Write a Ghidra Python script (avoids Java compilation issues with newer JDKs)
    DECOMPILE_SCRIPT="$GHIDRA_PROJECT_DIR/DecompileAll.py"
    cat > "$DECOMPILE_SCRIPT" << 'GHIDRA_SCRIPT'
# Decompile all functions and export to C pseudocode files grouped by class/namespace
# @category CivRev
# @runtime Jython

import os
import re
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

args = getScriptArgs()
outputDir = args[0] if args else "/tmp/ghidra_decompiled"

if not os.path.exists(outputDir):
    os.makedirs(outputDir)

decomp = DecompInterface()
decomp.openProgram(currentProgram)
monitor = ConsoleTaskMonitor()

fileContents = {}
fullDumpPath = os.path.join(outputDir, "_all_functions.c")
fullDump = open(fullDumpPath, "w")

funcs = currentProgram.getFunctionManager().getFunctions(True)
count = 0
errors = 0

for func in funcs:
    if monitor.isCancelled():
        break

    funcName = func.getName()
    ns = func.getParentNamespace()
    className = "_global" if ns.isGlobal() else ns.getName(True).replace("::", "_")

    results = decomp.decompileFunction(func, 30, monitor)

    if results and results.decompileCompleted():
        df = results.getDecompiledFunction()
        if df:
            decompiledC = df.getC()
            if decompiledC:
                header = "// Function: %s @ 0x%x\n" % (funcName, func.getEntryPoint().getOffset())

                if className not in fileContents:
                    fileContents[className] = ["// Decompiled functions for: %s\n\n" % className]
                fileContents[className].append(header)
                fileContents[className].append(decompiledC)
                fileContents[className].append("\n\n")

                fullDump.write("// === %s::%s @ 0x%x ===\n" % (className, funcName, func.getEntryPoint().getOffset()))
                fullDump.write(decompiledC)
                fullDump.write("\n\n")

                count += 1
    else:
        errors += 1

    if count > 0 and count % 500 == 0:
        println("Decompiled %d functions..." % count)

fullDump.close()

# Write per-class files
for className, parts in fileContents.items():
    sanitized = re.sub(r'[^a-zA-Z0-9_.\-]', '_', className)
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    outPath = os.path.join(outputDir, sanitized + ".c")
    with open(outPath, "w") as f:
        f.write("".join(parts))

# Write summary
summaryPath = os.path.join(outputDir, "_summary.txt")
with open(summaryPath, "w") as f:
    f.write("Ghidra Decompilation Summary\n")
    f.write("Binary: %s\n" % currentProgram.getExecutablePath())
    f.write("Functions decompiled: %d\n" % count)
    f.write("Functions failed: %d\n" % errors)
    f.write("Output files: %d class files + _all_functions.c\n\n" % len(fileContents))
    f.write("Files by class:\n")
    for cls in sorted(fileContents.keys()):
        sanitized = re.sub(r'[^a-zA-Z0-9_.\-]', '_', cls)
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        f.write("  %s.c\n" % sanitized)

println("Done. Decompiled %d functions (%d errors) into %d files in %s" % (count, errors, len(fileContents), outputDir))
GHIDRA_SCRIPT

    echo "Running Ghidra headless analysis + decompilation..."
    echo "  This will take a while (analyzing ~6700 functions in a 3.4 MB ARM binary)."
    echo "  Output: $GHIDRA_DIR/"

    # Remove old project if it exists (to allow re-import)
    rm -rf "$GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.gpr" \
           "$GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.rep" 2>/dev/null || true

    "$ANALYZE_HEADLESS" \
        "$GHIDRA_PROJECT_DIR" "$GHIDRA_PROJECT_NAME" \
        -import "$MAIN_EXEC" \
        -processor "ARM:LE:32:v7" \
        -postScript "$DECOMPILE_SCRIPT" "$GHIDRA_DIR" \
        -scriptPath "$GHIDRA_PROJECT_DIR" \
        -deleteProject \
        2>&1 | tee "$NATIVE_DIR/ghidra_log.txt"

    if [ -f "$GHIDRA_DIR/_summary.txt" ]; then
        echo ""
        cat "$GHIDRA_DIR/_summary.txt"
    fi

    echo ""
    CFILE_COUNT=$(find "$GHIDRA_DIR" -name "*.c" 2>/dev/null | wc -l)
    echo "Ghidra produced $CFILE_COUNT .c files in $GHIDRA_DIR/"
fi

# ── Step 6: Generate analysis summary ─────────────────────────────────────────

echo ""
echo "=== Generating analysis summary ==="

SUMMARY_FILE="$NATIVE_DIR/SUMMARY.txt"
{
    echo "=== CivIPAD Native Binary Analysis Summary ==="
    echo "Generated: $(date -Iseconds)"
    echo ""
    cat "$NATIVE_DIR/executable_info.txt" 2>/dev/null
    echo ""
    echo "--- Counts ---"
    echo "Total strings:        $(wc -l < "$NATIVE_DIR/all_strings.txt" 2>/dev/null || echo 0)"
    echo "Game-related strings: $(wc -l < "$NATIVE_DIR/game_strings.txt" 2>/dev/null || echo 0)"
    echo "r2 functions:         $(wc -l < "$NATIVE_DIR/r2_functions.txt" 2>/dev/null || echo 0)"
    echo "r2 imports:           $(wc -l < "$NATIVE_DIR/r2_imports.txt" 2>/dev/null || echo 0)"
    echo "r2 exports:           $(wc -l < "$NATIVE_DIR/r2_exports.txt" 2>/dev/null || echo 0)"
    echo "ObjC classes:         $(wc -l < "$NATIVE_DIR/class_list.txt" 2>/dev/null || echo 0)"
    echo "ObjC methods:         $(wc -l < "$NATIVE_DIR/r2_objc_methods.txt" 2>/dev/null || echo 0)"
    echo "Game functions:       $(wc -l < "$NATIVE_DIR/game_functions.txt" 2>/dev/null || echo 0)"
    if [ -d "$GHIDRA_DIR" ]; then
        echo "Ghidra decompiled:    $(find "$GHIDRA_DIR" -name "*.c" 2>/dev/null | wc -l) files"
    fi
    echo ""
    echo "--- Classes (from radare2) ---"
    cat "$NATIVE_DIR/class_list.txt" 2>/dev/null
    echo ""
    echo "--- Top 50 largest functions ---"
    sort -t' ' -k3 -rn "$NATIVE_DIR/r2_functions.txt" 2>/dev/null | head -50
} > "$SUMMARY_FILE" 2>&1
echo "Summary: $SUMMARY_FILE"

# ── Final output ──────────────────────────────────────────────────────────────

echo ""
echo "========================================="
echo "=== Extraction & Analysis Complete ==="
echo "========================================="
echo ""
echo "Outputs:"
echo "  $EXTRACT_DIR/          - Extracted IPA contents"
echo "  $STRUCTURE_FILE        - File structure report"
echo "  $NATIVE_DIR/           - radare2 analysis (strings, functions, classes, imports)"
echo "  $GHIDRA_DIR/           - Ghidra decompiled C pseudocode"
echo "    _all_functions.c     - Every function in one file"
echo "    <ClassName>.c        - Functions grouped by class/namespace"
echo "    _summary.txt         - Decompilation stats"
echo ""
echo "Key files to read:"
echo "  native_analysis/class_list.txt       - All ObjC/C++ classes"
echo "  native_analysis/game_functions.txt   - Game-logic functions"
echo "  native_analysis/r2_objc_methods.txt  - ObjC method list"
echo "  native_analysis/SUMMARY.txt          - Analysis overview"
echo "  ghidra_decompiled/_all_functions.c   - Full decompiled pseudocode"
