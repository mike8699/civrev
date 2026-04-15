# iter-222 generalization: 7 FPKs are dead, not just Common0

iter-222's empirical method (grep `sys_fs_open` for FPK names
across all captured RPCS3.log files) generalizes to every FPK
in `Resource/Common/`. Tallying across 7 surviving korea_play /
M9 RPCS3.log files in
`rpcs3_automation/output/rpcs3_logs/`:

| FPK | logs containing | total ref lines | runtime status |
|---|---|---|---|
| Pregame.FPK | 7/7 | 14 | **OPENED** (open + fd metadata, 2 lines per log) |
| pedia.FPK | 7/7 | 14 | **OPENED** |
| Misc0.FPK | 7/7 | 14 | **OPENED** |
| Misc1.FPK | 7/7 | 14 | **OPENED** |
| ps3_misc.FPK | 7/7 | 28 | **OPENED** (2 path attempts × 2 lines) |
| Common0.FPK | 0/7 | 0 | **DEAD** (iter-222 verified empirically) |
| leaderhead.FPK | 0/7 | 0 | **DEAD** |
| buildings.FPK | 0/7 | 0 | **DEAD** |
| units.FPK | 0/7 | 0 | **DEAD** |
| hoa.FPK | 0/7 | 0 | **DEAD** |
| Level.FPK | 0/7 | 0 | **DEAD** |
| music.FPK | 0/7 | 0 | **DEAD** (also missing from disc) |

**Conclusion:** Of the 11+ FPKs the BLUS-30130 disc ships
under `Resource/Common/`, only 5 are actually loaded at
runtime. The other 7 are legacy dead carry-over from earlier
Civilization Revolution ports (Xbox 360 / iOS — see iter-221's
cross-platform finding for context).

**Implications:**

- Any v1.1+ cosmetic asset for Korea (custom portrait,
  leaderhead, civ icon, etc.) **must** be packed into one of
  the 5 live FPKs (Pregame, pedia, Misc0, Misc1, ps3_misc) or
  embedded directly into the EBOOT. Replacing files inside
  any of the 7 dead FPKs is a no-op.
- The `iter222_renamed` empirical method only directly
  verified Common0.FPK as dead — but the open-trace evidence
  for the other 6 is just as strong. None of them have ever
  appeared in any RPCS3 log across 7 captured runs spanning
  iter-198..223. To be 100% rigorous, each could be
  individually rename-tested, but the open-trace evidence is
  conclusive enough that the burden of proof has shifted: a
  future iteration that wants to touch one of these FPKs must
  first prove it's NOT dead.
- iter-223 already removed Common0 from the install pipeline.
  If a future iteration ever needs to drop other FPK overlays,
  the same approach (archive overlays under
  `xml_overlays/dead_iter22x/`, skip in pack_korea.sh, restore
  to `.orig` in install.sh) applies.

**Why does the EBOOT still reference these names?**

The EBOOT strings contain all 12 FPK names because the file
mounting code is generic ("for each known FPK, try open"). The
runtime open-and-iterate path apparently has a SUBSET filter
that only retains 5 names — likely a hardcoded array of FPK
names the BLUS-30130 build was repacked to actually use. The
specific filter location is interesting v1.1 RE work but
out-of-scope for v1.0 (no live FPK asset patches are needed).

A likely candidate for the filter: PS3 build was created from
the iOS / 360 codebase by stripping unused asset paths and
consolidating live assets into Pregame/pedia/Misc0/Misc1/
ps3_misc. The remaining FPKs were left on the disc as bit-
for-bit copies but their open paths were removed from the
runtime mount list.
