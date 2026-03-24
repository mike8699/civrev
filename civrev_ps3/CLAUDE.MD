This repo is a work-in-progress map editor for Civilization Revolution (PS3/Xbox360 versions). The PS3 iso extracted into `extracted/`, and a DLC pack is in `Pak9/`. The DLC maps are the easiest to access and modify, so we'll be working with those primarily.

visualize_map.py includes a rudimentary 2D visualizer, which parses the .map files into 2D bitmaps with color-coded tiles based on the terrain type. There are other texture/unknown files ending in .dds too; those can be converted to other image formats. For example, to convert to .bmp -
`wine texconv.exe mapthe_world_lightmap.dds  -ft bmp`

The textures used in the game are in `extracted/Level` and end in .dds.

See screenshot.jpg for an example of how these maps are rendered in-game.


### What is Civilization Revolution?

🎮 Core Gameplay Loop

At its heart, Civilization Revolution is a streamlined turn-based 4X strategy game:

Explore the map and uncover terrain, primitives, and rival civilizations.

Expand your empire by founding new cities and securing territory.

Exploit resources through city development, research, and trade.

Exterminate or outmaneuver rivals through military, cultural influence, or technological superiority.

Unlike the main Civilization games on PC, Civ Revolution is designed for faster, more accessible play—most matches finish in a few hours rather than dozens, and many complex systems are simplified for clarity on consoles and handhelds.

🏙️ Starting Out
1. Choose a Civilization

You pick from 16 historical civilizations, each with:

A unique leader (e.g., Caesar, Elizabeth, Cleopatra)

Special bonuses tied to their historical traits

Extra era bonuses unlocked as you research technologies
These bonuses shape your strategy—some civilizations favor military might, others culture or economy.

⚙️ Game Mechanics
2. Turns & Time Scale

The game begins in 4000 BC and goes to 2100 AD. Turns represent increasing chunks of time (starting around 100 years per turn and ending around 2 years per turn), reflecting the pace of historical progress.

3. Cities & Resources

Cities generate three key yields every turn:

Food — grows your population

Production — builds units and buildings

Trade — converted into research (tech progress) or gold
You found additional cities with settlers as you expand. Geography matters: hills, rivers, and terrain types affect yields and strategy.

🔬 Research & Progress

A streamlined technology tree lets you advance through eras. Technologies unlock:

New units (archers → pikemen → tanks → bombers)

Buildings (granaries, libraries)

Wonders and special bonuses

Progressing technologies also grants additional civ-wide bonuses, making scientific progress a core part of strategic play.

🪖 Units & Combat
4. Military Units

You build units such as:

Scouts and warriors (early game)

Archers and pikemen (mid game)

Mechanized infantry and bombers (late game)

Combat uses distinct attack and defense values for units, unlike some Civ games with a single strength number.

Armies

✔ You can combine three units of the same type into an army.
An army pools their strength, making it significantly stronger than three single units.

Experience & Promotions

Winning battles gives units experience, promoting them to:

Veteran

Elite
which can unlock bonuses—extra movement, healing, or combat perks.

🏛️ City Improvements & Wonders

Cities can build:

Buildings that improve yields or unlock new abilities

Wonders that grant powerful global effects (e.g., boost production, culture, science)

Some wonders are tied directly to victory conditions (World Bank for Economic wins, United Nations for Cultural wins).

🤝 Diplomacy

You interact with rival leaders through diplomacy:

Form peace

Declare war

Trade or negotiate

AI leaders have personalities and react to your actions—friendly, hostile, cooperative, or opportunistic—though diplomacy is simpler than in the PC Civilization titles.

🏆 Victory Conditions

There are four primary paths to victory:

1. Domination

Capture all opponent capital cities—hold them long enough to secure the win.

2. Technological (Space Race)

Research the necessary technologies, build the spaceship components, and be the first to launch to Alpha Centauri.

3. Economic

Accumulate 20,000 gold and construct the World Bank wonder.

4. Cultural

Achieve a combined total of 20 cultural accomplishments — wonders built, great people generated or cities converted — and then build the United Nations.

If no condition is met by 2100 AD, the highest score wins (similar to a Domination victory).

📊 Streamlined Features (vs Classic Civ)

Civilization Revolution strips or simplifies many traditional Civ mechanics:

No worker units—roads and tile improvements come from cities and gold, not manual labor.

Simplified government and civic systems (changed to era bonuses).

No pollution, corruption, or starvation—focuses on core strategic decisions.

Barbarians live in villages and provide bonuses when defeated.

This streamlining makes the game faster and more accessible while still retaining strategic depth.

🎯 Multiplayer & Replayability

You can play against others online with up to four players in free-for-all or team modes. There’s matchmaking, ranked play, and leaderboards, though the pace can feel slower than single-player without turn timers.

🧠 Overall Feel

Civilization Revolution is often described as “Civ lite”—it captures the spirit of empire building, diplomacy, and historical progression, but with:

Faster matches

Fewer mechanics to micromanage

Simpler controls for consoles and casual players
