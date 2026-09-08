"""X-sheet builder — keys, holds, smears from beatmap + cel policy."""

from __future__ import annotations

from mvm.cel.masters import load_masters_rules, load_style_pack
from mvm.cel.timing import exposure_step, frames_for_duration, time_to_frame
from mvm.schemas.models import Beatmap, Shot, XSheet, XSheetCell


def build_xsheet_for_shot(shot: Shot, beatmap: Beatmap, fps: int = 24) -> XSheet:
    pack = load_style_pack(shot.cel.masters_pack)
    rules = load_masters_rules(pack.id)
    end_frame = frames_for_duration(shot.duration, fps)
    step = exposure_step(shot.cel.exposure)

    # Candidate key times inside shot from beats/onsets/downbeats
    key_times: list[float] = []
    sources = list(beatmap.downbeat_times) + list(beatmap.beat_times)
    if shot.cel.smear_on_accents:
        sources += list(beatmap.onset_times)
    for t in sources:
        if shot.start <= t < shot.end:
            key_times.append(t)
    key_times = sorted(set(round(t, 4) for t in key_times))

    # Thin keys for limited / held modes
    mode = shot.cel.mode
    if mode == "held_atmosphere" and key_times:
        key_times = key_times[:: max(2, len(key_times) // 3 or 1)]
    elif mode == "limited" and len(key_times) > 6:
        key_times = key_times[::2]

    key_frames = sorted(
        {
            min(end_frame, max(1, time_to_frame(t, fps, shot.start)))
            for t in key_times
        }
        | {1, end_frame}
    )

    # Accent frames for smears (high energy / chorus)
    smear_frames: set[int] = set()
    if shot.cel.smear_on_accents and shot.cel.smear_density > 0:
        onset_in_shot = [t for t in beatmap.onset_times if shot.start <= t < shot.end]
        density = shot.cel.smear_density * pack.smear_bias
        take = max(1, int(len(onset_in_shot) * density)) if onset_in_shot else 0
        for t in onset_in_shot[:take]:
            smear_frames.add(min(end_frame, max(1, time_to_frame(t, fps, shot.start))))

    cells: list[XSheetCell] = []
    layers = ["character", "fx", "bg"]

    # Character layer: keys + holds + inbetweens on exposure grid
    last_key = 1
    pose_i = 0
    for f in range(1, end_frame + 1):
        if f in key_frames:
            pose_i += 1
            cells.append(
                XSheetCell(
                    frame=f,
                    layer="character",
                    exposure="key",
                    pose_id=f"pose_{pose_i:02d}",
                    notes="extreme" if f in (1, end_frame) else "accent",
                )
            )
            last_key = f
        elif f in smear_frames:
            cells.append(
                XSheetCell(
                    frame=f,
                    layer="character",
                    exposure="smear",
                    pose_id=f"smear_{f}",
                    notes="impact smear",
                )
            )
        elif (f - last_key) % step == 0 and mode == "full":
            cells.append(
                XSheetCell(
                    frame=f,
                    layer="character",
                    exposure="inbetween",
                    pose_id=None,
                    notes="crafted inbetween",
                )
            )
        elif (f - last_key) == max(1, step // 2) and mode != "held_atmosphere":
            cells.append(
                XSheetCell(
                    frame=f,
                    layer="character",
                    exposure="breakdown",
                    pose_id=None,
                    notes="arc breakdown",
                )
            )
        else:
            cells.append(
                XSheetCell(
                    frame=f,
                    layer="character",
                    exposure="hold",
                    pose_id=None,
                    notes="held drawing",
                )
            )

    # FX layer: smears / blanks
    for f in range(1, end_frame + 1):
        if f in smear_frames:
            cells.append(
                XSheetCell(
                    frame=f,
                    layer="fx",
                    exposure="smear",
                    notes="speed lines / drybrush",
                )
            )
        else:
            cells.append(XSheetCell(frame=f, layer="fx", exposure="blank"))

    # BG: mostly holds (camera may move in 3D)
    for f in range(1, end_frame + 1):
        cells.append(
            XSheetCell(
                frame=f,
                layer="bg",
                exposure="hold" if f == 1 or f % (step * 4) == 0 else "hold",
                notes="layout plate",
            )
        )

    return XSheet(
        shot_id=shot.id,
        fps=fps,
        start_frame=1,
        end_frame=end_frame,
        layers=layers,
        cells=cells,
        timing_chart={
            "mode": mode,
            "exposure": shot.cel.exposure,
            "step": step,
            "key_frames": key_frames,
            "smear_frames": sorted(smear_frames),
            "masters_pack": pack.id,
            "rules_summary": rules.get("principles", [])[:3],
        },
    )
