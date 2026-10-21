import React from 'react';
import { OffthreadVideo, Sequence, staticFile } from 'remotion';
import { place, type View } from '../../methodology/layout';
import type { Grade } from '../../methodology/ReelConfig';
import { useGrade } from './Grade';
import { BackTextLayer } from './BackText';

/**
 * The ONLY place the host footage is drawn. A clipped viewport (the full frame, the glass
 * card, or the panel inset) with the source plane placed by `place()`: face-anchored,
 * cover-fit, clamped, so footage edges can never show. Always muted: the reel carries
 * exactly one audio track at the root.
 */
export const AvatarView: React.FC<{
  src: string; view: View; zoom: number; glass: number;
  faceX: number; faceY: number; sW: number; sH: number;
  dx?: number; dy?: number; grade?: Grade | null;
  back?: { text: string; from: number; lf: number; len: number; fg: string };   // back text + host cutout
}> = ({ src, view, zoom, glass, faceX, faceY, sW, sH, dx = 0, dy = 0, grade, back }) => {
  const p = place(view, zoom, faceX, faceY, sW, sH);
  const gr = useGrade(grade);
  const on = glass > 0.02;
  return (
    <div
      style={{
        position: 'absolute', left: view.x + dx, top: view.y + dy, width: view.w, height: view.h,
        borderRadius: view.r, overflow: 'hidden',
        boxShadow: on ? `0 34px 90px rgba(0,0,0,${(0.55 * glass).toFixed(3)})` : undefined,
        border: on ? `1px solid rgba(255,255,255,${(0.2 * glass).toFixed(3)})` : undefined,
      }}
    >
      <div style={{ position: 'absolute', left: p.left, top: p.top, width: p.width, height: p.height }}>
        <OffthreadVideo muted src={staticFile(src)} style={{ width: '100%', height: '100%', objectFit: 'fill', filter: gr.filter }} />
      </div>
      {back ? (
        <>
          <BackTextLayer text={back.text} lf={back.lf} len={back.len} w={view.w} h={view.h} />
          <Sequence from={back.from} durationInFrames={back.len} layout="none">
            <div style={{ position: 'absolute', left: p.left, top: p.top, width: p.width, height: p.height }}>
              <OffthreadVideo muted transparent src={staticFile(back.fg)} style={{ width: '100%', height: '100%', objectFit: 'fill', filter: gr.filter }} />
            </div>
          </Sequence>
        </>
      ) : null}
      {gr.defs}
      {gr.vignette}
      {on ? (
        <>
          <div style={{ position: 'absolute', inset: 0, borderRadius: view.r, background: `linear-gradient(135deg, rgba(255,255,255,${(0.16 * glass).toFixed(3)}), rgba(255,255,255,0) 44%)` }} />
          <div style={{ position: 'absolute', inset: 0, borderRadius: view.r, boxShadow: `inset 0 1px 0 rgba(255,255,255,${(0.3 * glass).toFixed(3)})` }} />
        </>
      ) : null}
    </div>
  );
};
