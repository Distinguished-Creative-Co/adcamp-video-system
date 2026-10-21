import React from 'react';
import { OffthreadVideo, staticFile } from 'remotion';
import { CREME_DARK } from '../vc/style';
import { SANS } from '../vc/fonts';
import { easeOutCubic } from '../../methodology/layout';
import type { ClipInsert } from '../../methodology/ReelConfig';

/**
 * The cutaway insert: one of the person's OWN clips (their office, their hands, their screen)
 * playing muted in a rounded 16:9 card in the top band while they keep talking underneath.
 * The person never leaves the screen. Clips are prepared by scripts/prep_insert.py into
 * public/inserts/. An optional label sits in the card's bottom-left corner.
 */
const CARD = { x: 160, y: 130, w: 760, h: 428, r: 34 } as const;   // right edge 920, clear of the action rail
const ENTER_F = 10;
const EXIT_F = 8;

export const ClipCard: React.FC<{ insert: ClipInsert; lf: number; len: number }> = ({ insert, lf, len }) => {
  const e = easeOutCubic(lf / ENTER_F);
  const outP = Math.min(1, Math.max(0, (len - lf) / EXIT_F));
  const startFrom = Math.round((insert.start ?? 0) * 30);
  return (
    <div style={{
      position: 'absolute', left: CARD.x, top: CARD.y, width: CARD.w, height: CARD.h, borderRadius: CARD.r, overflow: 'hidden',
      background: '#15171C', border: '1px solid rgba(255,255,255,0.16)', boxShadow: '0 28px 70px rgba(0,0,0,0.5)',
      opacity: e * outP, transform: `translateY(${(1 - e) * -40 - (1 - outP) * 20}px) scale(${0.96 + 0.04 * e})`, transformOrigin: '50% 0%',
    }}>
      <OffthreadVideo muted src={staticFile(insert.src)} startFrom={startFrom} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      {insert.label ? (
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '48px 26px 20px', background: 'linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.62) 100%)' }}>
          <span style={{ fontFamily: SANS, fontWeight: 600, fontSize: 30, color: CREME_DARK.ink, letterSpacing: '0.01em' }}>{insert.label}</span>
        </div>
      ) : null}
      <div style={{ position: 'absolute', inset: 0, borderRadius: CARD.r, boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.25)', pointerEvents: 'none' }} />
    </div>
  );
};
