/**
 * META'S AD SAFE ZONE. A paid reel (placement "paid") runs as a Reels ad, and Meta draws its own UI over the frame:
 * the sponsored line over the top 14% (y < 250), the ad copy and its call-to-action button over the bottom 35%
 * (y > 1250), and about 60 px down each side. So every word a paid reel draws stays inside x 60-1020, y 250-1250.
 * Organic reels keep their own layout (layout.ts SAFE): nothing here changes them.
 *
 * Pure functions, no Remotion imports. The components place a paid reel's words with these, and validateReel checks
 * the same boxes (adSafeFaults), so the drawing and the check share one geometry. scripts/test_layout.mjs plants
 * faults to prove the check catches words outside the zone.
 */
import { CAP_FULL, CAP_STAGE, CAP_PANEL, PANEL } from './layout';
import type { ReelConfig } from './ReelConfig';

export const AD_SAFE = { left: 60, right: 1020, top: 250, bottom: 1250 } as const;
/** caption blocks clamp inside the zone with room for their drift, the rise they enter on and, at the bottom, an accent
 *  word's descenders and pop (a Two-Font key word's ink runs about 30 px under its row) */
export const AD_CAPS = { top: 270, bottom: 1200 } as const;
/** the zone is short and the face sits in it: a paid caption block taller than this draws scaled down to it, so a tall
 *  style (a staircase, a three-row Two-Font line) stays low instead of climbing onto the face */
export const AD_CAP_MAX_H = 300;
export const adCapScale = (h: number, paid: boolean) => (paid && h > AD_CAP_MAX_H ? AD_CAP_MAX_H / h : 1);
/** The top band (effect cards, follow and clip cards, organic y 130-650) drops below Meta's top bar and draws at 85%,
 *  so it covers no more of the face than it does organically: y 262-704. One transform, origin (540, 0). */
export const AD_BAND = { k: 0.85, dy: 151.5 } as const;
export const adBandStyle = { transform: `translateY(${AD_BAND.dy}px) scale(${AD_BAND.k})`, transformOrigin: '540px 0px' } as const;
export const AD_PINNED_TOP = 266;      // the pinned line (organic 236)
export const AD_BACK_TOP = 266;        // the words behind the host (organic 7.5% of the height, 144)
export const AD_BACK_FIT = 0.82;       // ...and fit to 82% of the width (organic 90%), so their slow grow stays inside
export const AD_ARROW_NY = 270;        // an arrow note's words (organic 210)
export const AD_CARD_TOP = 270;        // a full-frame card's words (organic 240)
export const AD_GIANT_CAPS = { top: 930, h: 300 } as const;   // giant captions (organic 1080-1500)
export const AD_KICKER_TOP = 124;      // panel-relative: a panel's kicker (organic 64, so y 204)
export const AD_BUTTON_BOTTOM = 330;   // panel-relative: a CTA button's bottom edge (organic 64, so y 1496)
export const AD_PANEL_DY = 60;         // a panel's content sits this much lower, under the lowered kicker (a list box 40 px shorter)

/** Top of a caption block of height h centered on cy. Organic: the style's own bottom limit, as before.
 *  Paid: clamped inside AD_CAPS, so a look's low caption height still lands above Meta's bottom bar. */
export const capTop = (cy: number, h: number, organicBottom: number, paid: boolean) =>
  paid ? Math.max(AD_CAPS.top, Math.min(cy - h / 2, AD_CAPS.bottom - h)) : Math.min(cy - h / 2, organicBottom - h);

/** The words behind the host: one row, fit to the width. k: the face's em width per character (the house heavy caps run 0.74). */
export const backTextSize = (text: string, k: number, paid: boolean) =>
  Math.min(330, (1080 * (paid ? AD_BACK_FIT : 0.9)) / (k * Math.max(text.trim().length, 3)));

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

/** Where a back-text row sits. An entry may carry its own centre (y, x, canvas px) to set the words behind the host's head
 *  wherever the head is in that shot. Without them: organic top 7.5% of the height (as before), paid top 266. A paid row
 *  is held inside the zone with room for its rise-in (70 px from below) and its slow grow. k: em width per character. */
