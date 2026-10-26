import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { CREME, CREME_DARK, GOLD, INK_ON_ACCENT, lookColor, moneyColor } from '../vc/style';
import { displayFace } from '../vc/fonts';
import { LEAD_F } from '../../methodology/layout';
import type { Line } from '../../methodology/timeline';
import type { CaptionLook } from '../../methodology/ReelConfig';

/**
 * Word-timed caption lines, ported from Chris's own landscape engine's KineticCaption grammar: every word
 * is laid out from the line's first frame (space reserved, no reflow) and pops in place on
 * its own spoken frame; emphasis is the same face in glowing yellow; the block drifts so a
 * landed line is never a still.
 */
const lineSize = (l: Line, base: number, min: number, w: number, k = 0.56) => {
  const chars = l.words.reduce((n, x) => n + (x.t ? x.t.length + 1 : 0), 0);
  // ~0.56em per character for Hanken Grotesk 800 at -0.02em tracking; a style's face brings its own width
  return Math.max(min, Math.min(base, Math.floor(w / Math.max(chars * k, 1))));
};

export const CaptionLines: React.FC<{
  lines: Line[]; x: number; w: number; top?: number; cy?: number; bottom?: number;
  base: number; min: number; opacity: number; scrim?: boolean; align?: 'center' | 'left'; tone?: 'dark' | 'light';
  punch?: boolean;  // 1-2 words at a time: no backing box (it would show empty before a word pops), a heavy outline instead
  look?: CaptionLook;  // a saved style's type and color; absent = the house look, unchanged
}> = ({ lines, x, w, top, cy, bottom, base, min, opacity, scrim, align = 'center', tone = 'dark', punch = false, look }) => {
  const light = tone === 'light';
  const face = displayFace(look?.font);
  const lk = look ?? {};
  const typed = Object.keys(lk).some((k) => k !== 'money');   // a look with only a money color keeps the house type
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
        const size = lineSize(l, base, min, w, face.width);
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
              const sp = spring({ frame: frame - (Math.round(wd.s * fps) - LEAD_F), fps, config: { damping: 200, stiffness: 240, mass: 0.5 }, durationInFrames: 8 });
              const p = lk.motion === 'cut' ? 1 : sp;
              const said = now >= wd.s - LEAD_F / fps;
              const big = wd.big || !!wd.key;   // the key words dynamic_keys.py marked are lifted in every look
              const ink = light ? (big ? INK_ON_ACCENT : CREME.ink) : moneyColor(wd.t, lk) ?? (big ? lookColor(lk.keyColor, GOLD.yellow) : lookColor(lk.color, CREME_DARK.ink));
              const styled = !light && typed;
              const shadow = lk.shadow === 'none' ? undefined : lk.shadow === 'hard' ? '0 5px 0 rgba(0,0,0,0.55), 0 8px 24px rgba(0,0,0,0.6)' : '0 3px 16px rgba(0,0,0,0.7), 0 1px 3px rgba(0,0,0,0.6)';
              return (
                <span key={i} style={{
                  display: 'inline-block', fontFamily: face.family, fontWeight: lk.weight ?? face.weight, fontStyle: face.italic ? 'italic' : undefined,
                  fontSize: size, letterSpacing: typed ? '-0.01em' : '-0.02em',
                  textTransform: lk.case === 'upper' ? 'uppercase' : lk.case === 'lower' ? 'lowercase' : undefined,
                  WebkitTextStroke: styled && lk.outline ? `${lk.outline}px rgba(12,10,6,0.85)` : undefined, paintOrder: styled && lk.outline ? 'stroke fill' : undefined,
                  // light stage: dark ink, and emphasis becomes dark ink on a yellow bar (never yellow on light)
                  color: ink,
                  background: light && big ? GOLD.yellow : undefined,
                  padding: light && big ? `0 ${Math.round(size * 0.14)}px` : undefined,
                  borderRadius: light && big ? Math.round(size * 0.14) : undefined,
                  textShadow: light
                    ? undefined
                    : styled
                    ? shadow
                    : punch
                      ? `0 0 3px rgba(0,0,0,0.95), 0 0 3px rgba(0,0,0,0.95), 0 4px 18px rgba(0,0,0,0.85)${big ? `, 0 0 ${Math.round(size * 0.5)}px rgba(var(--accent-rgb,247,199,21),${breathe.toFixed(3)})` : ''}`
                      : big
                      ? `0 0 ${Math.round(size * 0.5)}px rgba(var(--accent-rgb,247,199,21),${breathe.toFixed(3)}), 0 2px 18px rgba(0,0,0,0.55)`
                      : '0 2px 18px rgba(0,0,0,0.55)',
                  opacity: said ? p : 0,
                  transform: lk.motion === 'rise' ? `translateY(${(1 - p) * 26}px)` : lk.motion === 'cut' ? undefined : `translateY(${(1 - p) * 10}px) scale(${interpolate(p, [0, 1], [0.72, 1])})`,
                }}>{wd.t}</span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};
