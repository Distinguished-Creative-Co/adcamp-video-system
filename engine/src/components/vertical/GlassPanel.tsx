import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { CREME_DARK, GOLD, ACCENT_ON_FOOTAGE } from '../vc/style';
import { SANS } from '../vc/fonts';
import { AvatarView } from './AvatarView';
import { CaptionLines } from './Captions';
import { PanelGraphic } from './PanelGraphics';
import { ShotPanel } from './ShotPanel';
import { CAP_PANEL, INSET, PANEL, LEAD_F } from '../../methodology/layout';
import { settledCues, contentCues, type ReelConfig, type Swap } from '../../methodology/ReelConfig';
import type { Line } from '../../methodology/timeline';

/**
 * The near-full frosted glass panel (the signature swap). Everything inside is positioned
 * relative to the panel, so the avatar INSET rides in and out WITH the panel: the host is
 * on screen through the whole swap. Text stays inside x < 960, y < 1600 by construction.
 */
const glassStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.10)',
  border: '1px solid rgba(255,255,255,0.20)',
  backdropFilter: 'blur(40px)',
  WebkitBackdropFilter: 'blur(40px)',
  boxShadow: '0 34px 90px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.3)',
};

// No count-up on a stat: a frame reading "9 of 15" is a wrong claim if screenshotted.
// The real number pops in whole.

export const GlassPanel: React.FC<{
  cfg: ReelConfig; swap: Swap; x: number; zoom: number;
  lines: Line[]; capOpacity: number; tone?: 'dark' | 'light';
}> = ({ cfg, swap, x, zoom, lines, capOpacity, tone = 'dark' }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = swap.content;
  const cues = settledCues(swap, cfg.frames) ?? contentCues(swap);   // the completion rule, as validated
  const at = (cues[0] ?? swap.in + 18) - LEAD_F;
  const pop = spring({ frame: frame - at, fps, config: { damping: 200, stiffness: 180, mass: 0.7 }, durationInFrames: 14 });
  const float = Math.sin(((frame / fps) * Math.PI * 2) / 3.2) * 4;
  const breathe = 0.4 + 0.2 * Math.sin(((frame / fps) * Math.PI * 2) / 2.2);
  const inner = PANEL.w - 2 * 56;

  return (
    // on a light stage the panel becomes a solid charcoal surface so its light text keeps contrast
    <div style={{ position: 'absolute', left: x, top: PANEL.y + float * 0.5, width: PANEL.w, height: PANEL.h, borderRadius: PANEL.r, overflow: 'hidden', ...glassStyle,
      ...(tone === 'light' ? { background: 'rgba(26,28,33,0.95)', border: '1px solid rgba(255,255,255,0.10)', boxShadow: '0 34px 90px rgba(80,60,30,0.35), inset 0 1px 0 rgba(255,255,255,0.12)' } : {}) }}>
      <div style={{ position: 'absolute', inset: 0, borderRadius: PANEL.r, background: 'linear-gradient(150deg, rgba(255,255,255,0.14), rgba(255,255,255,0) 42%)' }} />
      {swap.kicker ? (
        <div style={{ position: 'absolute', left: 56, top: 64, width: inner, fontFamily: SANS, fontWeight: 700, fontSize: 28, lineHeight: 1.3, letterSpacing: '0.1em', textTransform: 'uppercase', color: CREME_DARK.inkDim, textWrap: 'balance' } as React.CSSProperties}>
          {swap.kicker}
        </div>
      ) : null}

      {k.kind === 'stat' ? (
        <div style={{ position: 'absolute', left: 56, top: 250, width: inner, transform: `translateY(${float}px)` }}>
          <div style={{
            fontFamily: SANS, fontWeight: 800, fontSize: 210, lineHeight: 1, letterSpacing: '-0.04em', color: ACCENT_ON_FOOTAGE,
            textShadow: `0 0 90px rgba(var(--accent-rgb,247,199,21),${breathe.toFixed(3)})`,
            opacity: pop, transform: `scale(${interpolate(pop, [0, 1], [0.82, 1])})`, transformOrigin: 'left center',
          }}>{k.value}</div>
          <div style={{ marginTop: 28, fontFamily: SANS, fontWeight: 700, fontSize: 50, lineHeight: 1.15, color: CREME_DARK.ink, opacity: pop, transform: `translateY(${(1 - pop) * 14}px)`, textWrap: 'balance' } as React.CSSProperties}>
            {k.label}
          </div>
        </div>
      ) : null}

      {k.kind === 'cta' ? (
        <div style={{ position: 'absolute', left: 56, top: 190, width: inner, transform: `translateY(${float}px)` }}>
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 96, lineHeight: 1.02, letterSpacing: '-0.03em', color: CREME_DARK.ink, opacity: pop, transform: `translateY(${(1 - pop) * 16}px)`, textWrap: 'balance' } as React.CSSProperties}>
            {k.title}
          </div>
          {k.sub ? (
            <div style={{ marginTop: 30, fontFamily: SANS, fontWeight: 600, fontSize: 44, lineHeight: 1.25, color: CREME_DARK.inkDim, opacity: pop, textWrap: 'balance' } as React.CSSProperties}>{k.sub}</div>
          ) : null}
        </div>
      ) : null}

      {k.kind === 'cta' ? (
        <div style={{
          position: 'absolute', right: 56, bottom: 64, padding: '26px 40px', borderRadius: 999,
          background: ACCENT_ON_FOOTAGE, color: GOLD.ink, fontFamily: SANS, fontWeight: 800, fontSize: 40, letterSpacing: '-0.01em',
          boxShadow: `0 0 ${Math.round(40 + 30 * breathe)}px rgba(var(--accent-rgb,247,199,21),${(0.35 + breathe * 0.4).toFixed(3)}), 0 18px 40px rgba(0,0,0,0.45)`,
          opacity: pop, transform: `scale(${interpolate(pop, [0, 1], [0.85, 1]) * (1 + 0.015 * Math.sin((frame / fps) * Math.PI * 2 / 1.6))})`,
          transformOrigin: 'right bottom',
        }}>{k.button}</div>
      ) : null}

      {k.kind === 'checklist' || k.kind === 'funnel' || k.kind === 'decision' ? (
        <div style={{ position: 'absolute', left: 56, top: 170, height: 640, width: inner, display: 'flex', flexDirection: 'column', justifyContent: 'center', transform: `translateY(${float}px)` }}>
          <PanelGraphic content={k} cues={cues} width={inner} />
        </div>
      ) : null}

      {k.kind === 'shot' ? (
        <div style={{ position: 'absolute', left: 56, top: 160, width: inner, transform: `translateY(${float * 0.5}px)` }}>
          <ShotPanel src={k.src} w={k.w} h={k.h} focus={k.focus} at={cues[0]} source={k.source} width={inner} height={560} />
        </div>
      ) : null}

      {k.kind === 'words' ? (
        <CaptionLines lines={lines} x={56} w={inner} top={170} bottom={900} base={92} min={60} opacity={capOpacity} align="left" />
      ) : (
        <CaptionLines lines={lines} x={CAP_PANEL.x} w={CAP_PANEL.w} cy={CAP_PANEL.cy} base={CAP_PANEL.size} min={CAP_PANEL.min} opacity={capOpacity} align="left" />
      )}

      <AvatarView src={cfg.src} view={INSET} zoom={zoom} glass={1} faceX={cfg.faceX} faceY={cfg.faceY} sW={cfg.source.w} sH={cfg.source.h} dy={float * 0.6} />
    </div>
  );
};
