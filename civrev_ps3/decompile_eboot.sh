#!/bin/bash
# =============================================================================
# CivRev1 EBOOT.ELF Decompilation Script
# =============================================================================
# Exports decompiled C pseudocode from Ghidra analysis of the PS3 EBOOT.ELF.
# Uses the EXISTING Ghidra project (read-only copy) to avoid re-analyzing.
#
# Output: decompiled/EBOOT/ directory with one .c file per function
#
# Dependencies installed idempotently:
#   - JDK 17+ (via apt)
#   - Ghidra 11.3 (downloaded to ~/ghidra if not present)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CIVREV_DIR="$SCRIPT_DIR"
EBOOT="$CIVREV_DIR/EBOOT.ELF"
GHIDRA_PROJECT_DIR="$CIVREV_DIR/ghidra"
GHIDRA_PROJECT_NAME="civrev"
OUTPUT_DIR="$CIVREV_DIR/decompiled/EBOOT"
WORK_DIR="$CIVREV_DIR/decompiled/.ghidra_work"
GHIDRA_SCRIPT_DIR="$CIVREV_DIR/decompiled/.ghidra_scripts"

# Ghidra install location
GHIDRA_INSTALL="${GHIDRA_INSTALL:-$HOME/ghidra}"
GHIDRA_VERSION="11.3"
GHIDRA_DATE="20250205"
GHIDRA_URL="https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/ghidra_${GHIDRA_VERSION}_PUBLIC_${GHIDRA_DATE}.zip"

# --------------------------------------------------------------------------
# Color output helpers
# --------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# --------------------------------------------------------------------------
# Preflight checks
# --------------------------------------------------------------------------
if [[ ! -f "$EBOOT" ]]; then
    error "EBOOT.ELF not found at $EBOOT"
    exit 1
fi

if [[ ! -f "$GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.gpr" ]]; then
    error "Ghidra project not found at $GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.gpr"
    error "This script expects an existing Ghidra project with analysis already done."
    exit 1
fi

# --------------------------------------------------------------------------
# Step 1: Install JDK 17+ (idempotent)
# --------------------------------------------------------------------------
install_jdk() {
    if java -version 2>&1 | grep -qE 'version "(1[7-9]|[2-9][0-9])'; then
        info "JDK 17+ already installed: $(java -version 2>&1 | head -1)"
        return 0
    fi

    info "Installing JDK 17..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq openjdk-17-jdk
    info "JDK 17 installed: $(java -version 2>&1 | head -1)"
}

# --------------------------------------------------------------------------
# Step 2: Install Ghidra (idempotent)
# --------------------------------------------------------------------------
find_ghidra() {
    # Check common locations for analyzeHeadless
    local candidates=(
        "$GHIDRA_INSTALL/support/analyzeHeadless"
        "$GHIDRA_INSTALL/ghidra_${GHIDRA_VERSION}_PUBLIC/support/analyzeHeadless"
        "$HOME/ghidra_${GHIDRA_VERSION}_PUBLIC/support/analyzeHeadless"
    )
    # Also check if ghidra is in PATH
    if command -v analyzeHeadless &>/dev/null; then
        ANALYZE_HEADLESS="$(command -v analyzeHeadless)"
        return 0
    fi
    # Check /opt
    for f in /opt/ghidra*/support/analyzeHeadless; do
        if [[ -x "$f" ]]; then
            ANALYZE_HEADLESS="$f"
            return 0
        fi
    done
    # Check candidates
    for f in "${candidates[@]}"; do
        if [[ -x "$f" ]]; then
            ANALYZE_HEADLESS="$f"
            return 0
        fi
    done
    return 1
}

