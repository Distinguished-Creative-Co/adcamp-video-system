/**
 * LAYOUT + CAMERA MATH — pure functions, no Remotion imports (tested directly by
 * scripts/test_layout.mjs under Node). Engine-side constants: never per video.
 *
 * Instagram Reels UI covers the bottom 320px and the right 120px of 1080x1920, so every
 * caption, card edge, panel text and CTA stays inside x < SAFE.xMax and y < SAFE.yMax.
 *
 * THE CARD. A face this close to the lens spans about 1080 source rows (hair to chin).
 * A viewport shows h / scale source rows under cover fit, so a wide lower-third card
 * cannot show the whole head. 600x760 gives scale 0.556 and a 1368-row band: the full
 * head with headroom, glass bottom at 1560 (40px above the IG UI), right edge at 840.
 */
export const CANVAS = { w: 1080, h: 1920 } as const;
export const FPS = 30;
export const SAFE = { xMax: 960, yMax: 1600 } as const;

export const GLIDE_F = 20;   // full <-> card morph (0.67s)
export const SWAP_F = 18;    // card <-> panel swap (0.6s)
export const LEAD_F = 5;     // a word pops this many frames before it is voiced
export const HOLD_S = 1.2;   // a finished line lingers at most this long
export const BREATH_F = 90;  // plain speaker between two panel swaps (3s of the speaker between takeovers)
export const ENTER_F = 12;   // a panel element's entrance
export const SETTLE_F = 30;  // a panel's last element is settled at least this long before it slides out (the settle rule)

export type View = { x: number; y: number; w: number; h: number; r: number; ax: number; ay: number };
export type Rect = { x: number; y: number; w: number; h: number };

export const CARD: View = { x: 240, y: 800, w: 600, h: 760, r: 28, ax: 0.5, ay: 0.48 };
export const PANEL: Rect & { r: number } = { x: 60, y: 140, w: 860, h: 1420, r: 32 }; // right edge 920: 40px clear of the IG action rail
export const PANEL_ENTER_X = CANVAS.w + 60;      // panel waits fully off the right edge
export const CARD_EXIT_DX = -(CARD.x + CARD.w + 80); // card leaves fully off the left edge
export const CARD_HOST: View = { x: 60, y: 1100, w: 290, h: 360, r: 26, ax: 0.5, ay: 0.46 }; // the host's corner window while a full-frame card is up (above the app's bottom strip)
export const INSET: View = { x: 56, y: 996, w: 280, h: 360, r: 24, ax: 0.5, ay: 0.48 }; // panel-relative

// caption regions (absolute unless noted)
export const CAP_FULL = { x: 120, w: 840, cy: 1360, size: 74, min: 50 };
export const CAP_STAGE = { x: 110, w: 850, top: 250, bottom: 760, size: 76, min: 54 };
export const CAP_PANEL = { x: 56, w: 748, cy: 880, size: 58, min: 42 }; // panel-relative

export const fullView = (faceX: number, faceY: number, sW: number, sH: number): View => ({
  x: 0, y: 0, w: CANVAS.w, h: CANVAS.h, r: 0, ax: faceX / sW, ay: faceY / sH,
});

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export const lerpView = (a: View, b: View, t: number): View => ({
  x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t), w: lerp(a.w, b.w, t), h: lerp(a.h, b.h, t),
  r: lerp(a.r, b.r, t), ax: lerp(a.ax, b.ax, t), ay: lerp(a.ay, b.ay, t),
});

/** Where the source plane sits inside a view, face-anchored. Cover fit + clamp means the
 *  plane ALWAYS covers the viewport: footage edges cannot show at any zoom >= 1. */
export const place = (v: View, zoom: number, faceX: number, faceY: number, sW: number, sH: number) => {
  const s = Math.max(v.w / sW, v.h / sH) * Math.max(zoom, 1);
  const tx = clamp(v.ax * v.w - faceX * s, v.w - sW * s, 0);
  const ty = clamp(v.ay * v.h - faceY * s, v.h - sH * s, 0);
  return { left: tx, top: ty, width: sW * s, height: sH * s, scale: s };
};

