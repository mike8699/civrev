#!/usr/bin/env python3
"""In-place patcher for gfx_chooseciv.gfx.

Currently a no-op pass-through. Kept in the build pipeline as the
hook point for future Scaleform edits to the civ-select carousel
(slotData17 extension, theOptionArray bumps, etc.) — once an edit
is identified that actually moves the needle, drop it into
`patch()`.

iter-195 (2026-04-15) NEGATIVE FINDING:
    Tested flipping the `_root.numOptions = 6` default Push in
    tag[185] (top-level DoAction at file offset 0x5628) from i32(6)
    to i32(18). The Push record sits at file offset 0x59e5 and the
    i32 literal occupies the 4 bytes at 0x59eb. Patch was a clean
    same-size byte swap, no reflow.

    Result: slot 15 (Elizabeth) M6 PASS confirmed boot-safety.
    slot 17 probe — the PS3 Right cursor still clamps at slot 16
    (Random cell), no 18th carousel slot appears, no visual
    change anywhere on civ-select. The tag[185] `_root.numOptions`
    default is INERT for the civ-select panel: the PPU overrides
    it (likely via Flash::Invoke SetVariable at panel-init) before
    tag[185]'s collection loop at bc@0x153 ever runs. Verified
    output JSONs in verification/iter195_*/.

    Conclusion: extending the carousel CANNOT be done by patching
    tag[185]'s default. The next iteration must locate the PPU
    SetVariable call site that writes numOptions for the
    "ChooseCiv" panel, OR locate the cursor right-clamp that
    bounds Right press to slot 16.

Usage: gfx_chooseciv_patch.py <src.gfx> <dst.gfx>
"""

from __future__ import annotations

import sys
from pathlib import Path


EXPECTED_SIZE = 59646


def patch(src_bytes: bytes) -> bytes:
    if len(src_bytes) != EXPECTED_SIZE:
        raise SystemExit(
            f"unexpected gfx size {len(src_bytes)} (expected {EXPECTED_SIZE})"
        )
    return src_bytes


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <src.gfx> <dst.gfx>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    out = patch(src.read_bytes())
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(out)
    print(f"  gfx_chooseciv.gfx: no-op pass-through ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
