# Debug Mode - PS3 Civilization Revolution

The retail PS3 EBOOT.ELF contains extensive debug/development infrastructure from Firaxis's development process. While the debug features are all **disabled by default** in the retail build, they can be re-enabled via binary patching.

## Debug Configuration System

### Master Config Structure

All debug flags live in a global config structure accessed through `PTR_DAT_01929e14`. The flags field is at offset **+0x4** in this structure, stored as a 32-bit bitmask.

### Flag Setter: `FUN_00031908`

Address: `0x00031908` (32 bytes)

```c
void SetFlag(int config_ptr, uint flag_mask, int enable) {
    if (enable == 0)
        config_ptr[+0x4] &= ~flag_mask;  // clear flag
    else
        config_ptr[+0x4] |= flag_mask;   // set flag
}
```

### Config Loader: `FUN_0002dfb4`

Address: `0x0002dfb4` (2628 bytes)

This is the main config initialization function, called from `FUN_0002fa08` during game startup. It reads boolean values from an XML config document (at offset +0x54 of the game settings object) using `FUN_000357b0` (read bool from XML) and `FUN_00035948` (read int from XML), then sets the corresponding flags via `FUN_00031908`.

The XML tag names are stored as string pointers in the TOC (Table of Contents) data section, resolved at runtime. The following mapping was reconstructed from string extraction and code analysis:

## Debug Flags Reference

All flags are stored at `*(int *)PTR_DAT_01929e14 + 0x4`.

| Bit Mask | Default | Config Name | Description |
|----------|---------|-------------|-------------|
| `0x01` | 1 | *(set in constructors)* | Base initialization flag |
| `0x02` | 0 | *(unknown)* | Unknown (read from XML, cleared by default) |
| `0x04` | 0 | *(set at runtime)* | Set during input events and camera operations |
| `0x08` | 0 | *(unknown)* | Unknown (read from XML, cleared by default) |
| `0x10` | 0 | *(unknown bool)* | Read from XML, cleared by default |
| `0x20` | 0 | *(unknown bool)* | Read from XML, cleared by default |
| `0x40` | varies | *(conditional)* | Conditionally set based on timer/turn-limit config |
| `0x100` | 0 | *(runtime flag)* | **Camera lock / automation flag** - when set, bypasses normal game logic in favor of automated/locked camera behavior. Cleared in `FUN_00031350` (game end), set in `FUN_00144324` (camera mode toggle) |
| `0x400` | 0 | *(runtime flag)* | Set when entering specific game states (e.g., `FUN_001bbd84`), cleared on game end |
| `0x800` | 0 | *(runtime flag)* | **AutoPlay mode flag** - enables autonomous AI control. Set/cleared by `FUN_0002d988`. When active, `FUN_001ba468` calls special AI play methods |
| `0x1000` | 1 | *(conditional)* | Conditionally set based on flag 0x40 status |
| `0x2000` | 0 | `DisablePreloading` | Disables asset preloading. When set, `FUN_001b873c` skips scenario preloading |
| `0x4000` | 0 | *(unknown bool)* | Read from XML, cleared by default. Triggers forced refresh in UI code (`FUN_000b7934` line 98) |
| `0x8000` | 1 | *(default true)* | Unknown flag, set to 1 in config loader |
| `0x100000` | varies | *(icon indicator)* | **"SetIcon" indicator** - When set, `FUN_000d2538` displays a status icon overlay (icon index 0) using the "SetIcon" command |
| **`0x200000`** | **0** | **`EnableAsserts` / Debug Mode** | **PRIMARY DEBUG FLAG** - Controls debug input processor, debug icon indicator, and multiple gameplay behavior changes (see below) |
| `0x400000` | 0 | *(unknown)* | Set via `FUN_00031908` in config loader, cleared by default |
| `0x800000` | 1 | *(default true)* | Unknown flag, set to 1 in config loader |
| `0x1000000` | varies | *(from XML)* | Read from XML config |
| `0x2000000` | 0 | *(unknown)* | **"Show All" / Full Visibility flag** - When set, shows all units/resources/wonders regardless of fog-of-war state. Affects 10+ rendering functions (unit placement, wonder display, resource icons). Randomizes unit counts. Set via `FUN_00031908` in config loader |
| `0x4000000` | 0 | *(runtime flag)* | **Game-in-progress flag** - Set when gameplay begins (`FUN_00170ff0`), cleared when gameplay ends |
| `0x8000000` | 0 | *(runtime flag)* | **Screen transition flag** - Set/cleared during screen transitions (start screen, loading) |

