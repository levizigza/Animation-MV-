# Final delivery report — Oino (Interlude)

**Created:** 2026-09-07T23:49:26.116938+00:00  
**Title card:** `One Of Gods Fools`  
**Date:** `December 10, 2026`  
**Apostrophe in Gods:** `False`

## Locked ending (every output)

1. open doorway
2. final living melody
3. original recording reaching its imperfect ending
4. fade to title card
5. One Of Gods Fools
6. December 10, 2026

## Technical

- **Frame rate:** 24
- **Resolution:** 1920×1080
- **Duration:** 131.134979 s
- **Frame count:** 3148
- **Colour management:** display `sRGB`, view `AgX`, look `None`
- **Render engine:** `BLENDER_EEVEE_NEXT`
- **Audio files used:** `audio/master.wav`
- **Title-card frame range:** 3051–3148
- **Subtitle status:** clean_only_no_subtitle_approval

## Outputs

| Name | Path | Notes |
|------|------|-------|
| `clean_version_without_subtitles` | `renders/final/delivery/movies/OINO_DELIVERY_CLEAN.mp4` | Full audio; locked ending; no subtitles |
| `high_quality_delivery_movie` | `renders/final/delivery/movies/OINO_DELIVERY_HQ.mov` | Approved audio muxed; locked ending |
| `h264_review_movie_with_audio` | `renders/final/delivery/movies/OINO_DELIVERY_REVIEW_H264.mp4` | created |
| `subtitle_version` | `—` | No subtitle approval — clean version only |
| `lossless_or_image_sequence_master` | `renders/final/delivery/master_image_sequence/oino_master_%05d.png` | PNG sequence covering doorway→title-card end; audio remains source master.wav |
| `ten_still_frames` | `renders/final/delivery/stills` | created |
| `title_card_still` | `renders/final/delivery/stills/title_card_still.png` | One Of Gods Fools / December 10, 2026 |

## Warnings

- None

## Checksums (SHA-256)

- `clean_version_without_subtitles`: `b0af3b8aa90959b652355f45e095ccc6fc003c9713936b542f9c8a55efbae83e`
- `high_quality_delivery_movie`: `395df9a8e4d6fe9bc84e263082700fbca7c506f961168aaeb919b4a43a96ec93`
- `h264_review_movie_with_audio`: `fd4ce0eed6fdfed02b79c926a944b837f85c23961a6dc95ef3b0d1a0a0d4b6de`
- `title_card_still`: `08f72ba7d984eab7f5347baed0775c4a8ce53368682a5e63dd3f16e0d3ed4562`
- `still_01_f03021.png`: `c7deb3c26219fff71ed973a48db52241282bc77c613a39c5c103c8361a195111`
- `still_02_f03035.png`: `f2a721675adf7b1c28abd22322cff8df52bda733cc9f2299ab648e0ed56785a6`
- `still_03_f03047.png`: `f2a721675adf7b1c28abd22322cff8df52bda733cc9f2299ab648e0ed56785a6`
- `still_04_f03050.png`: `f2a721675adf7b1c28abd22322cff8df52bda733cc9f2299ab648e0ed56785a6`
- `still_05_f03051.png`: `08f72ba7d984eab7f5347baed0775c4a8ce53368682a5e63dd3f16e0d3ed4562`
- `still_06_f03059.png`: `08f72ba7d984eab7f5347baed0775c4a8ce53368682a5e63dd3f16e0d3ed4562`
- `still_07_f03063.png`: `08f72ba7d984eab7f5347baed0775c4a8ce53368682a5e63dd3f16e0d3ed4562`
- `still_08_f03099.png`: `08f72ba7d984eab7f5347baed0775c4a8ce53368682a5e63dd3f16e0d3ed4562`
- `still_09_f03142.png`: `08f72ba7d984eab7f5347baed0775c4a8ce53368682a5e63dd3f16e0d3ed4562`
- `still_10_f03148.png`: `08f72ba7d984eab7f5347baed0775c4a8ce53368682a5e63dd3f16e0d3ed4562`
- `title_card_still.png`: `08f72ba7d984eab7f5347baed0775c4a8ce53368682a5e63dd3f16e0d3ed4562`

## Preservation

- Source audio, blend files, scripts, caches, and prior renders were **not** deleted.

## Rebuild

```text
python scripts/final_delivery.py
```

