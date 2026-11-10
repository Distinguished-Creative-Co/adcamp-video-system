import React from 'react';
import { AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile } from 'remotion';
import { CREME_DARK, ACCENT_ON_FOOTAGE, GOLD, lookColor } from '../vc/style';
import { SANS, displayFace } from '../vc/fonts';
import { thumbFgSrc, type Cover as CoverT, type ReelConfig } from '../../methodology/ReelConfig';
import { useGrade } from './Grade';
import { coverLayout } from '../../methodology/adsafe';

/**
 * Frame 0 only: a chosen frame of the host, a dark title area, and 2-4 bold stacked words
 * (white, one accent word in yellow). Instagram uses frame 0 as the default cover, so this
 * replaces an accidental mid-blink first frame. The title block sits low (y 1330-1590), inside
 * the 3:4 profile-grid crop (y 240-1680), below the face and above the Reels UI. A paid ad fits the title to Meta's ad
 * safe zone and ends it at y 1200, above the ad copy, with the dark fade raised to match (adsafe.ts).
 */
/** Words behind you on a cover: 2-4 of their spoken words huge behind the head, then their one-frame cutout over them.
 *  Laid out in the source frame's own pixels and drawn into `box` (where the source frame sits), so the full-frame
 *  cover and the companion covers place them the same way. Two rows, each as big as the width allows, the last one's
 *  lower part tucked behind the top of the head (backY, measured by cover_options.py), so they read as standing behind. */
export const BehindWords: React.FC<{ cfg: ReelConfig; cover: CoverT; box: { left: number; top: number; width: number; height: number }; filter?: string }> = ({ cfg, cover, box, filter }) => {
  const look = cfg.look?.backText;
  const face = displayFace(look?.font);
  const k = look?.font ? face.width * 1.25 : 0.74;   // the back text's own width per character (BackText.tsx)
  const words = (cover.back ?? '').trim().toUpperCase().split(/\s+/);
  const half = Math.ceil(words.length / 2);
  const rows = [words.slice(0, half).join(' '), words.slice(half).join(' ')].filter(Boolean);   // two rows (one for a single word), each as big as the width allows
  const u = box.width / cfg.source.w;
  const sizes = rows.map((r) => Math.min(320, (cfg.source.w * 0.94) / (k * Math.max(r.length, 3))));   // each row fills the width
  const blockH = sizes.reduce((a, b) => a + b * 0.92, 0);
  // backY is the top of the head: the last row's lower half tucks behind it, so the words read as standing behind
  const top = Math.max(50, (cover.backY ?? cfg.faceY - 400) - blockH + sizes[sizes.length - 1] * 0.38);
  let y = top;
  return (
    <>
      {rows.map((r, i) => {
        const at = y; y += sizes[i] * 0.92;
        return (
          <div key={i} style={{ position: 'absolute', left: box.left, width: box.width, top: box.top + at * u, textAlign: 'center', whiteSpace: 'nowrap',
            fontFamily: face.family, fontWeight: look?.font ? face.weight : 900, fontStyle: face.italic ? 'italic' : undefined, fontSize: sizes[i] * u, lineHeight: 0.92,
            letterSpacing: look?.font ? '-0.01em' : '-0.035em', color: lookColor(look?.color, GOLD.yellow), WebkitTextStroke: `${(look?.outline ?? 6) * u}px rgba(18,14,4,0.55)`,
            paintOrder: 'stroke fill', textShadow: '0 6px 0 rgba(0,0,0,0.3), 0 12px 44px rgba(0,0,0,0.55)' } as React.CSSProperties}>{r}</div>
        );
      })}
      <Img src={staticFile(thumbFgSrc(cfg.src, cover.frame))} style={{ position: 'absolute', left: box.left, top: box.top, width: box.width, height: box.height, filter }} />
    </>
  );
};

export const Cover: React.FC<{ cfg: ReelConfig; cover: CoverT }> = ({ cfg, cover }) => {
  const gr = useGrade(cfg.grade);
  const paid = cfg.placement === 'paid';
  const { rows, size, top } = coverLayout(cover.title, paid);
  const titled = !!cover.title.trim();   // an empty title: the frame alone (a captions-only look)
  return (
    <AbsoluteFill style={{ zIndex: 95, backgroundColor: '#131419' }}>
      {/* the chosen frame: this Sequence starts the source at cover.frame, shown on reel frame 0 */}
      <Sequence from={0} durationInFrames={1} layout="none">
        <OffthreadVideo muted src={staticFile(cfg.src)} startFrom={cover.frame} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', filter: gr.filter }} />
        {cover.back && !paid ? <BehindWords cfg={cfg} cover={cover} box={{ left: 0, top: 0, width: 1080, height: 1920 }} filter={gr.filter} /> : null}
        {gr.defs}
        {gr.vignette}
      </Sequence>
      {titled ? <>
      <AbsoluteFill style={{ background: paid ? 'linear-gradient(180deg, rgba(10,11,14,0) 38%, rgba(10,11,14,0.8) 56%, rgba(10,11,14,0.94) 100%)'
        : 'linear-gradient(180deg, rgba(10,11,14,0) 52%, rgba(10,11,14,0.8) 70%, rgba(10,11,14,0.94) 100%)' }} />
      <div style={{ position: 'absolute', left: 80, width: paid ? 900 : 860, top, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {rows.map((r, i) => (
          <div key={i} style={{ fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 0.98, letterSpacing: '-0.03em', color: CREME_DARK.ink }}>
            {r.map((w, j) => (
              <span key={j} style={w === cover.accent ? { color: ACCENT_ON_FOOTAGE, textShadow: '0 0 60px rgba(var(--accent-rgb,247,199,21),0.55)' } : undefined}>
                {w}{j < r.length - 1 ? ' ' : ''}
              </span>
            ))}
          </div>
        ))}
      </div>
      </> : null}
    </AbsoluteFill>
  );
};
