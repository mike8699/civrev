# §5.2 Civ record layout — PS3 EBOOT (v1.30)

## Headline finding: there is NO civ-record struct

The PRD's mental model ("single civ table, one struct per civ, stride S,
leader-name field at offset O") does **not** match the PS3 binary. The game
stores civ data as a set of **parallel pointer arrays**, each 16 × 4 bytes,
indexed by the `CcCiv::Civs` enum value (0..15).

This changes the §6.2 implementation strategy materially:

- There is no single "civ table" to extend or relocate — the equivalent work
  is "find every parallel array and extend it to 17 entries".
- Each array sits in read-only `.rodata` in the text segment; there is no
  trailing padding for an in-place append of a 17th entry. Any 17th entry has
  to live somewhere else (see strategy below).
- Every machine-code site that loads one of these arrays uses a LIS/ADDI
  pair against the array base. Relocating a single array invalidates every
  such site. The patch count scales with the number of arrays × the number
  of call sites per array.

## Confirmed tables (all offsets = file offset = vaddr in seg0)

| Table                                   | Base        | Stride | Entries | Status    |
|-----------------------------------------|-------------|--------|---------|-----------|
| Leader display names                    | `0x0194b434`| 4      | 16      | confirmed |
| Civ internal tags (`CIV_Rome`, ...)     | `0x0194b35c`| 4      | 16      | confirmed |
| Civ adjective (flat, one entry per civ) | `0x0195fe28`| 4      | 16      | confirmed |
| Civ adjective+plural pair (interleaved) | `0x0194b3c8`| varies | ~26     | confirmed |
| Leader internal tags (`LDR_rome`, ...)  | `0x0194b318`| 4      | 16      | confirmed |

The leader-internal-tag array is confirmed end-to-end at `0x0194b318` ..
`0x0194b354` (16 × 4 bytes). A 4-byte filler word at `0x0194b358`
(pointer-shaped, points into the text segment at `0xa2b7c0` — likely a
vtable or initializer) separates it from the adjacent `CIV_*` internal
tag array at `0x0194b35c`.

Verification dump of the confirmed tables — see the appendix at the bottom of
this file for the raw pointer→string mapping.

## Order of civs (authoritative)

All of the above arrays are indexed by the same enum. The observed order
is identical across arrays and matches `leaderheads.xml` exactly:

```
 0  Rome        Caesar
 1  Egypt       Cleopatra
 2  Greece      Alexander
 3  Spain       Isabella
 4  Germany     Bismarck
 5  Russia      Catherine
 6  China       Mao
 7  America     Lincoln
 8  Japan       Tokugawa
 9  France      Napoleon
10  India       Gandhi
11  Arabia      Saladin
12  Aztec       Montezuma
13  Africa      Shaka       (leaderheads.xml calls him "Shaka Zulu";
                             the leader-name array holds just "Shaka")
14  Mongolia    Genghis Khan
15  England     Elizabeth
```

## Implementation strategy for Korea (revised §6.2)

Because none of the arrays has trailing padding we can re-use, the only
workable approach is **relocate every array**:

1. Find a contiguous free region in `.rodata` or `.data` large enough for
   17 × 4 bytes per array × N arrays. §6.2 already flagged the existence of
   multi-KB zero regions; one such region has to absorb all of them.
2. Copy each array's current 16 entries verbatim, then append a 17th entry
   whose pointer targets a "Korean" / "CIV_Korea" / "Sejong" / etc. string
   (new strings also placed in the free region — allocate both strings and
   pointer tables together in one blob).
3. Patch every LIS/ADDI pair that references the old array base.
4. Patch every `cmpwi rN, 0x10` (`< 16`) loop bound to `cmpwi rN, 0x11`
   (`< 17`).

Cross-checking with `docs/eboot-analysis.md`'s function map: the EBOOT is
~26 MB with ~69k functions decompiled. The array-reference sites are not yet
enumerated. Counting LIS/ADDI pairs that load any of the four confirmed
bases is the concrete next §5.1 subtask.

## Risks introduced by the parallel-array model

- **Miss one array and civ 16 reads garbage for that field.** If we find
  three arrays but miss a fourth, civ 16 will read past the end of the
  un-extended array and hit whatever byte pattern is at `array_base + 16*4`.
  Hard-to-debug crashes or silently-wrong behavior.
- **Savegame format.** If the save serializer walks any array by its
  pre-patch length (`sizeof / 4 == 16`), adding a 17th entry changes stored
  layout. Mitigation: bump the save version byte (§8 already notes this).
- **AI setup code that reads several arrays in lockstep.** If one array is
  extended but another isn't, the lockstep breaks. Mitigation: extend all
  arrays atomically in a single patch iteration and gate verify.sh on the
  full-extension set.

## Appendix: raw dumps

