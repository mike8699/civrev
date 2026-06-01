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

WARNING (path-b iter-2, 2026-05-31): every address in this file is in
EBOOT_v130_clean.ELF space (file_off==vaddr for seg0), verified because
eboot_patches.py matches these offsets at apply time. The existing Ghidra
project ghidra/civrev.rep is a DIFFERENT binary — the same rodata string
sits at a ~0x3c8/0x103c8-biased vaddr there and code at these callsites does
not match. Do NOT use the existing Ghidra project for addresses that feed
the patcher; re-import the current EBOOT_v130_clean.ELF into a fresh project
first. See korea_mod/docs/path-b-plan.md "RE log — iter-2".
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

# iter-14: the name-file init dispatcher. FUN_00a21ce8 calls
# FUN_00a216d4 eight times — once per name file (CityNames, UnitNames,
# TechNames, FamousNames, WondernamesMale, WondernamesFemale,
# RulerNames, CivNames). Each call passes an entry-count in r5. Only
# RulerNames and CivNames use count=0x11 (17) — everything else uses
# a different count depending on how many entries that file has.
#
# Patched from 0x11 → 0x12 in eboot_patches.py so the parser will
# accept an 18-entry input file (harmless no-op on the v0.9 path since
# the stock files still have exactly 17 rows — the parser bails at
# EOF regardless of the count ceiling).
KOREA_MOD_INIT_GENDERED_NAMES_DISPATCH = 0x00a21ce8  # (iter-14 stale name)
KOREA_MOD_INIT_GENDERED_NAMES_WORKER   = 0x00a216d4  # (iter-14 stale name)
KOREA_MOD_RULERNAMES_COUNT_LI_R5_SITE  = 0x00a2ee38  # li r5, 0x11
KOREA_MOD_CIVNAMES_COUNT_LI_R5_SITE    = 0x00a2ee7c  # li r5, 0x11

# iter-17..22 renamed these to "real_parser_dispatcher/worker":
KOREA_MOD_PARSER_DISPATCHER = 0x00a2ec54  # FUN_00a2ec54 (contains the 2 li r5 sites)
KOREA_MOD_PARSER_WORKER     = 0x00a2e640  # FUN_00a2e640 (called 8× by dispatcher)

# iter-202 CRITICAL correction: the dispatcher at 0xa2ec54 uses a
# DIFFERENT TOC base than the rest of the binary. Its function
# descriptor at 0x18f0380..0x18f038c holds {entry=0xa2ec54, toc=0x194a1f8}.
# All TOC-relative loads inside the dispatcher and worker reference
# 0x194a1f8, NOT 0x193a288. iter-197's TOC slot mapping was based on
# the wrong r2 and resolved half the "buffer holder" slots to rodata
# string literals. The correct slots are:
#   r2+0x1400 = 0x194b5f8 -> 0x1ac939c  (name file 1)
#   r2+0x1404 = 0x194b5fc -> 0x1ac93a0  (name file 2)
#   r2+0x1408 = 0x194b600 -> 0x1ac93a4
#   r2+0x140c = 0x194b604 -> 0x1ac93a8
#   r2+0x1410 = 0x194b608 -> 0x1ac93ac
#   r2+0x1414 = 0x194b60c -> 0x1ac93b0
#   r2+0x1418 = 0x194b610 -> 0x1ac93b4  (rulers name file)
#   r2+0x141c = 0x194b614 -> 0x1ac93b8  (civs name file)
# All 8 destinations are in writable .bss — the parser's
# `*param_2 = new_buf_ptr` write is valid.
#
# The dispatcher is called INDIRECTLY via
#   ld r11, <desc>
#   ld r0, 0(r11)   ; entry = 0xa2ec54
#   ld r2, 8(r11)   ; toc = 0x194a1f8  <<< NEW r2!
#   mtctr r0
#   bctrl
# which is why a direct-bl caller scan finds 0 callers.
KOREA_MOD_PARSER_DISPATCHER_TOC_BASE = 0x0194a1f8  # r2 when dispatcher runs
KOREA_MOD_PARSER_DISPATCHER_DESCRIPTOR = 0x018f0380  # {entry, toc} words

