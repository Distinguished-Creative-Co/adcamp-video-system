/**
 * THE BRAND KNOBS. One place for the accent colour and the canvas, read by the style tokens
 * (components/vc/style.ts). The accent comes from src/brand.json, so a rebrand is a JSON edit
 * and a re-render, never a code change.
 */
import brand from './brand.json';

/** '#RRGGBB' (or '#RGB') -> 'r,g,b', for rgba() strings. */
export const hexToRgb = (hex: string): string => {
  let h = hex.replace('#', '').trim();
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  const n = parseInt(h.slice(0, 6), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(',');
};

/** Mix a colour toward white (t > 0) or black (t < 0) by |t|. Returns uppercase '#RRGGBB'. */
const shade = (hex: string, t: number): string => {
  const ch = hexToRgb(hex).split(',').map(Number).map((c) => Math.round(t > 0 ? c + (255 - c) * t : c * (1 + t)));
  return '#' + ch.map((c) => Math.min(255, Math.max(0, c)).toString(16).padStart(2, '0')).join('').toUpperCase();
};

export const ENGINE = {
  brand: {
    accent: brand.accent,
    lite: shade(brand.accent, 0.18),
    deep: shade(brand.accent, -0.04),
    ink: '#1A1C21',     // the dark mark on a solid accent surface
    label: '#F5F1EA',   // light label text on a dark card
  },
  avatar: { src: 'host/video1.mp4', faceX: 950 },   // legacy fields, kept for type compatibility
  canvas: { width: 1080, height: 1920, fps: 30 },
} as const;
