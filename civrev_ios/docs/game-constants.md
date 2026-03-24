# Game Constants

Values extracted from decompiled source, game data files, and binary strings.

## Players & Limits

| Constant | Value | Source |
|----------|-------|--------|
| Max players per game | 6 | CcSetupData (loops 0-5) |
| Max civilizations | 16 + Barbarians | CivNames_enu.txt |
| Max achievements | 64 (0x40) | AchievementManager.c |
| Unit struct size | 0x54 bytes | Unit.c |
| City struct size | 0x101 bytes | City.c |
| Tech struct size | 0x6a bytes | Tech.c |
| Achievement struct size | 0x304 bytes | Achievement.c |
| Terrain instance size | 0xd55e0 bytes | CcTerrain.c |
| Map tile stride | 0x20 (32) | MakeCMap in _global.c |

## Civilizations (16 + Barbarians)

| Index | Civilization | Leader | Gender |
|-------|-------------|--------|--------|
| 0 | Romans | Caesar | M |
| 1 | Egyptians | Cleopatra | F |
| 2 | Greeks | Alexander | M |
| 3 | Spanish | Isabella | F |
| 4 | Germans | Bismarck | M |
| 5 | Russians | Catherine | F |
| 6 | Chinese | Mao | M |
| 7 | Americans | Lincoln | M |
| 8 | Japanese | Tokugawa | M |
| 9 | French | Napoleon | M |
| 10 | Indians | Gandhi | M |
| 11 | Arabs | Saladin | M |
| 12 | Aztecs | Montezuma | M |
| 13 | Zulu | Shaka | M |
| 14 | Mongols | Genghis Khan | M |
| 15 | English | Elizabeth | F |
| 16 | Barbarians | Grey Wolf | M |

Note: CivRev 2 renamed "Zulu" to "Africans" and added Korean as the 17th civ.

## Unit Types

### Standard Units (index order from UnitNames_enu.txt)

| Index | Unit | Army Name |
|-------|------|-----------|
| 0 | Settlers | Settlers |
| 1 | FSettler | FSettler |
| 2 | CSettler | CSettler |
| 3-5 | Barbarian (x3) | Barbarian Horde |
| 6 | Warrior | Warrior Army |
| 7 | Militia | Militia Army |
| 8 | Legion | Legion Army |
| 9 | Archer | Archer Army |
| 10 | Riflemen | Riflemen Army |
| 11 | Infantry | Modern Infantry Army |
| 12 | Horsemen | Horsemen Army |
| 13 | Knights | Knights Army |
| 14 | Tank | Tank Army |
| 15 | Pikemen | Pikemen Army |
| 16 | Catapult | Catapult Army |
| 17 | Cannon | Cannon Army |
| 18 | Artillery | Artillery Army |
| 19 | Submarine | Submarine Pack |
| 20 | Galley | Galley Fleet |
| 21 | Galleon | Galleon Fleet |
| 22 | Cruiser | Cruiser Fleet |
| 23 | Battleship | Battleship Fleet |
| 24 | (not used) | (not used) |
| 25 | Bomber | Bomber Wing |
| 26 | Fighter | Fighter Wing |
| 27 | ICBM | ICBM Group |
| 28 | Spy | Spy Ring |
| 29 | Caravan | Caravan Train |

### Great People

| Index | Unit | Army Equivalent |
|-------|------|-----------------|
| 30 | Great General | Great General |
| 31 | Great Scientist | Great Scientist |
| 32 | Great Humanitarian | Great Activist |
| 33 | Great Explorer/Industrialist | Great Explorer |
| 34 | Great Builder | Great Builder |
| 35 | Great Artist/Thinker | Great Artist/Thinker |
| 36 | Great Leader | Great Leader |
| 37 | Great Tycoon | Great Tycoon |

### Unique Units (Civilization-Specific)

| Index | Unit | Civilization |
|-------|------|-------------|
| 38 | Jaguar | Aztec |
| 39 | Impi Warrior | Zulu |
| 40 | Ashigaru | Japan |
| 41 | Hoplite | Greece |
| 42 | Longbow | English |
| 43 | Crossbow | — |
| 44 | Trebuchet | — |
| 45 | Cossack | Russia |
| 46 | Samurai | Japan |
| 47 | Conquistador | Spain |
| 48 | Panzer | Germany |
| 49 | T34 Tank | — |
| 50 | Sherman | — |
| 51 | 88mm Gun | — |
| 52 | Howitzer | — |
| 53 | Zero | — |
| 54 | Mustang | — |
| 55 | Spitfire | — |
| 56 | ME109 | — |
| 57 | Val Bomber | — |
| 58 | B17 | — |
| 59 | Lancaster | — |
| 60 | Heinkel | — |
| 61 | Trireme | — |
| 62 | Cataphract | Romans |
| 63 | Keshik | Mongol |
| 64 | Bowman | Egypt |
| 65 | Camel Archer | Arab |
| 66 | Chu-Ko-Nu | China |
| 67 | War-Chariot | Egypt |
| 68 | French Cannon | France |
| 69 | War Elephant | India |

