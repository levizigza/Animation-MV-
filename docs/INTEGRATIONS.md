# External craft references

**Principle:** The engine does not manufacture “great animation.” Integrations create
conditions for meaningful human decisions — phonetics, visual references, music
metadata, palette exploration, lyrics for hold planning — with attribution and
human accept. Nothing is applied as final automatically.

Source list curated from [public-apis](https://github.com/public-apis/public-apis).

| Provider | Category | Auth | Craft use |
|----------|----------|------|-----------|
| Free Dictionary | Dictionaries | No | Dialogue phonetics / acting |
| Art Institute of Chicago | Art & Design | No | PD visual refs → notebooks |
| Metropolitan Museum | Art & Design | No | Additional visual refs |
| MusicBrainz | Music | No | Recording credits / context |
| Colormind | Art & Design | No | Color-script suggestions |
| Lyrics.ovh | Music | No | Best-effort lyrics (unreliable) |

**Hard rules**

- `applied_as_final=False` always on `ExternalReference`
- `human_accepted` required before notebook attach
- Provenance recorded on fetch / accept / attach
- Living-artist style prompts remain forbidden (existing guardrails)
- Local MIR remains beat authority (MusicBrainz does not rewrite timing)

CLI: `mvm refs catalog|dictionary|art|music|palette|lyrics|accept|list`