install_ghidra() {
    if find_ghidra; then
        info "Ghidra already installed: $ANALYZE_HEADLESS"
        return 0
    fi

    info "Downloading Ghidra ${GHIDRA_VERSION} to $GHIDRA_INSTALL ..."
    mkdir -p "$GHIDRA_INSTALL"
    local zip_file="/tmp/ghidra_${GHIDRA_VERSION}.zip"

    if [[ ! -f "$zip_file" ]]; then
        wget -q --show-progress -O "$zip_file" "$GHIDRA_URL"
    else
        info "Using cached download at $zip_file"
    fi

    info "Extracting Ghidra..."
    unzip -qo "$zip_file" -d "$GHIDRA_INSTALL"

    if ! find_ghidra; then
        error "Ghidra installation failed — analyzeHeadless not found after extraction"
        exit 1
    fi
    info "Ghidra installed: $ANALYZE_HEADLESS"
}

# --------------------------------------------------------------------------
# Step 3: Write the Ghidra export script (Python/Jython)
# --------------------------------------------------------------------------
write_ghidra_script() {
    mkdir -p "$GHIDRA_SCRIPT_DIR"
    cat > "$GHIDRA_SCRIPT_DIR/ExportDecompiledC.py" << 'GHIDRA_SCRIPT'
# ExportDecompiledC.py — Ghidra headless script
# Exports decompiled C pseudocode for all functions in the program.
# Usage: analyzeHeadless ... -postScript ExportDecompiledC.py <output_dir>

import os
import sys
from ghidra.app.decompiler import DecompInterface, DecompileOptions
from ghidra.util.task import ConsoleTaskMonitor

args = getScriptArgs()
if len(args) < 1:
    print("ERROR: output directory argument required")
    sys.exit(1)

output_dir = args[0]
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Set up decompiler
monitor = ConsoleTaskMonitor()
decomp = DecompInterface()

# Increase timeout and configure options
opts = DecompileOptions()
decomp.setOptions(opts)
decomp.openProgram(currentProgram)

func_mgr = currentProgram.getFunctionManager()
func_count = func_mgr.getFunctionCount()
print("Total functions to decompile: %d" % func_count)

exported = 0
failed = 0
index_lines = []

for func in func_mgr.getFunctions(True):
    name = func.getName()
    addr = func.getEntryPoint().toString()

    try:
        results = decomp.decompileFunction(func, 60, monitor)
        if results is not None and results.decompileCompleted():
            decomp_func = results.getDecompiledFunction()
            if decomp_func is not None:
                code = decomp_func.getC()
                if code:
                    # Sanitize filename: replace non-alphanumeric chars
                    safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
                    filename = "%s_%s.c" % (addr, safe_name)
                    filepath = os.path.join(output_dir, filename)

                    with open(filepath, 'w') as f:
                        f.write("// Function: %s\n" % name)
                        f.write("// Address:  %s\n" % addr)
                        f.write("// Size:     %d bytes\n\n" % func.getBody().getNumAddresses())
                        f.write(code)

                    index_lines.append("%s\t%s\t%d" % (addr, name, func.getBody().getNumAddresses()))
                    exported += 1
                else:
                    failed += 1
            else:
                failed += 1
        else:
            error_msg = results.getErrorMessage() if results else "null result"
            failed += 1
    except Exception as e:
        print("WARN: Failed to decompile %s @ %s: %s" % (name, addr, str(e)))
        failed += 1

    total = exported + failed
    if total % 500 == 0:
        print("Progress: %d / %d (exported: %d, failed: %d)" % (total, func_count, exported, failed))

# Write index file
index_path = os.path.join(output_dir, "_function_index.tsv")
with open(index_path, 'w') as f:
    f.write("address\tname\tsize_bytes\n")
    for line in sorted(index_lines):
        f.write(line + "\n")

print("=" * 60)
print("Export complete!")
print("  Exported: %d functions" % exported)
print("  Failed:   %d functions" % failed)
print("  Output:   %s" % output_dir)
print("  Index:    %s" % index_path)
print("=" * 60)
GHIDRA_SCRIPT
    info "Ghidra export script written to $GHIDRA_SCRIPT_DIR/ExportDecompiledC.py"
}

