import React from 'react';
import { GOLD, ACCENT_ON_FOOTAGE } from '../vc/style';
import { SANS, accentFace, handFace, romanSerif } from '../vc/fonts';
import { easeOutCubic } from '../../methodology/layout';
import type { Effect } from '../../methodology/ReelConfig';

/**
 * More effects (AVS 2.0), same rules as Effects.tsx: anchored to spoken frames, in the TOP BAND (x 160-920,
 * y 130-650) or clear of the face, colours and fonts from the brand, words through the spoken-words guard.
 *   list-tracker  a header that steps through a list ("01/04" and the item) and stays up
 *   snap-zoom     a slow creep onto the face, then a hard snap tighter on one word (a camera move: snapZoomAt)
 *   quote-card    words someone said, typed on inside quote marks
 *   pinned-line   one short line pinned at the top, stepping aside while another top-band effect is up
 *   cover-story   the frame as a magazine cover: a big serif title, small cover lines, a strap line
 *   note-wall     paper notes with short lines stick up around the head, one per beat
 *   arrow-note    a handwritten note with an arrow drawn to a point on screen
 *   comment-box   the keyword types into a comment field, it posts, a heart pops
 */
const BAND = { x: 160, y: 130, w: 760, h: 520 } as const;
const PLATE = 'rgba(20,21,26,0.86)';
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const env = (lf: number, len: number, enter = 10) => ({ e: easeOutCubic(lf / enter), out: clamp01((len - lf) / 8) });
const pad2 = (n: number) => String(n).padStart(2, '0');

const Plate: React.FC<{ lf: number; len: number; top?: number; h?: number; children: React.ReactNode }> = ({ lf, len, top = BAND.y, h, children }) => {
  const { e, out } = env(lf, len);
  return (
    <div style={{ position: 'absolute', left: BAND.x, top, width: BAND.w, height: h, borderRadius: 28, background: PLATE, padding: '26px 34px',
      boxSizing: 'border-box', border: '1px solid rgba(255,255,255,0.14)', boxShadow: '0 24px 60px rgba(0,0,0,0.45)',
      opacity: e * out, transform: `translateY(${(1 - e) * -30}px)` }}>{children}</div>
  );
};

export const ListTracker: React.FC<{ fx: Extract<Effect, { kind: 'list-tracker' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const f = fx.in + lf;
  const n = fx.items.filter((it) => it.at <= f).length;
  const cur = n ? fx.items[n - 1] : null;
  const p = cur ? easeOutCubic(clamp01((f - cur.at) / 7)) : 0;
  const size = cur ? Math.min(64, 560 / (0.56 * Math.max(cur.t.length, 6))) : 64;
  return (
    <Plate lf={lf} len={len} h={200}>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 26, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.62)' }}>{fx.title}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 22, marginTop: 14, overflow: 'hidden', height: 90 }}>
        <span style={{ fontFamily: SANS, fontWeight: 900, fontSize: 58, color: ACCENT_ON_FOOTAGE, minWidth: 150 }}>{pad2(n)}<span style={{ opacity: 0.5, fontSize: 34 }}>/{pad2(fx.items.length)}</span></span>
        {cur ? <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: size, color: '#fff', whiteSpace: 'nowrap', opacity: p, transform: `translateY(${(1 - p) * 40}px)`, display: 'inline-block' }}>{cur.t}</span> : null}
      </div>
    </Plate>
  );
};

/** snap-zoom as a camera factor: 1.0 -> a slow creep to 1.05 until `at`, a snap to `scale`, hold, ease home. */
export const snapZoomAt = (fx: Extract<Effect, { kind: 'snap-zoom' }>, frame: number): number => {
  if (frame < fx.in || frame >= fx.out) return 1;
  const s = fx.scale ?? 1.15;
  if (frame < fx.at) return 1 + 0.05 * easeOutCubic((frame - fx.in) / Math.max(fx.at - fx.in, 1));
  const home = clamp01((fx.out - frame) / 12);
  const snap = easeOutCubic(clamp01((frame - fx.at) / 2));
  return 1 + ((1.05 + (s - 1.05) * snap) - 1) * home;
};

export const QuoteCard: React.FC<{ fx: Extract<Effect, { kind: 'quote-card' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const face = accentFace();
  const shown = Math.floor(clamp01((lf - 6) / Math.max(fx.text.length / 1.6, 1)) * fx.text.length);
  const size = Math.min(56, 660 / (face.width * Math.sqrt(fx.text.length * 9)));
  return (
    <Plate lf={lf} len={len}>
      <div style={{ fontFamily: face.family, fontStyle: 'italic', fontWeight: face.weight, fontSize: 130, lineHeight: 0.7, color: ACCENT_ON_FOOTAGE, height: 70 }}>&ldquo;</div>
      <div style={{ fontFamily: face.family, fontStyle: 'italic', fontWeight: face.weight, fontSize: size, lineHeight: 1.22, color: '#fff', minHeight: 280 }}>
        {fx.text.slice(0, shown)}<span style={{ opacity: 0 }}>{fx.text.slice(shown)}</span>
      </div>
      {fx.who ? <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 26, color: 'rgba(255,255,255,0.62)', marginTop: 10 }}>{fx.who}</div> : null}
    </Plate>
  );
};

