import React from 'react';
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile } from 'remotion';
import { CREME_DARK, GOLD } from '../vc/style';
import { SANS } from '../vc/fonts';
import type { Cover as CoverT, ReelConfig } from '../../methodology/ReelConfig';
import { useGrade } from './Grade';

/**
 * Frame 0 only: a chosen frame of the host, a dark title area, and 2-4 bold stacked words
 * (white, one accent word in yellow). Instagram uses frame 0 as the default cover, so this
 * replaces an accidental mid-blink first frame. The title block sits low (y 1330-1590), inside
 * the 3:4 profile-grid crop (y 240-1680), below the face and above the Reels UI.
 */
export const Cover: React.FC<{ cfg: ReelConfig; cover: CoverT }> = ({ cfg, cover }) => {
  const gr = useGrade(cfg.grade);
  const words = cover.title.trim().split(/\s+/);
  const mid = Math.ceil(words.length / 2);
  const rows = [words.slice(0, mid), words.slice(mid)].filter((r) => r.length);
  return (
    <AbsoluteFill style={{ zIndex: 95, backgroundColor: '#131419' }}>
      {/* the chosen frame: this Sequence starts the source at cover.frame, shown on reel frame 0 */}
      <Sequence from={0} durationInFrames={1} layout="none">
        <OffthreadVideo muted src={staticFile(cfg.src)} startFrom={cover.frame} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', filter: gr.filter }} />
        {gr.defs}
        {gr.vignette}
      </Sequence>
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(10,11,14,0) 52%, rgba(10,11,14,0.8) 70%, rgba(10,11,14,0.94) 100%)' }} />
      <div style={{ position: 'absolute', left: 80, width: 860, top: 1330, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {rows.map((r, i) => (
          <div key={i} style={{ fontFamily: SANS, fontWeight: 800, fontSize: 128, lineHeight: 0.98, letterSpacing: '-0.03em', color: CREME_DARK.ink }}>
            {r.map((w, j) => (
              <span key={j} style={w === cover.accent ? { color: GOLD.yellow, textShadow: '0 0 60px rgba(var(--accent-rgb,247,199,21),0.55)' } : undefined}>
                {w}{j < r.length - 1 ? ' ' : ''}
              </span>
            ))}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
