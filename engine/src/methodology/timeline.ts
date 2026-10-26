/**
 * TIMELINE STATE — what every layer should look like on a given frame. Pure: the only
 * motion curve comes in as `ease` (Remotion's spring in the engine, a cubic in tests),
 * so the whole state machine is testable frame by frame without a browser.
 *
 *   full    avatar fills the frame, one caption line in the lower-middle band
 *   window  avatar GLIDES DOWN into the glass card (same footage shrinking, face-anchored),
 *           captions live on the dark stage above
 *   swap    inside a window: the card slides off LEFT while a near-full glass panel slides
 *           in from the RIGHT carrying the beat's content; the avatar rides the panel as
 *           an inset, so it never leaves the screen
 */
import type { ReelConfig, ReelWord, Swap, Tone } from './ReelConfig';
import {
  CARD, CARD_EXIT_DX, GLIDE_F, HOLD_S, LEAD_F, PANEL, PANEL_ENTER_X, SWAP_F, FPS,
  View, easeOutCubic, fullView, lerp, lerpView,
} from './layout';

export type Ease = (localFrame: number, durFrames: number) => number;
export const cubicEase: Ease = (lf, d) => easeOutCubic(lf / d);

export type CapRegion = 'full' | 'stage' | 'panel';
export type Line = { line: number; sent: number; words: ReelWord[]; s: number; e: number };

export type State = {
  scene: number;
  view: View;          // main avatar viewport (before the swap offset)
  zoom: number;
  glass: number;       // 0 full frame .. 1 glass card
  floatY: number;
  cardDx: number;      // swap: card slides off left
  swap: { index: number; data: Swap; ps: number; panelX: number } | null;
  capRegion: CapRegion;
  capOpacity: number;
  tone: Tone;          // stage tone of the current scene (hard cut at scene changes)
};

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
/** 1 away from a transition's midpoint, 0 across its middle 30% (a caption never rides a move). */
const dip = (x: number) => clamp((Math.abs(x - 0.5) - 0.15) / 0.2, 0, 1);

const sceneEnd = (c: ReelConfig, i: number) => (i + 1 < c.scenes.length ? c.scenes[i + 1].from : c.frames);

export const openZoom = (c: ReelConfig, frame: number) =>
  frame >= c.open.frames ? 1 : lerp(c.open.scale, 1, easeOutCubic(frame / c.open.frames));

/** The idle push of scene i at local frame lf: never a frozen frame. */
const sceneZoom = (c: ReelConfig, i: number, lf: number) => {
  const sc = c.scenes[i];
  const len = Math.max(sceneEnd(c, i) - sc.from, 1);
  const start = i === 0 ? c.open.frames : 0;
  const u = clamp((lf - start) / Math.max(len - start, 1), 0, 1);
  const push = sc.mode === 'full' ? 1 + 0.04 * u : 1 + 0.03 * u;
  return i === 0 ? push * openZoom(c, sc.from + lf) : push;
};

export const sceneIndexAt = (c: ReelConfig, frame: number) => {
  let idx = 0;
  for (let i = 0; i < c.scenes.length; i++) if (frame >= c.scenes[i].from) idx = i;
  return idx;
};

export const swapAt = (c: ReelConfig, frame: number) => {
  const i = c.swaps.findIndex((s) => frame >= s.in && frame < (s.out >= c.frames ? Infinity : s.out + SWAP_F));
  return i < 0 ? null : { index: i, data: c.swaps[i] };
};