export const easeOutCubic = (t: number) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);

export const easeInOutCubic = (t: number) => { const x = clamp(t, 0, 1); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };

/** DRIFT: the faint idle breath on a graphic that holds still, so it never reads as a frozen sticker. A slow swell
 *  (scale up to 1 + DRIFT_SCALE) with a couple of pixels of float, one cycle every DRIFT_F frames, faded in over 12
 *  frames once the entrance is done. Per frame and pure (Remotion renders frames in any order). `phase` (0-1) staggers
 *  graphics that hold together (Note Wall's notes). */
export const DRIFT_F = 108;       // 3.6 s a breath
export const DRIFT_SCALE = 0.012;
export const DRIFT_Y = 3;         // px
export const drift = (lf: number, enter = 10, phase = 0) => {
  const on = clamp((lf - enter) / 12, 0, 1);
  const k = on * on * (3 - 2 * on);
  const w = (2 * Math.PI * Math.max(0, lf - enter)) / DRIFT_F + 2 * Math.PI * phase;
  const swell = (1 - Math.cos(w)) / 2;   // 0 at the start of a breath, so it starts from rest
  return { scale: 1 + DRIFT_SCALE * k * swell, dy: -DRIFT_Y * k * Math.sin(w) };
};

/** PUSH: a camera push onto one region of a picture shown in a frame `vw` x `vh` (a screenshot inside its card).
 *  `pic` is where the picture sits in that frame at rest (it may be narrower or shorter than the frame: a tall phone
 *  screenshot stands in the middle of a wide card), `box` the region in the same frame coordinates, `p` (0-1) how far
 *  the push has gone. Returns the scale and offset for a layer laid out like the frame (transform-origin 0 0). On each
 *  axis: while the picture is smaller than the frame it stays centred, once it is larger it never shows an edge inside
 *  the frame and the region's centre moves toward the middle. The scale stops at `kMax` (pushMaxFor: how far the
 *  screenshot's own pixels allow), so a push never turns into a blur. p = 0 is exactly the picture at rest. */
export const PUSH_MAX = 2.5;      // the default cap when no screenshot size is known
export const PUSH_MAX_HI = 4;     // the most any screenshot is ever pushed
export const PUSH_UPSCALE = 1.7;  // a push never blows the screenshot's own pixels up past this
export const PUSH_FILL = 0.86;    // the region fills this much of the frame at the end of the push
/** the push a screenshot's own resolution allows: shown at `shown` px wide from `srcW` real pixels. A desktop capture
 *  shown at two thirds goes to about 2.5x, a phone capture shown small to 4x, one already blown up gets no push. */
export const pushMaxFor = (srcW: number, shown: number) => clamp((PUSH_UPSCALE * srcW) / Math.max(shown, 1), 1, PUSH_MAX_HI);
export const pushTarget = (vw: number, vh: number, box: Rect, kMax = PUSH_MAX) =>
  clamp(Math.min((vw * PUSH_FILL) / Math.max(box.w, 1), (vh * PUSH_FILL) / Math.max(box.h, 1)), 1, kMax);
export const pushCam = (vw: number, vh: number, pic: Rect, box: Rect, p: number, kMax = PUSH_MAX) => {
  const k = 1 + (pushTarget(vw, vh, box, kMax) - 1) * clamp(p, 0, 1);
  const axis = (v: number, o: number, d: number, c: number) =>
    d * k >= v - 1e-9 ? clamp(v / 2 - c * k, v - (o + d) * k, -o * k) : (v - d * k) / 2 - o * k;
  return { k, tx: axis(vw, pic.x, pic.w, box.x + box.w / 2), ty: axis(vh, pic.y, pic.h, box.y + box.h / 2) };
};
/** the plain case: the picture fills its frame */
export const pushTo = (dw: number, dh: number, box: Rect, p: number, kMax = PUSH_MAX) =>
  pushCam(dw, dh, { x: 0, y: 0, w: dw, h: dh }, box, p, kMax);
