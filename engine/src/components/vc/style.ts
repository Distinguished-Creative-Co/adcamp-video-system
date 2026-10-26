/**
 * Style tokens shared by every vertical component: canvas, palettes, z-order, timing helper.
 * Brand colours flow in from engine.config.ts (and so from brand.json).
 */
import { ENGINE, hexToRgb } from '../../engine.config';

export const FPS = ENGINE.canvas.fps;
export const CANVAS = { w: ENGINE.canvas.width, h: ENGINE.canvas.height } as const;

export const ACCENT_RGB = hexToRgb(ENGINE.brand.accent);
export const glow = (a: number | string) => `rgba(${ACCENT_RGB},${a})`;

export const DIAGRAM = {
  w: 760,
  h: 560,
  top: 150,
  containerW: 1040,
  containerH: 700,
  leftByOpen: { l: 60, r: CANVAS.w - 1100 },
  capXByOpen: { l: 120, r: CANVAS.w - 1000 },
} as const;

/** The light "paper" palette. */
export const CREME = {
  bg1: '#F4ECDA',
  bg2: '#ECD7B8',
  ink: '#2A2017',
  inkDim: 'rgba(42,32,23,0.55)',
  coral: '#D97757',
  teal: '#2E8B82',
  card: '#FFFFFF',
  chip: '#F4EFE5',
  gridLine: 'rgba(255,251,243,0.55)',
  cardShadow: '0 34px 70px rgba(80,60,30,0.24)',
  chipShadow: '0 12px 24px rgba(80,60,30,0.16)',
} as const;

/** The dark charcoal palette. */
export const CREME_DARK = {
  ink: '#EFEAE0',
  inkDim: 'rgba(239,234,224,0.60)',
  coral: '#E8916F',
  teal: '#2E8B82',
  card: '#FFFFFF',
  cardText: '#2A2017',
  chip: '#F4EFE5',
  cardBorder: 'rgba(245,243,238,0.12)',
  cardShadow: '0 30px 64px rgba(0,0,0,0.58), 0 1px 0 0 rgba(255,255,255,0.7) inset',
  chipShadow: '0 12px 24px rgba(0,0,0,0.45)',
} as const;

/**
 * The accent family. Contrast rule: a dark surface carries an accent or white mark, a solid
 * accent surface carries the dark `ink` mark. Never white on the accent.
 */
export const GOLD = {
  yellow: ENGINE.brand.accent,
  lite: ENGINE.brand.lite,
  deep: ENGINE.brand.deep,
  ink: ENGINE.brand.ink,
  label: ENGINE.brand.label,
} as const;

/** The brand accent as text over footage: a dark brand color (navy, forest green, black) is lifted toward white until
 *  it reads on any shot. A bright accent comes back unchanged. */
const lum = (rgb: number[]) => {
  const l = rgb.map((v) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2];
};
const readable = (hex: string): string => {
  const base = hexToRgb(hex).split(',').map(Number);
  if (lum(base) >= 0.15) return hex;   // mid and bright colors (red, orange, green, yellow) read with the shadow as they are
  for (let t = 0; t <= 1.0001; t += 0.05) {
    const c = base.map((v) => Math.round(v + (255 - v) * t));
    if (lum(c) >= 0.5) return t === 0 ? hex : '#' + c.map((v) => v.toString(16).padStart(2, '0')).join('').toUpperCase();
  }
  return '#FFFFFF';
};
export const ACCENT_ON_FOOTAGE = readable(GOLD.yellow);
/** Text on a fill of the exact brand accent (a light-stage highlight, a funnel's last stage, a picked option): the house
 *  dark ink, or white when the brand color is dark. */
export const INK_ON_ACCENT = lum(hexToRgb(GOLD.yellow).split(',').map(Number)) < 0.35 ? '#FFFFFF' : GOLD.ink;
/** Any accent as text on a dark surface (footage, an ink card): lifted when it is too dark to read. */
export const readableAccent = (hex: string): string => readable(hex);
/** The mark on a solid accent fill (a highlight box, a tick, a pill): dark on a light accent, white on a dark one. */
export const inkOn = (hex: string): string => (lum(hexToRgb(hex).split(',').map(Number)) < 0.35 ? '#FFFFFF' : '#141414');

/** A look color: "accent" is the member's brand accent (so a starter look carries their brand), else #RRGGBB. Text
 *  over footage passes through ACCENT_ON_FOOTAGE so a dark brand color stays readable. */
export const lookColor = (c: string | undefined, fallback: string): string =>
  c === 'accent' ? ACCENT_ON_FOOTAGE : c ?? (fallback === GOLD.yellow ? ACCENT_ON_FOOTAGE : fallback);

/** A dollar amount as one caption word: $200, $1,200, $49.99, $5k, $20,000+, $199/month, "$200", ($200). Trailing punctuation allowed. */
export const MONEY = /^["\u201c(]?\$\d[\d,]*(\.\d+)?[kKmMbB]?\+?(\/(mo|month|yr|year|wk|week|hr|hour))?[.,!?;:"\u201d)]*$/;
/** The look's money color for a caption word that is a dollar amount, else undefined. Off unless a look sets captions.money. */
export const moneyColor = (t: string, look?: { money?: string }): string | undefined =>
  look?.money && MONEY.test(t.trim()) ? lookColor(look.money, look.money) : undefined;

export const Z = { base: 0, broll: 10, sideFill: 20, avatar: 30, over: 40, card: 50, fade: 90 } as const;

/** Seconds to frames at the engine rate. */
export const sec = (s: number) => Math.round(s * FPS);