export const backTextPlace = (text: string, k: number, paid: boolean, y?: number, x?: number) => {
  const size = backTextSize(text, k, paid), rowH = size * 0.92, w = k * size * Math.max(text.trim().length, 3);
  let top = y === undefined ? (paid ? AD_BACK_TOP : 1920 * 0.075) : y - rowH / 2;
  let cx = x ?? 540;
  if (paid) {
    top = clamp(top, AD_BACK_TOP, AD_SAFE.bottom - 56 - rowH * 1.03);
    const half = (w * 1.04) / 2;
    cx = half * 2 >= AD_SAFE.right - AD_SAFE.left - 40 ? 540 : clamp(cx, AD_SAFE.left + 20 + half, AD_SAFE.right - 20 - half);
  }
  return { size, top, cx, w, rowH };
};

/** The pinned line's top. y: its centre, canvas px (optional). Paid: held inside the zone. */
export const pinnedTop = (paid: boolean, y?: number) => {
  const top = y === undefined ? (paid ? AD_PINNED_TOP : 236) : y - 33;
  return paid ? clamp(top, AD_PINNED_TOP, AD_SAFE.bottom - 66 - 16) : top;
};

/** An arrow note's words: their top. noteY: their centre, canvas px (optional; the effect's x, y stay the arrow's target). */
export const arrowNoteTop = (text: string, paid: boolean, noteY?: number) => {
  const h = (text.length > 10 ? 2 : 1) * 64;
  const top = noteY === undefined ? (paid ? AD_ARROW_NY : 210) : noteY - h / 2;
  return paid ? clamp(top, AD_ARROW_NY, AD_SAFE.bottom - 20 - h) : top;
};

/** A note wall's shift down from its usual place, in the band's own px (the band draws at 85% in a paid ad). y: the wall's
 *  centre, canvas px (optional). Its notes span band y 160-590, centre 375. Paid: the wall stays inside the zone. */
export const noteWallShift = (paid: boolean, y?: number) => {
  if (y === undefined) return 0;
  if (!paid) return y - 375;
  const half = (430 * AD_BAND.k) / 2;
  const Y = clamp(y, AD_BAND.dy + 160 * AD_BAND.k + half, AD_SAFE.bottom - 30 - half);
  return (Y - AD_BAND.dy) / AD_BAND.k - 375;
};

/** The frame-0 cover title: rows of words, their size, and the block's top. Organic: 128 px from y 1330 (as before).
 *  Paid: fit to the zone's width and set so its last row ends at 1200. */
export const coverLayout = (title: string, paid: boolean) => {
  const words = title.trim().split(/\s+/);
  const mid = Math.ceil(words.length / 2);
  const rows = [words.slice(0, mid), words.slice(mid)].filter((r) => r.length);
  const longest = Math.max(...rows.map((r) => r.join(' ').length));
  const size = paid ? Math.min(128, 900 / (0.6 * longest)) : 128;   // paid: rows fit the 900 px block (x 80-980)
  const h = rows.length * size * 0.98 + 4 * (rows.length - 1);
  return { rows, size, top: paid ? AD_CAPS.bottom - h : 1330, h, width: 0.6 * size * longest };
};

/** The giant list number: centre and size. Paid: centred in the zone, small enough to stay inside it. */
export const giantNumberLayout = (value: string, paid: boolean) => ({
  cx: 520, cy: paid ? 750 : 860, size: paid ? Math.min(680, 800 / (0.56 * Math.max(value.length, 1))) : Math.min(1700, 900 / (0.56 * Math.max(value.length, 1))),
});

/** A full-frame card's words, top to bottom, estimated from the card's own type scale (Slide.tsx, k = 1.3 on a reel). */
const cardHeight = (e: Extract<NonNullable<ReelConfig['effects']>[number], { kind: 'card' }>) => {
  const k = 1.3, inner = 1080 - 2 * 90;
  const lines = e.headline.replace(/==/g, '').split('\n');
  const longest = Math.max(...lines.map((l) => l.length), 6);
  const head = e.layout === 'statement' ? 104 : 84;
  const hs = Math.min(head, inner / k / (0.56 * longest)) * k;
  const rows = (t: string, size: number, w: number) => Math.max(1, Math.ceil((t.length * 0.55 * size) / w));
  let h = lines.length * hs * 1.16;
  if (e.label) h += 30 * k * 1.2 + 26 * k;
  if (e.sub) h += 30 * k + rows(e.sub, 38 * k, inner) * 38 * k * 1.3;
  const items = e.items ?? [];
  if (items.length) h += 40 * k + items.reduce((n, it) => n + Math.max(52 * k, rows(it.t, 44 * k, inner - 76 * k) * 44 * k * 1.2), 0) + 22 * k * (items.length - 1);
  if (e.callout) h += 40 * k + 28 * k + rows(e.callout, 36 * k, inner - 60 * k) * 36 * k * 1.3;
  return h;
};

