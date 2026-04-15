# Dead Common0.FPK overlays — archived at iter-223

These three XML overlays were spec'd by PRD §6.3 and shipped under
iter-176 / iter-214 as part of the Common0_korea.FPK overlay path:

- `leaderheads.xml` — adds `<LeaderHead Nationality="16" Text="Sejong">`
  reusing `GLchi_Mao.xml` / `GLchi_Mao_` Mao assets.
- `console_pediainfo_civilizations.xml` — adds CIV_KOREA pedia entry
  reusing PEDIA_CHINA_*.dds.
- `console_pediainfo_leaders.xml` — adds LEADER_SEJONG pedia entry
  reusing PEDIA_MAO_*.dds.

iter-222 (2026-04-15) empirically proved that **`Common0.FPK` is
never opened by the BLUS-30130 PS3 build at runtime**. Renaming
`Common0.FPK` out of the way and re-running `korea_play 0 caesar`
produces an M9 PASS — the game doesn't even attempt to open the
file. This means these three XML overlays are **structurally inert**:
they ship in the FPK but cannot reach the runtime.

iter-223 archives them here for documentation completeness and removes
the Common0_korea.FPK production from the build/install pipeline. The
v1.0 shipping state now has only **two effective FPK overlays**
(both inside Pregame.FPK):

- `xml_overlays/civnames_enu.txt` (Korean at row 17)
- `xml_overlays/rulernames_enu.txt` (Sejong at row 17)

plus the 6 in-place EBOOT byte patches (iter-4 ADJ_FLAT extension ×4,
iter-14 parser-count bump ×2).

See PRD §10 iter-222 / iter-223 entries and
`korea_mod/verification/iter222_common0_unused/findings.md` for the
empirical proof.

## If a future v1.1 unblocks Common0.FPK

If a future investigation locates the actual code path that loads
leaderhead bindings on PS3 — most likely a hardcoded EBOOT table
indexed by Nationality, or a Scaleform-side bundle inside
`gfx_chooseciv.gfx` — these overlays could be revived as a
reference for what data SHOULD be at index 16. They are XML-valid
and structurally consistent with the stock Common0/leaderheads.xml.
