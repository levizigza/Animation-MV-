"""Explicit spacing curves — never silent-smooth."""

from __future__ import annotations

from mvm.schemas.domain import SpacingCurve, SpacingMode


def progress_at(curve: SpacingCurve, t: float) -> float:
    """Map normalized time t in [0,1] to spacing progress in [0,1].

    Modes are named and deterministic. CUSTOM uses piecewise-linear
    authored control points only — no auto bezier / hermite fit.
    """
    t = max(0.0, min(1.0, float(t)))
    mode = curve.mode

    if mode == SpacingMode.LINEAR:
        return t

    if mode == SpacingMode.SLOW_OUT:
        # More drawings near the start (ease away from outgoing pose)
        return t * t

    if mode == SpacingMode.SLOW_IN:
        # More drawings near the end (ease into incoming pose)
        u = 1.0 - t
        return 1.0 - u * u

    if mode == SpacingMode.SLOW_IN_OUT:
        # Classic smoothstep — only when this mode is chosen explicitly
        return t * t * (3.0 - 2.0 * t)

    if mode == SpacingMode.STEPPED:
        n = max(1, curve.step_count)
        # Quantize into n equal plateaus (no interpolation between steps)
        if t >= 1.0:
            return 1.0
        bucket = int(t * n)
        return bucket / float(n)

    if mode == SpacingMode.CUSTOM:
        pts = sorted(curve.control_points, key=lambda p: p[0])
        if not pts:
            raise ValueError("CUSTOM curve has no control points")
        if t <= pts[0][0]:
            return pts[0][1]
        for i in range(len(pts) - 1):
            t0, v0 = pts[i]
            t1, v1 = pts[i + 1]
            if t0 <= t <= t1:
                if t1 == t0:
                    return v1
                u = (t - t0) / (t1 - t0)
                return v0 + u * (v1 - v0)
        return pts[-1][1]

    raise ValueError(f"Unknown spacing mode: {mode}")


def sample_progress(curve: SpacingCurve, sample_count: int) -> list[tuple[float, float]]:
    """Return explicit (t, progress) samples for inspection — not a render."""
    if sample_count < 2:
        raise ValueError("sample_count must be >= 2")
    out: list[tuple[float, float]] = []
    for i in range(sample_count):
        t = i / float(sample_count - 1)
        out.append((t, progress_at(curve, t)))
    return out


def reconstruct_custom_from_samples(
    samples: list[tuple[float, float]],
    *,
    curve_id: str,
    source=None,
) -> SpacingCurve:
    """Rebuild a CUSTOM curve from authored samples (piecewise-linear roundtrip)."""
    from mvm.schemas.domain import TimingSource

    if len(samples) < 2:
        raise ValueError("Need >= 2 samples to reconstruct a CUSTOM curve")
    return SpacingCurve(
        id=curve_id,
        mode=SpacingMode.CUSTOM,
        control_points=[(float(t), float(v)) for t, v in samples],
        source=source or TimingSource.AUTHORED,
        notes="Reconstructed from inspectable samples (piecewise-linear)",
    )
