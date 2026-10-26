import React from 'react';
import { Img, staticFile } from 'remotion';
import { displayFace, SANS, type DisplayFont } from '../vc/fonts';
import { GOLD, inkOn, readableAccent } from '../vc/style';

/**
 * ONE slide design for two places: a carousel slide (a still, 1080x1350 or 1080x1080) and a full-frame card
 * inside a reel (1080x1920, animated by `t`). Layouts:
 *   hook       big headline, a short sub line, the swipe cue
 *   statement  an optional label (01, 02...), one big centered line, a sub line
 *   content    label, headline, a checklist or numbered list, an optional callout
 *   cta        headline, the keyword in a pill ("DM me the word SITE"), a sub line
 * Any slide may carry a photo (full bleed, the words over a dark fade). In a headline, ==words== get the
 * highlight: a solid accent box on paper, accent ink on ink and photo.
 */
export type SlideTheme = 'paper' | 'ink';
export type SlideLook = { theme?: SlideTheme; font?: DisplayFont; accent?: string; case?: 'upper' | 'none' };
export type SlideData = {
  layout: 'hook' | 'statement' | 'content' | 'cta';
  label?: string;
  headline: string;
  sub?: string;
  items?: { t: string; at?: number }[];     // at: frame (reel cards) when the item ticks; carousels show all
  list?: 'check' | 'number';
  callout?: string;
  keyword?: string; keywordLead?: string; keywordNote?: string;
  photo?: string;                          // a picture under public/ (staticFile path), carousels and cards alike
};
export type Identity = { handle?: string; name?: string; avatar?: string };

const PAL = {
  paper: { bg: '#F1EEE8', ink: '#141414', soft: '#5A564F', line: 'rgba(20,20,20,0.12)' },
  ink: { bg: '#121212', ink: '#F4F1EA', soft: '#B7B1A6', line: 'rgba(244,241,234,0.16)' },
};
const ease = (p: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, p)), 3);

/** "==One fee.== You own it." -> parts, the ==...== ones highlighted */
const marks = (s: string) => s.split(/(==.*?==)/).filter(Boolean).map((p) => (p.startsWith('==') && p.length > 4 ? { t: p.slice(2, -2), hi: true } : { t: p, hi: false }));

