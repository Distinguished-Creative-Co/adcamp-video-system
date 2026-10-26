import React from 'react';
import { AbsoluteFill, Img, OffthreadVideo, staticFile } from 'remotion';
import { ACCENT_RGB, CREME_DARK, GOLD, ACCENT_ON_FOOTAGE } from '../vc/style';
import { SANS } from '../vc/fonts';
import { CharcoalBg } from '../vc/CremeStage';
import { thumbFgSrc, type ReelConfig } from '../../methodology/ReelConfig';
import { place } from '../../methodology/layout';
import { useGrade } from './Grade';

/**
 * COMPANION PACK: covers and static ads rendered from the SAME config
 * as the reel, so they can only say what the reel already says: the cover title, the stat
 * panel (value, label, kicker), and the CTA. Each format is recomposed for its own shape,
 * never a stretched frame. Critical text stays in a conservative central region.
 *   cover-vertical 1080x1920   cover-feed 1440x1800   static-square 1080x1080
 *   static-feed 1440x1800      static-vertical 1440x2560
 */
export type CompanionFormat = 'cover-vertical' | 'cover-feed' | 'static-square' | 'static-feed' | 'static-vertical' | 'thumbnail';
export const COMPANION_SIZES: Record<CompanionFormat, [number, number]> = {
  'cover-vertical': [1080, 1920], 'cover-feed': [1440, 1800], 'static-square': [1080, 1080],
  'static-feed': [1440, 1800], 'static-vertical': [1440, 2560], 'thumbnail': [1080, 1920],
};

const Title: React.FC<{ title: string; accent?: string; size: number }> = ({ title, accent, size }) => {
  const words = title.trim().split(/\s+/);
  const mid = Math.ceil(words.length / 2);
  return (
    <div>
      {[words.slice(0, mid), words.slice(mid)].filter((r) => r.length).map((r, i) => (
        <div key={i} style={{ fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 0.98, letterSpacing: '-0.03em', color: CREME_DARK.ink }}>
          {r.map((w, j) => (
            <span key={j} style={w === accent ? { color: ACCENT_ON_FOOTAGE, textShadow: `0 0 60px rgba(${ACCENT_RGB},0.5)` } : undefined}>{w}{j < r.length - 1 ? ' ' : ''}</span>
          ))}
        </div>
      ))}
    </div>
  );
};

/** The host at the cover frame in an explicit w x h box, face-anchored with the engine's own
 *  camera math (cover fit, clamped: no footage edge, face kept in frame). */
const Host: React.FC<{ cfg: ReelConfig; frame: number; w: number; h: number; radius?: number }> = ({ cfg, frame, w, h, radius = 0 }) => {
  const p = place({ x: 0, y: 0, w, h, r: radius, ax: 0.5, ay: 0.45 }, 1, cfg.faceX, cfg.faceY, cfg.source.w, cfg.source.h);
  const gr = useGrade(cfg.grade);
  return (
    <div style={{ position: 'relative', width: w, height: h, overflow: 'hidden', borderRadius: radius, flex: 'none',
      ...(radius ? { boxShadow: '0 30px 80px rgba(0,0,0,0.55)', border: '1px solid rgba(255,255,255,0.18)' } : {}) }}>
      <div style={{ position: 'absolute', left: p.left, top: p.top, width: p.width, height: p.height }}>
        <OffthreadVideo muted src={staticFile(cfg.src)} startFrom={frame} style={{ width: '100%', height: '100%', objectFit: 'fill', filter: gr.filter }} />
      </div>
      {gr.defs}
      {gr.vignette}
    </div>
  );
};

/** THUMBNAIL (uploadable Reels cover): the host cutout set lower so the face sits at the centre
 *  of Instagram's 3:4 grid crop (y 240-1680), the spoken words huge behind it, one short line
 *  in front. Each back row is sized to fill the width on its own. */
