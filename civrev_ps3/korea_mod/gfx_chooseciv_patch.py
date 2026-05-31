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

# iter-1188 Korea-plays-as-China theSelectedOption overwrite — injected
# into the root frame's civ-select keyboard handler. When the user
# confirms slot 16 (Korea) via Enter/Z, the original code fires
# `fscommand("OnAccept", theSelectedOption)` which notifies the PPU of
# the user's pick. iter-1188 attempt A proved the PPU IGNORES the
# fscommand argument (empirically — hardcoding the arg to 13 for all
# slots produced identical in-game behavior). So the PPU must read the
# currently-selected civ from some OTHER source at OnAccept time. The
# most plausible source is Scaleform `getVariable("_level0.theSelectedOption")`
# — a SWF-side variable the PPU can read back directly.
#
# iter-1188 attempt A2 (this): overwrite `theSelectedOption` itself
# in-place BEFORE the fscommand fires, so any getVariable-based read
# by the PPU picks up the remapped slot. When the user confirms slot
# 16 (Korea), we rewrite `theSelectedOption = 6` (China's slot) then
# fire the fscommand. The SWF's visual state transitions out of
# civ-select immediately afterward so the brief cursor jump is
# invisible to the user. This keeps v1.0 spec "Korea is a renamed
# China" intact at the dispatch boundary. See PRD §9.Z for the full
# write-up of the iter-1188 investigation history.
#
# A future v1.2 that extends the PPU civ-record table to a real
# 17th entry can revert this overwrite and dispatch slot 16 to a real
# Korean civ index.
ONACCEPT_KOREA_REMAP = """\
var EnterMode = function(theMode)
{
   switch(theMode)
   {
      case "options":
         onKeyDown = function()
         {
            var _loc3_ = Key.getCode();
            switch(_loc3_)
            {
               case 20:
                  if(_root.testingMode == true)
                  {
                     trace("capslock");
                     this.theMainPanel.PortraitFadeOut();
                  }
                  break;
               case 77:
                  this.theMainPanel.ShowPortrait(true);
                  break;
               case 16:
                  this.theMainPanel.ShowPortrait(false);
                  break;
               case 87:
               case 38:
               case 83:
               case 40:
                  break;
               case 65:
               case 37:
                  goLeft();
                  break;
               case 68:
               case 39:
                  goRight();
                  break;
               case 45:
                  trace("fscommand(\\"OnPressY\\", 0);");
                  fscommand("OnPressY",0);
                  break;
               case 42:
                  trace("fscommand(\\"OnPressX\\", 0);");
                  fscommand("OnPressX",0);
                  break;
               case 13:
               case 90:
                  // iter-1188 Plan A2: overwrite theSelectedOption
                  // itself before the fscommand so any PPU-side
                  // getVariable("_level0.theSelectedOption") read at
                  // dispatch time picks up slot 6 (China) when the
                  // user confirms slot 16 (Korea). Iter-1188 attempt
                  // A1 proved the fscommand argument is ignored — the
                  // PPU must read the selection from a SWF variable
                  // instead. This in-place overwrite covers that path.
                  if(theSelectedOption == 16)
                  {
                     theSelectedOption = 6;
                  }
                  trace("fscommand(\\"OnAccept\\", " + theSelectedOption + ");");
                  fscommand("OnAccept",theSelectedOption);
                  break;
               case 8:
               case 81:
                  if(_root.demoMode == false)
                  {
                     trace("fscommand(\\"OnCancel\\", 0);");
                     fscommand("OnCancel",0);
                     AnimateExit();
                  }
                  break;
               default:
                  trace("Unknown Keypress " + _loc3_);
            }
         };
         Key.addListener(this);
         break;
      case "default":
      default:
         Key.removeListener(this);
   }
};
var ExitMode = function(theMode)
{
   switch(theMode)
   {
      case "stack":
         this.unitStack.ExitPanel();
         break;
      case "options":
      case "default":
   }
   Key.removeListener(this);
};
onLoad = function()
{
   var _loc2_ = "options";
   this.EnterMode("options");
};
"""

ONACCEPT_REL = "scripts/frame_1/DoAction_2.as"

CHOOSECIVLEADER_REL = (
    "scripts/DefineSprite_96_ChooseCivLeader/frame_1/DoAction.as"
)