## What Debug Mode (0x200000) Does

When the `0x200000` flag is active, the following behaviors change:

### 1. Debug Input Processor (`CcDebugInputProcessor`)
- **Normal**: `FUN_001bcde8` activates `CcGameInputProcessor` for standard game input
- **Debug**: When `0x200000` is set, the function returns early without creating the normal game input processor, leaving `CcDebugInputProcessor` active
- The game has three input processor classes:
  - `CcDebugInputProcessor` (at `PTR_s_CcDebugInputProcessor_019271e4`)
  - `CcGameInputProcessor` (at `PTR_s_CcGameInputProcessor_019271e8`)
  - `CcAppInputProcessor` (at `PTR_s_CcAppInputProcessor_019271ec`)

### 2. Debug Icon Indicator
- `FUN_000d2538`: Displays a debug status icon (index 2) on the HUD when `0x200000` is active
- Also shows icons for `0x100000` (index 0) and `0x80000` (index 1)
- These are likely visual indicators for developers showing which debug modes are active

### 3. Modified Game Update Loop (`FUN_001be018`)
- **Normal** (flag clear): Calls vtable method at offset `0x1e8` to cancel/close overlays when input is detected
- **Debug** (flag set): Forces offset `0x1e1` byte to 1 (debug state active), calls vtable method at offset `0x1ec` with param 0 instead, and calls vtable method `0x10` instead of `0xc` on the input handler - suggesting different input routing

