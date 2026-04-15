#!/usr/bin/env python3
"""AS2 patcher for gfx_chooseciv.gfx (JPEXS-backed).

iter-1183 (2026-04-15): rewritten onto the JPEXS round-trip path per
the iter-1182 §9.Y carousel unblock directive. The previous iter-195
in-place byte-patcher path is retained as a fallback under
`--mode=byte` but the default mode is `--mode=jpexs`, which does a
full SWF→XML→SWF round-trip through JPEXS so subsequent AS2-level
edits can live as XML transformations.

Current default behavior: **identity round-trip** — parses the
source file with JPEXS and re-serializes it with no edits. The
output is byte-different from the input (JPEXS canonicalizes some
tag length fields, typically yielding a 2-4 byte smaller file) but
semantically identical: same GFX\\x08 magic, same version 8, same
tag stream, same AS2 bytecode.

Purpose of the identity round-trip: to verify empirically that
a JPEXS-processed Pregame.FPK boots cleanly on PS3. Once M9
Caesar smoke PASSes with the identity round-trip, subsequent
iterations can drop real AS2 transformations into `patch_xml()`
with confidence that the round-trip itself isn't the thing
breaking boot.

Historical in-place byte-patch findings (iter-195, iter-200)
remain archived in git history at commit bda5c78 and earlier;
they identified specific byte offsets for `numOptions` literals
that turned out to be INERT for the cursor right-clamp. Under
the iter-1182 directive, the clamp is expected to live in AS2
event handlers that the byte-patcher couldn't reach cleanly;
the JPEXS path will.

Usage:
    gfx_chooseciv_patch.py <src.gfx> <dst.gfx>
        [--mode=jpexs|byte] [--ffdec=<path>]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


EXPECTED_SIZE = 59646

DEFAULT_FFDEC_JAR = (
    Path(__file__).resolve().parent.parent / "tools" / "ffdec" / "ffdec.jar"
)

# iter-195 byte-patch constants retained as reference (INERT per iter-200).
NUM_OPTIONS_I32_OFFSET = 0x52F8


def _run_jpexs(args: list[str], ffdec_jar: Path) -> None:
    cmd = ["java", "-jar", str(ffdec_jar), *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"ffdec.jar failed: {' '.join(cmd)}")


# iter-1185 Korea synthesis — injected into LoadOptions as a prefix
# that runs before the carousel cell-creation loop. When numOptions is
# 17 (stock production value set by PPU), the prefix bumps it to 18,
# clones slotData6 (China/Mao) into slotData16 with "Sejong"/"Koreans"
# label overrides, and pushes the old slotData16 (Random) to slot 17.
# The existing SWF-side carousel logic is already parameterized over
# _parent.numOptions so no other AS2 edits are required (see
# docs/as2-literals-inventory.md for the proof).
LOAD_OPTIONS_KOREA = """\
var LoadOptions = function()
{
   if(_parent.numOptions == 17 && _parent.slotData17 == undefined)
   {
      _parent.slotData17 = _parent.slotData16;
      _parent.slotData16 = _parent.slotData6.slice();
      _parent.slotData16[1] = "Sejong";
      _parent.slotData16[2] = "Koreans";
      _parent.theActiveArray[17] = _parent.theActiveArray[16];
      _parent.theActiveArray[16] = "1";
      _parent.theColorArray[17] = _parent.theColorArray[16];
      _parent.numOptions = 18;
   }
   if(_root.testingMode == 1)
   {
      numLoaded = _parent.numOptions - 1;
   }
   else
   {
      numLoaded = 0;
   }
   if(_parent.numOptions > 0)
   {
      i = 0;
      while(i < _parent.numOptions)
      {
         this.attachMovie("ChooseCivLeader",this["option_" + i],this.getNextHighestDepth(),{_name:["option_" + i],_x:parseInt(xloc),_y:parseInt(yloc)});
         i++;
      }
   }
   else
   {
      trace("PROBLEM LOADING: numOptions = " + numOptions);
   }
};
"""

LOAD_OPTIONS_REL = (
    "scripts/DefineSprite_98_options_mov/frame_1/DoAction_2.as"
)


def _stage_scripts(ffdec_jar: Path, src: Path, scripts_dir: Path) -> None:
    """Export the SWF's scripts tree and overwrite the targeted AS
    file with the Korea-synthesis version. Returns the scripts folder
    that `-importScript` should be invoked against."""
    scripts_dir.mkdir(parents=True, exist_ok=True)
    _run_jpexs(
        ["-export", "script", str(scripts_dir), str(src)],
        ffdec_jar,
    )
    target = scripts_dir / LOAD_OPTIONS_REL
    if not target.is_file():
        raise SystemExit(
            f"Expected JPEXS to export {LOAD_OPTIONS_REL}; got nothing"
        )
    target.write_text(LOAD_OPTIONS_KOREA)


def jpexs_synthesize_korea(src: Path, dst: Path, ffdec_jar: Path) -> int:
    """Apply the iter-1185 Korea synthesis edit via JPEXS.

    Steps:
      1. Export SWF scripts to a temp dir.
      2. Overwrite the LoadOptions .as source with the Korea-synthesis
         version (see LOAD_OPTIONS_KOREA above).
      3. Re-import via `-importScript`, producing a modified SWF at dst.

    The output SWF is larger than the input because JPEXS recompiles
    the scripts from source using a non-byte-equivalent AS1/2
    assembler. iter-1185 verified empirically that the larger file
    boots clean on PS3 and that the Korea cell renders at slot 16
    with Sejong/Koreans labels.
    """
    if not ffdec_jar.is_file():
        raise SystemExit(
            f"ffdec.jar not found at {ffdec_jar} — install JPEXS per §9.Y step 1"
        )
    in_size = src.stat().st_size
    with tempfile.TemporaryDirectory(prefix="gfx_patch_") as tmp:
        tmp_path = Path(tmp)
        staged_src = tmp_path / "src.gfx"
        scripts_dir = tmp_path / "scripts_export"
        shutil.copy(src, staged_src)
        _stage_scripts(ffdec_jar, staged_src, scripts_dir)
        _run_jpexs(
            ["-importScript", str(staged_src), str(dst), str(scripts_dir)],
            ffdec_jar,
        )
    out_size = dst.stat().st_size
    print(
        f"  gfx_chooseciv.gfx: JPEXS Korea synthesis ok "
        f"({in_size} → {out_size} bytes)"
    )
    return 0


def byte_passthrough(src: Path, dst: Path) -> int:
    src_bytes = src.read_bytes()
    if len(src_bytes) != EXPECTED_SIZE:
        raise SystemExit(
            f"unexpected gfx size {len(src_bytes)} (expected {EXPECTED_SIZE})"
        )
    dst.write_bytes(src_bytes)
    print(f"  gfx_chooseciv.gfx: byte pass-through ({len(src_bytes)} bytes)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument(
        "--mode",
        choices=["jpexs", "byte", "identity"],
        default="jpexs",
        help=(
            "jpexs = Korea synthesis via LoadOptions prefix injection "
            "(iter-1185 default). byte = iter-195 fallback pass-through. "
            "identity = iter-1183 swf2xml → xml2swf with no edits."
        ),
    )
    parser.add_argument("--ffdec", default=str(DEFAULT_FFDEC_JAR))
    args = parser.parse_args()
    src = Path(args.src)
    dst = Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == "byte":
        return byte_passthrough(src, dst)
    if args.mode == "identity":
        # Retained for iter-1183 regression use.
        in_size = src.stat().st_size
        with tempfile.TemporaryDirectory(prefix="gfx_patch_") as tmp:
            tmp_path = Path(tmp)
            xml_path = tmp_path / "gfx_chooseciv.xml"
            staged_src = tmp_path / "src.gfx"
            shutil.copy(src, staged_src)
            _run_jpexs(
                ["-swf2xml", str(staged_src), str(xml_path)],
                Path(args.ffdec),
            )
            _run_jpexs(
                ["-xml2swf", str(xml_path), str(dst)],
                Path(args.ffdec),
            )
        out_size = dst.stat().st_size
        print(
            f"  gfx_chooseciv.gfx: JPEXS identity round-trip ok "
            f"({in_size} → {out_size} bytes)"
        )
        return 0
    return jpexs_synthesize_korea(src, dst, Path(args.ffdec))


if __name__ == "__main__":
    sys.exit(main())
