from pathlib import Path

import numpy as np
import soundfile as sf


def write_demo_wav(path: Path, duration: float = 12.0, sr: int = 22050, bpm: float = 120.0) -> Path:
    """Synthetic track with beats for smoke tests."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Kick on quarters + rising energy
    beat = 60.0 / bpm
    kick = np.zeros_like(t)
    for i, ti in enumerate(t):
        phase = ti % beat
        if phase < 0.05:
            kick[i] = np.sin(2 * np.pi * 60 * phase) * (1 - phase / 0.05)
    tone = 0.15 * np.sin(2 * np.pi * 220 * t) * (0.3 + 0.7 * (t / duration))
    hi = 0.08 * np.sin(2 * np.pi * 880 * t) * ((t % (beat / 2)) < 0.03)
    y = np.clip(kick * 0.9 + tone + hi, -1, 1).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, y, sr)
    return path


if __name__ == "__main__":
    write_demo_wav(Path("projects/_fixtures/demo.wav"))
