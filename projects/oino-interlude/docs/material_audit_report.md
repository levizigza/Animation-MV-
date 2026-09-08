# Material audit report — Oino (Interlude)

**Library:** `OINO_MATERIAL_LIBRARY`  
**Missing images:** 33  
**Pink texture flags:** 0  
**Blend audit:** not run

## Categories

### missing_images (0)

_None._

### pink_textures (0)

_None._

### unsupported_nodes (0)

_None._

### disconnected_shaders (0)

_None._

### expensive_settings (0)

_None._

### other (42)

| Severity | Material | Detail |
|----------|----------|--------|
| `warn` | `MAT_WornWood` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_WornWood` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_WornWood` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_WetStone` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_WetStone` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_WetStone` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Rust` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Rust` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Rust` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_OxidizedMetal` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_OxidizedMetal` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_OxidizedMetal` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_OxidizedMetal` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_OldPaper` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_OldPaper` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Film` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Film` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_BlackGlass` | Expected image not on disk (placeholder ok until authored) |
| `info` | `MAT_BlackGlass` | Watch expensive feature in EEVEE: transmission |
| `info` | `MAT_BlackGlass` | transmission_weight=0.85 — keep samples modest in EEVEE |
| `warn` | `MAT_MonitorSurface` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_MonitorSurface` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_TranslucentSynthetic` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_TranslucentSynthetic` | Expected image not on disk (placeholder ok until authored) |
| `info` | `MAT_TranslucentSynthetic` | Watch expensive feature in EEVEE: transmission |
| `info` | `MAT_TranslucentSynthetic` | transmission_weight=0.7 — keep samples modest in EEVEE |
| `warn` | `MAT_Cloth` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Cloth` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Cloth` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Ceramic` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Ceramic` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Skin` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Skin` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_Skin` | Expected image not on disk (placeholder ok until authored) |
| `info` | `MAT_Skin` | Watch expensive feature in EEVEE: subsurface |
| `warn` | `MAT_VineLeaf` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_VineLeaf` | Expected image not on disk (placeholder ok until authored) |
| `warn` | `MAT_VineLeaf` | Expected image not on disk (placeholder ok until authored) |
| `info` | `MAT_Water` | Watch expensive feature in EEVEE: transmission |
| `info` | `MAT_Water` | transmission_weight=0.95 — keep samples modest in EEVEE |
| `info` | `—` | Pass --audit-blend <file.blend> to scan node trees |
| `info` | `—` | Pass --audit-blend <file.blend> to scan Material Output links |

## Rebuild

```text
python scripts/build_material_library.py
python scripts/build_material_library.py --audit-blend scenes/SCN_08_TABLE_ROOM.blend
```

