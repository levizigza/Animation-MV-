# Oino archive — project notes

## Scene

`SCN_02_OINO_ARCHIVE` — great-great-grandfather's archive as a place of
**preservation and transformation**, not a trophy room of bloodline prestige.

## Genealogy (artistic canon)

The on-screen family line

**DIONYSUS → STAPHYLUS → RHOEO → ANIUS → OINO**

is **project canon for One Of God's Fools / Oino (Interlude)**. It is an artistic
adaptation. Variant mythic traditions exist. This insert must **not** read as:

- a claim that one genealogy is universally correct
- biological superiority
- automatic wisdom inherited by blood

The insert lasts **under two seconds**, looks like a **damaged family document**
(obscured, possibly mistranslated, mixed materials) — never a classroom diagram.

## Footage ethics

| Label | Meaning |
|-------|---------|
| Ancestor-origin plates | Suggest material the watcher personally shot / kept |
| Reconstructed plates | Clearly marked reconstructed / later-assembled imagery |

Never blur those categories into one “authentic archive” look.

## Broken thyrsus

`PROP_BrokenThyrsus_Mech` is a **mechanical / worn object** that only *resembles*
a broken thyrsus. It must not become a costume prop or literal god attribute.

## Water stain

`FX_WaterStain_ConditionalWine` reads as water damage in ordinary light; wine-like
amber only under `LIGHT_AmberReveal` (see transition `TR_STAIN_TO_AMBER`).

## Transitions (story, not VFX showreel)

1. Archive dust → steam  
2. Vine vein → cable  
3. Handwritten name → digital label  
4. Water stain → amber light  
5. Film gate → factory gate  
6. Oino's hand on the reel → crossing the threshold  

Build: `python scripts/build_oino_archive.py` · with Blender: `--write-blend`
