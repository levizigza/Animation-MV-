import type { CraftBuildEvent, DecisionEvent } from "./types";

type Props = {
  buildEvents: CraftBuildEvent[];
  decisions: DecisionEvent[];
};

function NeuroSymbolicLine({
  accepted,
  blocked,
  needsHuman,
}: {
  accepted?: number;
  blocked?: number;
  needsHuman?: number;
}) {
  const a = accepted ?? 0;
  const b = blocked ?? 0;
  const h = needsHuman ?? 0;
  if (a + b + h === 0) return null;
  return (
    <div className="ns-line" aria-label="Neuro-symbolic grounding">
      <span className="ns-badge ns-neuro">Neuro</span>
      <span className="ns-sep">→</span>
      <span className="ns-badge ns-symbolic">Symbolic</span>
      <span className="ns-counts">
        {" "}
        accepted {a} · blocked {b}
        {h > 0 ? ` · human ${h}` : ""}
      </span>
    </div>
  );
}

export default function BuildFeed({ buildEvents, decisions }: Props) {
  const recent = [...decisions].reverse().slice(0, 10);

  return (
    <aside className="build-feed" aria-label="Build and decisions feed">
      <h3>Build feed</h3>
      {buildEvents.length === 0 ? (
        <p className="muted">Craft progress appears here live.</p>
      ) : (
        <ul>
          {buildEvents
            .slice(-24)
            .reverse()
            .map((e, i) => (
              <li key={`${e.type}-${e.frame ?? i}-${i}`}>
                <strong>{e.type}</strong>
                {e.engine ? <span> · {e.engine}</span> : null}
                {e.frame != null ? (
                  <span>
                    {" "}
                    · f{e.frame}/{e.total}
                  </span>
                ) : null}
                {e.warning ? <div className="muted">{e.warning}</div> : null}
                {e.message ? <div className="muted">{e.message}</div> : null}
                {e.neurosymbolic ? (
                  <NeuroSymbolicLine
                    accepted={e.neurosymbolic.accepted}
                    blocked={e.neurosymbolic.blocked}
                    needsHuman={e.neurosymbolic.needs_human}
                  />
                ) : null}
              </li>
            ))}
        </ul>
      )}

      <h3>Decisions</h3>
      {recent.length === 0 ? (
        <p className="muted">No ledger events yet.</p>
      ) : (
        <ul>
          {recent.map((ev, i) => (
            <li key={`${ev.type}-${ev.at}-${i}`}>
              <strong>{ev.type}</strong>
              {ev.engine ? <span> · {ev.engine}</span> : null}
              {ev.shot_id ? <span> · {ev.shot_id}</span> : null}
              {ev.note ? <div className="muted">{ev.note}</div> : null}
              {ev.neurosymbolic ? (
                <NeuroSymbolicLine
                  accepted={ev.neurosymbolic.accepted}
                  blocked={ev.neurosymbolic.blocked}
                  needsHuman={ev.neurosymbolic.needs_human}
                />
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
