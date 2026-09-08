# Material library — Oino (Interlude)

**System:** `OINO_MATERIAL_LIBRARY`  
**Engine target:** `BLENDER_EEVEE_NEXT`  
**Pink placeholders allowed:** `False`  
**Dionysian not every surface red:** `True`

## Audit summary

- Missing images: **33** (expected until textures are authored)
- Pink texture flags: **0**
- Expensive watches: **4**

## Materials

| Id | Label | Roughness | Images expected | Missing |
|----|-------|-----------|-----------------|---------|
| `MAT_WornWood` | worn wood | 0.72 | 3 | 3 |
| `MAT_WetStone` | wet stone | 0.28 | 3 | 3 |
| `MAT_Rust` | rust | 0.85 | 3 | 3 |
| `MAT_OxidizedMetal` | oxidized metal | 0.55 | 4 | 4 |
| `MAT_OldPaper` | old paper | 0.9 | 2 | 2 |
| `MAT_Film` | film | 0.35 | 2 | 2 |
| `MAT_BlackGlass` | black glass | 0.05 | 1 | 1 |
| `MAT_MonitorSurface` | monitor surfaces | 0.2 | 2 | 2 |
| `MAT_TranslucentSynthetic` | translucent synthetic materials | 0.25 | 2 | 2 |
| `MAT_Cloth` | cloth | 0.95 | 3 | 3 |
| `MAT_Ceramic` | ceramic | 0.35 | 2 | 2 |
| `MAT_Skin` | skin | 0.45 | 3 | 3 |
| `MAT_VineLeaf` | vine and leaf | 0.65 | 3 | 3 |
| `MAT_Water` | water | 0.02 | 0 | 0 |

## Material recipes

### `MAT_WornWood` — worn wood

- **Category:** organic_surface
- **Base color:** `[0.42, 0.29, 0.196, 1.0]`
- **Roughness / metallic:** 0.72 / 0.0
- **Links:** `TABLE_WornSurface`, `TABLE_WARMTH`
- **Expected images:**
  - `assets/materials/worn_wood_albedo.png` (missing)
  - `assets/materials/worn_wood_roughness.png` (missing)
  - `assets/materials/worn_wood_normal.png` (missing)

### `MAT_WetStone` — wet stone

- **Category:** organic_surface
- **Base color:** `[0.35, 0.36, 0.38, 1.0]`
- **Roughness / metallic:** 0.28 / 0.0
- **Links:** `ZONE_ShallowWater`, `ZONE_REFLECTION`
- **Expected images:**
  - `assets/materials/wet_stone_albedo.png` (missing)
  - `assets/materials/wet_stone_roughness.png` (missing)
  - `assets/materials/wet_stone_normal.png` (missing)

### `MAT_Rust` — rust

- **Category:** metal
- **Base color:** `[0.545, 0.271, 0.075, 1.0]`
- **Roughness / metallic:** 0.85 / 0.55
- **Links:** `STEAM_SOOT`, `ARCH_IndustrialFrame_A`
- **Expected images:**
  - `assets/materials/rust_albedo.png` (missing)
  - `assets/materials/rust_roughness.png` (missing)
  - `assets/materials/rust_metallic.png` (missing)

### `MAT_OxidizedMetal` — oxidized metal

- **Category:** metal
- **Base color:** `[0.29, 0.306, 0.322, 1.0]`
- **Roughness / metallic:** 0.55 / 0.8
- **Links:** `STEAM_SOOT`, `ZONE_RootMachine`
- **Expected images:**
  - `assets/materials/oxidized_metal_albedo.png` (missing)
  - `assets/materials/oxidized_metal_roughness.png` (missing)
  - `assets/materials/oxidized_metal_metallic.png` (missing)
  - `assets/materials/oxidized_metal_normal.png` (missing)

### `MAT_OldPaper` — old paper

- **Category:** archive
- **Base color:** `[0.91, 0.875, 0.815, 1.0]`
- **Roughness / metallic:** 0.9 / 0.0
- **Links:** `OINO_ARCHIVE`, `ATTIC_DUST`
- **Expected images:**
  - `assets/materials/old_paper_albedo.png` (missing)
  - `assets/materials/old_paper_roughness.png` (missing)

### `MAT_Film` — film

