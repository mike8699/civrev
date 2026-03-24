#!/usr/bin/env bash
# Extract and decompile Civilization Revolution NDS ROM
# Idempotent - safe to run multiple times
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROM="$SCRIPT_DIR/civrev.nds"
EXTRACT_DIR="$SCRIPT_DIR/extracted"
NATIVE_DIR="$SCRIPT_DIR/native_analysis"
GHIDRA_DIR="$SCRIPT_DIR/ghidra_decompiled"
STRUCTURE_FILE="$SCRIPT_DIR/file_structure.txt"

# Use existing NDS_UNPACK if available (from extract_nds.py)
NDS_UNPACK_DIR="/home/mike/Desktop/civrev/NDS_UNPACK"

# Ghidra location
GHIDRA_INSTALL_DIR="$HOME/ghidra"

# ── Prerequisites ────────────────────────────────────────────────────────────

echo "=== Checking prerequisites ==="

MISSING=()
command -v strings &>/dev/null || MISSING+=(binutils)
command -v file &>/dev/null || MISSING+=(file)
command -v r2 &>/dev/null || MISSING+=(radare2)
command -v java &>/dev/null || MISSING+=(default-jdk)

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "Error: Missing required tools. Install with:"
    echo "  sudo apt-get install -y ${MISSING[*]}"
    exit 1
fi

# Ghidra
ANALYZE_HEADLESS=""
for candidate in \
    "$GHIDRA_INSTALL_DIR/support/analyzeHeadless" \
    "$GHIDRA_INSTALL_DIR"/ghidra_*/support/analyzeHeadless \
    /opt/ghidra/support/analyzeHeadless \
    /opt/ghidra/ghidra_*/support/analyzeHeadless \
    /opt/ghidra_*/support/analyzeHeadless; do
    if [ -x "$candidate" ] 2>/dev/null; then
        ANALYZE_HEADLESS="$candidate"
        break
    fi
done

if [ -z "$ANALYZE_HEADLESS" ]; then
    echo "Error: Ghidra not found. Install Ghidra first (see civrev_ios/extract_and_decompile.sh for auto-install)"
    exit 1
fi
echo "Ghidra: $ANALYZE_HEADLESS"

# ── Verify ROM exists ────────────────────────────────────────────────────────

if [ ! -f "$ROM" ]; then
    echo "Error: NDS ROM not found at $ROM"
    exit 1
fi
echo "ROM: $(basename "$ROM") ($(du -h "$ROM" | cut -f1))"
file "$ROM"

# ── Step 1: Extract ROM (use existing NDS_UNPACK or extract fresh) ────────

ARM9_BIN=""
DATA_DIR=""

if [ -d "$NDS_UNPACK_DIR" ] && [ -f "$NDS_UNPACK_DIR/arm9_original.bin" ]; then
    echo "=== Using existing NDS_UNPACK at $NDS_UNPACK_DIR ==="
    ARM9_BIN="$NDS_UNPACK_DIR/arm9_original.bin"
    DATA_DIR="$NDS_UNPACK_DIR/data"
elif [ -d "$EXTRACT_DIR" ] && [ -f "$EXTRACT_DIR/arm9_original.bin" ]; then
    echo "=== Using existing extraction at $EXTRACT_DIR ==="
    ARM9_BIN="$EXTRACT_DIR/arm9_original.bin"
    DATA_DIR="$EXTRACT_DIR/data"
else
    echo "=== Extracting ROM with extract_nds.py ==="
    EXTRACT_SCRIPT="/home/mike/Desktop/civrev/extract_nds.py"
    if [ ! -f "$EXTRACT_SCRIPT" ]; then
        echo "Error: extract_nds.py not found at $EXTRACT_SCRIPT"
        echo "  Run: pip install ndspy  # then use extract_nds.py"
        exit 1
    fi
    # extract_nds.py outputs to NDS_UNPACK in its own directory
    cd /home/mike/Desktop/civrev && python extract_nds.py "$ROM"
    cd "$SCRIPT_DIR"
    ARM9_BIN="$NDS_UNPACK_DIR/arm9_original.bin"
    DATA_DIR="$NDS_UNPACK_DIR/data"
fi

echo "ARM9 binary: $ARM9_BIN ($(du -h "$ARM9_BIN" | cut -f1))"
echo "Data dir: $DATA_DIR ($(find "$DATA_DIR" -type f | wc -l) files)"

# ── Step 2: Generate file structure report ────────────────────────────────────

