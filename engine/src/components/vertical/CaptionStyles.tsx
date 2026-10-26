import React from 'react';
import { GOLD, inkOn, lookColor, moneyColor } from '../vc/style';
import { accentFace, displayFace, type AccentFont } from '../vc/fonts';
import type { Line } from '../../methodology/timeline';
import type { CaptionLook } from '../../methodology/ReelConfig';
import { LEAD_F } from '../../methodology/layout';

/**
 * Four more caption modes for full-screen shots (captionStyle):
 *   bigword    the line in small type, its key word on its own row, huge, in the key color
 *   pill       the line as a short phrase, bold; its key word sits in a solid rounded pill
 *   editorial  a small, widely tracked caps line, the key word under it in the italic serif, rising from a mask
 *   steps      the line's words land one by one, each a step down and to the right; the key word in the
 *              italic serif with an underline that draws in
 * Every word appears on its spoken frame (layout reserved up front, so nothing jumps). The key word is the
 * one the config marks (key, else big), else the line's longest content word. A style's look sets the type
 * and color; without one the house sans, white and the brand accent are used.
 */
export type CaptionMode = 'bigword' | 'pill' | 'editorial' | 'steps';
export const CAPTION_MODES: CaptionMode[] = ['bigword', 'pill', 'editorial', 'steps'];

const W = 840, LEFT = (1080 - W) / 2;
const STOP = new Set('the and that this with from your have about there their they them then than what when where which while would could should into onto just going also only even more most some like over very much does after want around gonna is are was were be been a an of to in on at for it its it\'s i i\'m you you\'re we he she but or so if as by my me'.split(' '));
const bare = (t: string) => t.toLowerCase().replace(/[^a-z0-9']/g, '');

export const keyIndex = (ws: { t: string; key?: boolean; big?: boolean }[]): number => {
  const marked = ws.findIndex((w) => w.key ?? w.big);
  if (marked >= 0) return marked;
  let best = -1, len = 3;
  ws.forEach((w, i) => { const b = bare(w.t); if (!STOP.has(b) && b.length > len) { best = i; len = b.length; } });
  return best;
};

const ease = (p: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, p)), 3);
// a word starts arriving as its line takes the screen (visibleLines, LEAD_F before it is voiced), already part-way in on
// that first frame, so a line change leaves no empty frame and a line's last word is never cut to a frame
const shown = (now: number, s: number, fps: number, f = 5) => Math.min(1, Math.max(0, (now - s + (LEAD_F + 1) / fps) * fps / f));
const shadowOf = (k?: CaptionLook['shadow']) => k === 'none' ? undefined : k === 'hard' ? '0 5px 0 rgba(0,0,0,0.55), 0 8px 24px rgba(0,0,0,0.6)' : '0 3px 16px rgba(0,0,0,0.7), 0 1px 3px rgba(0,0,0,0.6)';
const caseOf = (k?: CaptionLook['case']): React.CSSProperties['textTransform'] => k === 'upper' ? 'uppercase' : k === 'lower' ? 'lowercase' : undefined;

