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


def patch_xml(xml_path: Path) -> None:
    """Apply AS2 transformations to the JPEXS XML dump.

    Currently a no-op — iter-1183 ships the identity round-trip so
    the boot-safety of the JPEXS pipeline can be verified in
    isolation before real AS2 edits land in iter-1184+.
    """
    _ = xml_path  # intentional no-op


def jpexs_round_trip(src: Path, dst: Path, ffdec_jar: Path) -> int:
    if not ffdec_jar.is_file():
        raise SystemExit(
            f"ffdec.jar not found at {ffdec_jar} — install JPEXS per §9.Y step 1"
        )
    # Capture src size before the JPEXS call overwrites dst (which may
    # alias src when the build pipeline passes the same path for both).
    in_size = src.stat().st_size
    with tempfile.TemporaryDirectory(prefix="gfx_patch_") as tmp:
        tmp_path = Path(tmp)
        xml_path = tmp_path / "gfx_chooseciv.xml"
        staged_src = tmp_path / "src.gfx"
        shutil.copy(src, staged_src)
        _run_jpexs(["-swf2xml", str(staged_src), str(xml_path)], ffdec_jar)
        patch_xml(xml_path)
        _run_jpexs(["-xml2swf", str(xml_path), str(dst)], ffdec_jar)
    out_size = dst.stat().st_size
    print(
        f"  gfx_chooseciv.gfx: JPEXS round-trip ok "
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
    parser.add_argument("--mode", choices=["jpexs", "byte"], default="jpexs")
    parser.add_argument("--ffdec", default=str(DEFAULT_FFDEC_JAR))
    args = parser.parse_args()
    src = Path(args.src)
    dst = Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == "byte":
        return byte_passthrough(src, dst)
    return jpexs_round_trip(src, dst, Path(args.ffdec))


if __name__ == "__main__":
    sys.exit(main())
