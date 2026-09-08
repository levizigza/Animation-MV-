import { useEffect, useRef, useState } from "react";
import type { CraftBuildEvent, FramesManifest } from "./types";

type Props = {
  slug: string | null;
  shotId: string | null;
  manifest: FramesManifest | null;
  buildEvents: CraftBuildEvent[];
  crafting: boolean;
  engine: string | null;
  currentFrame: number;
  onSeekFrame: (frameIndex0: number) => void;
};

export default function CinemaStage({
  slug,
  shotId,
  manifest,
  buildEvents,
  crafting,
  engine,
  currentFrame,
  onSeekFrame,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const frameRef = useRef(currentFrame);
  const onSeekRef = useRef(onSeekFrame);
  frameRef.current = currentFrame;
  onSeekRef.current = onSeekFrame;

  const hasMp4 = Boolean(manifest?.has_mp4 && manifest.preview_url);
  const frames = manifest?.frames ?? [];
  const fps = manifest?.fps || 24;
  const progressEvt = [...buildEvents].reverse().find((e) => e.type === "frame");
  const progress =
    crafting && progressEvt?.progress != null
      ? progressEvt.progress
      : crafting
        ? 0.05
        : null;

  useEffect(() => {
    if (hasMp4 || !playing || frames.length === 0) return;
    const interval = 1000 / fps;
    let last = performance.now();
    let id = 0;
    const tick = (now: number) => {
      if (now - last >= interval) {
        last = now;
        const next = (frameRef.current + 1) % frames.length;
        onSeekRef.current(next);
      }
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [hasMp4, playing, frames.length, fps]);

  useEffect(() => {
    if (!hasMp4 || !videoRef.current || !manifest?.preview_url) return;
    const url = `${manifest.preview_url}?v=${manifest.frame_count}`;
    if (videoRef.current.getAttribute("data-src") !== url) {
      videoRef.current.setAttribute("data-src", url);
      videoRef.current.src = url;
    }
  }, [hasMp4, manifest?.preview_url, manifest?.frame_count, slug, shotId]);

  const active = frames[currentFrame];
  const latestBuildFrame = crafting
    ? [...buildEvents].reverse().find((e) => e.type === "frame" && e.url)
    : null;

  return (
    <section className="cinema-stage" aria-label="Craft preview stage">
      <div className="stage-frame">
        {hasMp4 ? (
          <video
            ref={videoRef}
            className="stage-media"
            controls
            playsInline
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
          />
        ) : active || latestBuildFrame ? (
          <img
            className="stage-media"
            src={latestBuildFrame?.url || active?.url}
            alt={
              latestBuildFrame
                ? `Building frame ${latestBuildFrame.frame}`
                : `Frame ${active?.frame}`
            }
          />
        ) : (
          <div className="stage-empty">
            <p>No cel frames yet</p>
            <span>Approve the plan, then Craft — watch cells appear here.</span>
          </div>
        )}

        {progress != null && (
          <div className="stage-build-overlay" aria-live="polite">
            <div className="build-bar">
              <div
                className="build-bar-fill"
                style={{ width: `${Math.min(100, progress * 100)}%` }}
              />
            </div>
            <p>
              Crafting cel frames
              {progressEvt?.frame != null
                ? ` · f${progressEvt.frame}/${progressEvt.total}`
                : "…"}
            </p>
          </div>
        )}

        <div className="stage-badges">
          {engine && <span className="badge">{engine}</span>}
          {manifest && (
            <span className="badge">
              {manifest.frame_count} frames · {fps} fps
            </span>
          )}
          {active && (
            <span className="badge">
              f{active.frame}
              {active.is_key ? " · key" : ""}
              {active.is_smear ? " · smear" : ""}
            </span>
          )}
        </div>
      </div>

      {!hasMp4 && frames.length > 0 && (
        <div className="stage-transport">
          <button type="button" onClick={() => setPlaying((p) => !p)}>
            {playing ? "Pause" : "Play cells"}
          </button>
          <input
            type="range"
            min={0}
            max={Math.max(0, frames.length - 1)}
            value={currentFrame}
            onChange={(e) => {
              setPlaying(false);
              onSeekFrame(Number(e.target.value));
            }}
          />
        </div>
      )}
    </section>
  );
}