def _patch_getimage_korea(scripts_dir: Path) -> None:
    """Inject the Korea case into ChooseCivLeader's GetImageName().

    The stock GetImageName maps portrait indices 0-16 to nation keys
    (rome, egypt, ..., barbarian). Index 16 maps to "barbarian" and
    17+ maps to "default". We add a Korea case so index "16" now
    routes to "korea" (loading ldr_korea.dds) instead of "barbarian".
    The old barbarian case is unreachable since no slotData uses it
    in the Korea-mod carousel.
    """
    chooseciv = scripts_dir / CHOOSECIVLEADER_REL
    if not chooseciv.is_file():
        raise SystemExit(
            f"Expected JPEXS to export {CHOOSECIVLEADER_REL}; got nothing"
        )
    src = chooseciv.read_text()
    # Replace the stock case "16" → barbarian with Korea
    old = '''\
      case "16":
      case "barbarian":
         _loc1_ = "barbarian";
         break;'''
    new = '''\
      case "16":
      case "korea":
      case "korean":
      case "sejong":
         _loc1_ = "korea";
         break;'''
    if old not in src:
        print(f"  WARNING: could not find barbarian case in GetImageName; skipping")
        return
    src = src.replace(old, new)
    chooseciv.write_text(src)
    print(f"  patched GetImageName: index 16 → korea")


SETUPUNITS_REL = "scripts/frame_1/DoAction_4.as"


def _patch_setupunits_korea(scripts_dir: Path) -> None:
    """Override Korea cell's thumbnail after SetPortrait in SetUpUnits.

    slotData16[0] stays "6" (China) so the PPU loads Mao's 3D
    leaderhead model with working animation. But the small carousel
    cell thumbnail should show Sejong, not Mao. This patch adds
    a one-liner after SetPortrait that calls SetPortraitImage("16")
    for slot 16, which routes through GetImageName → "korea" →
    ldr_korea.dds.
    """
    setupunits = scripts_dir / SETUPUNITS_REL
    if not setupunits.is_file():
        raise SystemExit(
            f"Expected JPEXS to export {SETUPUNITS_REL}; got nothing"
        )
    src = setupunits.read_text()
    old = '      _loc2_.SetPortrait(myDataArray[0]);'
    new = (
        '      _loc2_.SetPortrait(myDataArray[0]);\n'
        '      if(j == 16)\n'
        '      {\n'
        '         _loc2_.SetPortraitImage("16");\n'
        '      }'
    )
    if old not in src:
        print("  WARNING: SetPortrait call not found in SetUpUnits; skipping")
        return
    src = src.replace(old, new, 1)
    setupunits.write_text(src)
    print("  patched SetUpUnits: slot 16 thumbnail → korea")


def _stage_scripts(ffdec_jar: Path, src: Path, scripts_dir: Path) -> None:
    """Export the SWF's scripts tree and overwrite the targeted AS
    files with the Korea-synthesis + OnAccept-remap versions.
    Returns the scripts folder that `-importScript` should be
    invoked against."""
    scripts_dir.mkdir(parents=True, exist_ok=True)
    _run_jpexs(
        ["-export", "script", str(scripts_dir), str(src)],
        ffdec_jar,
    )

    # iter-1185 LoadOptions Korea synthesis (sprite 98).
    load_options = scripts_dir / LOAD_OPTIONS_REL
    if not load_options.is_file():
        raise SystemExit(
            f"Expected JPEXS to export {LOAD_OPTIONS_REL}; got nothing"
        )
    load_options.write_text(LOAD_OPTIONS_KOREA)

    # iter-1188 OnAccept slot-16-to-6 remap (root frame keyboard handler).
    on_accept = scripts_dir / ONACCEPT_REL
    if not on_accept.is_file():
        raise SystemExit(
            f"Expected JPEXS to export {ONACCEPT_REL}; got nothing"
        )
    on_accept.write_text(ONACCEPT_KOREA_REMAP)

    # Sejong portrait: patch GetImageName in ChooseCivLeader to route
    # index "16" → "korea" instead of "barbarian".
    _patch_getimage_korea(scripts_dir)

    # Sejong portrait: override Korea cell's small thumbnail in
    # SetUpUnits so it shows Sejong (ldr_korea.dds) while keeping
    # slotData16[0]="6" for the PPU's 3D leaderhead model.
    _patch_setupunits_korea(scripts_dir)


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
