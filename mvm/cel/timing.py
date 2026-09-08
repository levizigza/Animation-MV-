"""Timing helpers for cel exposure and musical mapping."""

from __future__ import annotations


def exposure_step(exposure: str) -> int:
    return {"1s": 1, "2s": 2, "3s": 3}.get(exposure, 2)


def frames_for_duration(duration_sec: float, fps: int) -> int:
    return max(1, int(round(duration_sec * fps)))


def time_to_frame(t: float, fps: int, start: float = 0.0) -> int:
    return max(1, int(round((t - start) * fps)) + 1)
