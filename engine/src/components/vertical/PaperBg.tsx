import React from 'react';
import { AbsoluteFill } from 'remotion';
import { CREME } from '../vc/style';

/**
 * The LIGHT stage (a "paper" run), from the engine's existing CREME tokens: a warm cream
 * gradient with a fine ink grid, so a light run reads as a chapter change from the charcoal
 * stage. Grid drawn in screen space like CharcoalBg; the parent drifts it (never a still).
 */
export const PaperBg: React.FC = () => (
  <AbsoluteFill style={{ background: `linear-gradient(180deg, ${CREME.bg1} 0%, ${CREME.bg2} 100%)` }}>
    <AbsoluteFill style={{
      backgroundImage: 'linear-gradient(rgba(42,32,23,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(42,32,23,0.06) 1px, transparent 1px)',
      backgroundSize: '12px 12px',
    }} />
    <AbsoluteFill style={{ background: 'radial-gradient(120% 90% at 50% 40%, transparent 60%, rgba(80,60,30,0.14))' }} />
  </AbsoluteFill>
);
