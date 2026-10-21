import React from 'react';
import { GOLD } from '../vc/style';
import { accentFace, SANS, type AccentFont } from '../vc/fonts';
import type { Line } from '../../methodology/timeline';

/**
 * DYNAMIC captions (captionStyle "dynamic"): the current line, rebuilt as a stacked block.
 * The line's key word (its `big` word) gets its own row in the italic accent serif, large and
 * yellow; the rest are white caps in the house sans, smaller. Each word pops on as it is
 * spoken (the layout is reserved up front, so nothing jumps). Rows shrink to fit 840px.
 */
const W = 840, CY = 1290, BOTTOM = 1580;   // 120-960: clear of the right-side Reels buttons
const chunk = <T,>(a: T[], n: number) => { const o: T[][] = []; for (let i = 0; i < a.length; i += n) o.push(a.slice(i, i + n)); return o; };
const backOut = (p: number) => { const c = 1.7; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };

export const DynamicCaptions: React.FC<{ line?: Line; now: number; fps: number; accent?: AccentFont; opacity: number; plain?: boolean }> = ({ line, now, fps, accent, opacity, plain = false }) => {
  if (!line) return null;
  const face = accentFace(accent);
  const words = line.words.filter((w) => w.t);
  // plain: back text is on screen, so it is the one big word and the captions step back
  const ei = plain ? -1 : words.findIndex((w) => w.key ?? w.big);
  type Row = { ws: typeof words; accent: boolean };
  const rows: Row[] = ei < 0
    ? chunk(words, words.length > 4 ? 3 : 2).map((ws) => ({ ws, accent: false }))
    : [...chunk(words.slice(0, ei), 3).map((ws) => ({ ws, accent: false })), { ws: [words[ei]], accent: true },
       ...chunk(words.slice(ei + 1), 3).map((ws) => ({ ws, accent: false }))];
  const plainSize = plain ? 66 : ei < 0 ? 96 : 66;   // a line with no key word runs bigger, so sizes keep moving
  const sized = rows.map((r) => {
    const chars = r.ws.reduce((n, w) => n + w.t.length, 0) + (r.ws.length - 1);
    const want = r.accent ? 200 : plainSize;
    const k = r.accent ? face.width : 0.64;
    return { ...r, size: Math.min(want, W / (k * Math.max(chars, 2))) };
  });
  const lh = (r: (typeof sized)[number]) => r.size * (r.accent ? 0.95 : 1.02);
  const H = sized.reduce((n, r) => n + lh(r), 0);
  const top = Math.min(CY - H / 2, BOTTOM - H);
  const enter = Math.min(1, Math.max(0, (now - line.s + 0.12) * fps / 6));
  return (
    <div style={{ position: 'absolute', left: (1080 - W) / 2, width: W, top, opacity: opacity * Math.min(1, enter * 1.5),
      transform: `translateY(${(1 - enter) * 18}px)` }}>
      {sized.map((r, i) => (
        <div key={i} style={{ height: lh(r), display: 'flex', justifyContent: 'center', alignItems: 'center', gap: r.size * 0.24, whiteSpace: 'nowrap' }}>
          {r.ws.map((w, j) => {
            const p = Math.min(1, Math.max(0, (now - w.s + 0.04) * fps / 5));
            const style: React.CSSProperties = r.accent
              ? { fontFamily: face.family, fontStyle: 'italic', fontWeight: face.weight, fontSize: r.size, color: GOLD.yellow,
                  letterSpacing: '-0.01em', lineHeight: 1, WebkitTextStroke: '5px rgba(18,14,4,0.62)', paintOrder: 'stroke fill',
                  textShadow: '0 4px 0 rgba(0,0,0,0.4), 0 8px 30px rgba(0,0,0,0.8)' }   // dark rim: yellow must read on white walls
              : { fontFamily: SANS, fontWeight: 800, fontSize: r.size, color: '#fff', textTransform: 'uppercase', letterSpacing: '-0.02em',
                  textShadow: '0 5px 22px rgba(0,0,0,0.6), 0 1px 3px rgba(0,0,0,0.5)' };
            return (
              <span key={j} style={{ ...style, display: 'inline-block', opacity: p, transform: `scale(${0.7 + 0.3 * backOut(p)})`, transformOrigin: '50% 70%' }}>{w.t}</span>
            );
          })}
        </div>
      ))}
    </div>
  );
};
