import type { Project, Shot } from "./types";

type Props = {
  project: Project;
  selected: Shot | null;
  busy: boolean;
  crafting: boolean;
  onApprove: () => void;
  onCraft: () => void;
  onAssemble: () => void;
  onSaveShot: (patch: Record<string, unknown>) => void;
};

export default function ComposerRail({
  project,
  selected,
  busy,
  crafting,
  onApprove,
  onCraft,
  onAssemble,
  onSaveShot,
}: Props) {
  return (
    <aside className="composer-rail">
      <div className="composer-meta">
        <h2>{project.meta.title}</h2>
        <p className="muted">{project.story?.logline || project.meta.prompt}</p>
        <div className="badges">
          <span>{project.meta.style_pack}</span>
          {project.beatmap && <span>{project.beatmap.bpm.toFixed(1)} BPM</span>}
          <span className={project.meta.plan_approved ? "ok" : "warn"}>
            {project.meta.plan_approved ? "Plan approved" : "Needs approval"}
          </span>
        </div>
      </div>

      {selected && (
        <div className="composer-shot">
          <h3>{selected.id}</h3>
          <label>
            Description
            <textarea
              key={selected.id + "-d"}
              defaultValue={selected.description}
              rows={3}
              onBlur={(e) => onSaveShot({ description: e.target.value })}
            />
          </label>
          <label>
            Notes
            <textarea
              key={selected.id + "-n"}
              defaultValue={selected.notes}
              rows={2}
              onBlur={(e) => onSaveShot({ notes: e.target.value })}
            />
          </label>
          <div className="row">
            <label>
              Cel mode
              <select
                key={selected.id + "-m"}
                defaultValue={selected.cel.mode}
                onChange={(e) => onSaveShot({ cel_mode: e.target.value })}
              >
                <option value="full">full</option>
                <option value="limited">limited</option>
                <option value="held_atmosphere">held_atmosphere</option>
              </select>
            </label>
            <label>
              Exposure
              <select
                key={selected.id + "-e"}
                defaultValue={selected.cel.exposure}
                onChange={(e) => onSaveShot({ cel_exposure: e.target.value })}
              >
                <option value="1s">1s</option>
                <option value="2s">2s</option>
                <option value="3s">3s</option>
              </select>
            </label>
            <label>
              Smear
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                key={selected.id + "-s"}
                defaultValue={selected.cel.smear_density}
                onBlur={(e) => onSaveShot({ smear_density: Number(e.target.value) })}
              />
            </label>
          </div>
        </div>
      )}

      <div className="composer-actions">
        <button
          type="button"
          onClick={onApprove}
          disabled={busy || project.meta.plan_approved}
        >
          Approve plan
        </button>
        <button
          type="button"
          className="primary"
          onClick={onCraft}
          disabled={busy || crafting || !project.meta.plan_approved || !selected}
        >
          {crafting ? "Crafting…" : "Craft shot"}
        </button>
        <button
          type="button"
          onClick={onAssemble}
          disabled={busy || !selected}
        >
          Assemble + audio
        </button>
      </div>
    </aside>
  );
}
