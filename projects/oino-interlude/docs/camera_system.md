# Camera system — Oino (Interlude)

**System:** `OINO_CAMERA_SYSTEM`  
**Shots:** 22 (19 hero)  
**CSV:** [`shot_list.csv`](shot_list.csv)

## Hard rules

- Avoid constant aerial tours: `True`
- Avoid aggressive camera shake: `True`
- Avoid cuts only for environment detail: `True`
- Protect table performance: `True`
- Title card still: `True`

## Camera language

### attic

- **Framing:** close domestic framing with glimpses downward toward the sister
- **Movement:** small, human; eyeline dips to stairs/floor
- **Must not:** aerial attic tour; shock cut to sister face as scare

### archive

- **Framing:** slow lateral movement, frames within frames, partial faces
- **Movement:** lateral drift / push into documents
- **Must not:** orbiting showcase of props

### steam

- **Framing:** low human perspective with machinery above and around workers
- **Movement:** grounded track; height stays with bodies
- **Must not:** crane over factory for spectacle only

### electric

- **Framing:** wider compositions showing relief and absence together
- **Movement:** slow widen or locked wide
- **Must not:** shake on power-up sting

### digital

- **Framing:** reflections and flattened screens that make Oino watch herself
- **Movement:** locked or micro push into glass
- **Must not:** glitch-horror whip pans

### zone

- **Framing:** patient movement, uncertain depth, empty space after people leave
- **Movement:** patient; hold empty after exit
- **Must not:** aggressive shake; explainer moves

### table

- **Framing:** restrained two-shots and close-ups that protect performance
- **Movement:** minimal; saved positions over roaming
- **Must not:** constant cutaways that break acting

### return

- **Framing:** opening angles repeated with changed behaviour
- **Movement:** echo attic/door angles; behaviour carries the change
- **Must not:** new spectacle language that abandons the open

### title_card

- **Framing:** still frame, no decorative trailer motion
- **Movement:** none
- **Must not:** Ken Burns; parallax trailer drift; coloured gel wash

## Hero shots

| Shot | Label | Lens | Priority | Purpose |
|------|-------|------|----------|---------|
| `SH010_SISTER_CALL` | sister calling Oino | 35mm | HERO | Invitation arrives; domestic closeness with a glimpse toward the sister she will refuse. |
| `SH020_FATHERS_RECORDING` | father's unfinished recording | 50mm | HERO | Need crystallizes in the unfinished melody — intimate, not spectacular. |
| `SH030_ARCHIVE_BOX_OINO` | archive box marked OINO | 40mm | HERO | Name inheritance as object — discovery without classroom diagram. |
| `SH041_ANCESTOR_IGNORES_DINNER` | ancestor ignoring the call to dinner | 28mm | HERO | Embarrassing ordinary refusal — implication, not sermon. |
| `SH031_FAMILY_LINE_DOCUMENT` | family-line document | 50mm | HERO | Lineage as worn paper — artistic adaptation, not universal claim. |
| `SH040_ANCESTOR_SLEEVE` | ancestor repairing the sleeve | 35mm | HERO | Care as ordinary labour — watcher still able to mend. |
| `SH050_FACTORY_GATE` | first factory-gate transition | 24mm | HERO | Doorway becomes factory gate — history through bodies, not labels. |
| `SH051_ELECTRIC_HOUSEHOLD_TIME` | electricity returning time to a household | 28mm | HERO | Benefit and cost together: relief of light, absence still present. |
| `SH060_SYNTHETIC_VOICE` | person using a synthetic voice | 40mm | HERO | Care through technology — not memorial ghost; living person uses the tool. |
| `SH061_OINO_SEES_OWN_RECORDING` | Oino seeing her own recording | 50mm | HERO | She becomes watcher of her own controlled archive — shadow foreshadow without scare. |
| `SH070_TABLE_GLIMPSE` | first glimpse of the table | 35mm | HERO | Destination appears before arrival — ordinary sacred ahead; Zone unexplained. |
| `SH080_WARM_TWO_SHOT` | father and Oino in the warm two-shot | 40mm | HERO | Genuine comfort — why she stays; protect performance. |
| `SH090_HAND_RESET_CONTROL` | Oino's hand on the reset control | 55mm | HERO | Shadow as merciful grip — dread from control, not horror light. |
| `SH100_SISTER_REFLECTION` | sister in the table reflection | 45mm | HERO | Cost already present — loneliness in progress, not later warning. |
| `SH110_RELEASE_CONTROL` | Oino releasing the control | 50mm | HERO | Holy-fool hinge — ordinary costly release. |
| `SH120_ACCEPTS_BOWL` | Oino accepting the bowl | 40mm | HERO | Nourishment accepted; presence without demanding forgiveness. |
| `SH121_SISTER_CHANGES_MELODY` | sister changing the melody | 50mm | HERO | Real creative contribution — living variation, not symbolic child. |
| `SH122_OPEN_DOORWAY` | open doorway | 28mm | HERO | Final story image — invitation kept open (answers closed attic). |
| `SH130_TITLE_CARD` | title card | 50mm | HERO | Final film image — still; no trailer motion. |

## All shots

See [`shot_list.csv`](shot_list.csv) for camera, lens, focus target, duration, emotional purpose, and render priority.

## Rebuild

```text
python scripts/build_camera_system.py
python scripts/build_camera_system.py --check-animatic
```