export const PinnedLine: React.FC<{ fx: Extract<Effect, { kind: 'pinned-line' }>; lf: number; len: number; away: number }> = ({ fx, lf, len, away }) => {
  const { e, out } = env(lf, len, 8);
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, top: 236, display: 'flex', justifyContent: 'center', opacity: e * out * (1 - away) }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, background: PLATE, borderRadius: 999, padding: '12px 28px', border: '1px solid rgba(255,255,255,0.16)',
        fontFamily: SANS, fontWeight: 800, fontSize: 34, color: '#fff', transform: `translateY(${(1 - e) * -20}px)` }}>
        <span style={{ width: 14, height: 14, borderRadius: '50%', background: ACCENT_ON_FOOTAGE, display: 'inline-block' }} />{fx.text}
      </div>
    </div>
  );
};

export const CoverStory: React.FC<{ fx: Extract<Effect, { kind: 'cover-story' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const { e, out } = env(lf, len, 12);
  const serif = romanSerif();
  const size = Math.min(230, 980 / (0.55 * Math.max(fx.title.length, 5)));
  const lines = fx.lines ?? [];
  const side = (i: number): React.CSSProperties => (i % 2 === 0 ? { left: 64, textAlign: 'left' } : { right: 64, textAlign: 'right' });
  return (
    <div style={{ position: 'absolute', inset: 0, opacity: out }}>
      <div style={{ position: 'absolute', top: 150, left: 0, right: 0, textAlign: 'center', fontFamily: serif, fontWeight: 400, fontSize: size, lineHeight: 0.9,
        letterSpacing: '-0.02em', color: '#fff', textShadow: '0 6px 30px rgba(0,0,0,0.45)', opacity: e, transform: `translateY(${(1 - e) * -40}px)`, textTransform: 'uppercase' }}>{fx.title}</div>
      {fx.strap ? <div style={{ position: 'absolute', top: 160 + size * 0.95, left: 0, right: 0, textAlign: 'center', fontFamily: serif, fontStyle: 'italic', fontSize: 40,
        color: ACCENT_ON_FOOTAGE, opacity: easeOutCubic(clamp01((lf - 8) / 10)) }}>{fx.strap}</div> : null}
      {lines.map((l, i) => (
        <div key={i} style={{ position: 'absolute', top: 470 + Math.floor(i / 2) * 110, width: 300, ...side(i), fontFamily: SANS, fontWeight: 800, fontSize: 28,
          lineHeight: 1.15, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.04em', textShadow: '0 3px 14px rgba(0,0,0,0.6)',
          opacity: easeOutCubic(clamp01((lf - 12 - 5 * i) / 8)) }}>
          <div style={{ width: 54, height: 5, background: ACCENT_ON_FOOTAGE, marginBottom: 10, ...(i % 2 ? { marginLeft: 'auto' } : {}) }} />{l}
        </div>
      ))}
    </div>
  );
};

const SPOTS = [{ x: 180, y: 170, r: -5 }, { x: 600, y: 160, r: 4 }, { x: 170, y: 410, r: 3 }, { x: 610, y: 420, r: -4 }];

export const NoteWall: React.FC<{ fx: Extract<Effect, { kind: 'note-wall' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const f = fx.in + lf;
  const out = clamp01((len - lf) / 8);
  const hand = handFace();
  return (
    <div style={{ position: 'absolute', inset: 0, opacity: out }}>
      {fx.notes.map((n, i) => {
        const p = clamp01((f - n.at) / 8);
        if (p <= 0) return null;
        const sp = SPOTS[i];
        const k = easeOutCubic(p);
        return (
          <div key={i} style={{ position: 'absolute', left: sp.x, top: sp.y, width: 300, minHeight: 150, padding: '34px 24px 22px', boxSizing: 'border-box',
            background: '#F6EFD9', borderRadius: 6, boxShadow: '0 18px 40px rgba(0,0,0,0.45)', transform: `rotate(${sp.r * (2 - k)}deg) scale(${1.25 - 0.25 * k})`, opacity: k }}>
            <div style={{ position: 'absolute', top: -14, left: 110, width: 90, height: 30, background: 'rgba(255,255,255,0.55)', transform: 'rotate(-3deg)' }} />
            <div style={{ fontFamily: hand, fontWeight: 700, fontSize: Math.min(52, 470 / Math.max(n.t.length, 8) * 1.6), lineHeight: 1.05, color: '#1D1B17' }}>{n.t}</div>
          </div>
        );
      })}
    </div>
  );
};

export const ArrowNote: React.FC<{ fx: Extract<Effect, { kind: 'arrow-note' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const { e, out } = env(lf, len, 8);
  const hand = handFace();
  const left = fx.x >= 540;               // the note sits on the far side of the frame from its target
  const nx = left ? 190 : 640, ny = 210;
  const sx = left ? nx + 250 : nx + 20, sy = ny + 110;
  const draw = easeOutCubic(clamp01((lf - 6) / 12));
  const ang = Math.atan2(fx.y - sy, fx.x - sx);
  const hx = fx.x - Math.cos(ang) * 6, hy = fx.y - Math.sin(ang) * 6;
  const cx = (sx + fx.x) / 2 + (left ? 80 : -80), cy = Math.min(sy, fx.y) - 40;
  const a1 = ang + Math.PI * 0.82, a2 = ang - Math.PI * 0.82;
  return (
    <div style={{ position: 'absolute', inset: 0, opacity: out }}>
      <div style={{ position: 'absolute', left: nx, top: ny, width: 270, fontFamily: hand, fontWeight: 700, fontSize: 64, lineHeight: 1, color: ACCENT_ON_FOOTAGE,
        textShadow: '0 3px 14px rgba(0,0,0,0.6)', transform: `rotate(${left ? -4 : 4}deg) scale(${0.85 + 0.15 * e})`, opacity: e, textAlign: left ? 'right' : 'left' }}>{fx.text}</div>
      <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0 }}>
        <path d={`M ${sx} ${sy} Q ${cx} ${cy} ${hx} ${hy}`} fill="none" stroke={ACCENT_ON_FOOTAGE} strokeWidth={8} strokeLinecap="round"
          pathLength={1} strokeDasharray="1" strokeDashoffset={1 - draw} style={{ filter: 'drop-shadow(0 3px 8px rgba(0,0,0,0.5))' }} />
        <path d={`M ${hx + Math.cos(a1) * 34} ${hy + Math.sin(a1) * 34} L ${hx} ${hy} L ${hx + Math.cos(a2) * 34} ${hy + Math.sin(a2) * 34}`} fill="none"
          stroke={ACCENT_ON_FOOTAGE} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" opacity={draw > 0.96 ? 1 : 0} />
      </svg>
    </div>
  );
};

export const CommentBox: React.FC<{ fx: Extract<Effect, { kind: 'comment-box' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const kw = fx.keyword.toUpperCase();
  const typed = Math.max(0, Math.min(kw.length, Math.floor((lf - 10) / 4) + 1));
  const sent = lf >= 14 + 4 * kw.length;
  const heart = clamp01((lf - (16 + 4 * kw.length)) / 8);
  const pop = heart > 0 ? 1 + 0.35 * Math.sin(Math.PI * heart) : 0;
  return (
    <Plate lf={lf} len={len} h={300}>
      <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 30, color: 'rgba(255,255,255,0.7)' }}>{fx.lead ?? 'Comment'}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginTop: 22 }}>
        <div style={{ flex: 1, height: 104, borderRadius: 52, background: 'rgba(255,255,255,0.1)', border: `2px solid ${sent ? ACCENT_ON_FOOTAGE : 'rgba(255,255,255,0.28)'}`,
          display: 'flex', alignItems: 'center', padding: '0 34px', fontFamily: SANS, fontWeight: 900, fontSize: 58, letterSpacing: '0.08em', color: '#fff' }}>
          {kw.slice(0, typed)}{!sent && lf >= 6 && Math.floor(lf / 8) % 2 === 0 ? <span style={{ width: 4, height: 54, background: '#fff', marginLeft: 4, display: 'inline-block' }} /> : null}
        </div>
        <div style={{ width: 104, height: 104, display: 'grid', placeItems: 'center' }}>
          {heart > 0 ? (
            <svg width={84} height={84} viewBox="0 0 24 24" style={{ transform: `scale(${pop})` }} aria-hidden>
              <path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.3 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.6.7-1.4 2.2-2.6 4.3-2.6 3.7 0 5.8 3.8 4.3 7.3C19.5 16.4 12 21 12 21z" fill={ACCENT_ON_FOOTAGE} />
            </svg>
          ) : (
            <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 30, color: typed === kw.length ? ACCENT_ON_FOOTAGE : 'rgba(255,255,255,0.35)' }}>Post</div>
          )}
        </div>
      </div>
    </Plate>
  );
};
