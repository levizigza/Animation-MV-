import type { FrameEntry } from "./types";

type Props = {
  frames: FrameEntry[];
  currentIndex: number;
  onSelect: (index: number) => void;
};

export default function FrameStrip({ frames, currentIndex, onSelect }: Props) {
  if (frames.length === 0) {
    return (
      <div className="frame-strip empty">
        <p>Frame strip empty — craft to verify each cel.</p>
      </div>
    );
  }

  return (
    <div className="frame-strip" role="list" aria-label="Cel frame strip">
      {frames.map((f, i) => (
        <button
          key={f.name}
          type="button"
          role="listitem"
          className={
            "frame-thumb" +
            (i === currentIndex ? " active" : "") +
            (f.is_key ? " key" : "") +
            (f.is_smear ? " smear" : "")
          }
          onClick={() => onSelect(i)}
          title={`f${f.frame}${f.is_key ? " key" : ""}${f.is_smear ? " smear" : ""}`}
        >
          <img src={f.url} alt={`f${f.frame}`} loading="lazy" />
          <span className="frame-label">
            {f.frame}
            {f.is_key ? "K" : ""}
            {f.is_smear ? "S" : ""}
          </span>
        </button>
      ))}
    </div>
  );
}
