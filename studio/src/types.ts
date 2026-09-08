export type Section = { name: string; start: number; end: number; energy: number };

export type Shot = {
  id: string;
  index: number;
  section: string;
  start: number;
  end: number;
  duration: number;
  description: string;
  notes: string;
  lens_mm: number;
  approval: string;
  cel: {
    mode: string;
    exposure: string;
    smear_density: number;
    masters_pack: string;
  };
};

export type DecisionEvent = {
  type: string;
  at?: string;
  engine?: string;
  shot_id?: string;
  changed_fields?: string[];
  approval_revoked?: boolean;
  note?: string;
  warning?: string;
  source?: string;
  neurosymbolic?: {
    accepted?: number;
    blocked?: number;
    needs_human?: number;
    total?: number;
    applied?: boolean;
    layers?: { neuro?: string; symbolic?: string };
  };
  xsheet?: {
    key_frames?: number[];
    smear_frames?: number[];
    end_frame?: number;
  };
};

export type Project = {
  meta: {
    slug: string;
    title: string;
    prompt: string;
    plan_approved: boolean;
    style_pack: string;
  };
  beatmap?: {
    bpm: number;
    duration: number;
    sections: Section[];
    energy_curve: { t: number; v: number }[];
  };
  story?: { title: string; logline: string; themes: string[] };
  shots: Shot[];
  xsheets: {
    shot_id: string;
    end_frame: number;
    fps?: number;
    timing_chart: Record<string, unknown>;
  }[];
  decisions?: { version?: number; events: DecisionEvent[] };
};

export type FrameEntry = {
  frame: number;
  name: string;
  url: string;
  is_key: boolean;
  is_smear: boolean;
};

export type FramesManifest = {
  shot_id: string;
  fps: number;
  end_frame: number;
  frame_count: number;
  has_mp4: boolean;
  preview_url: string | null;
  key_frames: number[];
  smear_frames: number[];
  frames: FrameEntry[];
};

export type CraftBuildEvent = {
  type: string;
  frame?: number;
  total?: number;
  url?: string;
  name?: string;
  progress?: number;
  engine?: string;
  message?: string;
  warning?: string;
  frames?: FramesManifest;
  ok?: boolean;
  neurosymbolic?: {
    accepted?: number;
    blocked?: number;
    needs_human?: number;
    total?: number;
  };
};

export const API = "/api";
