# Combat System

Analysis of combat mechanics from Ghidra decompilation of `CombatPreview.c`, `NDSCombat.c`, and `SpecialUnit.c`.

## Combat Resolution

Combat is resolved in `qCombat` (316 basic blocks at ~0x34ebc). Pre-combat calculations are displayed via `CombatPreview` which shows expected outcomes before committing.

### Base Formula

From CombatPreview.c Init function:

```
effective_strength = (base_attack * (experience_level + 1) * attack_multiplier) / divisor
```

Where:
- `base_attack` = unit's base combat value
- `experience_level` = 0 (green), 1 (veteran), 2 (elite)
- `attack_multiplier` = 1 (melee) or 3 (ranged/cavalry with `[unit_data + 4] != 0`)
- `divisor` = 4 (normal) or 2 (with leader bonus `HasLBonus(0x33, player, 0)`)

## Defense Modifiers

All modifiers are additive percentages applied to the base defense value.

| Modifier | Bonus | Condition |
|----------|-------|-----------|
| **Fortress** | +100% | Unit is in a fortress |
| **City Walls** | +100% | Defending in city with Walls |
| **Fortified** | +100% | Unit has completed fortification |
| **Fortifying** | +50% | Unit is currently fortifying (partial) |
| **Palace** | +50% | Defending in capital city |
| **Hill terrain** | +50% | Defending on hill tile |
| **Great General** | +50% | Great General present in same tile |
| **Veteran bonus** | +50% | Unit has veteran status |
| **Militia penalty** | -50% | Unit is militia (weak early unit) |
| **Uncivilized penalty** | -50% | Both attacker and defender can receive this |

## Attack Modifiers

| Modifier | Effect | Condition |
|----------|--------|-----------|
| **River crossing** | -50% attack | Attacker crosses river to engage |
| **Ranged/cavalry** | x3 multiplier | Unit has ranged or cavalry flag |
| **Leader bonus** | Divisor 2 instead of 4 | `HasLBonus(0x33)` active |

## Terrain Defense Calculation

From CombatPreview.c line 633-640:

```c
terrain_bonus = terrain_table[terrain_type * 0x1d + 0x1c] * 50;
total_defense = base_defense + 50 + terrain_bonus;
```

The terrain defense lookup table is indexed by terrain type with stride 0x1d (29 bytes per entry), reading the value at offset 0x1c (28th byte). The result is multiplied by 50 (0x32) and added to a base of 50.

## Combat AI

`CombatAI` at ~0x34ac8 (404 basic blocks, 7.2 KB) handles:
- Target selection and prioritization
- Retreat decisions
- Army vs army resolution
- Naval bombardment calculations

## Special Unit Handling

From SpecialUnit.c, 16 switch cases (0x0-0xf) map civilizations to their unique units at specific technology levels:
- Technology gates: 0xc (12), 0xd (13), 0xf (15), 0x11 (17)
- Each civilization gets a unique unit replacement at certain tech levels

## Combat Sound Effects

From NDSCombat.c and AudioDepot.xml, 92+ distinct combat sounds:

- **Melee**: Sword hits, shield blocks
- **Ranged**: Arrow impacts (ArrowImpactArmor, ArrowImpactFlesh, ArrowImpactTank)
- **Siege**: CannonMove, CannonGetsHit, CannonDeath, CatapultDeath, ArtilleryFire
- **Naval**: BattleShipFortify
- **Air**: BombDrop, BomberFlyBy
- **Voice**: 10x2 cheer variations per era, 5 victory voxes, spy voxes
- **Ambient**: 3 combat ambience tracks (CmbtAmbience1-3) that fade on resolution

## Army Formation

Three units of the same type can be combined into an army:
- Armies receive increased defense
- Army names defined separately in UnitNames_enu.txt (e.g., "Warrior Army", "Tank Army", "Bomber Wing", "Battleship Fleet")
- Each unit type has a corresponding army name

## Unit Experience & Promotion

- **Green** (level 0): No bonus
- **Veteran** (level 1): +50% combat strength
- **Elite** (level 2): +100% combat strength, can acquire special ability
- Promotion occurs after defeating equal or greater strength enemy
- Barracks building: New units created as veterans
- Great Leader: Can upgrade all non-veteran units to veterans

## Aircraft Rules

- Fighters: Must return to friendly city every 2 turns
- Bombers: Must return to friendly city every 4 turns
- Only Fighters can attack other air units
- Bombers can attack cities but cannot capture them
- Failure to return results in unit loss
