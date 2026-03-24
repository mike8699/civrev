# Game Constants

All values from `ccglobaldefines.xml` (Pregame FPK). These are the tunable parameters for the game engine.

## Version

| Constant | Value |
|----------|-------|
| CivConsoleGameVersion | 1.0 |
| CUR_XDK_VER (Xbox) | 6534 |

## Camera

| Constant | Value | Notes |
|----------|-------|-------|
| CAMERA_START_DISTANCE | 9000 | Initial zoom height |
| CAMERA_MIN_DISTANCE | 250 | Maximum zoom in |
| CAMERA_MAX_DISTANCE | 30000 | Maximum zoom out |
| CAMERA_MAX_TRAVEL_DISTANCE | 30000 | Jump threshold for wrapping |
| CAMERA_FIELD_OF_VIEW | 50 | Degrees |
| CAMERA_UPPER_PITCH | -90 | Top-down at max zoom |
| CAMERA_LOWER_PITCH | -50 | Angled at min zoom |
| CAMERA_BASE_YAW | -5 | Constant yaw offset |
| CAMERA_BATTLE_ZOOM_IN_DISTANCE | 3000 | |
| CAMERA_SHRINE_ZOOM_IN_DISTANCE | 2500 | |
| CAMERA_CITY_ZOOM_IN_DISTANCE | 5000 | |
| CAMERA_FOUND_CITY_ZOOM_IN_DISTANCE | 3500 | |
| CAMERA_SMALL_CITY_ZOOM_DISTANCE | 14240 | |
| CAMERA_BIG_CITY_ZOOM_DISTANCE | 12240 | |
| CAMERA_GLOBE_VIEW_ZOOM_DISTANCE | 30000 | |
| GLOBE_VIEW_CURVATURE | 33.0 | |

## World

| Constant | Value | Notes |
|----------|-------|-------|
| WORLD_CURVED | 1 | World curvature enabled |
| WORLD_CURVATURE | 57 | Curvature amount |
| WORLD_WIND_ANGLE | 275 | Degrees |

## Terrain

| Constant | Value | Notes |
|----------|-------|-------|
| MapList | (see [Map System](map-system.md)) | 277 valid map seeds |
| TERRAIN_TEXTURESCALE | 12 | Base terrain texture tiling |
| MOUNTAIN_TEXTURESCALE | 16 | Mountain texture tiling |
| TerrainZScale | 2.3 | Procedural terrain height scale |
| PBTerrainZScale | 7 | Pre-built terrain height scale |
| TreeScale | 3.4 | Tree model size |
| TreeAlpha | 100 | Tree opacity |
| TreeRandRangePercent | 10 | Size variation (%) |

### Terrain Textures by Climate

Each base terrain has warm/temperate/cold texture variants:

| Terrain | Warm | Temperate | Cold |
|---------|------|-----------|------|
| Grass | grass_warm.dds | grass_temperate.dds | grass_cold.dds |
| Plains | plains_warm.dds | plains_temperate.dds | plains_cold.dds |
| Desert | desert_warm.dds | desert_temperate.dds | desert_cold.dds |
| Hill | hill8x8.dds | (same) | (same) |
| Mountain | mountain8x8.dds | (same) | (same) |
| Ocean | ocean.dds | (same) | (same) |
| Coast | coast.dds | (same) | (same) |
| Ice | snow.dds | (same) | (same) |

### Terrain Blending Priority

Higher priority terrains render on top at tile boundaries:

| Terrain | Priority |
|---------|----------|
| None | 200 |
| Mountain | 120 |
| Hill | 110 |
| Ocean | 100 |
| Coast | 90 |
| Icecap | 80 |
| Plains (cold/temp/warm) | 42 / 41 / 40 |
| Grass (cold/temp/warm) | 32 / 31 / 30 |
| Desert (cold/temp/warm) | 22 / 21 / 20 |

### Clutter (Ground Cover)

| Terrain | Count | Scale Z | Scale XY | Alpha | Height |
|---------|-------|---------|----------|-------|--------|
| Grass | 32 | 42 | 96 | 70 | 0 |
| Plains | 30 | 35 | 124 | 50 | 8 |
| Ocean | 32 | 100 | 100 | 100 | 0 |
| Forest | 30 | 120 | 100 | 100 | 0 |

