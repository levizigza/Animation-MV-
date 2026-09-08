"""MIR Audio Lab — BPM, beats, sections, energy for craft-synced animation."""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from mvm.schemas.models import Beatmap, Section


SECTION_LABELS = ("intro", "verse", "prechorus", "chorus", "bridge", "outro")


def _downsample_curve(times: np.ndarray, values: np.ndarray, max_points: int = 400) -> list[dict[str, float]]:
    if len(times) == 0:
        return []
    if len(times) <= max_points:
        return [{"t": float(t), "v": float(v)} for t, v in zip(times, values)]
    idx = np.linspace(0, len(times) - 1, max_points).astype(int)
    return [{"t": float(times[i]), "v": float(values[i])} for i in idx]


def _estimate_sections(
    duration: float,
    bpm: float,
    energy_times: np.ndarray,
    energy_vals: np.ndarray,
) -> list[Section]:
    """Heuristic structure from energy novelty — good enough for planning."""
    if duration <= 0:
        return [Section(name="intro", start=0.0, end=0.0, energy=0.0)]

    # Prefer ~8 musical bars per section when BPM is sane
    bar_sec = (60.0 / max(bpm, 1.0)) * 4.0
    target_len = max(8.0, min(24.0, bar_sec * 8.0))
    n_sections = max(3, min(10, int(round(duration / target_len))))
    edges = np.linspace(0.0, duration, n_sections + 1)

    # Place stronger boundaries near energy peaks in the middle third of candidates
    if len(energy_vals) > 8:
        novelty = np.abs(np.diff(energy_vals, prepend=energy_vals[0]))
        for i in range(1, n_sections):
            lo = edges[i] - target_len * 0.25
            hi = edges[i] + target_len * 0.25
            mask = (energy_times >= lo) & (energy_times <= hi)
            if mask.any():
                local_t = energy_times[mask]
                local_n = novelty[mask]
                edges[i] = float(local_t[int(np.argmax(local_n))])

    edges = np.clip(np.sort(edges), 0.0, duration)
    edges[0] = 0.0
    edges[-1] = duration

    # Label by relative energy + position
    sections: list[Section] = []
    energies: list[float] = []
    for i in range(len(edges) - 1):
        start, end = float(edges[i]), float(edges[i + 1])
        mask = (energy_times >= start) & (energy_times < end)
        e = float(np.mean(energy_vals[mask])) if mask.any() else 0.5
        energies.append(e)

    e_arr = np.array(energies)
    e_norm = (e_arr - e_arr.min()) / (np.ptp(e_arr) + 1e-8)
    chorus_idx = int(np.argmax(e_norm)) if len(e_norm) else 0

    for i, (start, end, e, en) in enumerate(
        zip(edges[:-1], edges[1:], energies, e_norm)
    ):
        if i == 0:
            name = "intro"
        elif i == len(energies) - 1:
            name = "outro"
        elif i == chorus_idx or (en > 0.75 and abs(i - chorus_idx) <= 1):
            name = "chorus"
        elif en < 0.35:
            name = "bridge" if i > chorus_idx else "verse"
        elif i + 1 == chorus_idx:
            name = "prechorus"
        else:
            name = "verse"
        sections.append(Section(name=name, start=float(start), end=float(end), energy=float(e)))
    return sections


def analyze_audio(path: Path | str, sr: int = 22050) -> Beatmap:
    path = Path(path)
    y, loaded_sr = librosa.load(path, sr=sr, mono=True)
    duration = float(librosa.get_duration(y=y, sr=loaded_sr))

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=loaded_sr)
    bpm = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=loaded_sr)
    # Approximate downbeats every 4 beats
    downbeat_times = beat_times[::4] if len(beat_times) else np.array([])

    onset_env = librosa.onset.onset_strength(y=y, sr=loaded_sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=loaded_sr, units="frames"
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=loaded_sr)

    # RMS energy + spectral flux
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    rms_t = librosa.frames_to_time(np.arange(len(rms)), sr=loaded_sr, hop_length=hop)
    rms_n = (rms - rms.min()) / (np.ptp(rms) + 1e-8)

    S = np.abs(librosa.stft(y, hop_length=hop))
    flux = np.sqrt(np.sum(np.diff(S, axis=1) ** 2, axis=0))
    flux = np.concatenate([[0.0], flux])
    flux_n = (flux - flux.min()) / (np.ptp(flux) + 1e-8)
    flux_t = librosa.frames_to_time(np.arange(len(flux_n)), sr=loaded_sr, hop_length=hop)

    sections = _estimate_sections(duration, bpm, rms_t, rms_n)

    return Beatmap(
        duration=duration,
        sample_rate=int(loaded_sr),
        bpm=round(bpm, 3),
        beat_times=[float(t) for t in beat_times],
        downbeat_times=[float(t) for t in downbeat_times],
        onset_times=[float(t) for t in onset_times],
        sections=sections,
        energy_curve=_downsample_curve(rms_t, rms_n),
        spectral_flux=_downsample_curve(flux_t, flux_n),
    )