# .bss buffer-pointer holders for each name file (per-iteration
# writes happen here at parser_worker line 0xa2e708: stw r0, 0(r25))
KOREA_MOD_CIVS_BUFFER_HOLDER    = 0x01ac93b8  # civs, *r25 for civs bl
KOREA_MOD_RULERS_BUFFER_HOLDER  = 0x01ac93b4  # rulers

# FUN_00029f18 — the std::vector::insert/reserve variant whose
# instruction at 0x0002a12c is the fault-address target whenever the
# broken-18-entry civnames path is active (see
# verification/M2_iter25_analysis.md). Kept here so future debugging
# sessions have a named anchor.
KOREA_MOD_STD_VECTOR_INSERT_VARIANT    = 0x00029f18  # FUN_00029f18
KOREA_MOD_FAULT_TARGET_INSIDE_VECTOR   = 0x0002a12c  # stb target of corrupted r11
KOREA_MOD_FAULTING_INSTRUCTION_SITE    = 0x00c26a98  # stb r0, 0(r11)

# Placeholders pending investigation ---------------------------------------

# §5.1 — _NCIV references. RESOLVED at iter-213 (2026-04-15).
# The binary has no single "NCIV" constant; "16" (0x10) appears at
# many inline `cmpwi rN, 0x10` / `li rN, 0x10` sites but NONE of them
# are on the civ-select carousel render path (verified by iter-150,
# iter-154, iter-198, iter-206 ×2, iter-209 b . diagnostics, plus
# iter-198/210/211 selective + collective `li r8, 0x10` patch tests).
# The carousel cell count is hardcoded SCALEFORM-side in
# gfx_chooseciv.gfx, not in the PPU EBOOT. See
# `korea_mod/docs/ncv-references.md` for the full resolution write-up.
KOREA_MOD_NCIV_ADDR               = None        # §5.1 RESOLVED — no PPU constant

# §5.2 — per-player nationality array. Players hold a nationality field
# somewhere in the per-player struct; the binary stores players in an array
# of fixed stride. Needed by M6 oracle 1.
KOREA_MOD_PLAYER_NATIONALITY_ARR  = None
KOREA_MOD_PLAYER_SLOT_STRIDE      = None
KOREA_MOD_CIV_CITY_COUNT_OFFSET   = None

# §5.4 — game state counters (turn number).
KOREA_MOD_TURN_COUNTER_ADDR       = None

# ---------------------------------------------------------------------------
# path-b iter-3 (2026-05-31): rodata string anchors located in clean-ELF
# space (file_off==vaddr). NOTE: these are all in the Scaleform/UI/entity
# string pool (~0x169xxxx) and lead to the UI/binding layer, NOT the civ
# gameplay/effect code (which is enum-driven with few string anchors). Kept
# for reference; the effect-layer RE must anchor on ADJ_FLAT (0x195fe28) +
# its call sites, or on runtime memory diffing. None of these have a
# lis/addi load, a 4-byte pointer, or a Ghidra ref (all loaded indirectly).
# ---------------------------------------------------------------------------
KOREA_MOD_STR_THE_SELECTED_OPTION = 0x0169cacd  # SWF var path (Flash binding)
KOREA_MOD_STR_ONACCEPT            = 0x01694708  # fscommand name
KOREA_MOD_STR_ONPRESSY            = 0x01693e50  # fscommand name (pedia/bonus btn)
KOREA_MOD_STR_CIVBONUSTEXT        = 0x016dd35e  # @CIVBONUSTEXT template token
KOREA_MOD_STR_LBTEXT              = 0x016928a9  # @LBTEXT template token
KOREA_MOD_STR_CC_CIV_FLAG_ENTITY  = 0x01692728  # C++ entity class name
KOREA_MOD_STR_CHOOSECIV           = 0x0169f438  # UI screen name

# Fresh clean-ELF Ghidra project (correct addressing, unlike ghidra/civrev.rep
# which is a different binary). Built by importing EBOOT_v130_clean.ELF; lives
# at ghidra_clean/civrev_clean (gitignored). Default analysis under-covers it
# (entry is a PPC64 descriptor in .data) — rebuild with a larger heap + seed
# disassembly from known code addresses. See path-b-plan.md "RE log — iter-3".

