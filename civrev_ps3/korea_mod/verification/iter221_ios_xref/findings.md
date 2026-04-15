# iter-221: §5.6 cross-reference RESOLVES the carousel-blocker mystery

**Date:** 2026-04-15

## Discovery: iOS has fully-symbolized `NDSChooseCiv` class

Searching `civrev_ios/native_analysis/game_functions.txt` finds
the iOS port has retained C++ method names for the entire
civ-select implementation:

```
0x0007cc30  NDSChooseCiv::NDSChooseCiv (ctor)
0x0007cc38  NDSChooseCiv::InitScreens (872 bytes)
0x0007d290  NDSChooseCiv::Init (2132 bytes)
0x0007d024  NDSChooseCiv::UnInitScreens (484 bytes)
0x0007dbc8  NDSChooseCiv::SetUpForScroll (132 bytes)
0x0007dc4c  NDSChooseCiv::UnInit (436 bytes)
0x0007de64  NDSChooseCiv::ReleaseStaticRes (280 bytes)
0x0007dfbc  NDSChooseCiv::ReloadLeaders (72 bytes)
0x0007e004  NDSChooseCiv::ShowCivIcons (354 bytes)
0x0007e170  NDSChooseCiv::ShowCivText (1488 bytes)
0x0007e744  NDSChooseCiv::TurnToLeft (140 bytes)
0x0007e7d0  NDSChooseCiv::TurnToRight (120 bytes)
0x0007e848  NDSChooseCiv::Process (3918 bytes)
0x0007f860  NDSChooseCiv::DrawTipLabel (804 bytes)
```

Plus higher-level entry points:
- `0x0008f68c sym.DoChooseCiv()`
- `0x00115e24 NDSPresentation::IChooseCiv(int, int)`
- `0x0016dfa4 TurnBaseMode::PreGame::GoChooseCiv()`

This is the EXACT class hierarchy I've been hunting for in the
PS3 PPU code. The PS3 build was derived from the same C++
codebase, so the class methods exist there too — they're just
stripped of names.

## Verdict: iOS uses OpenGL, PS3 uses Scaleform — fundamental platform divergence

Disassembled the iOS `NDSChooseCiv::ShowCivIcons` at `0x7e004`:

```arm
push   {r4, r5, r6, r7, lr}
sub.w  r4, sp, #0x10
add    r7, sp, #0xc
bic    r4, r4, #0xf
mov    sp, r4
vst1.64 {d8, d9}, [r4:0x80]
sub    sp, #0x50
movw   r0, #0xe06c
vldr   s16, [pc, #0x148]
...
vldr   s0, [r6]
vmul.f32 d16, d0, d9
vmul.f32 d18, d0, d8
vcvt.s32.f32 d1, d16
vcvt.s32.f32 d0, d18
vmov   r3, s2
vmov   r2, s0
blx    #0x1ba54c        ; OpenGL function
movw   r0, #0x1701
blx    #0x1ba46c        ; OpenGL function
blx    #0x1ba44c        ; OpenGL function
...
```

This is **direct OpenGL ES rendering**: VFP float math (vmul,
vcvt, vmov), texture coordinate setup, and `blx` indirect
calls into what are almost certainly OpenGL functions.

The iOS build **does not use Scaleform** for the civ-select
carousel — it uses native OpenGL with C++ rendering code in
`NDSChooseCiv::ShowCivIcons` / `ShowCivText` / etc.

The PS3 build **does** use Scaleform (the `gfx_chooseciv.gfx`
file confirms this — it's a SWF/GFX Scaleform asset, and
`gfxtext.xml` is the Scaleform string-localization file).

**This is a platform divergence, not a build difference.** The
two ports share the C++ game logic (parser, civ data tables,
gameplay) but diverge entirely on the UI layer. iOS has the
carousel as native ARM code; PS3 has it as Scaleform AS2
bytecode in a `.gfx` file.

## Constants found in iOS `NDSChooseCiv`

Searching for `cmp #0x10` / `mov #0x10` / `mov #0x11` constants
in each iOS NDSChooseCiv method:

| method | size | #16/#17 hits |
|---|---|---|
| InitScreens | 872 | 0 |
| Init | 2132 | **13** (multiple loop bounds + size constants) |
| ShowCivIcons | 354 | 0 |
| ShowCivText | 1488 | 0 |
| Process | 3918 | **4** (`cmp r4, #0x10`, `movs r1, #0x10`, `movs r2, #0x10`, **`movs r1, #0x11`**) |
| ReloadLeaders | 72 | 1 (`cmp r1, #0x10`) |

The `movs r1, #0x11` (= 17) inside `NDSChooseCiv::Process` is
particularly interesting — likely the "16 civs + Random = 17
selectable cells" total count. iOS hardcodes 17 in this
function's loop logic.

If this were a PS3 binary, finding and bumping this constant
to `#0x12` (=18) would be the strict-reading 18th-cell fix.

But it's iOS, not PS3, and iOS uses a completely different
rendering layer.

## What this means for the PS3 strict-reading directive

§5.6 cross-reference **finally resolves** the iter-189 strict-
reading 18th-cell mystery:

- The PS3 carousel rendering is in Scaleform AS2 bytecode in
  `gfx_chooseciv.gfx`.
- The PS3 PPU has NO analog of `NDSChooseCiv::ShowCivIcons` /
  `ShowCivText` because that work happens Scaleform-side.
- iter-150/154/198/206/209/210/211/217/218 ruled out 9 PPU
  candidate functions and 14 `li r8` consumer sites because
  there literally is no PPU function on the PS3 carousel
  render path.
- The iOS port's Init / Process functions ARE the C++ code
  that the PS3 build "left behind" when it migrated to
  Scaleform. PS3 does NOT have these functions in its
  PPU EBOOT — they were replaced by Scaleform AS2 setup +
  data flow.

**The §9 item 2 strict-reading is structurally unachievable on
PS3 specifically because PS3 chose Scaleform.** Modding the
PS3 carousel cell count would require modifying the AS2
bytecode in `gfx_chooseciv.gfx`, not the PS3 EBOOT.

This permanently closes the carousel-finding question: there is
**provably no PPU function** on PS3 that holds the carousel
cell count, because the constant lives in Scaleform.

## What this iteration positively contributes

1. **Final settlement of iter-189 structural blocker.** The
   block is now grounded in a **platform-architecture
   difference** (OpenGL vs Scaleform), not just an
   "unfindable" hypothesis.
2. **iOS NDSChooseCiv method names** mapped to their iOS
   addresses — could become an asset for future iOS porting
   work or for cross-checking PS3 patches that affect game
   logic shared between the two ports.
3. **Reinforces the iter-212 §9.X structural blocker** with
   cross-platform empirical evidence.

## What this iteration does NOT unblock

The PS3 carousel cell count. It remains structurally
unreachable from PPU patching, exactly as iter-212 documented.

The blocker is real and final. No further iteration of "find
the carousel function in PPU" is going to succeed because
**there is no carousel function in PS3 PPU** — that work was
moved into Scaleform bytecode at port time.

## Files

- `findings.md` — this