if [ ! -f "$STRUCTURE_FILE" ]; then
    echo "=== Generating file structure report ==="
    {
        echo "=== Civilization Revolution NDS - File Structure ==="
        echo "Generated: $(date -Iseconds)"
        echo ""

        echo "--- ROM info ---"
        echo "File: $(basename "$ROM")"
        echo "Size: $(du -h "$ROM" | cut -f1)"
        file "$ROM"
        echo ""

        echo "--- ARM9 binary ---"
        echo "Size: $(du -h "$ARM9_BIN" | cut -f1)"
        file "$ARM9_BIN"
        echo ""

        echo "--- Overlays ---"
        OVERLAY_DIR="$(dirname "$ARM9_BIN")/overlay"
        if [ -d "$OVERLAY_DIR" ]; then
            ls -la "$OVERLAY_DIR/"
        fi
        echo ""

        echo "--- Data directory tree ---"
        find "$DATA_DIR" -type d | sort
        echo ""

        echo "--- File type summary ---"
        find "$DATA_DIR" -type f | while read f; do
            ext="${f##*.}"
            if [ "$ext" != "$f" ]; then echo ".$ext"; else echo "(no extension)"; fi
        done | sort | uniq -c | sort -rn
        echo ""

        echo "--- Localization files ---"
        find "$DATA_DIR" -path "*/Localization/*" -type f | sort
        echo ""

        echo "--- Total file count ---"
        find "$DATA_DIR" -type f | wc -l
        echo ""

        echo "--- Total size ---"
        du -sh "$DATA_DIR"

    } > "$STRUCTURE_FILE" 2>&1
    echo "Structure report: $STRUCTURE_FILE"
else
    echo "=== Structure report already exists, skipping ==="
fi

# ── Step 3: Native binary analysis (radare2 + strings) ───────────────────────

echo ""
echo "=== Analyzing ARM9 binary ==="
mkdir -p "$NATIVE_DIR"

# Strings
if [ ! -f "$NATIVE_DIR/all_strings.txt" ]; then
    echo "Dumping strings..."
    strings "$ARM9_BIN" > "$NATIVE_DIR/all_strings.txt"
    echo "  $(wc -l < "$NATIVE_DIR/all_strings.txt") strings extracted"
fi

# Game-related strings
if [ ! -f "$NATIVE_DIR/game_strings.txt" ]; then
    echo "Filtering game strings..."
    grep -iE "spawn|map|tile|terrain|city|unit|combat|settler|civ|tech|wonder|building|leader|victory|save|load|scenario|native|random|seed" \
        "$NATIVE_DIR/all_strings.txt" > "$NATIVE_DIR/game_strings.txt" 2>/dev/null || true
    echo "  $(wc -l < "$NATIVE_DIR/game_strings.txt") game-related strings"
fi

# Class/type names from mangled symbols
if [ ! -f "$NATIVE_DIR/class_names.txt" ]; then
    echo "Extracting class names..."
    grep -oE '[0-9]+[A-Z][A-Za-z]+' "$NATIVE_DIR/all_strings.txt" \
        | sed 's/^[0-9]*//' | sort -u > "$NATIVE_DIR/class_names.txt" 2>/dev/null || true
    echo "  $(wc -l < "$NATIVE_DIR/class_names.txt") class names found"
fi

# radare2 analysis
if [ ! -f "$NATIVE_DIR/r2_functions.txt" ]; then
    echo "Running radare2 analysis (ARM9 binary, this takes a few minutes)..."
    r2 -q -a arm -b 32 -e anal.timeout=300 -c "aaa; afl" "$ARM9_BIN" \
        > "$NATIVE_DIR/r2_functions.txt" 2>/dev/null || true
    echo "  $(wc -l < "$NATIVE_DIR/r2_functions.txt") functions found"
fi

if [ ! -f "$NATIVE_DIR/r2_imports.txt" ]; then
    echo "Extracting imports..."
    r2 -q -a arm -b 32 -c "ii" "$ARM9_BIN" > "$NATIVE_DIR/r2_imports.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_sections.txt" ]; then
    echo "Extracting sections..."
    r2 -q -a arm -b 32 -c "iS" "$ARM9_BIN" > "$NATIVE_DIR/r2_sections.txt" 2>/dev/null || true
fi

if [ ! -f "$NATIVE_DIR/r2_strings_data.txt" ]; then
    echo "Extracting data-section strings..."
    r2 -q -a arm -b 32 -c "iz" "$ARM9_BIN" > "$NATIVE_DIR/r2_strings_data.txt" 2>/dev/null || true
fi

# Game function filtering
if [ ! -f "$NATIVE_DIR/game_functions.txt" ]; then
    echo "Filtering game functions..."
    grep -iE "city|unit|combat|tech|map|terrain|tile|wonder|leader|civ|save|load|game|turn|victory|scenario|barbar|diplo|trade|settler|spawn|generate|random|seed" \
        "$NATIVE_DIR/r2_functions.txt" > "$NATIVE_DIR/game_functions.txt" 2>/dev/null || true
    echo "  $(wc -l < "$NATIVE_DIR/game_functions.txt") game-related functions"
fi