# ---------------------------------------------------------------------------
# path-b iter-6 (2026-05-31): RUNTIME game-state anchors (found via
# test_player_dump.py — boot in-game, scan .bss for heap pointers). The static
# effect-grant hunt had no anchor; runtime found the game objects directly.
# .bss globals are fixed; the heap pointers they hold vary per run.
# ---------------------------------------------------------------------------
KOREA_MOD_GAME_OBJ_BSS_HOLDER   = 0x01ac1678  # .bss -> heap game session object
KOREA_MOD_GAME_OBJ_VTABLE       = 0x018a2738  # vtable of the game session obj
#   vtable methods (descriptors): 0x9a6018, 0x9a7228, 0x9a7350, ... ; these use
#   TOC 0x194a1f8 (parser-module TOC), NOT the main 0x193a288 — set r2 to
#   0x194a1f8 when decompiling them in civrev_clean.
KOREA_MOD_OBJ_B_BSS_HOLDERS     = (0x01ad8114, 0x01add514)  # vtable 0x0188ac38
# iter-9 (2026-05-31): 3-way noise-subtracted runtime diff (China-A/China-B/
# Rome via diff3_player_dumps.py) localized the player/civ game-state region.
# Candidate per-player/per-civ objects (vtable 0x0188ac38), .bss holders spaced
# exactly 0x5400 apart, each holding the human civ index (China=6, Rome=0) +
# civ team color (China RGB 0x069644, Rome 0x05aaa3) + leader name:
KOREA_MOD_PLAYER_CIV_OBJ_BSS_HOLDERS = (
    0x01ad8114, 0x01add514, 0x01ae2914, 0x01ae7d14, 0x01aed114,
)
KOREA_MOD_PLAYER_CIV_OBJ_VTABLE      = 0x0188ac38
# iter-10: find the starting-tech BITFIELD within these objects (bits differ
# China=Writing vs Rome), then trace/Z0-breakpoint its writer = the civ-keyed
# effect-grant. See path-b-plan.md "RE log — iter-9".
#
# iter-11 BREAKTHROUGH (2026-06-01): the cross-port scout (iOS symbolicated
# build = Rosetta Stone) revealed the effect layer fully. The authoritative
# state is PARALLEL GLOBAL ARRAYS (not heap structs — that's why runtime object
# scans only hit UI/Cc* caches). iOS reference (civrev_ios decompiled, with
# symbols; SAME Firaxis CcCiv engine as PS3):
#   AddTech(player,tech,src,type,flags)   iOS vaddr 0x338b0  (flags 6 = free)
#   InitCustomGame  (start-tech grant)    iOS vaddr 0x3130c  (reads ucStartTechs)
#   InitCGame       (random-game init)    iOS vaddr 0x2e49c
#   qBeginTurn      (era-bonus AddTech)   iOS vaddr 0x3c9a0
#   HasLBonus(id,player,era)              iOS vaddr 0x72574  (_lbonus[civ*0x10+era*4])
#   getRealUnitType (civ->unique unit)    iOS _global.c:4062
# iOS data tables: _lbonus 0x1fc554 (int[NUM_CIV][4], stride 0x10);
#   ucStartTechs 0x1fc488 (byte[civ*0x2f]); TeamMap 0x1fc0ec (player->civ);
#   Techs 0x1fc29c (bitmask 1<<player, 0x30 slots, 0x2f sentinel).
# PS3 value-match signatures (find via ghidra_clean): HasLBonus = era clamp
#   [0,3] + civ*0x10+era*4 scan (~200B); qBeginTurn = nested if(NTech>4/0xd/0x17)
#   SetEra; AddTech = Techs[t]|=1<<player + flag const 6; tech bound 0x30,
#   sentinel 0x2f; Writing=tech 8, Currency=0xf, Monarchy=0x13.
# PS3 addresses TO BE FILLED as found:
KOREA_MOD_PS3_ADDTECH                = None
KOREA_MOD_PS3_HASLBONUS              = None
KOREA_MOD_PS3_LBONUS_TABLE           = None   # int[NUM_CIV][4], stride 0x10
KOREA_MOD_PS3_UCSTARTTECHS_TABLE     = None   # byte[civ*0x2f]
KOREA_MOD_PS3_INITCUSTOMGAME         = None
KOREA_MOD_PS3_QBEGINTURN             = None
KOREA_MOD_PS3_TEAMMAP                = None   # player->civ index
# See path-b-plan.md "## BREAKTHROUGH (iter-11)".

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
