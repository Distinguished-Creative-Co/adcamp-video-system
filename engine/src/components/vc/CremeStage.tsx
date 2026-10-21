import React from 'react';
import { AbsoluteFill } from 'remotion';

/**
 * The DARK stage: a charcoal radial base, a fine square grid, an optional coarser major grid,
 * and a vignette on top. Grid lines are whole pixels so they never shimmer under h.264.
 * PaperBg.tsx is the light counterpart.
 */
export type CharcoalVariant = 'A' | 'B';

type Grid = { cell: number; line: string; width: number };
type Look = { base: string; grid: Grid; gridOpacity: number; major?: Grid; vignette: string };

const LOOKS: Record<CharcoalVariant, Look> = {
  A: {
    base: 'radial-gradient(130% 110% at 50% 0%, #24272D 0%, #1A1C21 55%, #131419 100%)',
    grid: { cell: 12, line: 'rgba(245,243,238,0.05)', width: 1 },
    gridOpacity: 0.9,
    vignette: 'radial-gradient(120% 90% at 50% 40%, transparent 55%, rgba(0,0,0,0.36))',
  },
  B: {
    base: 'radial-gradient(130% 110% at 50% 0%, #25282E 0%, #1B1D22 48%, #141518 100%)',
    grid: { cell: 12, line: 'rgba(245,243,238,0.07)', width: 1 },
    gridOpacity: 1,
    major: { cell: 60, line: 'rgba(245,243,238,0.10)', width: 1 },
    vignette: 'radial-gradient(120% 95% at 50% 38%, transparent 50%, rgba(6,6,8,0.46))',
  },
};

const gridLayer = (g: Grid, opacity = 1): React.CSSProperties => ({
  backgroundImage: `linear-gradient(${g.line} ${g.width}px, transparent ${g.width}px), linear-gradient(90deg, ${g.line} ${g.width}px, transparent ${g.width}px)`,
  backgroundSize: `${g.cell}px ${g.cell}px`,
  opacity,
});

export const CharcoalBg: React.FC<{ variant?: CharcoalVariant }> = ({ variant = 'A' }) => {
  const look = LOOKS[variant];
  return (
    <AbsoluteFill style={{ background: look.base }}>
      <AbsoluteFill style={gridLayer(look.grid, look.gridOpacity)} />
      {look.major ? <AbsoluteFill style={gridLayer(look.major)} /> : null}
      <AbsoluteFill style={{ background: look.vignette, pointerEvents: 'none' }} />
    </AbsoluteFill>
  );
};