- **Category:** archive
- **Base color:** `[0.12, 0.1, 0.08, 1.0]`
- **Roughness / metallic:** 0.35 / 0.05
- **Links:** `MOTIF_RECORDING`, `OINO_ARCHIVE`
- **Expected images:**
  - `assets/materials/film_albedo.png` (missing)
  - `assets/materials/film_alpha.png` (missing)

### `MAT_BlackGlass` — black glass

- **Category:** digital
- **Base color:** `[0.02, 0.025, 0.03, 1.0]`
- **Roughness / metallic:** 0.05 / 0.0
- **Links:** `DIGITAL_COLD`, `ECHO_MASK_BLACK_GLASS`
- **Expected images:**
  - `assets/materials/black_glass_roughness.png` (missing)

### `MAT_MonitorSurface` — monitor surfaces

- **Category:** digital
- **Base color:** `[0.05, 0.08, 0.07, 1.0]`
- **Roughness / metallic:** 0.2 / 0.3
- **Links:** `DIGITAL_COLD`
- **Expected images:**
  - `assets/materials/monitor_emission.png` (missing)
  - `assets/materials/monitor_roughness.png` (missing)

### `MAT_TranslucentSynthetic` — translucent synthetic materials

- **Category:** synthetic
- **Base color:** `[0.85, 0.9, 0.92, 1.0]`
- **Roughness / metallic:** 0.25 / 0
- **Links:** `ELECTRIC_WARMTH`, `DIGITAL_COLD`
- **Expected images:**
  - `assets/materials/translucent_synthetic_albedo.png` (missing)
  - `assets/materials/translucent_synthetic_alpha.png` (missing)

### `MAT_Cloth` — cloth

- **Category:** fabric
- **Base color:** `[0.769, 0.722, 0.659, 1.0]`
- **Roughness / metallic:** 0.95 / 0.0
- **Links:** `TABLE_WARMTH`
- **Note:** Wine cloth only as optional edge accent — not every fabric.
- **Expected images:**
  - `assets/materials/cloth_albedo.png` (missing)
  - `assets/materials/cloth_roughness.png` (missing)
  - `assets/materials/cloth_normal.png` (missing)

### `MAT_Ceramic` — ceramic

- **Category:** props
- **Base color:** `[0.92, 0.9, 0.88, 1.0]`
- **Roughness / metallic:** 0.35 / 0.0
- **Links:** `PROP_Bowl`, `PROP_Cup`, `MOTIF_BOWL_TABLE`
- **Expected images:**
  - `assets/materials/ceramic_albedo.png` (missing)
  - `assets/materials/ceramic_roughness.png` (missing)

### `MAT_Skin` — skin

- **Category:** character
- **Base color:** `[0.831, 0.647, 0.455, 1.0]`
- **Roughness / metallic:** 0.45 / 0.0
- **Links:** `TABLE_WARMTH`, `PROXY_Oino_Head`
- **Expected images:**
  - `assets/materials/skin_albedo.png` (missing)
  - `assets/materials/skin_roughness.png` (missing)
  - `assets/materials/skin_normal.png` (missing)

### `MAT_VineLeaf` — vine and leaf

- **Category:** organic_growth
- **Base color:** `[0.25, 0.4, 0.18, 1.0]`
- **Roughness / metallic:** 0.65 / 0.0
- **Links:** `MOTIF_VINE_WATER`, `TABLE_VineLeg`, `ECHO_IVY_THROUGH_MACHINE`
- **Expected images:**
  - `assets/materials/vine_leaf_albedo.png` (missing)
  - `assets/materials/vine_leaf_alpha.png` (missing)
  - `assets/materials/vine_leaf_normal.png` (missing)

### `MAT_Water` — water

- **Category:** liquid
- **Base color:** `[0.15, 0.25, 0.35, 1.0]`
- **Roughness / metallic:** 0.02 / 0.0
- **Links:** `ZONE_ShallowWater`, `MOTIF_VINE_WATER`, `ZONE_REFLECTION`
- **Note:** May briefly resemble wine under DIONYSUS_AMBER_RED — never a literal magic trick.

## Rebuild

```text
python scripts/build_material_library.py
```

Audit detail: [`material_audit_report.md`](material_audit_report.md)

