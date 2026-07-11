# Profiles & saves (H9)

The oracle container bind-mounts a **persistent** Xenia content root
(`fixtures/xenia_content/` on the host → `/root/.local/share/Xenia/content` in
the container). Anything Xenia writes there — a user profile, in-game saves —
survives across runs. `fixtures.sh` snapshots that state into committable,
named fixtures under `fixtures/saves/`.

## Why a profile is needed

CivRev queries a signed-in Xbox profile early in boot. With none, Xenia shows
**"No Profiles Found"** and the guest then **crashes** (observed at PC
`0x82A6DE1C`, null read). So the `menu`, `newgame_20turns`, and `save_load`
scenarios cannot produce a clean reference until a profile exists. (The `boot`
scenario, which only needs the first frame, works without one.)

## One-time profile provisioning (manual, over VNC)

Automated input to Xenia's own GUI dialogs is unreliable on the WM-less Xvfb
display (SDL ignores synthetic events — see INPUT_MAP.md), so create the profile
once by hand; it then persists in the mounted content dir:

1. Launch interactively:
   ```
   oracle/run_extracted.sh                 # VNC on :5900
   vncviewer localhost:5900                 # (host)
   ```
2. In the Xenia window, open the profile UI (title-bar menu → *Profile* →
   *Create Profile*, or click **Create Profile** on the "No Profiles Found"
   dialog) and create a profile. Note its XUID (Xenia shows it in the profile
   menu / logs `ProfileManager`).
3. Wire it to load on boot by setting, in the mounted config
   (`fixtures/xenia_content/../xenia-edge.config.toml`, or via the container):
   ```
   [Profiles]
   logged_profile_slot_0_xuid = "<the XUID>"
   ```
   (The scenario runner can be extended to pass this; for now it lives in the
   persistent config.)
4. Snapshot it so it is reproducible and committable:
   ```
   oracle/fixtures.sh export base_profile
   git add xenia_automation/fixtures/saves/base_profile
   ```
5. Re-run the gated scenarios; they should now get past the profile crash. Once
   `menu` boots cleanly, verify the input map (INPUT_MAP.md) and regenerate the
   `menu` / `newgame_20turns` references.

## Save fixtures for cross-implementation checks (PRD M7)

Once in-game saving works:
```
oracle/fixtures.sh export midgame_turn20     # snapshot the content dir
```
Point the ReXGlue port's `user_data_root` at the same content layout (or import
the fixture) and confirm the port **loads a save produced in Xenia**. Divergence
here localizes a XamContent / save-serialization bug.

## Commands

| Command | Effect |
|---|---|
| `fixtures.sh status` | profiles/saves currently in the live content dir |
| `fixtures.sh export <name>` | snapshot live content → `fixtures/saves/<name>` |
| `fixtures.sh import <name>` | restore a snapshot into the live content dir |
| `fixtures.sh list` | list snapshots |
| `fixtures.sh reset` | wipe the live content dir |

Note: committed fixtures contain a Xenia **profile/account blob and save data**,
not game assets. Keep them in this private repo only.
