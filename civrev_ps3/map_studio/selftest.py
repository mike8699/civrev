#!/usr/bin/env python3
"""Self-test for Map Studio's data pipeline (no GUI required).

Checks, against the pristine originals in Pak9_original:
  1. .map round-trip is byte-identical
  2. generated DDS headers match the originals byte-for-byte
  3. smart patch with zero edits reproduces the originals byte-for-byte
  4. smart patch with edits only touches the edited cells (+ height feather)
  5. full-synth output has correct sizes and reports similarity scores

Run:  ../../.venv/bin/python selftest.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import texgen
from model import DLC_SLOTS, MapModel
from settings import _default_pak9_original

PAK9_ORIG = _default_pak9_original()

passed = 0
failed = 0


def check(name, ok, detail=""):
    global passed, failed
    mark = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))


def main():
    print(f"Originals: {PAK9_ORIG}")
    corpus = texgen.load_corpus(PAK9_ORIG)
    refs = texgen.load_blend_refs()
    check("load originals corpus", len(corpus) == 4,
          f"{len(corpus)}/4 maps")
    check("load blend refs", len(refs) == 8, f"{len(refs)}/8 terrain types")

    for slot in DLC_SLOTS:
        tag = slot["tag"].lower()
        print(f"\n── {slot['title']} ──")
        map_path = PAK9_ORIG / slot["file"]
        raw = map_path.read_bytes()

        # 1. Round-trip
        m = MapModel()
        m.load_file(map_path)
        check(".map round-trip", m.to_file_bytes() == raw)

        orig = {
            "heights": (PAK9_ORIG / f"map{tag}_heights.dds").read_bytes(),
            "lightmap": (PAK9_ORIG / f"map{tag}_lightmap.dds").read_bytes(),
            "blends": (PAK9_ORIG /
                       f"map{tag}_mountainhill_blends.dds").read_bytes(),
        }

        # 2. Header parity
        check("heights header", texgen.HEIGHTS_HEADER == orig["heights"][:128])
        check("lightmap header",
              texgen.LIGHTMAP_HEADER == orig["lightmap"][:128])
        check("blends header", texgen.BLENDS_HEADER == orig["blends"][:128])

        # 3. Zero-edit smart patch => byte-identical
        target = next(s for s in corpus if s.tag == tag)
        result = texgen.generate_textures(m, target, corpus, refs)
        check("smart patch is byte-identical with no edits",
              result["heights"] == orig["heights"]
              and result["lightmap"] == orig["lightmap"]
              and result["blends"] == orig["blends"])

        # 4. Edited tiles only touch their own cells (+ feather bands)
        m2 = MapModel()
        m2.load_file(map_path)
        edits = [(10, 10), (10, 11), (20, 5)]
        for r, c in edits:
            old = m2.get_terrain(r, c)
            m2.set_terrain(r, c, 4 if old != 4 else 1)   # flip to a new type
        t0 = time.time()
        result2 = texgen.generate_textures(m2, target, corpus, refs)
        dt = time.time() - t0

        lb = np.frombuffer(result2["lightmap"], dtype=np.uint8,
                           offset=128).reshape(1024, 1024, 8)
        ob = np.frombuffer(orig["lightmap"], dtype=np.uint8,
                           offset=128).reshape(1024, 1024, 8)
        diff_blocks = np.argwhere((lb != ob).any(axis=2))
        in_cells = all(
            any(r * 32 <= y < (r + 1) * 32 and c * 32 <= x < (c + 1) * 32
                for r, c in edits)
            for y, x in diff_blocks
        )
        check("edits stay inside their lightmap cells", in_cells,
              f"{len(diff_blocks)} blocks changed, {dt:.2f}s")

        hb = np.frombuffer(result2["heights"], dtype="<u2",
                           offset=128).reshape(512, 512)
        oh = np.frombuffer(orig["heights"], dtype="<u2",
                           offset=128).reshape(512, 512)
        diff_px = np.argwhere(hb != oh)
        if len(diff_px):
            # All diffs within edited cells grown by the 2px feather band
            ok = True
            for y, x in diff_px:
                near = any(
                    r * 16 - 2 <= y < (r + 1) * 16 + 2
                    and c * 16 - 2 <= x < (c + 1) * 16 + 2
                    for r, c in edits)
                if not near:
                    ok = False
                    break
            check("height edits stay inside cells + feather", ok,
                  f"{len(diff_px)} px changed")
        else:
            check("height edits present", False, "no pixels changed at all")

    # 4b. Scenario schema + XML round-trip + STARTLOC codec + gates
    print("\n── Scenario rules ──")
    import scenario_io
    import scenario_schema as SS

    check("schema has 35 variators, indices 0-34",
          len(SS.VARIATORS) == 35
          and [v.index for v in SS.VARIATORS] == list(range(35)))
    check("every variator has a category in CATEGORIES",
          all(v.category in SS.CATEGORIES for v in SS.VARIATORS))
    # STARTLOC codec is an exact inverse and matches the verified probe
    check("startloc codec round-trips + matches probe 3089=(12,17)",
          SS.encode_startloc(12, 17) == 3089
          and SS.decode_startloc(3089) == (12, 17)
          and all(SS.decode_startloc(SS.encode_startloc(r, c)) == (r, c)
                  for r in (0, 5, 31) for c in (0, 17, 31)))
    # XML round-trip against a pristine copy (never touches the real Pak9)
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name in ("dlcscenariodata5.xml",):
            shutil.copy2(PAK9_ORIG / name, tmp / name)
        before = (tmp / "dlcscenariodata5.xml").read_bytes()
        want = {"DISPLAYCARD": 1539, "STARTYEAR": 1800, "STARTSIZE": 2,
                "STARTLOCME": SS.encode_startloc(12, 17)}
        scenario_io.write_variators(tmp, "The_UK", want)
        check("scenario XML write+verify round-trips",
              scenario_io.verify_written(tmp, "The_UK", want),
              str(scenario_io.read_variators(tmp, "The_UK")))
        check("write leaves OTHER entries untouched",
              scenario_io.read_variators(tmp, "The_World") == {"DISPLAYCARD": 1552})
        # File stays ISO-8859-1 / CRLF (no accidental re-encode of the rest)
        after = (tmp / "dlcscenariodata5.xml").read_bytes()
        check("write preserves CRLF line endings", b"\r\n" in after)
        # UK is the last entry: everything before its tag must be byte-identical,
        # and the UK region itself must have changed.
        check("bytes before the UK entry are untouched",
              before.split(b"SCENARIO_THE_UK")[0]
              == after.split(b"SCENARIO_THE_UK")[0])
        check("the UK entry region changed",
              before.split(b"SCENARIO_THE_UK")[1]
              != after.split(b"SCENARIO_THE_UK")[1])
    # Gate validation fires correctly
    g1 = SS.validate({"STARTSIZE": 2}, fixed_map=True)
    check("gate: STARTSIZE without STARTYEAR fails on fixed map",
          any(s == "fail" for s, _ in g1))
    g2 = SS.validate({"STARTSIZE": 2, "STARTYEAR": 1800}, fixed_map=True)
    check("gate: STARTSIZE with STARTYEAR is clean",
          not any(s == "fail" for s, _ in g2))
    g3 = SS.validate({"STARTSIZE": 1}, fixed_map=False)
    check("gate: random-map STARTSIZE needs no STARTYEAR",
          not any(s == "fail" for s, _ in g3))
    g4 = SS.validate({"MUSTWINBY": 2, "NOSPACERACE": 1}, fixed_map=True)
    check("gate: MUSTWINBY=Space + NOSPACERACE conflict fails",
          any(s == "fail" for s, _ in g4))

    # 5. Full synth on a from-scratch map
    print("\n── Full synthesis (no originals) ──")
    from newmap import random_map

    m3 = MapModel()
    m3.data[:] = random_map(seed=7)
    t0 = time.time()
    result3 = texgen.generate_textures(m3, None, [], refs)
    dt = time.time() - t0
    check("full synth sizes",
          len(result3["heights"]) == 524416
          and len(result3["lightmap"]) == 8388736
          and len(result3["blends"]) == 2097280,
          f"{dt:.1f}s")

    # Similarity of full synth vs an original (sanity, not a gate)
    m4 = MapModel()
    m4.load_file(PAK9_ORIG / "the_world.map")
    r4 = texgen.generate_textures(m4, None, [], refs)
    ho = np.frombuffer(
        (PAK9_ORIG / "mapthe_world_heights.dds").read_bytes(),
        dtype="<u2", offset=128).astype(np.int64)
    hg = np.frombuffer(r4["heights"], dtype="<u2", offset=128).astype(np.int64)
    sim = 1.0 - np.abs(hg - ho).mean() / 65535
    print(f"  [info] full-synth heights similarity vs original: {sim:.1%}")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
