"""
Confirmed addresses for the Korea civ mod (PS3 CivRev BLUS-30130, EBOOT v1.30).

Every constant here is either:
  - verified by static bytes in EBOOT_v130_clean.ELF and cross-checked against
    leaderheads.xml (16 civs in a known order), OR
  - runtime-verified against RPCS3 via GDB stub / process_vm_readv.

Unverified placeholders use `None` so code that tries to use them fails loudly.

The PS3 EBOOT is 64-bit PPC but uses 32-bit addressing — every pointer we care
about is a 4-byte big-endian word. p_offset == p_vaddr for PT_LOAD segment 0,
so file offsets in EBOOT_v130_clean.ELF equal virtual addresses directly.
"""

# ---------------------------------------------------------------------------
# §5.2 civ data: the PS3 EBOOT stores civ fields as PARALLEL POINTER ARRAYS,
# not as a single civ-record struct. Each array is 16 × 4 bytes = 64 bytes
# and indexed by CcCiv::Civs enum value (0 = Caesar/Rome .. 15 = Elizabeth/England).
#
# The PRD §6.2 mental model of "one civ-record struct per civ with fields at
# fixed offsets" does NOT match this binary. Extending Korea requires finding
# and extending EVERY parallel array, not relocating a single struct table.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CRITICAL iter-4 finding: of the five parallel pointer tables located in
# PS3 rodata, ONLY the flat civ-adjective table at 0x0195fe28 is actually
# live runtime data. The other four are dead rodata — they appear as static
# 16 × 4 byte pointer blocks but NO code reference exists anywhere in the
# binary (verified by exhaustive 32-bit and 64-bit BE scan across the full
# 26 MB file). They are most likely C++ static-init constants that the
# compiler emitted into .rodata but that the real runtime code path never
# consumes (the runtime leader data comes from leaderheads.xml parsing,
# which populates a separate heap-allocated table).
#
# Concretely:
#   - 0x0195fe28 (ADJ_FLAT)     → LIVE. 9 call sites load it TOC-relative
#                                 via `lwz rN, offset(r2)` at offsets
#                                 -0x1f34 and -0x9d8 from r2=0x0193a288.
#   - 0x0194b318 (LDR_TAG)      → DEAD rodata, 0 refs.
#   - 0x0194b35c (CIV_TAG)      → DEAD rodata, 0 refs.
#   - 0x0194b3c8 (ADJ_PAIR)     → DEAD rodata, 0 refs.
#   - 0x0194b434 (LEADER_NAMES) → DEAD rodata, 0 refs.
#
# Implication for §6.2: only ADJ_FLAT needs extension to 17 entries. The
# other four tables can be left untouched (extending them is harmless but
# pointless). The leader-name display strings for Sejong come from the
# leaderheads.xml overlay (already shipping in xml_overlays/), not from a
# rodata pointer table.
# ---------------------------------------------------------------------------

KOREA_MOD_CIV_TAG_ARRAY           = 0x0194b35c  # DEAD rodata (kept for docs)
KOREA_MOD_LDR_TAG_ARRAY           = 0x0194b318  # DEAD rodata (kept for docs)
KOREA_MOD_LEADER_NAME_PTR_ARRAY   = 0x0194b434  # DEAD rodata (kept for docs)
KOREA_MOD_CIV_ADJ_PAIR_ARRAY      = 0x0194b3c8  # DEAD rodata (kept for docs)

# The one live table — every Korea civ-adjective lookup hits this.
KOREA_MOD_CIV_ADJECTIVE_PTR_ARRAY = 0x0195fe28  # LIVE, 9 call sites

# TOC entries that hold 0x0195fe28 as a 32-bit pointer. Both are
# signed-16-bit offsets from r2 = 0x0193a288.
KOREA_MOD_TOC_ADJ_FLAT_ENTRIES    = (0x01938354, 0x019398b0)  # r2-0x1f34, r2-0x9d8
KOREA_MOD_TOC_BASE                = 0x0193a288  # PPC64 r2 at function entry

# PS3 call sites that load ADJ_FLAT via lwz rN, X(r2). Each is a candidate
# consumer of the adjective table; any index ≥ 16 passed to one of these
# sites will read past the end of the current 16-entry table.
KOREA_MOD_ADJ_FLAT_CALLSITES = (
    0x0013cbf8,  # lwz r9, -0x1f34(r2)
    0x0017e9b0,  # lwz r9, -0x9d8(r2)
    0x0097d948,  # lwz r28, -0x1f34(r2)
    0x0097dad0,  # lwz r9, -0x1f34(r2)
    0x0097db28,  # lwz r28, -0x1f34(r2)
    0x0097e0ac,  # lwz r29, -0x1f34(r2)
    0x009f81d4,  # lwz r4, -0x9d8(r2)
    0x009f9600,  # lwz r4, -0x9d8(r2)
    0x00ff09e4,  # lwz r28, -0x9d8(r2)
)

# Placeholders pending investigation ---------------------------------------

# §5.1 — _NCIV references. The binary has no single "NCIV" constant; `16`
# (0x10) appears in dozens of loop bounds. The authoritative list is produced
# by scanning every `cmpwi rN, 0x10` / `li rN, 0x10` instruction whose dest
# register is used as an index into one of the four arrays above.
KOREA_MOD_NCIV_ADDR               = None        # §5.1 follow-up

# §5.2 — per-player nationality array. Players hold a nationality field
# somewhere in the per-player struct; the binary stores players in an array
# of fixed stride. Needed by M6 oracle 1.
KOREA_MOD_PLAYER_NATIONALITY_ARR  = None
KOREA_MOD_PLAYER_SLOT_STRIDE      = None
KOREA_MOD_CIV_CITY_COUNT_OFFSET   = None

# §5.4 — game state counters (turn number).
KOREA_MOD_TURN_COUNTER_ADDR       = None

# ---------------------------------------------------------------------------
# Expected values for verification oracles (M5)
# ---------------------------------------------------------------------------

EXPECTED_LEADER_NAMES = [
    "Caesar", "Cleopatra", "Alexander", "Isabella", "Bismarck",
    "Catherine", "Mao", "Lincoln", "Tokugawa", "Napoleon",
    "Gandhi", "Saladin", "Montezuma", "Shaka", "Genghis Khan",
    "Elizabeth",
    # Post-patch index 16:
    "Sejong",
]

# Note: leaderheads.xml has "Shaka Zulu" for nationality 13 but the EBOOT
# leader-name pointer table holds "Shaka" only. leaderheads.xml's Text
# attribute is a separate display string for the leaderhead pedia entry, not
# the in-game leader-name table.

EXPECTED_CIV_TAGS = [
    "CIV_Rome", "CIV_Egypt", "CIV_Greece", "CIV_Spain", "CIV_Germany",
    "CIV_Russia", "CIV_China", "CIV_America", "CIV_Japan", "CIV_France",
    "CIV_India", "CIV_Arabia", "CIV_Aztec", "CIV_Africa", "CIV_Mongolia",
    "CIV_England",
    "CIV_Korea",
]

EXPECTED_CIV_ADJECTIVES = [
    "Roman", "Egyptian", "Greek", "Spanish", "German", "Russian", "Chinese",
    "American", "Japanese", "French", "Indian", "Arab", "Aztec", "African",
    "Mongolian", "English",
    "Korean",
]
