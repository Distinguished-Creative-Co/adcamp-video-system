import React from 'react';
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { CREME_DARK, GOLD } from '../vc/style';
import { SANS } from '../vc/fonts';
import { LEAD_F } from '../../methodology/layout';

/**
 * PROOF (harvested from Shortify: "every claim shows the real thing within two seconds, crop
 * to the word"). A real, unedited capture is shown whole, then on its cue it punches in hard
 * so the exact line or number fills the frame, and a highlight box lands on it. The source
 * line (where and when it was captured) stays visible under the image the whole time.
 * The image is never redrawn, retouched, or cropped in a way that changes what it says.
 */
export const ShotPanel: React.FC<{
  src: string; w: number; h: number; focus: { x: number; y: number; w: number; h: number };
  at: number; source: string; width: number; height: number;
}> = ({ src, w, h, focus, at, source, width, height }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame: frame - (at - 30 - LEAD_F), fps, config: { damping: 200, stiffness: 160, mass: 0.7 }, durationInFrames: 14 });
  const p = spring({ frame: frame - (at - LEAD_F), fps, config: { damping: 200, stiffness: 140, mass: 0.8 }, durationInFrames: 18 });
  const W = width, H = height;
  const s0 = Math.min(W / w, H / h);                                   // whole capture, contained
  const s1 = Math.max(s0, Math.min((W * 0.92) / focus.w, (H * 0.8) / focus.h, s0 * 5)); // the exact line fills the frame
  const drift = 1 + 0.012 * Math.sin((frame / fps) * Math.PI * 2 / 3.4) * p;
  const s = interpolate(p, [0, 1], [s0, s1]) * drift;
  const cx = interpolate(p, [0, 1], [w / 2, focus.x + focus.w / 2]);
  const cy = interpolate(p, [0, 1], [h / 2, focus.y + focus.h / 2]);
  const left = W / 2 - cx * s;
  const top = H / 2 - cy * s;
  const hl = interpolate(p, [0.75, 1], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const pad = 10;
  return (
    <div style={{ opacity: enter, transform: `translateY(${(1 - enter) * 16}px)` }}>
      <div style={{ position: 'relative', width: W, height: H, borderRadius: 22, overflow: 'hidden', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.14)' }}>
        <Img src={staticFile(src)} style={{ position: 'absolute', left, top, width: w * s, height: h * s }} />
        <div style={{
          position: 'absolute', left: left + focus.x * s - pad, top: top + focus.y * s - pad,
          width: focus.w * s + 2 * pad, height: focus.h * s + 2 * pad, borderRadius: 14,
          border: `5px solid ${GOLD.yellow}`, opacity: hl,
          boxShadow: `0 0 40px rgba(var(--accent-rgb,247,199,21),${(0.5 * hl).toFixed(3)})`,
        }} />
      </div>
      <div style={{ marginTop: 16, fontFamily: SANS, fontWeight: 600, fontSize: 26, color: CREME_DARK.inkDim, letterSpacing: '0.02em' }}>{source}</div>
    </div>
  );
};