# --------------------------------------------------------------------------
# Step 4: Copy Ghidra project to working directory (don't modify original)
# --------------------------------------------------------------------------
prepare_work_project() {
    if [[ -d "$WORK_DIR" ]]; then
        info "Cleaning previous work directory..."
        rm -rf "$WORK_DIR"
    fi

    mkdir -p "$WORK_DIR"
    info "Copying Ghidra project to work directory (preserving original)..."
    cp "$GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.gpr" "$WORK_DIR/"
    cp -r "$GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.rep" "$WORK_DIR/"
    info "Work project at $WORK_DIR/$GHIDRA_PROJECT_NAME.gpr"
}

# --------------------------------------------------------------------------
# Step 5: Detect program name inside the Ghidra project
# --------------------------------------------------------------------------
detect_program_name() {
    # The program name in Ghidra's project is typically the imported filename.
    # Look inside the .rep directory for it.
    local rep_dir="$WORK_DIR/$GHIDRA_PROJECT_NAME.rep"

    # Ghidra stores programs under .rep/idata/ or .rep/user/ directories
    # The folder name under idata is usually a hash, but we can check the project XML
    local project_xml="$WORK_DIR/$GHIDRA_PROJECT_NAME.rep/project.prp"
    if [[ -f "$project_xml" ]]; then
        # Try to extract program name from project properties
        local prog_name
        prog_name=$(grep -oP 'NAME="[^"]*"' "$project_xml" 2>/dev/null | head -1 | sed 's/NAME="//;s/"//' || true)
        if [[ -n "$prog_name" ]]; then
            PROGRAM_NAME="$prog_name"
            info "Detected program name from project: $PROGRAM_NAME"
            return 0
        fi
    fi

    # Fallback: try common names
    PROGRAM_NAME="EBOOT.ELF"
    info "Using default program name: $PROGRAM_NAME"
}

# --------------------------------------------------------------------------
# Step 6: Run Ghidra headless export
# --------------------------------------------------------------------------
run_export() {
    mkdir -p "$OUTPUT_DIR"

    info "Starting Ghidra headless decompilation export..."
    info "This may take a while for a 26MB binary..."
    echo ""

    "$ANALYZE_HEADLESS" \
        "$WORK_DIR" \
        "$GHIDRA_PROJECT_NAME" \
        -process "$PROGRAM_NAME" \
        -readOnly \
        -noanalysis \
        -scriptPath "$GHIDRA_SCRIPT_DIR" \
        -postScript ExportDecompiledC.py "$OUTPUT_DIR" \
        2>&1 | tee "$OUTPUT_DIR/_ghidra_export.log"

    local exit_code=${PIPESTATUS[0]}
    if [[ $exit_code -ne 0 ]]; then
        error "Ghidra headless export failed (exit code $exit_code)"
        error "Check log at $OUTPUT_DIR/_ghidra_export.log"
        exit 1
    fi

    info "Export complete! Output in $OUTPUT_DIR"
}

# --------------------------------------------------------------------------
# Step 7: Cleanup work directory
# --------------------------------------------------------------------------
cleanup() {
    if [[ -d "$WORK_DIR" ]]; then
        info "Cleaning up work directory..."
        rm -rf "$WORK_DIR"
    fi
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
main() {
    echo "============================================="
    echo " CivRev1 EBOOT.ELF Decompilation"
    echo "============================================="
    echo ""
    info "EBOOT.ELF:      $EBOOT ($(du -sh "$EBOOT" | cut -f1))"
    info "Ghidra project: $GHIDRA_PROJECT_DIR/$GHIDRA_PROJECT_NAME.gpr"
    info "Output dir:     $OUTPUT_DIR"
    echo ""

    install_jdk
    install_ghidra
    write_ghidra_script
    prepare_work_project
    detect_program_name
    run_export
    cleanup

    echo ""
    info "Done! Decompiled functions are in: $OUTPUT_DIR"
    info "Function index: $OUTPUT_DIR/_function_index.tsv"
    echo ""
    echo "Next steps:"
    echo "  grep -rl 'spawn' $OUTPUT_DIR/       # Find spawn-related functions"
    echo "  grep -rl 'settler' $OUTPUT_DIR/      # Find settler placement logic"
    echo "  grep -rl 'StartPos' $OUTPUT_DIR/     # Find starting position logic"
}

main "$@"
