import React, { useMemo } from 'react';
import { AbsoluteFill, Audio, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { ACCENT_RGB } from '../components/vc/style';
import { SANS } from '../components/vc/fonts';
import { CharcoalBg } from '../components/vc/CremeStage';
import { AvatarView } from '../components/vertical/AvatarView';
import { CaptionLines } from '../components/vertical/Captions';
import { DynamicCaptions } from '../components/vertical/DynamicCaptions';
import { GlassPanel } from '../components/vertical/GlassPanel';
import { Cover } from '../components/vertical/Cover';
import { PaperBg } from '../components/vertical/PaperBg';
import { CAP_FULL, CAP_STAGE, CARD_HOST, lerpView } from './layout';
import { buildLines, stateAt, visibleLines, type Ease } from './timeline';
import { backFgSrc, framingAt, validateReel, zoomAt, type ReelConfig } from './ReelConfig';
import { FollowCard } from '../components/vertical/FollowCard';
import { EffectLayer, GiantNumber, ShapeTransition, cameraMove } from '../components/vertical/Effects';
import { ClipCard } from '../components/vertical/ClipCard';
import { BackTextLayer } from '../components/vertical/BackText';
import { Slide } from '../components/slides/Slide';
import { CAPTION_MODES, StyledCaptions, type CaptionMode } from '../components/vertical/CaptionStyles';
import { PinnedLine, snapZoomAt } from '../components/vertical/EffectsMore';
import { TOP_BAND_FX } from './ReelConfig';

/**
 * THE VERTICAL ENGINE. Written once, never edited per video: it renders whatever
 * ReelConfig it is handed. A new short is a new reels/<name>.config.ts plus one line in
 * Root.tsx. If a short seems to need an edit here, the engine is missing a capability:
 * add it for every reel, never fork it for one.
 *
 * Laws (carried over from Chris's own landscape engine): the spoken script is the timeline; the
 * avatar is always on screen (one brief, capped exception: a giant-number effect); nothing is ever a frozen still; captions show the writer's
 * words on whisperX timing; one audio track.
 */
export const VerticalReel: React.FC<{ cfg: ReelConfig | null }> = ({ cfg }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lines = useMemo(() => (cfg ? buildLines(cfg.words, cfg.captionStyle === 'punch' || cfg.captionStyle === 'word' ? cfg.captionStyle : 'lines') : []), [cfg]);
  useMemo(() => cfg && validateReel(cfg), [cfg]);
  if (!cfg) return null;

  // the one motion curve (AvatarGlide's spring grammar), snapped home once settled
  const ease: Ease = (lf, d) => (lf <= 0 ? 0 : lf >= d + 2 ? 1 : spring({ frame: lf, fps, config: { damping: 200, stiffness: 120, mass: 0.9 }, durationInFrames: d }));
  const st = stateAt(cfg, frame, ease);
  const now = frame / fps;
  const shown = visibleLines(lines, now, st.capRegion);
  const drift = Math.sin((frame / fps) * (Math.PI * 2) / 12) * 8;
  const cardGone = !!st.swap && st.swap.ps >= 0.999;
  const word = cfg.captionStyle === 'word';
  const punch = cfg.captionStyle === 'punch' || word;   // one word at a time draws like punch: no plate, outlined
  const capLook = cfg.look?.captions;
  const styledMode = (CAPTION_MODES as string[]).includes(cfg.captionStyle ?? '') ? (cfg.captionStyle as CaptionMode) : null;
  const dynamic = cfg.captionStyle === 'dynamic';
  const snaps = (cfg.effects ?? []).filter((e): e is Extract<typeof e, { kind: 'snap-zoom' }> => e.kind === 'snap-zoom');
  const zm = st.capRegion === 'full' ? zoomAt(cfg, frame) * framingAt(cfg, frame) * snaps.reduce((k, e) => k * snapZoomAt(e, frame), 1) : 1;
  const bt = st.capRegion === 'full' ? (cfg.backText ?? []).find((b) => frame >= b.in && frame < b.out) : undefined;
  const over = !!cfg.look?.backText?.over;   // in front of the host: no cutout needed
  const back = bt && !over ? { text: bt.text, from: bt.in, lf: frame - bt.in, len: bt.out - bt.in, fg: backFgSrc(cfg.src, bt), look: bt.glass ? { ...cfg.look?.backText, glass: true } : cfg.look?.backText } : undefined;
  const ins = st.capRegion === 'full' ? (cfg.inserts ?? []).find((b) => frame >= b.in && frame < b.out) : undefined;
  const fxs = st.capRegion === 'full' ? (cfg.effects ?? []).filter((e) => e.kind !== 'transition' && e.kind !== 'card' && e.kind !== 'snap-zoom' && e.kind !== 'pinned-line' && e.kind !== 'giant-number' && frame >= e.in && frame < e.out) : [];
  // a giant list number: drawn over everything, captions included, so the caption steps aside while it shows
  const bigNum = st.capRegion === 'full' ? (cfg.effects ?? []).find((e): e is Extract<typeof e, { kind: 'giant-number' }> => e.kind === 'giant-number' && frame >= e.in && frame < e.out) : undefined;
  // a pinned line steps aside while anything else is in the top band
  const pinned = st.capRegion === 'full' ? (cfg.effects ?? []).find((e): e is Extract<typeof e, { kind: 'pinned-line' }> => e.kind === 'pinned-line' && frame >= e.in && frame < e.out) : undefined;
  const bandBusy = (f: number) => (cfg.effects ?? []).some((e) => e.kind !== 'transition' && (TOP_BAND_FX as readonly string[]).includes(e.kind) && f >= e.in - 4 && f < e.out + 4)
    || (cfg.backText ?? []).some((b) => f >= b.in - 4 && f < b.out + 4) || (cfg.inserts ?? []).some((b) => f >= b.in - 4 && f < b.out + 4);
  const away = pinned ? [0, 1, 2, 3, 4, 5].filter((d) => bandBusy(frame - d)).length / 6 : 0;
  // a full-frame card: the slide fills the frame and the host glides into a corner window, then back
  const card = st.capRegion === 'full' ? (cfg.effects ?? []).find((e): e is Extract<typeof e, { kind: 'card' }> => e.kind === 'card' && frame >= e.in && frame < e.out) : undefined;
  const ck = card ? Math.min(ease(frame - card.in, 10), 1 - ease(frame - (card.out - 10), 10)) : 0;
  const hostView = card ? lerpView(st.view, CARD_HOST, ck) : st.view;
  const giant = fxs.some((e) => e.kind === 'giant-captions');
  const trans = (cfg.effects ?? []).filter((e): e is Extract<typeof e, { kind: 'transition' }> => e.kind === 'transition');
  const cam = trans.map((t) => cameraMove(t, frame, cfg.faceX, cfg.faceY)).find((m) => m);
  const host = (b?: typeof back) => (
    <AvatarView src={cfg.srcHi ?? cfg.src} view={hostView} zoom={card ? st.zoom * (zm + (1 - zm) * ck) : st.zoom * zm} glass={Math.max(st.glass, ck)} faceX={cfg.faceX} faceY={cfg.faceY} sW={cfg.source.w} sH={cfg.source.h} dx={st.cardDx} dy={st.floatY} grade={cfg.grade} back={b} />
  );

  return (
    <AbsoluteFill style={{ fontFamily: SANS, backgroundColor: '#131419', ['--accent-rgb' as string]: ACCENT_RGB } as React.CSSProperties}>
      <AbsoluteFill style={{ transform: `scale(1.06) translate(${drift}px, ${drift * 0.6}px)` }}>
        {st.tone === 'light' ? <PaperBg /> : <CharcoalBg />}
      </AbsoluteFill>

      {st.capRegion === 'stage' ? (
        <CaptionLines lines={shown} x={CAP_STAGE.x} w={CAP_STAGE.w} top={CAP_STAGE.top} bottom={CAP_STAGE.bottom} base={punch ? 116 : CAP_STAGE.size} min={CAP_STAGE.min} opacity={st.capOpacity} tone={st.tone} punch={punch} look={capLook} />
      ) : null}

      {card ? (
        <div style={{ position: 'absolute', inset: 0, opacity: ck }}>
          <Slide data={{ ...card, items: card.items?.map((it) => ({ t: it.t, at: it.at === undefined ? undefined : it.at - card.in })) }}
            look={{ theme: card.theme ?? 'paper', font: cfg.look?.captions?.font, accent: cfg.look?.captions?.keyColor === 'accent' ? undefined : cfg.look?.captions?.keyColor }} w={1080} h={1920} t={frame - card.in} safeBottom={1060} />
        </div>
      ) : null}

      {!cardGone ? (
        <div style={cam ? { position: 'absolute', inset: 0, transform: cam.transform, filter: cam.filter, transformOrigin: cam.origin } : { position: 'absolute', inset: 0 }}>
        {/* a whip's open side: the footage's outermost few px, flipped and stretched into a streak, inside the move so the
            blur runs across the seam, and tucked 40 px under the footage so neither its own blur nor the two antialiased
            edges ever let the frame through */}
        {cam?.streak ? (
          <div style={{ position: 'absolute', top: 0, left: cam.streak === 'left' ? -1080 : 1040, width: 1120, height: 1920, overflow: 'hidden', filter: `blur(${(cam.streakBlur ?? 0).toFixed(1)}px)` }}>
            <div style={{ position: 'absolute', top: 0, left: cam.streak === 'left' ? 1120 : -1080, width: 1080, height: 1920, transform: 'scaleX(-80)', transformOrigin: cam.streak === 'left' ? '0 0' : '100% 0' }}>
              {host()}
            </div>
          </div>
        ) : null}
        {host(back)}
        </div>
      ) : null}

      {bt && over ? <BackTextLayer text={bt.text} lf={frame - bt.in} len={bt.out - bt.in} w={1080} h={1920} look={cfg.look?.backText} /> : null}

      {trans.map((t) => <ShapeTransition key={t.at} fx={t} frame={frame} faceX={cfg.faceX} faceY={cfg.faceY} />)}
      {fxs.map((e, i) => <EffectLayer key={e.kind + i} fx={e} frame={frame} words={cfg.words} now={now} look={capLook} />)}

      {pinned ? <PinnedLine fx={pinned} lf={frame - pinned.in} len={pinned.out - pinned.in} away={away} /> : null}
      {ins?.kind === 'follow' ? <FollowCard insert={ins} lf={frame - ins.in} len={ins.out - ins.in} /> : null}
      {ins?.kind === 'clip' ? <ClipCard insert={ins} lf={frame - ins.in} len={ins.out - ins.in} /> : null}

      {giant || card || (bigNum && frame > bigNum.in && frame < bigNum.out - 1) ? null : st.capRegion === 'full' && styledMode ? (
        <StyledCaptions mode={styledMode} line={shown[0]} now={now} fps={fps} opacity={st.capOpacity} look={capLook} serif={cfg.captionAccent} cy={capLook?.y ?? cfg.fullCaptionY ?? 1290} />
      ) : st.capRegion === 'full' && dynamic ? (
        <DynamicCaptions line={shown[0]} now={now} fps={fps} accent={cfg.captionAccent} opacity={st.capOpacity} plain={!!bt} money={capLook?.money} />
      ) : st.capRegion === 'full' ? (
        <CaptionLines lines={shown} x={CAP_FULL.x} w={CAP_FULL.w} cy={capLook?.y ?? cfg.fullCaptionY ?? CAP_FULL.cy} base={capLook?.size ?? (word ? 150 : punch ? 128 : CAP_FULL.size)} min={punch ? 76 : CAP_FULL.min} opacity={st.capOpacity} scrim={capLook?.plate ? capLook.plate === 'dark' : !punch} punch={punch} look={capLook} />
      ) : null}

      {st.swap ? (
        <GlassPanel cfg={cfg} swap={st.swap.data} x={st.swap.panelX} zoom={st.zoom} lines={st.capRegion === 'panel' ? shown : []} capOpacity={st.capOpacity} tone={st.tone} />
      ) : null}

      {bigNum ? <GiantNumber fx={bigNum} lf={frame - bigNum.in} len={bigNum.out - bigNum.in} /> : null}

      {frame === 0 && cfg.cover ? <Cover cfg={cfg} cover={cfg.cover} /> : null}

      {/* Studio preview audio. The delivered file is rendered muted and its sound is mixed and
          mastered from the cut by scripts/mix_master.py (one audio path, no browser decode drift). */}
      <Audio src={staticFile(cfg.src)} />
    </AbsoluteFill>
  );
};