/** The tallest caption block this reel's caption style can draw (upper bounds of each style's own sizing). */
const captionHeight = (c: ReelConfig) => {
  const L = c.look?.captions ?? {};
  const st = c.captionStyle ?? 'lines';
  const pad = L.plate === 'dark' || (!L.plate && st === 'lines') ? 24 : 0;
  if (st === 'dynamic') return Math.max(2 * 66 * 1.02 + 200 * 0.95, 2 * 96 * 1.02);
  if (st === 'bigword') return 2 * (L.size ? L.size * 0.42 : 56) * 1.15 + (L.size ?? 170);
  if (st === 'pill') return (L.size ?? 96) * 1.5;
  if (st === 'editorial') return 34 * 1.6 + (L.size ?? 190);
  if (st === 'steps') { const small = L.size ? L.size * 0.5 : 64; return (4 * small + small * 2.1) * 1.12; }
  const base = L.size ?? (st === 'word' ? 150 : st === 'punch' ? 128 : CAP_FULL.size);
  return base * 1.05 + pad;
};

export type TextBox = { what: string; x: number; y: number; w: number; h: number };
const band = (what: string, x: number, y: number, w: number, h: number): TextBox =>
  ({ what, x: 540 + (x - 540) * AD_BAND.k, y: AD_BAND.dy + y * AD_BAND.k, w: w * AD_BAND.k, h: h * AD_BAND.k });
const BAND_FX = { x: 160, y: 130, w: 760, h: 520 };