### 4. HUD/Cursor Behavior (`FUN_000a1c10`)
- When `0x200000` is set: Forces `FUN_0009ff84` (cursor/selection reset) even when conditions would normally skip it (e.g., when the active player's city tab is being viewed)

### 5. Tile Selection Visibility (`FUN_001556b0`)
- Returns `true` when `0x200000` is set AND certain tile flags (`0x43`) are present
- This likely makes normally-hidden tile selection indicators visible in debug mode

### 6. Various UI Skip/Bypass
- Multiple functions check the flag to skip animations, bypass normal turn flow guards, or show additional information

## Other Notable Debug Features

### `isDebugger` Flag
A separate check (from Flash/Scaleform `capabilities.isDebugger`) that gates certain UI behaviors. This is a Flash Player property, not a game config flag.

### `Art cheat codes`
String references suggest developer art/asset viewing cheats exist. The strings "See tons of buildings and units" and "See tons of buildings (all cities)" and "Add a Wonder" describe what these do.

### Tuner/Remark Debug Output
- **`SendRemarksToTuner`**: Sends `FRemark()` debug output to PS3 dev kit ProDG tuner
- **`Set_remark_levels`**: Controls verbosity (R0=normal, R1=verbose)
- **`EnableMemTrackerSystem`**: Enables memory leak detection/tracking
- These are activated by tuner commands (param_1==1, param_2==0xFFFF), meaning they require a PS3 development kit

### Full List of Development Toggles (from EBOOT strings)
| Toggle Name | Description |
|---|---|
| `EnableAsserts` | Enable asserts in debug mode |
| `GFX debugging` | Show GFX debugging information |
| `DEMO mode` | Enable demo/kiosk mode |
| `UseQuickLaunch` | Skip menus, go straight to game |
| `UseTrophyRoomLaunch` | Skip menus and gameplay, go to trophy room |
| `UseAutoPlay` | AI plays autonomously (spectator mode) |
| `TakeUnitScreenshots` | Auto-capture unit screenshots |
| `ShowMovie` | Enable movies and attract mode |
| `DisablePreloading` | Disable asset preloading |
| `DisableBackgroundLoading` | Disable background asset loading |
| `DisableHotLoading` | Disable hot-reload of assets |
| `Disable LoadingScreen` | Skip loading screens |
| `Disable Audio` | Mute all audio |
| `DisableTalkingHeads` | Hide leader animated portraits |
| `DisablePhysicsThreads` | Single-threaded physics |
| `Disable Walls` | Hide city wall rendering |
| `Disable VFOW` / `Disable the Volume Fog Of War` | Disable volumetric fog of war |
| `Disable Terrain PreBuilts` | Use procedural terrain instead of prebaked |
| `Hide Unit Flag` | Hide unit banners |
| `Use MP Resynchronization` | Multiplayer resync protocol |
| `EnableMemTrackerSystem` | Memory leak tracking |
| `SendRemarksToTuner` | Debug output to ProDG tuner |
| `Login` | Auto-login to PSN profile |
| `SkipDeviceSelection` | Skip storage device prompt |
| `QuickExit` | Exit without cleanup/leak reports |
| `Enable Z-Prepass` | Enable depth pre-pass rendering |

## How to Enable Debug Mode

### Method 1: Binary Patch the EBOOT.ELF (Verified)

The config loader `FUN_0002dfb4` reads boolean flags from an internal XML config and passes them as the third argument to `FUN_00031908`. The Ghidra decompiler incorrectly shows these as hardcoded `0` values, but they are actually loaded from the stack via `lbz r5, offset(r1)` instructions (PPC "load byte and zero").

All patch locations below have been **verified against the raw binary bytes** of the retail EBOOT.ELF.

#### Patch A: Enable Debug Mode (flag 0x200000) - CONFIRMED

| | |
|---|---|
| **Virtual address** | `0x0002E488` |
| **File offset** | `0x0001E488` |
| **Original bytes** | `88 A1 00 74` (`lbz r5, 0x74(r1)` - loads XML value from stack) |
| **Patched bytes** | `38 A0 00 01` (`li r5, 1` - forces flag ON) |
| **Effect** | Enables CcDebugInputProcessor, debug HUD icon, modified game loop |

Surrounding context:
```
0x0002E484: 7F43D378   mr r3, r26          (config ptr)
0x0002E488: 88A10074   lbz r5, 0x74(r1)    <-- PATCH THIS
0x0002E48C: 3C800020   lis r4, 0x20        (flag = 0x200000)
0x0002E490: 48003479   bl FUN_00031908
```

#### Patch B: Enable Full Visibility (flag 0x2000000) - CONFIRMED

| | |
|---|---|
| **Virtual address** | `0x0002E774` |
| **File offset** | `0x0001E774` |
| **Original bytes** | `38 A0 00 00` (`li r5, 0` - hardcoded OFF) |
| **Patched bytes** | `38 A0 00 01` (`li r5, 1` - forces flag ON) |
| **Effect** | Shows all units/resources/wonders regardless of fog of war. Randomizes unit counts (dev testing feature) |

Note: Unlike most flags, `0x2000000` is hardcoded to 0 (not read from XML), so it was intentionally disabled even in dev builds.

#### Applying the patches

```bash
# Make a backup first!
cp EBOOT.ELF EBOOT.ELF.bak

# Patch A: Enable debug mode (0x200000)
printf '\x38\xa0\x00\x01' | dd of=EBOOT.ELF bs=1 seek=$((0x1E488)) conv=notrunc

# Patch B: Enable full visibility (0x2000000)
printf '\x38\xa0\x00\x01' | dd of=EBOOT.ELF bs=1 seek=$((0x1E774)) conv=notrunc
```

### Complete Flag Patch Reference

All flags set in `FUN_0002dfb4` (`0x0002dfb4`, 2628 bytes) and their patch locations:

| Flag | File Offset | Original Instr | Source | Known Name |
|------|-------------|----------------|--------|------------|
| `0x01` | `0x1E108` | `li r5, 1` | hardcoded 1 | *(base init, always on)* |
| `0x02` | `0x1E4BC` | `lbz` | XML | *(unknown)* |
| `0x08` | `0x1E4F0` | `lbz` | XML | *(unknown)* |
| `0x10` | `0x1E330` | `lbz` | XML | *(unknown)* |
| `0x20` | `0x1E2F8` | `lbz` | XML | *(unknown)* |
| `0x100` | `0x1E850` | `lbz` | XML | Camera lock / automation |
| `0x200` | `0x1E894` | `lbz` | XML | *(unknown)* |
| `0x1000` | `0x1E7C0` | `lbz` | XML | *(conditional)* |
| `0x2000` | `0x1E450` | `lbz` | XML | `DisablePreloading` |
| `0x4000` | `0x1E410` | `lbz` | XML | *(unknown)* |
| **`0x200000`** | **`0x1E488`** | **`lbz`** | **XML** | **Debug mode** |
| `0x400000` | `0x1E760` | `lbz` | XML | *(unknown)* |
| `0x800000` | `0x1E3A4` | `lbz` | XML | *(unknown, defaults 1)* |
| `0x1000000` | `0x1E65C` | `lbz` | XML | *(unknown)* |
| **`0x2000000`** | **`0x1E774`** | **`li r5, 0`** | **hardcoded 0** | **Full visibility (show all)** |

To force any XML-sourced flag ON, replace the 4-byte `lbz` instruction at the given file offset with `38 A0 00 01` (`li r5, 1`).

### Method 2: RPCS3 Memory Patch (Runtime)

For runtime patching without modifying the EBOOT:

1. In RPCS3, use **Manage > Game Patches** or the **Debugger**
2. The config structure pointer is at `0x01929e14` in memory
3. Dereference the pointer, then read offset `+0x4` for the flags field
4. OR the flags value with `0x200000` (debug) or `0x2200000` (debug + full visibility)

## Key Function Addresses

| Address | Size | Purpose |
|---------|------|---------|
| `0x00031908` | 32 | `SetFlag(config, mask, enable)` - flag setter |
| `0x0002dfb4` | 2628 | Config loader - reads XML, sets all flags |
| `0x0002fa08` | 336 | Startup init - creates XML doc, calls config loader |
| `0x001bcde8` | 388 | Input processor switcher (checks 0x200000) |
| `0x001be018` | 2900 | Main game update loop (different paths for debug) |
| `0x001b6e50` | 196 | Input processor cleanup/switch back to normal |
| `0x000d2538` | 240 | Debug icon indicator display |
| `0x000a1c10` | 472 | HUD update (cursor behavior differs in debug) |
| `0x001bad0c` | 400 | Camera/map render (0x100 flag - automation) |
| `0x001ba468` | 736 | AutoPlay handler (0x800 flag) |
| `0x001b873c` | 288 | Preload handler (0x2000 flag) |
| `0x001bbd84` | 312 | Game state transition (sets 0x400) |
| `0x0002d988` | 264 | AutoPlay mode toggle (sets/clears 0x800) |
| `0x00116be4` | 8 | `GetDebugInputProcessor()` |
| `0x00116bec` | 8 | `GetGameInputProcessor()` |
| `0x00116bf4` | 8 | `GetAppInputProcessor()` |

## Memory Addresses

| Address | Description |
|---------|-------------|
| `0x01929e14` | Pointer to main config structure (PTR_DAT_01929e14) |
| `0x019271e4` | "CcDebugInputProcessor" string pointer |
| `0x019271e8` | "CcGameInputProcessor" string pointer |
| `0x019271ec` | "CcAppInputProcessor" string pointer |
| `0x01929e98` | Input processor manager reference |
| `0x019257c4` | Icon/status flags variable (for debug indicator) |