## Water

| Constant | Value | Notes |
|----------|-------|-------|
| WATER_HEIGHT | 85 | Sea level |
| WATER_SCALE | 17 | |
| ShallowWaterColor | #75ECEC | |
| DeepWaterColor | #477EB6 | |
| OceanAlpha | 100 | |
| CoastAlpha | 29 | |
| WaveWidth | 848 | |
| WaveHeight | 617 | |
| WaveSpeed | 80 | |
| WaveOpacity | 6 | |
| WaterCloudSpeed | 2 | |

### Pre-Built (DLC) Water Overrides

| Constant | Value |
|----------|-------|
| PBWATER_HEIGHT | 100 |
| PBShallowWaterColor | #0CF3F3 |
| PBDeepWaterColor | #3D57C0 |
| PBOceanAlpha | 92 |
| PBCoastAlpha | 60 |

## Rivers

| Constant | Value |
|----------|-------|
| ShallowRiverColor | #75ECEC |
| DeepRiverColor | #6AD1DD |
| RiverSpeed | 10 |
| RiverAlpha | 0 |
| RiverNoiseScale | 25 |
| RiverbedZOffset | 8 |
| RiverWaterZOffset | 10 |
| RoadZOffset | 4 |

## Units

| Constant | Value |
|----------|-------|
| UnitScale | 2.8 |
| WorkerScale | 2.5 |
| FidgetInterval | 11.0 seconds |
| FidgetChance | 0.03 |
| Enable Unit Trails | 0 (disabled) |

## Fog of War

| Constant | Value |
|----------|-------|
| FogSeenAlpha | 0.45 |
| FogNoVisibleAlpha | 1.0 |
| FogFadeTime | 0.75 |
| Solid Fog Color | #709BB4 |
| Solid Fog Density | 365 |
| Solid Fog Amplitude | 219 |
| Solid Fog Height from Ground | 1000 |
| Transparent Fog Color | #DCF5FF |
| Transparent Fog Density | 323 |
| Transparent Fog Amplitude | 80 |
| FOW LOD Transition | 67 |

## Shadows

| Constant | Value |
|----------|-------|
| ShadowOpacity | 76 |
| ShadowColor | #393F57 |
| ShadowLength | -100.0 |

## Distance Fog

| Context | Start | End | Color |
|---------|-------|-----|-------|
| Default | 6849 | 10959 | #607BFB |
| Trophy Room | 600 | 6500 | #0c2256 |
| Hall of Achievements | 600 | 6500 | #0c2256 |

## Weather

| Constant | Value |
|----------|-------|
| Number of Storms | 30 |
| Storm Rotation Speed | 15 |
| Storm Movement Speed | 10 |
| Storm Acceleration | 40 |
| Storm Frame Speed | 25 |
| Storm Number Frames | 8 |
| Weather Amplitude | 11 |
| Storm Size | 3 |

## Post-Processing

| Effect | Enabled | Notes |
|--------|---------|-------|
| HDR | Disabled | |
| Sepia | Disabled | |
| DOF | Enabled | Focal distance 7000, range 3000 |
| Motion Blur | Enabled | Scale 0.5 default, 0.7 city screen |
| Color Correction | Disabled | Brightness/contrast/saturation all 1.0 |
| Nuke | Disabled | |
| Combat DOF | Enabled | |

## Physics

| Constant | Value | Notes |
|----------|-------|-------|
| Gravity | -19.6 | |
| Static Friction | 30 | Divide by 100 = 0.30 |
| Dynamic Friction | 80 | Divide by 100 = 0.80 |
| Restitution | 40 | Divide by 100 = 0.40 |

## Audio

| Constant | Value |
|----------|-------|
| Dynamic Resident Audio Buffer Size | 4,194,304 (4 MB) |
| Audio Listener Zoom Out Starting Height | 3000 |
| WorldSoundscape City Radius | 3 tiles |
| WorldSoundscape Crossfade Time | 1.0 seconds |