Total: ~70 unit types (including 3 settler variants and 3 barbarian variants).

## Technologies (47)

From TechNames_enu.txt, in research order:

| Index | Technology |
|-------|-----------|
| 0 | (never) |
| 1 | Alphabet |
| 2 | Bronze Working |
| 3 | Ceremonial Burial |
| 4 | Horseback Riding |
| 5 | Pottery |
| 6 | Iron Working |
| 7 | Masonry |
| 8 | Writing |
| 9 | Code of Laws |
| 10 | Construction |
| 11 | Irrigation |
| 12 | Literacy |
| 13 | Mathematics |
| 14 | Currency |
| 15 | Democracy |
| 16 | Engineering |
| 17 | Feudalism |
| 18 | Monarchy |
| 19 | Religion |
| 20 | Banking |
| 21 | University |
| 22 | Invention |
| 23 | Navigation |
| 24 | Gunpowder |
| 25 | Metallurgy |
| 26 | Printing Press |
| 27 | Steam Power |
| 28 | Combustion |
| 29 | Electricity |
| 30 | Industrialization |
| 31 | Railroad |
| 32 | Communism |
| 33 | Flight |
| 34 | Mass Production |
| 35 | Steel |
| 36 | The Corporation |
| 37 | Atomic Theory |
| 38 | Electronics |
| 39 | Mass Media |
| 40 | The Automobile |
| 41 | Advanced Flight |
| 42 | Nuclear Power |
| 43 | Networking |
| 44 | Space Flight |
| 45 | Globalization |
| 46 | Superconductor |
| 47 | Future Technology |

## Wonders (41)

From WonderNames_enu.txt:

| Index | Wonder | Short Name |
|-------|--------|-----------|
| 0 | Great Pyramid | Great Pyramid |
| 1 | Great Wall | Great Wall |
| 2 | Hanging Gardens | Hanging Gardens |
| 3 | Stonehenge | Stonehenge |
| 4 | Colossus of Rhodes | Colossus of Rhodes |
| 5 | Oracle of Delphi | Oracle of Delphi |
| 6 | Great Library | Great Library |
| 7 | East India Company | East India Company |
| 8 | Oxford University | Oxford University |
| 9 | Great Theatre | Great Theatre |
| 10 | Himeji Samurai Castle | Samurai Castle |
| 11 | Leonardo's Workshop | Leonardo's Workshop |
| 12 | Magna Carta | Magna Carta |
| 13 | Trade Fair of Troyes | Trade Fair |
| 14 | Mil-Ind. Complex | Mil-Ind. Complex |
| 15 | Hollywood | Hollywood |
| 16 | Internet | Internet |
| 17 | Apollo Program | Apollo Program |
| 18 | Manhattan Project | Manhattan Project |
| 19 | United Nations | United Nations |
| 20 | World Bank | World Bank |
| 21 | Lighthouse of Alexandria | Lighthouse of Alexandria |
| 22 | Taj Mahal | Taj Mahal |
| 23 | Statue of Liberty | Statue of Liberty |
| 24 | Sydney Opera House | Sydney Opera House |
| 25 | Leaning Tower of Pisa | Leaning Tower of Pisa |
| 26 | Scotland Yard | Scotland Yard |
| 27 | SETI Program | SETI Program |
| 28 | Sudwala Caves | Sudwala Caves |
| 29 | Sukhbaatar Square | Sukhbaatar Square |
| 30 | Sphinx | Sphinx |
| 31 | Eiffel Tower | Eiffel Tower |
| 32 | Hisham's Palace | Hisham's Palace |
| 33 | Palacio Real de Madrid | Palacio Real de Madrid |
| 34 | Cologne Cathedral | Cologne Cathedral |
| 35 | Parthenon | Parthenon |
| 36 | Machu Pichu | Machu Pichu |
| 37 | Forbidden Palace | Forbidden Palace |
| 38 | Himeji Castle | Himeji Castle |
| 39 | Buddhist Stupa | Buddhist Stupa |
| 40 | Kremlin | Kremlin |

## Terrain Types

From audio ambient mapping and binary analysis:

| Value | Terrain | Ambient Sound |
|-------|---------|--------------|
| 0 | Ocean | AmbOcean |
| 1 | Grassland | AmbGrass |
| 2 | Plains | AmbPlain |
| 3 | Mountains | — |
| 4 | Forest | AmbForest |
| 5 | Desert | AmbDesert |
| 6 | Hills | — |
| 7 | Ice | AmbIcecap |
| — | Coast | AmbCoast |
| — | Fog | AmbFog |

