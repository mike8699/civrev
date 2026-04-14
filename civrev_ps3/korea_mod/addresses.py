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

# Internal civ tag strings (e.g. "CIV_Rome", "CIV_Egypt"). Matches the 16-entry
# CcCiv enum order derived from leaderheads.xml.
KOREA_MOD_CIV_TAG_ARRAY           = 0x0194b35c  # 16 × 4 bytes

# Internal leader tag strings ("LDR_rome", "LDR_egypt", ..., "LDR_england").
# 16 × 4 bytes, adjacent to CIV_TAG_ARRAY (which starts at +0x44 past this
# array's end, with one 4-byte filler/vtable word at 0x194b358).
KOREA_MOD_LDR_TAG_ARRAY           = 0x0194b318  # 16 × 4 bytes

# English-facing leader names as displayed in menus:
# "Caesar", "Cleopatra", "Alexander", "Isabella", "Bismarck", "Catherine",
# "Mao", "Lincoln", "Tokugawa", "Napoleon", "Gandhi", "Saladin",
# "Montezuma", "Shaka", "Genghis Khan", "Elizabeth".
KOREA_MOD_LEADER_NAME_PTR_ARRAY   = 0x0194b434  # 16 × 4 bytes

# Flat civ-adjective pointer table ("Roman", "Egyptian", ..., "English").
# Stride-4, 16 entries. This is the clean form used by the name-resolver.
KOREA_MOD_CIV_ADJECTIVE_PTR_ARRAY = 0x0195fe28  # 16 × 4 bytes

# Interleaved adjective+plural pair table ("Roman","Romans","Egyptian",
# "Egyptians", ...). Irregular stride — some civs omit the plural because the
# singular and plural forms are identical (Chinese, Japanese, French, English).
# Listed here for completeness; verification should treat it as a second
# table to patch, not just a cosmetic duplicate.
KOREA_MOD_CIV_ADJ_PAIR_ARRAY      = 0x0194b3c8  # variable stride, walk by ptrs

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
