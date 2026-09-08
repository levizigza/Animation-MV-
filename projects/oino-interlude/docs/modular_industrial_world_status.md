# Modular industrial world

**Scene:** `SCN_MODULAR_INDUSTRIAL_WORLD`  
**Intent:** One human world changing around the same needs — not four unrelated cities.

## Controls (0..1)

| Control | Value | Meaning |
|---------|-------|---------|
| `era_blend` | 0.500 | 0=water/timber/stone early industrial; 1=digital/possible futures dominant |
| `future_branch` | 0.050 | 0=historical continuum; 1=possible-futures modules assert |
| `organic_growth` | 0.100 | vine/moss/wear reclaiming structure |
| `dionysus_presence` | 0.300 | symbolic musical/visual echoes only — not a literal god set |

## Collection visibility (derived)

| Collection | Weight |
|------------|--------|
| `WORLD_DIGITAL` | 0.837 |
| `WORLD_DIONYSUS_ECHOES` | 0.300 |
| `WORLD_ELECTRIC` | 0.993 |
| `WORLD_ORGANIC_GROWTH` | 0.100 |
| `WORLD_POSSIBLE_FUTURES` | 0.050 |
| `WORLD_STEAM` | 0.945 |
| `WORLD_STRUCTURE` | 0.939 |
| `WORLD_WATER_AND_REFLECTIONS` | 0.574 |

## Persistent anchors (same human needs)

- Doorway: `ANCHOR_Doorway`
- Vertical beam (Babel-capable): `ANCHOR_VerticalBeam_BabelCore`
- Path: `ANCHOR_Path`
- Bowl: `ANCHOR_Bowl`
- Hand-level surface: `ANCHOR_HandSurface`

## Module groups

- **water_channels:** `MOD_WaterChannel_A`, `MOD_WaterChannel_B`
- **waterwheel:** `MOD_Waterwheel`
- **timber_beams:** `MOD_TimberBeam_A`, `MOD_TimberBeam_B`, `MOD_TimberBeam_C`
- **brick_and_stone:** `MOD_BrickWall_A`, `MOD_StoneBlock_A`, `MOD_StoneBlock_B`
- **steam_pipes:** `MOD_SteamPipe_A`, `MOD_SteamPipe_B`, `MOD_SteamPipe_C`
- **loom_and_belt:** `MOD_LoomFrame`, `MOD_BeltRun_A`, `MOD_BeltRun_B`
- **pressure_valves:** `MOD_Valve_A`, `MOD_Valve_B`
- **electrical_poles_lamps:** `MOD_Pole_A`, `MOD_Pole_B`, `MOD_Lamp_A`, `MOD_Lamp_B`
- **generators_cables:** `MOD_Generator`, `MOD_CableBundle_A`, `MOD_CableBundle_B`
- **assembly_line:** `MOD_AssemblyBay_A`, `MOD_AssemblyBay_B`
- **terminals_monitors:** `MOD_Terminal_A`, `MOD_Monitor_A`, `MOD_Monitor_B`
- **server_cooling:** `MOD_ServerRack_A`, `MOD_CoolingUnit_A`
- **assistive_communication:** `MOD_AssistiveComm_A`, `MOD_AssistiveComm_B`
- **medical_synthetic_voice:** `MOD_MedModule_A`, `MOD_SynthVoicePanel`
- **circulation:** `MOD_OldDoor_A`, `MOD_Ladder_A`, `MOD_Catwalk_A`, `MOD_Platform_A`, `MOD_Corridor_A`
- **babel_core:** `ANCHOR_VerticalBeam_BabelCore`

## Blender

- Target: `scenes/SCN_MODULAR_INDUSTRIAL_WORLD.blend`
- Status: **skipped**
- Detail: Pass --write-blend to create .blend

Rebuild: `python scripts/build_modular_industrial_world.py --write-blend`