export const StyledCaptions: React.FC<{
  mode: CaptionMode; line?: Line; now: number; fps: number; opacity: number; look?: CaptionLook; serif?: AccentFont; cy?: number;
}> = ({ mode, line, now, fps, opacity, look, serif, cy = 1290 }) => {
  if (!line || opacity <= 0) return null;
  const words = line.words.filter((w) => w.t);
  if (!words.length) return null;
  const lk = look ?? {};
  const face = displayFace(lk.font);
  const ser = accentFace(serif);
  const ink = lookColor(lk.color, '#FFFFFF');
  const key = lookColor(lk.keyColor, GOLD.yellow);
  const ki = keyIndex(words);
  const shadow = shadowOf(lk.shadow);
  const stroke = lk.outline ? { WebkitTextStroke: `${lk.outline}px rgba(12,10,6,0.85)`, paintOrder: 'stroke fill' } as React.CSSProperties : {};
  const base: React.CSSProperties = { fontFamily: face.family, fontWeight: lk.weight ?? face.weight, fontStyle: face.italic ? 'italic' : undefined,
    textTransform: caseOf(lk.case), color: ink, textShadow: shadow, whiteSpace: 'nowrap', lineHeight: 1, ...stroke };
  const enter = ease((now - line.s + (LEAD_F + 1) / fps) * fps / 6);
  const box = (h: number): React.CSSProperties => ({ position: 'absolute', left: LEFT, width: W, top: Math.min(cy - h / 2, 1470 - h), opacity: opacity * Math.min(1, enter * 1.5) });
  const fit = (chars: number, want: number, k: number) => Math.min(want, W / (k * Math.max(chars, 2)));
  const money = (t: string): React.CSSProperties => { const m = moneyColor(t, lk); return m ? { color: m } : {}; };   // a dollar amount, when the look turns it on

  if (mode === 'bigword') {
    const rest = words.filter((_, i) => i !== ki);
    const before = ki < 0 ? words : words.slice(0, ki), after = ki < 0 ? [] : words.slice(ki + 1);
    const small = fit(Math.max(before.map((w) => w.t).join(' ').length, after.map((w) => w.t).join(' ').length), lk.size ? lk.size * 0.42 : 56, face.width);
    const big = ki < 0 ? 0 : fit(words[ki].t.length, lk.size ?? 170, face.width * 1.05);
    const row = (ws: typeof words) => ws.length ? (
      <div style={{ display: 'flex', justifyContent: 'center', gap: small * 0.28, height: small * 1.15, alignItems: 'center' }}>
        {ws.map((w, j) => <span key={j} style={{ ...base, fontSize: small, opacity: shown(now, w.s, fps), ...money(w.t) }}>{w.t}</span>)}
      </div>) : null;
    const h = (before.length ? small * 1.15 : 0) + big * 1.0 + (after.length ? small * 1.15 : 0);
    const kp = ki < 0 ? 0 : shown(now, words[ki].s, fps, 4);
    return (
      <div style={box(h || small * 1.2)}>
        {row(before)}
        {ki >= 0 ? (
          <div style={{ height: big, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <span style={{ ...base, fontSize: big, color: key, opacity: kp, transform: `scale(${0.82 + 0.18 * ease(kp)})`, ...money(words[ki].t) }}>{words[ki].t}</span>
          </div>) : null}
        {row(ki < 0 ? rest.slice(0, 0) : after)}
      </div>
    );
  }

  if (mode === 'pill') {
    const size = fit(words.map((w) => w.t).join(' ').length + 2, lk.size ?? 96, face.width);
    return (
      <div style={{ ...box(size * 1.5), display: 'flex', justifyContent: 'center', alignItems: 'center', gap: size * 0.26 }}>
        {words.map((w, j) => {
          const p = shown(now, w.s, fps, 4);
          const isKey = j === ki;
          const m = moneyColor(w.t, lk);
          return (
            <span key={j} style={{ ...base, fontSize: size, opacity: p, transform: `translateY(${(1 - ease(p)) * 14}px)`, ...(m && !isKey ? { color: m } : {}),
              ...(isKey ? { color: m ? inkOn(m) : '#111111', background: m ?? (lk.keyColor ? lookColor(lk.keyColor, '#FFFFFF') : '#FFFFFF'), padding: `${size * 0.1}px ${size * 0.28}px ${size * 0.14}px`,
                borderRadius: size * 0.5, textShadow: undefined, WebkitTextStroke: undefined, boxShadow: '0 8px 26px rgba(0,0,0,0.45)' } : {}) }}>{w.t}</span>
          );
        })}
      </div>
    );
  }

  if (mode === 'editorial') {
    const rest = words.filter((_, i) => i !== ki);
    const small = fit(rest.map((w) => w.t).join(' ').length * 1.35, 34, face.width);
    const big = ki < 0 ? 0 : fit(words[ki].t.length, lk.size ?? 190, ser.width);
    const kp = ki < 0 ? 0 : shown(now, words[ki].s, fps, 7);
    const h = small * 1.6 + big;
    return (
      <div style={box(h)}>
        <div style={{ display: 'flex', justifyContent: 'center', gap: small * 0.6, height: small * 1.6, alignItems: 'center' }}>
          {rest.map((w, j) => <span key={j} style={{ ...base, fontWeight: 700, fontSize: small, letterSpacing: '0.32em', textTransform: 'uppercase', opacity: shown(now, w.s, fps), ...money(w.t) }}>{w.t}</span>)}
        </div>
        {ki >= 0 ? (
          <div style={{ height: big, overflow: 'hidden', display: 'flex', justifyContent: 'center', alignItems: 'flex-end' }}>
            <span style={{ fontFamily: ser.family, fontStyle: 'italic', fontWeight: ser.weight, fontSize: big, lineHeight: 0.98, color: key, whiteSpace: 'nowrap',
              textShadow: '0 6px 30px rgba(0,0,0,0.55)', transform: `translateY(${(1 - ease(kp)) * 100}%)`, ...money(words[ki].t) }}>{words[ki].t}</span>
          </div>) : null}
      </div>
    );
  }

  // steps: a diagonal staircase, a row per one or two words
  const rows: { ws: typeof words; key: boolean }[] = [];
  words.forEach((w, i) => {
    const last = rows[rows.length - 1];
    if (i === ki) rows.push({ ws: [w], key: true });
    else if (last && !last.key && last.ws.length < 2) last.ws.push(w);
    else rows.push({ ws: [w], key: false });
  });
  const shownRows = rows.slice(-5);
  const small = lk.size ? lk.size * 0.5 : 64;
  const big = ki < 0 ? small : Math.min(small * 2.1, W * 0.62 / (ser.width * Math.max(words[ki].t.length, 3)));
  const stepX = Math.min(70, (W - 420) / Math.max(shownRows.length - 1, 1));
  const heights = shownRows.map((r) => (r.key ? big : small) * 1.12);
  const h = heights.reduce((a, b) => a + b, 0);
  let y = 0;
  return (
    <div style={{ ...box(h), height: h }}>
      {shownRows.map((r, i) => {
        const top = y; y += heights[i];
        const p = shown(now, r.ws[0].s, fps, 4);
        const left = i * stepX;
        if (r.key) {
          const u = ease((now - r.ws[0].s - 0.1) * fps / 8);
          return (
            <div key={i} style={{ position: 'absolute', left, top, opacity: p, transform: `translateY(${(1 - ease(p)) * 16}px)` }}>
              <span style={{ fontFamily: ser.family, fontStyle: 'italic', fontWeight: ser.weight, fontSize: big, lineHeight: 1.05, color: key, whiteSpace: 'nowrap', textShadow: '0 6px 26px rgba(0,0,0,0.55)', ...money(r.ws[0].t) }}>{r.ws[0].t}</span>
              <div style={{ height: Math.max(4, big * 0.05), width: `${u * 100}%`, background: moneyColor(r.ws[0].t, lk) ?? key, borderRadius: 4, marginTop: -big * 0.06 }} />
            </div>
          );
        }
        return (
          <div key={i} style={{ position: 'absolute', left, top, display: 'flex', gap: small * 0.25 }}>
            {r.ws.map((w, j) => <span key={j} style={{ ...base, fontSize: small, opacity: shown(now, w.s, fps), transform: `translateY(${(1 - ease(shown(now, w.s, fps))) * 14}px)`, ...money(w.t) }}>{w.t}</span>)}
          </div>
        );
      })}
    </div>
  );
};
