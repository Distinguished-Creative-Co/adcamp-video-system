import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { CREME, CREME_DARK, GOLD } from '../vc/style';
import { SANS } from '../vc/fonts';
import { LEAD_F } from '../../methodology/layout';
import type { Line } from '../../methodology/timeline';

/**
 * Word-timed caption lines, ported from the landscape KineticCaption grammar: every word
 * is laid out from the line's first frame (space reserved, no reflow) and pops in place on
 * its own spoken frame; emphasis is the same face in glowing yellow; the block drifts so a
 * landed line is never a still.
 */
const lineSize = (l: Line, base: number, min: number, w: number) => {
  const chars = l.words.reduce((n, x) => n + (x.t ? x.t.length + 1 : 0), 0);
  // ~0.56em per character for Hanken Grotesk 800 at -0.02em tracking
  return Math.max(min, Math.min(base, Math.floor(w / Math.max(chars * 0.56, 1))));
};

export const CaptionLines: React.FC<{
  lines: Line[]; x: number; w: number; top?: number; cy?: number; bottom?: number;
  base: number; min: number; opacity: number; scrim?: boolean; align?: 'center' | 'left'; tone?: 'dark' | 'light';
  punch?: boolean;  // 1-2 words at a time: no backing box (it would show empty before a word pops), a heavy outline instead
}> = ({ lines, x, w, top, cy, bottom, base, min, opacity, scrim, align = 'center', tone = 'dark', punch = false }) => {
  const light = tone === 'light';
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!lines.length || opacity <= 0) return null;
  const now = frame / fps;
  const drift = Math.sin(((frame / fps) * Math.PI * 2) / 2.8) * 4;
  const breathe = 0.45 + 0.2 * Math.sin(((frame / fps) * Math.PI * 2) / 2.2);
  const first = lines[lines.length - 1];
  const rise = spring({ frame: frame - Math.round((first.s * fps)) + LEAD_F, fps, config: { damping: 200, stiffness: 200, mass: 0.6 }, durationInFrames: 10 });
  const box: React.CSSProperties = {
    position: 'absolute', left: x, width: w, display: 'flex', flexDirection: 'column',
    alignItems: align === 'center' ? 'center' : 'flex-start', gap: 6, opacity,
    transform: `translateY(${drift + (1 - rise) * 12}px)`,
  };
  if (cy !== undefined) { box.top = cy; box.transform += ' translateY(-50%)'; }
  if (top !== undefined && bottom !== undefined) { box.top = top; box.height = bottom - top; box.justifyContent = 'center'; }
  return (
    <div style={box}>
      {lines.map((l) => {
        const size = lineSize(l, base, min, w);
        return (
          <div key={l.line} style={{
            display: 'flex', flexWrap: 'wrap', justifyContent: align === 'center' ? 'center' : 'flex-start',
            columnGap: Math.round(size * 0.22), lineHeight: 1.05,
            padding: scrim ? '10px 22px 14px' : 0, borderRadius: 18,
            background: scrim ? 'rgba(10,12,16,0.42)' : undefined,
            backdropFilter: scrim ? 'blur(12px)' : undefined,
          }}>
            {l.words.map((wd, i) => {
              if (!wd.t) return null;
              const p = spring({ frame: frame - (Math.round(wd.s * fps) - LEAD_F), fps, config: { damping: 200, stiffness: 240, mass: 0.5 }, durationInFrames: 8 });
              const said = now >= wd.s - LEAD_F / fps;
              return (
                <span key={i} style={{
                  display: 'inline-block', fontFamily: SANS, fontWeight: 800, fontSize: size, letterSpacing: '-0.02em',
                  // light stage: dark ink, and emphasis becomes dark ink on a yellow bar (never yellow on light)
                  color: light ? (wd.big ? GOLD.ink : CREME.ink) : wd.big ? GOLD.yellow : CREME_DARK.ink,
                  background: light && wd.big ? GOLD.yellow : undefined,
                  padding: light && wd.big ? `0 ${Math.round(size * 0.14)}px` : undefined,
                  borderRadius: light && wd.big ? Math.round(size * 0.14) : undefined,
                  textShadow: light
                    ? undefined
                    : punch
                      ? `0 0 3px rgba(0,0,0,0.95), 0 0 3px rgba(0,0,0,0.95), 0 4px 18px rgba(0,0,0,0.85)${wd.big ? `, 0 0 ${Math.round(size * 0.5)}px rgba(var(--accent-rgb,247,199,21),${breathe.toFixed(3)})` : ''}`
                      : wd.big
                      ? `0 0 ${Math.round(size * 0.5)}px rgba(var(--accent-rgb,247,199,21),${breathe.toFixed(3)}), 0 2px 18px rgba(0,0,0,0.55)`
                      : '0 2px 18px rgba(0,0,0,0.55)',
                  opacity: said ? p : 0,
                  transform: `translateY(${(1 - p) * 10}px) scale(${interpolate(p, [0, 1], [0.72, 1])})`,
                }}>{wd.t}</span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
