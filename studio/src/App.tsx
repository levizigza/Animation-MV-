import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import BuildFeed from "./BuildFeed";
import CinemaStage from "./CinemaStage";
import ComposerRail from "./ComposerRail";
import FrameStrip from "./FrameStrip";
import ShotTimeline from "./ShotTimeline";
import {
  API,
  CraftBuildEvent,
  FramesManifest,
  Project,
} from "./types";

export default function App() {
  const [projects, setProjects] = useState<
    { slug: string; title: string; plan_approved: boolean }[]
  >([]);
  const [slug, setSlug] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [styles, setStyles] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [crafting, setCrafting] = useState(false);
  const [status, setStatus] = useState("");
  const [selectedShot, setSelectedShot] = useState<string | null>(null);
  const [manifest, setManifest] = useState<FramesManifest | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [buildEvents, setBuildEvents] = useState<CraftBuildEvent[]>([]);
  const [engine, setEngine] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  async function refreshList() {
    const r = await fetch(`${API}/projects`);
    setProjects(await r.json());
  }

  async function loadFrames(s: string, shotId: string) {
    const r = await fetch(`${API}/projects/${s}/shots/${shotId}/frames`);
    if (!r.ok) {
      setManifest(null);
      return;
    }
    const data = (await r.json()) as FramesManifest;
    setManifest(data);
    setCurrentFrame(0);
    if (data.has_mp4) setEngine((e) => e || "preview");
  }

  async function loadProject(s: string) {
    setBusy(true);
    try {
      const r = await fetch(`${API}/projects/${s}`);
      const data = (await r.json()) as Project;
      setProject(data);
      setSlug(s);
      const first = data.shots[0]?.id ?? null;
      setSelectedShot(first);
      setCreateOpen(false);
      if (first) await loadFrames(s, first);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refreshList();
    fetch(`${API}/styles`)
      .then((r) => r.json())
      .then(setStyles)
      .catch(() => setStyles(["classic_cel"]));
  }, []);

  useEffect(() => {
    if (!slug || !selectedShot) return;
    loadFrames(slug, selectedShot);
    setBuildEvents([]);
  }, [slug, selectedShot]);

  const selected = useMemo(
    () => project?.shots.find((s) => s.id === selectedShot) ?? null,
    [project, selectedShot]
  );

  const recentDecisions = useMemo(() => {
    const events = project?.decisions?.events ?? [];
    return events;
  }, [project]);

  const onSeekFrame = useCallback((i: number) => setCurrentFrame(i), []);

  async function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    setStatus("Analyzing music & planning cel craft…");
    try {
      const r = await fetch(`${API}/projects`, { method: "POST", body: fd });
      if (!r.ok) throw new Error(await r.text());
      const data = (await r.json()) as Project;
      setProject(data);
      setSlug(data.meta.slug);
      setSelectedShot(data.shots[0]?.id ?? null);
      await refreshList();
      setStatus("Plan ready — approve, then craft to see cells on the stage.");
      setCreateOpen(false);
    } catch (err) {
      setStatus(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveShot(patch: Record<string, unknown>) {
    if (!slug || !selectedShot) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/projects/${slug}/shots/${selectedShot}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
      await loadProject(slug);
      if (data.approval_revoked) {
        setStatus(
          `Cel change: X-sheet rebuilt; plan approval revoked — re-approve before craft.`
        );
      }
    } finally {
      setBusy(false);
    }
  }

  async function approvePlan() {
    if (!slug) return;
    setBusy(true);
    try {
      await fetch(`${API}/projects/${slug}/approve-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved: true }),
      });
      await loadProject(slug);
      setStatus("Plan approved — craft unlocked.");
      await refreshList();
    } finally {
      setBusy(false);
    }
  }

  async function craftSelected() {
    if (!slug || !selectedShot) return;
    setCrafting(true);
    setBuildEvents([]);
    setStatus("Crafting cel frames…");
    try {
      const r = await fetch(`${API}/projects/${slug}/craft/${selectedShot}/stream`, {
        method: "POST",
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || r.statusText);
      }
      const reader = r.body?.getReader();
      if (!reader) throw new Error("No craft stream");
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() || "";
        for (const chunk of chunks) {
          const line = chunk
            .split("\n")
            .find((l) => l.startsWith("data: "));
          if (!line) continue;
          const ev = JSON.parse(line.slice(6)) as CraftBuildEvent;
          setBuildEvents((prev) => [...prev, ev]);
          if (ev.type === "engine_selected" && ev.engine) setEngine(ev.engine);
          if (ev.type === "frame" && ev.url) {
            // Live strip growth: merge into manifest lightly
            setManifest((prev) => {
              const base: FramesManifest = prev || {
                shot_id: selectedShot,
                fps: ev.total ? 24 : 24,
                end_frame: ev.total || 0,
                frame_count: 0,
                has_mp4: false,
                preview_url: null,
                key_frames: [],
                smear_frames: [],
                frames: [],
              };
              if (base.frames.some((f) => f.name === ev.name)) return base;
              return {
                ...base,
                frame_count: base.frames.length + 1,
                frames: [
                  ...base.frames,
                  {
                    frame: ev.frame || base.frames.length + 1,
                    name: ev.name || "",
                    url: ev.url!,
                    is_key: false,
                    is_smear: false,
                  },
                ],
              };
            });
            if (ev.frame != null) setCurrentFrame(Math.max(0, ev.frame - 1));
          }
          if (ev.type === "done") {
            if (ev.engine) setEngine(ev.engine);
            if (ev.frames) {
              setManifest(ev.frames);
              setCurrentFrame(0);
            } else {
              await loadFrames(slug, selectedShot);
            }
            setStatus(
              `Craft done · ${ev.engine || "engine"}${ev.warning ? ` — ${ev.warning}` : ""}`
            );
            await loadProject(slug);
          }
          if (ev.type === "error") {
            setStatus(`Craft error: ${ev.message}`);
          }
        }
      }
    } catch (err) {
      setStatus(String(err));
    } finally {
      setCrafting(false);
    }
  }

  async function assembleSelected() {
    if (!slug || !selectedShot) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/projects/${slug}/assemble/${selectedShot}`, {
        method: "POST",
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
      setStatus(`Assembled → ${data.output || "final/"}`);
    } catch (err) {
      setStatus(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="cinema-app">
      <header className="cinema-top">
        <div className="brand-block">
          <p className="brand">Cel Music Video Studio</p>
          <span className="tagline">Watch cells craft · verify every frame</span>
        </div>
        <div className="top-actions">
          <select
            value={slug || ""}
            onChange={(e) => e.target.value && loadProject(e.target.value)}
            aria-label="Open project"
          >
            <option value="">Open project…</option>
            {projects.map((p) => (
              <option key={p.slug} value={p.slug}>
                {p.title} {p.plan_approved ? "✓" : ""}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => setCreateOpen((o) => !o)}>
            {createOpen ? "Hide new" : "New project"}
          </button>
        </div>
      </header>

      {createOpen && (
        <section className="create-drawer panel">
          <h2>New project</h2>
          <form onSubmit={onCreate} className="create-form">
            <label>
              Title
              <input name="title" required placeholder="Neon Harbor" />
            </label>
            <label>
              Prompt
              <textarea name="prompt" required rows={3} placeholder="Rider through rain…" />
            </label>
            <label>
              Style
              <select name="style" defaultValue="classic_cel">
                {styles.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Audio
              <input name="audio" type="file" accept="audio/*" required />
            </label>
            <button type="submit" disabled={busy}>
              Analyze & plan
            </button>
          </form>
        </section>
      )}

      {!project ? (
        <main className="cinema-empty">
          <h1>Open a project to enter the craft stage</h1>
          <p>Approve the plan, craft a shot, and scrub every cel on the frame strip.</p>
        </main>
      ) : (
        <main className="cinema-layout">
          <div className="cinema-main">
            <CinemaStage
              slug={slug}
              shotId={selectedShot}
              manifest={manifest}
              buildEvents={buildEvents}
              crafting={crafting}
              engine={engine}
              currentFrame={currentFrame}
              onSeekFrame={onSeekFrame}
            />
            <ShotTimeline
              shots={project.shots}
              selectedId={selectedShot}
              onSelect={setSelectedShot}
            />
            <FrameStrip
              frames={manifest?.frames ?? []}
              currentIndex={currentFrame}
              onSelect={(i) => setCurrentFrame(i)}
            />
            {status && <p className="status-line">{status}</p>}
          </div>
          <div className="cinema-side">
            <ComposerRail
              project={project}
              selected={selected}
              busy={busy}
              crafting={crafting}
              onApprove={approvePlan}
              onCraft={craftSelected}
              onAssemble={assembleSelected}
              onSaveShot={saveShot}
            />
            <BuildFeed buildEvents={buildEvents} decisions={recentDecisions} />
          </div>
        </main>
      )}
    </div>
  );
}
