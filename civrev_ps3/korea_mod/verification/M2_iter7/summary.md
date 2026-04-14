# M2 iter-7 — string source search + text.ini overlay dead-end

## Experiments this iteration

### 1. Overwrote "Elizabeth\0" in rodata at 0x016a38d0

Added a diagnostic EBOOT patch that replaces `Elizabeth\0` →
`SejongX\0\0\0` at rodata address `0x016a38d0`. Rebuilt, reinstalled,
re-ran `test_korea.py`.

**Result:** civ-select slot 15 still rendered **"Elizabeth / English"**.
Screenshot `slot15_elizabeth.png` confirms unchanged. There are 3
occurrences of the literal `Elizabeth\0` in the EBOOT (0x169dd9c,
0x169e513, 0x16a38d0) — the first two are embedded inside longer
strings (`eng_Elizabeth` asset filename, `GL_Elizabeth` renderer key)
so only 0x016a38d0 is a standalone display-name string, and NONE of
the three is read by the civ-select screen.

Patch reverted.

### 2. Found stringdatabase.gsd and text.ini in Pregame.FPK

Grep of `extracted/Pregame/` surfaced:
- `text.ini` — a source-format string database with sections like
  `[CIVNAMEP]` (civ-adjective list: Roman, Egyptian, ..., English,
  Barbarian).
- `stringdatabase.gsd` — an 816 KB binary file that contains 35
  literal occurrences of `Elizabeth`, 37 of `Mao`, 17 of `Caesar`,
  4 of `English`. This looks like the compiled/binary form of
  text.ini and is the strongest remaining candidate for the real
  civ-select name source.

### 3. text.ini overlay with "Value = Korean" BROKE boot

Added `Value = Korean` to `[CIVNAMEP]` in a copy of text.ini, wired
`pack_korea.sh` to also overlay `.ini` files, rebuilt. Pregame.FPK
repacked cleanly (via fpk.py).

**Result:** RPCS3 timed out after 300s waiting for RSX init. The
game failed to reach even the title screen. Reverted by restoring
`Pregame.FPK.orig` from the iter-3 install backup; stock mod boots
again (verified — see §cursor-normalized result below).

Possible causes (not yet distinguished):
- text.ini is actually parsed at runtime and our edit triggered a
  parser error / out-of-bounds write.
- fpk.py's repack of Pregame.FPK corrupts something at the FPK level
  (even though the same repacker works fine for Common0.FPK).
- Some Pregame.FPK entry depends on byte-exact alignment that
  fpk.py doesn't preserve.

Iter-8 must isolate this — the simplest diagnostic is a
round-trip test: `extracted/Pregame` → `fpk.py repack` → install
UNMODIFIED Pregame, verify boot. If that fails, fpk.py itself is
Pregame-unsafe and we need a different packing strategy.

### 4. Cursor normalization fix (per user feedback)

Per `launch.py:557` (the Russian-select pattern), the civ-select
cursor starts on a random civ. iter-5/iter-6's test_korea.py swept
Right 25 times without normalizing, so the initial cursor position
could be anywhere and the sweep effectively only covered slots
N..N+15 (then clamped at Random).

Iter-7's `test_korea.py` now presses Left 20 times before the sweep
to guarantee arrival at slot 0 (Caesar/Romans). After 20 Lefts the
cursor landed on slot 0: `slot01_cleopatra_normalized.png` shows
Cleopatra selected (after the first Right press) with Caesar visible
to the left of the carousel — confirming normalization reached
the leftmost position.

### 5. With normalization: carousel sweep confirmed 17 slots, clamped at Random

Driving 25 Rights from normalized slot 0:
- slots 0..15 render the 16 real civs (Caesar..Elizabeth)
- slot 16 renders **Random** (question-mark silhouette, "randomly
  choose a civilization") — screenshot `slot16_random.png`
- slots 16..24 (all subsequent Rights) stay on Random — the cursor
  does **not** wrap and does **not** advance. Random is a hard
  right-clamp.

## What this iteration proves

1. The civ-select screen's display name source is **not** the
   rodata strings at 0x016a38d0 and is **not** the leaderheads.xml
   Text attribute.
2. `stringdatabase.gsd` in Pregame.FPK is the strongest remaining
   candidate — it contains every civ/leader name as a literal.
3. text.ini is risky to overlay via fpk.py repack — either the file
   is load-critical or the Pregame repack path is corrupt.
4. The civ-select carousel is exactly 17 slots: 16 civs + Random at
   slot 16, Random is a hard clamp.

## Next iteration should

1. **Round-trip test Pregame.FPK** — repack the UNMODIFIED
   `extracted/Pregame/` via `fpk.py` and install. If boot fails,
   fpk.py is Pregame-unsafe and we need to either (a) extend fpk.py
   to preserve alignment, or (b) use a byte-level patcher on the
   stock Pregame.FPK that rewrites specific offsets without
   re-emitting the whole archive.
2. **Byte-patch stringdatabase.gsd directly** — find one of the
   35 `Elizabeth` occurrences and overwrite it with `SejongX\0\0`
   in place, without touching any other byte. If this changes the
   civ-select display, we have the right lever. If it doesn't, a
   yet-undiscovered source is driving the names.
3. **Research stringdatabase.gsd format** — it's 816 KB with a
   32-byte header and regular structure. Likely indexed by hash or
   string-id. A Python parser is a plausible iter-8 deliverable.
