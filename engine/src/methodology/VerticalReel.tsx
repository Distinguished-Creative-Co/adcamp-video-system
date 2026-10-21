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
import { CAP_FULL, CAP_STAGE } from './layout';
import { buildLines, stateAt, visibleLines, type Ease } from './timeline';
import { backFgSrc, framingAt, validateReel, zoomAt, type ReelConfig } from './ReelConfig';
import { FollowCard } from '../components/vertical/FollowCard';
import { EffectLayer, ShapeTransition, cameraMove } from '../components/vertical/Effects';
import { ClipCard } from '../components/vertical/ClipCard';

/**
 * THE VERTICAL ENGINE. Written once, never edited per video: it renders whatever
 * ReelConfig it is handed. A new short is a new reels/<name>.config.ts plus one line in
 * Root.tsx. If a short seems to need an edit here, the engine is missing a capability:
 * add it for every reel, never fork it for one.
 *
 * Laws (inherited from the landscape engine): the spoken script is the timeline; the
 * avatar is always on screen; nothing is ever a frozen still; captions show the writer's
 * words on whisperX timing; one audio track.
 */
export const VerticalReel: React.FC<{ cfg: ReelConfig | null }> = ({ cfg }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lines = useMemo(() => (cfg ? buildLines(cfg.words, cfg.captionStyle === 'punch' ? 'punch' : 'lines') : []), [cfg]);
  useMemo(() => cfg && validateReel(cfg), [cfg]);
  if (!cfg) return null;

  // the one motion curve (AvatarGlide's spring grammar), snapped home once settled
  const ease: Ease = (lf, d) => (lf <= 0 ? 0 : lf >= d + 2 ? 1 : spring({ frame: lf, fps, config: { damping: 200, stiffness: 120, mass: 0.9 }, durationInFrames: d }));
  const st = stateAt(cfg, frame, ease);
  const now = frame / fps;
  const shown = visibleLines(lines, now, st.capRegion);
  const drift = Math.sin((frame / fps) * (Math.PI * 2) / 12) * 8;
  const cardGone = !!st.swap && st.swap.ps >= 0.999;
  const punch = cfg.captionStyle === 'punch';
  const dynamic = cfg.captionStyle === 'dynamic';
  const zm = st.capRegion === 'full' ? zoomAt(cfg, frame) * framingAt(cfg, frame) : 1;
  const bt = st.capRegion === 'full' ? (cfg.backText ?? []).find((b) => frame >= b.in && frame < b.out) : undefined;
  const back = bt ? { text: bt.text, from: bt.in, lf: frame - bt.in, len: bt.out - bt.in, fg: backFgSrc(cfg.src, bt) } : undefined;
  const ins = st.capRegion === 'full' ? (cfg.inserts ?? []).find((b) => frame >= b.in && frame < b.out) : undefined;
  const fxs = st.capRegion === 'full' ? (cfg.effects ?? []).filter((e) => e.kind !== 'transition' && frame >= e.in && frame < e.out) : [];
  const giant = fxs.some((e) => e.kind === 'giant-captions');
  const trans = (cfg.effects ?? []).filter((e): e is Extract<typeof e, { kind: 'transition' }> => e.kind === 'transition');
  const cam = trans.map((t) => cameraMove(t, frame)).find((m) => m);

  return (
    <AbsoluteFill style={{ fontFamily: SANS, backgroundColor: '#131419', ['--accent-rgb' as string]: ACCENT_RGB } as React.CSSProperties}>
      <AbsoluteFill style={{ transform: `scale(1.06) translate(${drift}px, ${drift * 0.6}px)` }}>
        {st.tone === 'light' ? <PaperBg /> : <CharcoalBg />}
      </AbsoluteFill>

      {st.capRegion === 'stage' ? (
        <CaptionLines lines={shown} x={CAP_STAGE.x} w={CAP_STAGE.w} top={CAP_STAGE.top} bottom={CAP_STAGE.bottom} base={punch ? 116 : CAP_STAGE.size} min={CAP_STAGE.min} opacity={st.capOpacity} tone={st.tone} punch={punch} />
      ) : null}

      {!cardGone ? (
        <div style={cam ? { position: 'absolute', inset: 0, transform: cam.transform, filter: cam.filter, transformOrigin: `${cfg.faceX}px ${cfg.faceY}px` } : { position: 'absolute', inset: 0 }}>
        <AvatarView src={cfg.srcHi ?? cfg.src} view={st.view} zoom={st.zoom * zm} glass={st.glass} faceX={cfg.faceX} faceY={cfg.faceY} sW={cfg.source.w} sH={cfg.source.h} dx={st.cardDx} dy={st.floatY} grade={cfg.grade} back={back} />
        </div>
      ) : null}

      {trans.map((t) => <ShapeTransition key={t.at} fx={t} frame={frame} faceX={cfg.faceX} faceY={cfg.faceY} />)}
      {fxs.map((e, i) => <EffectLayer key={e.kind + i} fx={e} frame={frame} words={cfg.words} now={now} />)}

      {ins?.kind === 'follow' ? <FollowCard insert={ins} lf={frame - ins.in} len={ins.out - ins.in} /> : null}
      {ins?.kind === 'clip' ? <ClipCard insert={ins} lf={frame - ins.in} len={ins.out - ins.in} /> : null}

      {giant ? null : st.capRegion === 'full' && dynamic ? (
        <DynamicCaptions line={shown[0]} now={now} fps={fps} accent={cfg.captionAccent} opacity={st.capOpacity} plain={!!bt} />
      ) : st.capRegion === 'full' ? (
        <CaptionLines lines={shown} x={CAP_FULL.x} w={CAP_FULL.w} cy={cfg.fullCaptionY ?? CAP_FULL.cy} base={punch ? 128 : CAP_FULL.size} min={punch ? 76 : CAP_FULL.min} opacity={st.capOpacity} scrim={!punch} punch={punch} />
      ) : null}

      {st.swap ? (
        <GlassPanel cfg={cfg} swap={st.swap.data} x={st.swap.panelX} zoom={st.zoom} lines={st.capRegion === 'panel' ? shown : []} capOpacity={st.capOpacity} tone={st.tone} />
      ) : null}

      {frame === 0 && cfg.cover ? <Cover cfg={cfg} cover={cfg.cover} /> : null}

      {/* Studio preview audio. The delivered file is rendered muted and its sound is mixed and
          mastered from the cut by scripts/mix_master.py (one audio path, no browser decode drift). */}
      <Audio src={staticFile(cfg.src)} />
    </AbsoluteFill>
  );
};