export const stateAt = (c: ReelConfig, frame: number, ease: Ease = cubicEase): State => {
  const idx = sceneIndexAt(c, frame);
  const sc = c.scenes[idx];
  const prev = idx > 0 ? c.scenes[idx - 1] : null;
  const lf = frame - sc.from;
  const changed = !!prev && prev.mode !== sc.mode;
  const t = changed ? clamp(ease(Math.max(lf, 0), GLIDE_F), 0, 1) : 1;
  const wT = sc.mode === 'window' ? 1 : 0;
  const wP = prev ? (prev.mode === 'window' ? 1 : 0) : wT;
  const g = lerp(wP, wT, t);
  const full = fullView(c.faceX, c.faceY, c.source.w, c.source.h);
  const view = lerpView(full, CARD, g);

  let zoom = sceneZoom(c, idx, lf);
  if (prev) {
    const prevEnd = sceneZoom(c, idx - 1, sc.from - prev.from);
    zoom += (prevEnd - sceneZoom(c, idx, 0)) * (1 - t);   // carry the seam, no pop
  }

  let swap: State['swap'] = null;
  let cardDx = 0;
  let capOpacity = changed ? dip(t) : 1;
  const sw = swapAt(c, frame);
  if (sw) {
    const s = sw.data;
    const ps = frame < s.out ? clamp(ease(frame - s.in, SWAP_F), 0, 1) : clamp(1 - ease(frame - s.out, SWAP_F), 0, 1);
    cardDx = CARD_EXIT_DX * ps;
    swap = { index: sw.index, data: s, ps, panelX: lerp(PANEL_ENTER_X, PANEL.x, ps) };
    const moving = frame - s.in < SWAP_F || (frame >= s.out && s.out < c.frames);
    if (moving) capOpacity = Math.min(capOpacity, dip(ps));
  }

  const capRegion: CapRegion = swap && swap.ps > 0.5 ? 'panel' : g >= 0.5 ? 'stage' : 'full';
  return {
    scene: idx, view, zoom, glass: g, floatY: Math.sin((2 * Math.PI * frame) / 90) * 3 * g,
    cardDx, swap, capRegion, capOpacity, tone: sc.mode === 'window' ? sc.tone ?? 'dark' : 'dark',
  };
};

/** Caption lines (words grouped by the generator's line index). Absorbed tokens keep timing only. */
export const buildLines = (words: ReelWord[], style: 'lines' | 'punch' | 'word' = 'lines'): Line[] => {
  const lines = buildLineGroups(words);
  if (style === 'word') {
    // one spoken word at a time, each on its own clock
    const out: Line[] = [];
    for (const L of lines) for (const w of L.words) if (w.t) out.push({ line: L.line * 100 + out.length, sent: L.sent, words: [w], s: w.s, e: w.e });
    return out;
  }
  if (style !== 'punch') return lines;
  // punch: 1-2 spoken words at a time, breaking after punctuation, each on its own clock
  const out: Line[] = [];
  for (const L of lines) {
    let cur: ReelWord[] = [];
    const flush = () => {
      const spoken = cur.filter((w) => w.t);
      if (spoken.length) out.push({ line: L.line * 100 + out.length, sent: L.sent, words: cur, s: spoken[0].s, e: Math.max(...cur.map((w) => w.e)) });
      cur = [];
    };
    for (const w of L.words) {
      cur.push(w);
      const n = cur.filter((x) => x.t).length;
      if (n >= 2 || /[.,?!:]["\u201d]?$/.test(w.t)) flush();
    }
    flush();
  }
  return out;
};

const buildLineGroups = (words: ReelWord[]): Line[] => {
  const out: Line[] = [];
  for (const w of words) {
    let L = out[out.length - 1];
    if (!L || L.line !== w.line) {
      L = { line: w.line, sent: w.sent, words: [], s: w.s, e: w.e };
      out.push(L);
    }
    L.words.push(w);
    L.e = Math.max(L.e, w.e);
  }
  return out.filter((l) => l.words.some((w) => w.t));
};

/** Lines on screen at time `now` (seconds). full/panel: the one current line. stage: the
 *  current sentence's lines, stacking, the newest 3. */
export const visibleLines = (lines: Line[], now: number, region: CapRegion): Line[] => {
  const lead = LEAD_F / FPS;
  let cur = -1;
  for (let i = 0; i < lines.length; i++) if (now >= lines[i].s - lead) cur = i;
  if (cur < 0) return [];
  const L = lines[cur];
  const next = lines[cur + 1];
  const until = Math.min(next ? next.s - lead : Infinity, L.e + HOLD_S);
  if (now > until) return [];
  if (region !== 'stage') return [L];
  const same: Line[] = [];
  for (let i = cur; i >= 0 && lines[i].sent === L.sent && same.length < 3; i--) same.unshift(lines[i]);
  return same;
};