Leader display name table (`0x0194b434`, stride 4, 16 entries):
```
[ 0] 0x194b434 -> 0x16a38a8 'Caesar'
[ 1] 0x194b438 -> 0x16a3c10 'Cleopatra'
[ 2] 0x194b43c -> 0x16a3cb8 'Alexander'
[ 3] 0x194b440 -> 0x16a3ca8 'Isabella'
[ 4] 0x194b444 -> 0x16a3c60 'Bismarck'
[ 5] 0x194b448 -> 0x16a3c98 'Catherine'
[ 6] 0x194b44c -> 0x16a3c38 'Mao'
[ 7] 0x194b450 -> 0x16a3c28 'Lincoln'
[ 8] 0x194b454 -> 0x16a3c70 'Tokugawa'
[ 9] 0x194b458 -> 0x16a3c50 'Napoleon'
[10] 0x194b45c -> 0x16a3868 'Gandhi'
[11] 0x194b460 -> 0x16a3c30 'Saladin'
[12] 0x194b464 -> 0x16a3870 'Montezuma'
[13] 0x194b468 -> 0x16a3c80 'Shaka'
[14] 0x194b46c -> 0x16a3958 'Genghis Khan'
[15] 0x194b470 -> 0x16a38d0 'Elizabeth'
```

Civ internal tag table (`0x0194b35c`, stride 4, 16 entries):
```
[ 0] 0x194b35c -> 0x16edec0 'CIV_Rome'
[ 1] 0x194b360 -> 0x16eded0 'CIV_Egypt'
[ 2] 0x194b364 -> 0x16edee0 'CIV_Greece'
[ 3] 0x194b368 -> 0x16edef0 'CIV_Spain'
[ 4] 0x194b36c -> 0x16edf00 'CIV_Germany'
[ 5] 0x194b370 -> 0x16edf10 'CIV_Russia'
[ 6] 0x194b374 -> 0x16edf20 'CIV_China'
[ 7] 0x194b378 -> 0x16edf30 'CIV_America'
[ 8] 0x194b37c -> 0x16edf40 'CIV_Japan'
[ 9] 0x194b380 -> 0x16edf50 'CIV_France'
[10] 0x194b384 -> 0x16edf60 'CIV_India'
[11] 0x194b388 -> 0x16edf70 'CIV_Arabia'
[12] 0x194b38c -> 0x16edf80 'CIV_Aztec'
[13] 0x194b390 -> 0x16edf90 'CIV_Africa'
[14] 0x194b394 -> 0x16edfa0 'CIV_Mongolia'
[15] 0x194b398 -> 0x16edfb0 'CIV_England'
```

Leader internal tag table (`0x0194b318`, stride 4, 16 entries):
```
[ 0] 0x194b318 -> 0x16eddc0 'LDR_rome'
[ 1] 0x194b31c -> 0x16eddd0 'LDR_egypt'
[ 2] 0x194b320 -> 0x16edde0 'LDR_greece'
[ 3] 0x194b324 -> 0x16eddf0 'LDR_spain'
[ 4] 0x194b328 -> 0x16ede00 'LDR_germany'
[ 5] 0x194b32c -> 0x16ede10 'LDR_russia'
[ 6] 0x194b330 -> 0x16ede20 'LDR_china'
[ 7] 0x194b334 -> 0x16ede30 'LDR_america'
[ 8] 0x194b338 -> 0x16ede40 'LDR_japan'
[ 9] 0x194b33c -> 0x16ede50 'LDR_france'
[10] 0x194b340 -> 0x16ede60 'LDR_india'
[11] 0x194b344 -> 0x16ede70 'LDR_arabia'
[12] 0x194b348 -> 0x16ede80 'LDR_aztec'
[13] 0x194b34c -> 0x16ede90 'LDR_africa'
[14] 0x194b350 -> 0x16edea0 'LDR_mongolia'
[15] 0x194b354 -> 0x16edeb0 'LDR_england'
```

Civ adjective table (`0x0195fe28`, stride 4, 16 entries):
```
[ 0] 0x195fe28 -> 0x16a49f8 'Roman'
[ 1] 0x195fe2c -> 0x16a4a00 'Egyptian'
[ 2] 0x195fe30 -> 0x16a4a10 'Greek'
[ 3] 0x195fe34 -> 0x16a4a18 'Spanish'
[ 4] 0x195fe38 -> 0x16a4a20 'German'
[ 5] 0x195fe3c -> 0x16a4a28 'Russian'
[ 6] 0x195fe40 -> 0x16a4a30 'Chinese'
[ 7] 0x195fe44 -> 0x16a4a38 'American'
[ 8] 0x195fe48 -> 0x16a4a48 'Japanese'
[ 9] 0x195fe4c -> 0x16a4a58 'French'
[10] 0x195fe50 -> 0x16a4a60 'Indian'
[11] 0x195fe54 -> 0x16a4a68 'Arab'
[12] 0x195fe58 -> 0x16a4a70 'Aztec'
[13] 0x195fe5c -> 0x16a4a78 'African'
[14] 0x195fe60 -> 0x16a4a80 'Mongolian'
[15] 0x195fe64 -> 0x1692b00 'English'
```