/** Every block of words a paid reel draws, where it rests, from the same layout the components draw it with. */
export const adTextBoxes = (c: ReelConfig): TextBox[] => {
  const out: TextBox[] = [];
  const full = c.scenes.some((s) => s.mode === 'full'), win = c.scenes.some((s) => s.mode === 'window');
  if (full) {
    const h = captionHeight(c) * adCapScale(captionHeight(c), true);
    out.push({ what: 'captions', x: CAP_FULL.x, y: capTop(c.look?.captions?.y ?? c.fullCaptionY ?? CAP_FULL.cy, h, 1600, true), w: CAP_FULL.w, h });
  }
  if (win) out.push({ what: 'captions over the card', x: CAP_STAGE.x, y: CAP_STAGE.top, w: CAP_STAGE.w, h: CAP_STAGE.bottom - CAP_STAGE.top });
  c.swaps.forEach((s, i) => {
    const px = PANEL.x, py = PANEL.y + AD_PANEL_DY, inner = PANEL.w - 2 * 56;
    if (s.kicker) out.push({ what: `panel ${i} kicker`, x: px + 56, y: PANEL.y + AD_KICKER_TOP, w: inner, h: 2 * 28 * 1.3 });
    out.push({ what: `panel ${i} captions`, x: px + CAP_PANEL.x, y: PANEL.y + CAP_PANEL.cy - 60, w: CAP_PANEL.w, h: 120 });
    const k = s.content;
    if (k.kind === 'stat') out.push({ what: `panel ${i} stat`, x: px + 56, y: py + 250, w: inner, h: 210 + 28 + 2 * 50 * 1.15 });
    if (k.kind === 'cta') {
      out.push({ what: `panel ${i} call to action`, x: px + 56, y: py + 190, w: inner, h: 3 * 96 * 1.02 + (k.sub ? 30 + 2 * 44 * 1.25 : 0) });
      out.push({ what: `panel ${i} button "${k.button}"`, x: px + PANEL.w - 56 - (k.button.length * 0.6 * 40 + 80), y: PANEL.y + PANEL.h - AD_BUTTON_BOTTOM - 100, w: k.button.length * 0.6 * 40 + 80, h: 100 });
    }
    if (k.kind === 'checklist' || k.kind === 'funnel' || k.kind === 'decision') out.push({ what: `panel ${i} ${k.kind}`, x: px + 56, y: py + 170, w: inner, h: 600 });
    if (k.kind === 'shot') out.push({ what: `panel ${i} proof shot`, x: px + 56, y: py + 160, w: inner, h: 560 + 50 });
    if (k.kind === 'words') out.push({ what: `panel ${i} words`, x: px + 56, y: py + 170, w: inner, h: 900 - 170 - AD_PANEL_DY });
  });
  (c.backText ?? []).forEach((b) => {
    const p = backTextPlace(b.text, 0.775, true, b.y, b.x), w = p.w * 1.04;   // 0.775: the widest face a look can set
    out.push({ what: `back text "${b.text}"`, x: p.cx - w / 2, y: p.top, w, h: p.rowH * 1.03 });
  });
  (c.inserts ?? []).forEach((b) => out.push(b.kind === 'follow' ? band('follow card', 160, 150, 760, 150) : band('clip card', 160, 130, 760, 428)));
  (c.effects ?? []).forEach((e) => {
    if (e.kind === 'transition' || e.kind === 'snap-zoom' || e.kind === 'lights-down') return;   // no words of their own
    if (e.kind === 'pinned-line') { const w = e.text.length * 0.6 * 34 + 84 + (e.point ? 12 : 0); out.push({ what: `pinned line "${e.text}"`, x: 540 - w / 2, y: pinnedTop(true, e.y), w, h: 66 }); return; }
    if (e.kind === 'arrow-note') {
      const nx = e.x >= 540 ? 190 : 640;
      out.push({ what: `arrow note "${e.text}"`, x: nx, y: arrowNoteTop(e.text, true, e.noteY), w: 270, h: (e.text.length > 10 ? 2 : 1) * 64 });
      out.push({ what: `arrow note "${e.text}" points at`, x: e.x, y: e.y, w: 0, h: 0 });
      return;
    }
    if (e.kind === 'giant-number') { const g = giantNumberLayout(e.value, true); const w = 0.56 * g.size * e.value.length; out.push({ what: `giant number ${e.value}`, x: g.cx - w / 2, y: g.cy - g.size * 0.36, w, h: g.size * 0.72 }); return; }
    if (e.kind === 'giant-captions') { out.push({ what: 'giant captions', x: 120, y: AD_GIANT_CAPS.top, w: 840, h: AD_GIANT_CAPS.h }); return; }
    if (e.kind === 'card') {
      const h = cardHeight(e), mid = (AD_CARD_TOP + 1060) / 2;
      out.push({ what: `card "${e.headline.replace(/==/g, '')}"`, x: 90, y: mid - h / 2, w: 900, h });
      return;
    }
    if (e.kind === 'cover-story') { out.push(band('cover story', 64, 150, 952, 600)); return; }
    if (e.kind === 'note-wall') { out.push(band('note wall', 170, 160 + noteWallShift(true, e.y), 740, 430)); return; }
    if (e.kind === 'word-stamp') { out.push(band(`word stamp "${e.word}"`, BAND_FX.x, BAND_FX.y + 40, BAND_FX.w, 240)); return; }
    out.push(band(`${e.kind} card`, BAND_FX.x, BAND_FX.y, BAND_FX.w, BAND_FX.h));
  });
  if (c.cover) {
    const L = coverLayout(c.cover.title, true);
    out.push({ what: `cover title "${c.cover.title}"`, x: 80, y: L.top, w: L.width, h: L.h });
  }
  return out;
};

/** The words a paid reel would draw outside Meta's ad safe zone (empty: all inside). */
export const adSafeFaults = (c: ReelConfig): string[] => adTextBoxes(c)
  .filter((b) => b.x < AD_SAFE.left - 0.5 || b.x + b.w > AD_SAFE.right + 0.5 || b.y < AD_SAFE.top - 0.5 || b.y + b.h > AD_SAFE.bottom + 0.5)
  .map((b) => `${b.what} sits at x ${Math.round(b.x)}-${Math.round(b.x + b.w)}, y ${Math.round(b.y)}-${Math.round(b.y + b.h)}`);
