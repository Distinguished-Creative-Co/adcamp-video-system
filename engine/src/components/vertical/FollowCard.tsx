import React from 'react';
import { Img, staticFile } from 'remotion';
import brand from '../../brand.json';
import { CREME_DARK, GOLD, glow } from '../vc/style';
import { SANS } from '../vc/fonts';
import { easeOutCubic } from '../../methodology/layout';
import type { FollowInsert } from '../../methodology/ReelConfig';

/**
 * The profile-follow insert: a floating card with the person's photo, name and handle, and a
 * Follow pill that gets "tapped" and flips to Following while the card is up. Drawn in
 * viewport space over a full-screen scene, in the top band where the face never sits, inside
 * the safe zone (x 160-920, y 150-300). Identity comes from src/brand.json (handle, name,
 * avatar), each overridable on the insert. No photo on disk: initials in a circle instead.
 */
const CARD = { x: 160, y: 150, w: 760, h: 150, r: 34 } as const;   // right edge 920, clear of the action rail
const ENTER_F = 10;   // slide in
const TAP_AT = 22;    // frames after entry when the pill is tapped
const TAP_F = 8;      // press and release
const EXIT_F = 8;     // fade out before the insert ends

const initials = (name: string) => name.trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? '').join('');

export const FollowCard: React.FC<{ insert: FollowInsert; lf: number; len: number }> = ({ insert, lf, len }) => {
  const name = insert.name ?? brand.name ?? '';
  const handle = insert.handle ?? brand.handle ?? '';
  const avatar = insert.avatar ?? brand.avatar ?? '';
  const e = easeOutCubic(lf / ENTER_F);
  const outP = Math.min(1, Math.max(0, (len - lf) / EXIT_F));
  const tapP = Math.min(1, Math.max(0, (lf - TAP_AT) / TAP_F));            // 0 before the tap, 1 after
  const press = tapP <= 0 || tapP >= 1 ? 0 : Math.sin(tapP * Math.PI);     // one dip of the pill
  const followed = lf >= TAP_AT + TAP_F / 2;
  const burst = Math.min(1, Math.max(0, (lf - (TAP_AT + TAP_F / 2)) / 14)); // soft glow after the flip
  const dark = { fontFamily: SANS, color: CREME_DARK.ink } as React.CSSProperties;
  const handleSize = Math.min(30, Math.max(22, 330 / (0.56 * Math.max(handle.length, 12))))   // room left beside the Following pill;   // a long handle shrinks instead of clipping
  return (
    <div style={{
      position: 'absolute', left: CARD.x, top: CARD.y, width: CARD.w, height: CARD.h, borderRadius: CARD.r,
      display: 'flex', alignItems: 'center', gap: 22, padding: '0 24px', boxSizing: 'border-box',
      background: 'rgba(20,21,26,0.74)', backdropFilter: 'blur(18px)', WebkitBackdropFilter: 'blur(18px)',
      border: '1px solid rgba(255,255,255,0.14)', boxShadow: '0 24px 60px rgba(0,0,0,0.45)',
      opacity: e * outP, transform: `translateY(${(1 - e) * -40 - (1 - outP) * 20}px)`,
    }}>
      <div style={{ width: 104, height: 104, borderRadius: 52, flex: 'none', overflow: 'hidden', boxSizing: 'border-box',
        border: `3px solid ${GOLD.yellow}`, background: '#2A2D34', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {avatar ? (
          <Img src={staticFile(avatar)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : (
          <span style={{ ...dark, fontWeight: 800, fontSize: 40 }}>{initials(name)}</span>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0, flex: 1 }}>
        <span style={{ ...dark, fontWeight: 700, fontSize: 40, lineHeight: 1.05, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</span>
        <span style={{ fontFamily: SANS, fontWeight: 500, fontSize: handleSize, color: CREME_DARK.inkDim, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{handle}</span>
      </div>
      <div style={{
        flex: 'none', height: 72, padding: '0 28px', borderRadius: 36, display: 'flex', alignItems: 'center', gap: 12,
        fontFamily: SANS, fontWeight: 800, fontSize: 32, whiteSpace: 'nowrap',
        background: followed ? 'rgba(255,255,255,0.14)' : GOLD.yellow, color: followed ? CREME_DARK.ink : GOLD.ink,
        border: followed ? '1px solid rgba(255,255,255,0.25)' : '1px solid transparent', boxSizing: 'border-box',
        transform: `scale(${1 - 0.08 * press})`,
        boxShadow: followed ? `0 0 ${Math.round(40 * (1 - burst))}px ${glow((0.6 * (1 - burst)).toFixed(3))}` : `0 8px 24px ${glow(0.25)}`,
      }}>
        {followed ? (
          <>
            <svg width={30} height={30} viewBox="0 0 40 40"><path d="M10 21 L17 28 L30 13" fill="none" stroke={CREME_DARK.ink} strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Following
          </>
        ) : 'Follow'}
      </div>
    </div>
  );
};