## Scenario Options

From `Scenario.txt` (full game) and `TurnBaseScenario.txt` (turn-based):

### General

| Option | Type | Values | Default |
|--------|------|--------|---------|
| Starting Year | 31 | 4000 BC, 2000 BC, 0, 1000 AD, 2000 AD | 4000 BC |
| World Climate | 16 | Freezing, Cold, Standard, Warm, Hot | Standard |
| Starting Era | 14 | Current, Medieval, Industrial, Modern, All Techs | Current |
| Starting Size | 15 | Settlers, 1 city, 3 cities | Settlers |
| Starting Gold | 19 | 0, 100, 500, 1000 | 0 |

### Victory

| Option | Type | Values | Default |
|--------|------|--------|---------|
| Can Win By | 10 | Domination, Science, Economic, Culture | All (bitmask 15) |
| Quick Win | 11 | Off, Quick, Blitz | Off |
| No Space Race | 18 | On | Off |

### Resources

| Option | Type | Values | Default |
|--------|------|--------|---------|
| Resource Density | 3 | None, Sparse, Normal | Normal |
| Caravan Gold | 20 | Less, Standard, More | Standard |
| Max City Size | 7 | 8, 16, 32 | 32 |
| Great People Rate | 22 | Less, Standard, More | Standard |

### Technologies

| Option | Type | Values | Default |
|--------|------|--------|---------|
| Technology Rate | 4 | Slower, Current, Faster | Current |
| Upgrade Rate | 5 | Slower, Current, Faster | Current |
| Wonders Expire | 8 | Anyone, Anyone else, Never | Anyone |
| Initial Technologies | 13 | 0, 1, 2, 3 | 0 |

### Barbarians

| Option | Type | Values | Default |
|--------|------|--------|---------|
| Aggressive Barbarians | 0 | Less, Standard, More | Standard |
| Barbarian Occurrence | 1 | Less, Standard, More | Standard |
| Barbarians vs Villages | 2 | All friendly, Mixed, All barbarian | Mixed |

### Combat

| Option | Type | Values | Default |
|--------|------|--------|---------|
| Naval Support | 6 | None, Current, Doubled | Current |
| War and Peace | 9 | No war, Current, Permanent war | Current |
| +1 Unit Speed Bonus | 12 | On | Off |
| Unit Attack Bonus | 21 | 0, +1, +2 | 0 |

### Turn-Based Multiplayer Extras

| Option | Type | Values | Default |
|--------|------|--------|---------|
| Map Size | 23 | Big, Medium, Small | Medium |
| Production Rate | 25 | 1x, 2x, 3x | 1x |
| Fog of War | 24 | Normal, Show capital, No | Normal |
| Turn Number Limit | 26 | Unlimited, 100, 50 | Unlimited |

## Custom Maps

From `map_config.ini`:

| Index | File | Title | Players |
|-------|------|-------|---------|
| 0 | Earth.civscen | The World | 4 |
| 1 | Rivalry_2P.civscen | Rivalry | 2 |
| 2 | Squadron_4P.civscen | Squadron | 4 |
| 3 | TwistedIsle_2P.civscen | Twisted Isle | 2 |
| 4 | Cabinet_4P.civscen | Four Corners | 4 |

## Great People

From FamousNames_enu.txt (selection):

Ancient: Gilgamesh, Imhotep, Sargon, Cheops, Plato, Lao Tzu, Agamemnon, David, Solomon, Nebuchadnezzar, Homer, Aesop
Classical: Confucius, Pythagoras, Sophocles, Aristotle, Archimedes
Exploration: Marco Polo, Vasco da Gama, Leonardo DaVinci, Christopher Columbus
Industrial: James Watt, Eli Whitney, George Stephenson, Charles Babbage, Alexander G. Bell, Thomas Edison, Henry Ford
Modern: Marie Curie, Albert Einstein, Enrico Fermi, Wilbur Wright, Albert Schweitzer, Florence Nightingale
Cultural: J.S. Bach, Fyodor Dostoevsky, Salvador Dali, W.R. Hearst, Leopold Stokowski

## Setup Data Structure

From CcSetupData.c decompilation:

| Offset | Size | Field |
|--------|------|-------|
| 0x4 | 4 | Game type (single/multi) |
| 0x8-0x36 | 6 x FStringA | Player names |
| 0x38-0x68 | varies | Civilization choices per player |
| 0x50 | — | Handicap settings |
| 0x68 | — | Team settings |
| 0x80-0x85 | 6 x 1 | Ready status flags |
| 0x9c | — | Difficulty (4=standard, 2=alternate) |
| 0xa8 | 4 | Map seed (procedural generation) |
| 0xac | 4 | Map index within seed |
| 0xb0 | — | Civilization selection index |