# Overlay analysis
OVERLAY_DIR="$(dirname "$ARM9_BIN")/overlay"
if [ -d "$OVERLAY_DIR" ] && [ ! -f "$NATIVE_DIR/overlay_info.txt" ]; then
    echo "Analyzing overlays..."
    {
        for ov in "$OVERLAY_DIR"/overlay_*.bin; do
            ovname=$(basename "$ov")
            ovsize=$(du -h "$ov" | cut -f1)
            ovstrings=$(strings "$ov" 2>/dev/null | wc -l)
            echo "$ovname  size=$ovsize  strings=$ovstrings"
        done
    } > "$NATIVE_DIR/overlay_info.txt"
fi

# ── Step 4: Ghidra headless decompilation ─────────────────────────────────────

echo ""
echo "=== Decompiling ARM9 with Ghidra ==="

GHIDRA_PROJECT_DIR="$SCRIPT_DIR/.ghidra_project"
GHIDRA_PROJECT_NAME="CivRevNDS"

if [ -d "$GHIDRA_DIR" ] && [ "$(find "$GHIDRA_DIR" -name '*.c' 2>/dev/null | head -1)" != "" ]; then
    echo "Ghidra decompilation already exists, skipping"
    echo "  $(find "$GHIDRA_DIR" -name '*.c' | wc -l) C files in $GHIDRA_DIR"
else
    mkdir -p "$GHIDRA_DIR"
    mkdir -p "$GHIDRA_PROJECT_DIR"

    # Python decompile script (avoids Java version issues)
    DECOMPILE_SCRIPT="$GHIDRA_PROJECT_DIR/DecompileAll.py"
    cat > "$DECOMPILE_SCRIPT" << 'GHIDRA_SCRIPT'
# Decompile all functions to C pseudocode grouped by namespace
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

for className, parts in fileContents.items():
    sanitized = re.sub(r'[^a-zA-Z0-9_.\-]', '_', className)
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    outPath = os.path.join(outputDir, sanitized + ".c")
    with open(outPath, "w") as f:
        f.write("".join(parts))

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
    echo "  ARM9 binary: $(du -h "$ARM9_BIN" | cut -f1)"
    echo "  Output: $GHIDRA_DIR/"

    rm -rf "$GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.gpr" \
           "$GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.rep" 2>/dev/null || true

    "$ANALYZE_HEADLESS" \
        "$GHIDRA_PROJECT_DIR" "$GHIDRA_PROJECT_NAME" \
        -import "$ARM9_BIN" \
        -processor "ARM:LE:32:v4t" \
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

# ── Step 5: Generate summary ─────────────────────────────────────────────────

echo ""
echo "=== Generating analysis summary ==="

SUMMARY_FILE="$NATIVE_DIR/SUMMARY.txt"
{
    echo "=== CivRev NDS ARM9 Analysis Summary ==="
    echo "Generated: $(date -Iseconds)"
    echo ""
    echo "ROM: $(file "$ROM")"
    echo "ARM9: $(du -h "$ARM9_BIN" | cut -f1)"
    echo ""
    echo "--- Counts ---"
    echo "Total strings:        $(wc -l < "$NATIVE_DIR/all_strings.txt" 2>/dev/null || echo 0)"
    echo "Game strings:         $(wc -l < "$NATIVE_DIR/game_strings.txt" 2>/dev/null || echo 0)"
    echo "Class names:          $(wc -l < "$NATIVE_DIR/class_names.txt" 2>/dev/null || echo 0)"
    echo "r2 functions:         $(wc -l < "$NATIVE_DIR/r2_functions.txt" 2>/dev/null || echo 0)"
    echo "Game functions:       $(wc -l < "$NATIVE_DIR/game_functions.txt" 2>/dev/null || echo 0)"
    if [ -d "$GHIDRA_DIR" ]; then
        echo "Ghidra decompiled:    $(find "$GHIDRA_DIR" -name '*.c' 2>/dev/null | wc -l) files"
    fi
    echo ""
    echo "--- Class names ---"
    cat "$NATIVE_DIR/class_names.txt" 2>/dev/null | head -100
} > "$SUMMARY_FILE" 2>&1
echo "Summary: $SUMMARY_FILE"

# ── Final output ──────────────────────────────────────────────────────────────

echo ""
echo "========================================="
echo "=== Extraction & Analysis Complete ==="
echo "========================================="
echo ""
echo "Outputs:"
echo "  $STRUCTURE_FILE             - File structure report"
echo "  $NATIVE_DIR/                - Binary analysis (strings, functions, classes)"
echo "  $GHIDRA_DIR/                - Ghidra decompiled C pseudocode"
echo "    _all_functions.c          - Every function in one file"
echo "    <ClassName>.c             - Functions grouped by class"
echo ""
echo "Data files (from NDS_UNPACK):"
echo "  $DATA_DIR/Localization/     - Game text data"
echo "  $DATA_DIR/interface/        - UI sprite assets"
echo "  $DATA_DIR/units/            - Unit sprites"
echo "  $DATA_DIR/terrain/          - Terrain tiles"
echo "  $DATA_DIR/structures/       - Building/wonder sprites"
echo "  $DATA_DIR/leaders/          - Leader portraits"
echo "  $DATA_DIR/audio/            - Sound data (SDAT)"
