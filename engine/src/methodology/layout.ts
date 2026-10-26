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