/** a box clipped to the picture, so a mark drawn past an edge never aims the push off the picture; null (no push) when
 *  the box misses the picture altogether (a mark placed off the screenshot in an older video) */
export const clipBox = (b: Rect, pic: Rect): Rect | null => {
  const x0 = Math.max(pic.x, b.x), y0 = Math.max(pic.y, b.y), x1 = Math.min(pic.x + pic.w, b.x + b.w), y1 = Math.min(pic.y + pic.h, b.y + b.h);
  return x1 - x0 >= 4 && y1 - y0 >= 4 ? { x: x0, y: y0, w: x1 - x0, h: y1 - y0 } : null;
};
/** The region a Live Markup push aims at: the mark (X, Y, MW, MH in frame px) and everything its pen draws, as
 *  Effects.tsx draws it: the circle an ellipse 14/12 px outside the mark tilted 4 degrees, the underline a curve up to
 *  22 px below, the arrow a curve from 90 right and 70 above to its head beside the mark's middle (head 18 px tall). */
export const MARK_PEN = 9;   // half the widest pen, plus a pixel
export const markReach = (shape: 'circle' | 'underline' | 'arrow', X: number, Y: number, MW: number, MH: number): Rect => {
  if (shape === 'circle') {
    const rx = MW / 2 + 14, ry = MH / 2 + 12, t = (4 * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t);
    const hw = Math.sqrt(rx * rx * c * c + ry * ry * s * s) + MARK_PEN, hh = Math.sqrt(rx * rx * s * s + ry * ry * c * c) + MARK_PEN;
    return { x: X + MW / 2 - hw, y: Y + MH / 2 - hh, w: 2 * hw, h: 2 * hh };
  }
  if (shape === 'underline') return { x: X - 6 - MARK_PEN, y: Y - MARK_PEN, w: MW + 12 + 2 * MARK_PEN, h: MH + 22 + 2 * MARK_PEN };
  const top = Math.min(Y, Y - 70), bottom = Math.max(Y + MH, Y + MH / 2 + 18);
  return { x: X - MARK_PEN, y: top - MARK_PEN, w: MW + 90 + 2 * MARK_PEN, h: bottom - top + 2 * MARK_PEN };
};
/** Page Scroll to a focus: where the page stops (its top, px, 0 or negative) so the focus centre sits mid-view, as far
 *  as the page allows */
export const scrollStop = (focusY: number, focusH: number, sc: number, viewH: number, travel: number) =>
  -Math.min(travel, Math.max(0, (focusY + focusH / 2) * sc - viewH / 2));

/** When a push runs inside an effect `len` frames long that starts at `from`: PUSH_F frames (PUSH_MIN_F at the least),
 *  ending PUSH_HOLD_F frames before the effect ends, so it holds 8 frames at full strength before the 8-frame fade.
 *  null when there is no room: then no push, never a rushed one. */
export const PUSH_F = 16;
export const PUSH_MIN_F = 12;
export const PUSH_HOLD_F = 16;
export const pushWindow = (from: number, len: number): { a: number; b: number } | null => {
  const b = Math.min(from + PUSH_F, len - PUSH_HOLD_F);
  return b - from >= PUSH_MIN_F ? { a: from, b } : null;
};

/** The completion rule, made structural: element cue frames (word-anchored) shift
 *  EARLIER together, stagger preserved, so the last one has finished entering at least
 *  SETTLE_F before `deadline`. Returns null when the build cannot fit after `earliest`
 *  (simplify the graphic; never move audio or later beats). */
export const completionTimes = (ats: number[], deadline: number, earliest: number): number[] | null => {
  if (!ats.length) return ats;
  const last = ats[ats.length - 1] + ENTER_F;
  const advance = Math.max(0, last - (deadline - SETTLE_F));
  const out = ats.map((a) => a - advance);
  return out[0] < earliest ? null : out;
};
