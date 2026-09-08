/**
 * Remotion overlay stub — section titles & lyric punches over Blender plates.
 * Wire with: npx remotion render after installing remotion + @remotion/cli.
 */
import React from "react";

export type RemotionProps = {
  fps: number;
  sections: { name: string; start: number; end: number }[];
  shots: { id: string; section: string; start: number; end: number; title: string }[];
  overlay: { showSectionTitles: boolean; showBeatPulses: boolean };
};

export const SectionTitleOverlay: React.FC<{
  title: string;
  section: string;
}> = ({ title, section }) => {
  return (
    <div
      style={{
        position: "absolute",
        left: 64,
        bottom: 72,
        color: "#f5efe6",
        fontFamily: "Georgia, serif",
        textShadow: "0 2px 12px rgba(0,0,0,0.55)",
      }}
    >
      <div style={{ fontSize: 18, letterSpacing: 4, textTransform: "uppercase", opacity: 0.8 }}>
        {section}
      </div>
      <div style={{ fontSize: 42, maxWidth: 720, lineHeight: 1.1 }}>{title}</div>
    </div>
  );
};

/** Placeholder composition entry — expand when Remotion project is bootstrapped. */
export const MusicVideoOverlays: React.FC<RemotionProps> = (props) => {
  const shot = props.shots[0];
  if (!shot || !props.overlay.showSectionTitles) return null;
  return <SectionTitleOverlay title={shot.title} section={shot.section} />;
};

export default MusicVideoOverlays;
