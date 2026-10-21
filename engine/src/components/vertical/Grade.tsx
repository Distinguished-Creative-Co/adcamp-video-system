import React from 'react';
import { gradeFilter, vignetteBg, type Grade } from '../../methodology/ReelConfig';

/**
 * The host-footage grade, shared by every place the footage is drawn (AvatarView, Cover,
 * Companion). `film` (0-1) blends per-channel tone curves toward a teal-and-orange film look:
 * shadows lean teal, skin and highlights lean warm, whites roll off instead of clipping.
 * It runs as an inline SVG filter ahead of the CSS exposure/contrast/saturation/warmth chain.
 */
const ID = [0, 0.2, 0.4, 0.6, 0.8, 1];
const FILM = {
  // shadows lean teal, mids keep a little warmth for skin, highlights land neutral so whites and grays stay clean
  r: [0.0, 0.17, 0.44, 0.67, 0.85, 0.94],
  g: [0.01, 0.18, 0.43, 0.66, 0.84, 0.94],
  b: [0.05, 0.21, 0.42, 0.64, 0.83, 0.93],
};
const table = (ch: number[], k: number) => ID.map((v, i) => (v + (ch[i] - v) * k).toFixed(3)).join(' ');

export const useGrade = (g?: Grade | null) => {
  const id = 'grade-' + React.useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const k = g?.film ?? 0;
  const css = gradeFilter(g);
  const filter = k > 0 ? [`url(#${id})`, css].filter(Boolean).join(' ') : css;
  const defs = k > 0 ? (
    <svg width={0} height={0} style={{ position: 'absolute' }} aria-hidden>
      <filter id={id} colorInterpolationFilters="sRGB">
        <feComponentTransfer>
          <feFuncR type="table" tableValues={table(FILM.r, k)} />
          <feFuncG type="table" tableValues={table(FILM.g, k)} />
          <feFuncB type="table" tableValues={table(FILM.b, k)} />
        </feComponentTransfer>
      </filter>
    </svg>
  ) : null;
  const vignette = vignetteBg(g) ? <div style={{ position: 'absolute', inset: 0, background: vignetteBg(g) }} /> : null;
  return { filter, defs, vignette };
};
