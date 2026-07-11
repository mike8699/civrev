# Xenia keyboard → controller map (verification record)

`input.sh` translates logical gamepad actions to X11 keysyms via
`input_map.conf`, then injects them into the running oracle container with
`xdotool`. **The mechanism (key delivery) is verified; the specific bindings in
`input_map.conf` are NOT.** This file records what has been confirmed and how to
confirm the rest.

## Why this needs empirical verification

Xenia's keyboard→controller emulation and its default bindings vary by build and
by the `--hid` backend in use. The doc's rule stands: *do not trust documentation
for the mapping — drive the real menu once and observe.* Two independent unknowns:

1. **Which keysym maps to which pad button** in this pinned `xenia-edge`
   (`d158580`) build.
2. **Whether synthetic events reach the game.** Xvfb has no window manager, so
   `xdotool` sends `XSendEvent` to the Xenia window by id. SDL apps sometimes
   ignore synthetic key events. If they do, the fallback is `xdotool`'s global
   send, or enabling a real (Weston/Xephyr) path. This must be confirmed.

## Verification procedure (one VNC session)

1. Start the oracle against the extracted tree and attach a VNC viewer:
   ```
   oracle/run_extracted.sh              # foreground, VNC on :5900
   vncviewer localhost:5900             # (host)
   ```
2. In another terminal, with the container running, probe each action and watch
   the VNC screen for the cursor/menu reaction:
   ```
   oracle/input.sh --list               # see current guesses
   oracle/input.sh DPAD_DOWN            # does the menu selection move down?
   oracle/input.sh A                    # does it confirm?
   ...
   ```
   If nothing happens, first rule out the synthetic-event problem:
   ```
   oracle/input.sh --key Return         # raw send
   # then try focusing: does a real keypress via the VNC viewer work?
   ```
3. Correct `input_map.conf` so each logical action drives the intended UI motion.
4. Record confirmed bindings in the table below and commit both files.

## Confirmed bindings

| Action | keysym | Status | Notes |
|---|---|---|---|
| (all) | see input_map.conf | **UNVERIFIED** | seed values only; run the procedure above |

Update this table as bindings are confirmed. Once `START`, `A`, `B`, and the
D-pad are verified enough to reach the main menu and start a game, the `boot`
and `menu` scenarios (oracle/scenarios/) can be trusted end-to-end.

## Synthetic-event status

Observed 2026-07-11 against the pinned image (lavapipe/Xvfb, host GPU via /dev/dri):

- [x] `xdotool key/click --window <xenia>` (XSendEvent) does **NOT** affect the
      Xenia UI — a Return keypress and a mouse click on the "Create Profile"
      button both left the dialog unchanged. SDL ignores synthetic events.
- [ ] `xdotool windowfocus <xenia>` + global `xdotool key` (XTEST) — the correct
      approach; runs cleanly (rc 0) but its effect is not yet confirmed on a
      real interactive frame. **Verify over VNC.** input.sh now uses this path.
- [ ] if XTEST also fails on Xvfb: switch reference capture to the Weston
      display mode (real libinput) or add Xephyr with a WM.

## Boot findings (critical for oracle readiness)

Capturing the first rendered frame revealed that the game boots, renders the
**"Sid Meier's Civilization Revolution" title logo**, then hits:

1. A Xenia **"No Profiles Found"** modal ("There is no profile available! You
   will not be able to save without one.") — Xenia has zero user profiles.
2. A **guest crash** ("Uh-oh! The guest has crashed … PC: 0x82A6DE1C").

The crash is very likely caused by the missing profile/save device (the game
queries a signed-in profile early). **A usable menu/in-game reference therefore
requires provisioning a Xenia profile before boot.** Xenia exposes this via the
`[Profiles]` config section — `logged_profile_slot_0_xuid = "<xuid>"` loads a
profile on boot in slot 0. The remaining setup task (tracked in the scenario
runner / H9 fixtures): create one profile once, persist it in the content dir,
and wire its XUID into the pinned config. Until then, only the **boot** scenario
(up to the logo / first frame) yields a clean reference; menu/in-game scenarios
are blocked on the profile. This is a genuine finding, not a harness bug.