const ThumbnailView: React.FC<{ cfg: ReelConfig }> = ({ cfg }) => {
  const t = cfg.thumbnail!;
  const gr = useGrade(cfg.grade);
  const words = t.back.trim().toUpperCase().split(/\s+/);
  const half = Math.ceil(words.length / 2);
  const rows = words.length > 2 ? [words.slice(0, half).join(' '), words.slice(half).join(' ')] : [words.join(' ')];
  const dy = 960 - cfg.faceY;   // face to the centre of the grid crop
  let top = 300;
  const placed = rows.map((r) => {
    const size = Math.min(300, 1000 / (0.6 * Math.max(r.length, 3)));
    const y = top; top += size * 0.9;
    return { r, size, y };
  });
  return (
    <AbsoluteFill style={{ fontFamily: SANS, backgroundColor: '#131419' }}>
      <CharcoalBg />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 70% 30% at 50% 22%, rgba(${ACCENT_RGB},0.16), rgba(${ACCENT_RGB},0) 70%)` }} />
      {placed.map(({ r, size, y }, i) => (
        <div key={i} style={{ position: 'absolute', left: 0, width: 1080, top: y, textAlign: 'center', fontWeight: 900, fontSize: size,
          lineHeight: 0.92, letterSpacing: '-0.035em', whiteSpace: 'nowrap', color: ACCENT_ON_FOOTAGE,
          textShadow: `0 0 90px rgba(${ACCENT_RGB},0.45), 0 10px 40px rgba(0,0,0,0.35)` }}>{r}</div>
      ))}
      <Img src={staticFile(thumbFgSrc(cfg.src, t.frame))} style={{ position: 'absolute', left: 0, top: dy, width: cfg.source.w, height: cfg.source.h, filter: gr.filter }} />
      {gr.defs}
      <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(10,11,14,0) 62%, rgba(10,11,14,0.78) 76%, rgba(10,11,14,0.92) 100%)' }} />
      {t.front ? (
        <div style={{ position: 'absolute', left: 80, right: 80, top: 1440, textAlign: 'center', fontWeight: 800, fontSize: 70, lineHeight: 1.08,
          color: CREME_DARK.ink, textWrap: 'balance', textShadow: '0 4px 24px rgba(0,0,0,0.5)' } as React.CSSProperties}>
          {t.front.split(/(?<=\.)\s+/).map((line, i) => <div key={i}>{line}</div>)}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

export const Companion: React.FC<{ cfg: ReelConfig | null; format: CompanionFormat }> = ({ cfg, format }) => {
  if (!cfg) return null;
  if (format === 'thumbnail') return cfg.thumbnail ? <ThumbnailView cfg={cfg} /> : null;
  const [W, H] = COMPANION_SIZES[format];
  const cover = cfg.cover ?? { frame: Math.min(45, cfg.frames - 1), title: '', accent: undefined };
  const stat = cfg.swaps.map((s) => ({ s, k: s.content })).find((x) => x.k.kind === 'stat');
  const cta = cfg.swaps.map((s) => ({ s, k: s.content })).find((x) => x.k.kind === 'cta');
  const paid = cfg.placement === 'paid';
  const button = cta && cta.k.kind === 'cta' ? cta.k.button : paid ? 'Click Learn More' : '';
  const u = W / 1080; // scale unit

  if (format === 'cover-vertical' || format === 'cover-feed') {
    return (
      <AbsoluteFill style={{ backgroundColor: '#131419' }}>
        <AbsoluteFill><Host cfg={cfg} frame={cover.frame} w={W} h={H} /></AbsoluteFill>
        <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(10,11,14,0) 50%, rgba(10,11,14,0.82) 70%, rgba(10,11,14,0.94) 100%)' }} />
        <div style={{ position: 'absolute', left: 80 * u, right: 80 * u, bottom: format === 'cover-vertical' ? 330 : 150 * u }}>
          <Title title={cover.title} accent={cover.accent} size={128 * u} />
        </div>
      </AbsoluteFill>
    );
  }

  // STATIC ADS: title, the reel's proof (stat) if it has one, the host, the CTA. Every box has
  // an explicit size, so nothing can overlap and the face is always framed.
  const pad = 80 * u;
  const inner = W - 2 * pad;
  const titleSize = (format === 'static-square' ? 100 : 118) * u;
  const titleH = titleSize * 0.98 * 2;
  const gap = 40 * u;
  const statCard = (width: number) => {
    if (!stat || stat.k.kind !== 'stat') return null;
    const v = stat.k.value;
    const vSize = Math.min(170 * u, (width - 80 * u) / (0.6 * Math.max(v.length, 4)));
    return (
      <div style={{ width, boxSizing: 'border-box', padding: `${34 * u}px ${40 * u}px`, borderRadius: 32 * u, background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.18)' }}>
        {stat.s.kicker ? <div style={{ fontWeight: 700, fontSize: 24 * u, letterSpacing: '0.1em', textTransform: 'uppercase', color: CREME_DARK.inkDim, marginBottom: 14 * u, textWrap: 'balance' } as React.CSSProperties}>{stat.s.kicker}</div> : null}
        <div style={{ fontWeight: 800, fontSize: vSize, lineHeight: 1, letterSpacing: '-0.04em', color: ACCENT_ON_FOOTAGE, textShadow: `0 0 70px rgba(${ACCENT_RGB},0.45)`, whiteSpace: 'nowrap' }}>{v}</div>
        <div style={{ marginTop: 16 * u, fontWeight: 700, fontSize: 34 * u, lineHeight: 1.15, color: CREME_DARK.ink, textWrap: 'balance' } as React.CSSProperties}>{stat.k.label}</div>
      </div>
    );
  };
  const pill = button ? (
    <div style={{ alignSelf: 'flex-end', padding: `${24 * u}px ${40 * u}px`, borderRadius: 999, background: ACCENT_ON_FOOTAGE, color: GOLD.ink, fontWeight: 800, fontSize: 40 * u, boxShadow: `0 0 60px rgba(${ACCENT_RGB},0.4)` }}>{button}</div>
  ) : null;
  const shell = (children: React.ReactNode) => (
    <AbsoluteFill style={{ fontFamily: SANS, ['--accent-rgb' as string]: ACCENT_RGB } as React.CSSProperties}>
      <CharcoalBg />
      <div style={{ position: 'absolute', left: pad, top: pad, width: inner, height: H - 2 * pad, display: 'flex', flexDirection: 'column', gap }}>
        <Title title={cover.title} accent={cover.accent} size={titleSize} />
        {children}
      </div>
    </AbsoluteFill>
  );
  if (format === 'static-vertical') {
    const pillH = 110 * u;
    const statH = stat ? 460 * u : 0;
    const hostH = H - 2 * pad - titleH - statH - pillH - gap * (stat ? 3 : 2);
    return shell(<>{statCard(inner)}<Host cfg={cfg} frame={cover.frame} w={inner} h={hostH} radius={32 * u} />{pill}</>);
  }
  // square and 4:5: host card on the left, proof and CTA on the right
  const rowH = H - 2 * pad - titleH - gap;
  const hostW = Math.min(rowH * 0.62, inner * 0.44);
  return shell(
    <div style={{ display: 'flex', gap, height: rowH }}>
      <Host cfg={cfg} frame={cover.frame} w={hostW} h={rowH} radius={32 * u} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap }}>
        {statCard(inner - hostW - gap)}
        {pill}
      </div>
    </div>
  );
};
