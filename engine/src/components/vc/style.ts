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

export const Z = { base: 0, broll: 10, sideFill: 20, avatar: 30, over: 40, card: 50, fade: 90 } as const;

/** Seconds to frames at the engine rate. */
export const sec = (s: number) => Math.round(s * FPS);
