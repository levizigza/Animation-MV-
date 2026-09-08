import type { Shot } from "./types";

type Props = {
  shots: Shot[];
  selectedId: string | null;
  onSelect: (id: string) => void;
};

export default function ShotTimeline({ shots, selectedId, onSelect }: Props) {
  return (
    <div className="shot-timeline" role="list" aria-label="Shot timeline">
      {shots.map((s) => (
        <button
          key={s.id}
          type="button"
          role="listitem"
          className={"shot-card" + (s.id === selectedId ? " active" : "")}
          onClick={() => onSelect(s.id)}
        >
          <strong>
            {String(s.index).padStart(2, "0")} · {s.section}
          </strong>
          <span>
            {s.duration.toFixed(1)}s · {s.cel.mode}
          </span>
          <em>{s.approval}</em>
        </button>
      ))}
    </div>
  );
}