export const Slide: React.FC<{
  data: SlideData; look?: SlideLook; who?: Identity; w: number; h: number;
  t?: number;            // frames since a reel card entered (animates the parts in); undefined = a still, everything shown
  page?: [number, number];
  safeBottom?: number;   // reel cards: keep words above this y (the host's corner window and the app's buttons)
}> = ({ data, look, who, w, h, t, page, safeBottom }) => {
  const photo = !!data.photo;
  const theme: SlideTheme = photo ? 'ink' : look?.theme ?? 'paper';
  const P = PAL[theme];
  const accent = look?.accent ?? GOLD.yellow;
  const onAccent = inkOn(accent);   // the mark on an accent fill: dark on a light brand color, white on a dark one
  const card = t !== undefined && h > 1500;          // a full-frame card in a reel: bigger words, centered above the host's window
  const k = (w / 1080) * (card ? 1.3 : 1);
  const face = displayFace(look?.font);
  const upper = look?.case === 'upper';
  const show = (delay: number) => (t === undefined ? 1 : ease((t - delay) / 9));
  const pad = (card ? 90 : 96) * (w / 1080);
  const bottom = safeBottom ?? h - 170 * k;
  const head = data.layout === 'statement' ? 104 : data.layout === 'hook' ? 112 : 84;
  const longest = Math.max(...data.headline.replace(/==/g, '').split('\n').map((l) => l.length), 6);
  const hs = Math.min(head, (w - 2 * pad) / k / (face.width * longest * (upper ? 1.08 : 1))) * k;

  const headline = (
    <div style={{ fontFamily: face.family, fontWeight: face.weight, fontStyle: face.italic ? 'italic' : undefined, fontSize: hs, lineHeight: 1.16,
      letterSpacing: '-0.015em', color: P.ink, textTransform: upper ? 'uppercase' : undefined, whiteSpace: 'pre-line',
      textAlign: data.layout === 'statement' ? 'center' : 'left', opacity: show(4), transform: `translateY(${(1 - show(4)) * 26 * k}px)` }}>
      {marks(data.headline).map((m, i) => m.hi ? (
        <span key={i} style={theme === 'paper' && !photo
          ? { background: accent, color: onAccent, padding: `${0.02 * hs}px ${0.12 * hs}px 0`, borderRadius: 0.08 * hs, boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone' }
          : { color: readableAccent(accent) }}>{m.t}</span>) : <span key={i}>{m.t}</span>)}
    </div>
  );
  const label = data.label ? (
    <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 30 * k, letterSpacing: '0.16em', textTransform: 'uppercase', color: theme === 'paper' && !photo ? P.soft : readableAccent(accent),
      marginBottom: 26 * k, opacity: show(0), textAlign: data.layout === 'statement' ? 'center' : 'left' }}>{data.label}</div>
  ) : null;
  const sub = data.sub ? (
    <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 38 * k, lineHeight: 1.3, color: P.soft, marginTop: 30 * k, maxWidth: 820 * k,
      textAlign: data.layout === 'statement' ? 'center' : 'left', alignSelf: data.layout === 'statement' ? 'center' : undefined, opacity: show(10) }}>{data.sub}</div>
  ) : null;
  const list = data.items?.length ? (
    <div style={{ marginTop: 40 * k, display: 'flex', flexDirection: 'column', gap: 22 * k }}>
      {data.items.map((it, i) => {
        const on = t === undefined || it.at === undefined ? 1 : ease((t - (it.at ?? 0)) / 6);
        const seen = t === undefined ? 1 : ease((t - 8 - i * 4) / 8);
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 24 * k, opacity: seen, transform: `translateX(${(1 - seen) * -20 * k}px)` }}>
            {data.list === 'number' ? (
              <span style={{ fontFamily: face.family, fontWeight: face.weight, fontSize: 52 * k, color: theme === 'paper' ? accent : readableAccent(accent), width: 64 * k }}>{i + 1}</span>
            ) : (
              <span style={{ width: 52 * k, height: 52 * k, borderRadius: 12 * k, flex: 'none', border: `${4 * k}px solid ${P.ink}`,
                background: on > 0.5 ? accent : 'transparent', borderColor: on > 0.5 ? accent : P.ink, display: 'grid', placeItems: 'center' }}>
                <svg width={30 * k} height={30 * k} viewBox="0 0 24 24" style={{ opacity: on }} aria-hidden><path d="M4.5 12.5l5 5 10-11" fill="none" stroke={onAccent} strokeWidth={3.6} strokeLinecap="round" strokeLinejoin="round" /></svg>
              </span>
            )}
            <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 44 * k, color: P.ink, lineHeight: 1.2 }}>{it.t}</span>
          </div>
        );
      })}
    </div>
  ) : null;
  const callout = data.callout ? (
    <div style={{ marginTop: 40 * k, borderLeft: `${8 * k}px solid ${accent}`, padding: `${14 * k}px ${26 * k}px`, fontFamily: SANS, fontWeight: 600,
      fontSize: 36 * k, lineHeight: 1.3, color: P.ink, background: P.line, borderRadius: `0 ${16 * k}px ${16 * k}px 0`, opacity: show(16) }}>{data.callout}</div>
  ) : null;
  const pill = data.keyword ? (
    <div style={{ marginTop: 44 * k, display: 'flex', flexDirection: 'column', gap: 22 * k, opacity: show(10) }}>
      {data.keywordLead ? <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 40 * k, color: P.soft }}>{data.keywordLead}</div> : null}
      <div style={{ alignSelf: 'flex-start', fontFamily: face.family, fontWeight: face.weight, fontSize: 96 * k, letterSpacing: '0.04em', color: onAccent,
        background: accent, padding: `${8 * k}px ${44 * k}px ${12 * k}px`, borderRadius: 999, textTransform: 'uppercase' }}>{data.keyword}</div>
      {data.keywordNote ? <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 38 * k, color: P.soft, lineHeight: 1.3, maxWidth: 820 * k }}>{data.keywordNote}</div> : null}
    </div>
  ) : null;

  return (
    <div style={{ position: 'absolute', inset: 0, width: w, height: h, background: P.bg, overflow: 'hidden' }}>
      {photo ? (
        <>
          <Img src={staticFile(data.photo as string)} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.78) 72%, rgba(0,0,0,0.9) 100%)' }} />
        </>
      ) : null}
      <div style={{ position: 'absolute', left: pad, right: pad, display: 'flex', flexDirection: 'column',
        ...(photo ? { bottom: h - bottom + 40 * k }
          : data.layout === 'statement' || data.layout === 'hook' || card ? { top: card ? 240 : 0, bottom: h - bottom, justifyContent: 'center' }
          : { top: 150 * k }) }}>
        {label}{headline}{sub}{list}{callout}{pill}
      </div>
      {t === undefined && (who?.handle || page) ? (
        <div style={{ position: 'absolute', left: pad, right: pad, bottom: 64 * k, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18 * k }}>
            {who?.avatar ? <Img src={staticFile(who.avatar)} style={{ width: 64 * k, height: 64 * k, borderRadius: '50%', objectFit: 'cover' }} /> : null}
            <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30 * k, color: P.ink }}>{who?.handle}</span>
          </div>
          <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 28 * k, color: P.soft }}>
            {page ? `${page[0]}/${page[1]}` : ''}{data.layout === 'hook' && page && page[1] > 1 ? '  →' : ''}
          </span>
        </div>
      ) : null}
    </div>
  );
};
