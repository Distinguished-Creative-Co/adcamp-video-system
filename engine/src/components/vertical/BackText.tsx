import React from 'react';
import { GOLD, lookColor } from '../vc/style';
import { displayFace, type DisplayFont } from '../vc/fonts';
import { backTextPlace } from '../../methodology/adsafe';

/** The words themselves, in viewport space (they do not ride the camera's zoom). Rise in on a
 *  short ease, breathe slightly while held, fade out before the cut. Drawn between the
 *  footage and the host cutout, so the host's head and shoulders cover part of them. An entry's own y, x (the row's
 *  centre) set them behind the head wherever it is in that shot. A paid ad sets them lower and a little narrower, held
 *  inside Meta's ad safe zone (adsafe.ts). */
export const BackTextLayer: React.FC<{ text: string; lf: number; len: number; w: number; h: number; look?: { font?: DisplayFont; color?: string; outline?: number; glass?: boolean }; paid?: boolean; y?: number; x?: number }> = ({ text, lf, len, w, h, look, paid = false, y, x }) => {
  const face = displayFace(look?.font);
  const words = text.trim().toUpperCase().split(/\s+/);
  const rows = [words.join(' ')];   // one row: the host covers the middle, so a second row would hide behind the head
  const longest = Math.max(...rows.map((r) => r.length));
  // heavy caps run wide (M, W): 0.74em per character keeps a word like COMMUTE inside the frame
  const place = paid || y !== undefined || x !== undefined ? backTextPlace(rows[0], look?.font ? face.width * 1.25 : 0.74, paid, y, x) : null;
  const size = place ? place.size : Math.min(330, (w * 0.9) / ((look?.font ? face.width * 1.25 : 0.74) * Math.max(longest, 3)));
  const inP = Math.min(1, Math.max(0, lf / 10));
  const e = 1 - Math.pow(1 - inP, 3);
  const outP = Math.min(1, Math.max(0, (len - lf) / 8));
  const op = e * outP;
  const scale = (0.9 + 0.1 * e) * (1 + 0.04 * (lf / Math.max(len, 1)));
  return (
    <div style={{ position: 'absolute', left: place ? place.cx - w / 2 : 0, top: place ? place.top : h * 0.075, width: w, display: 'flex', flexDirection: 'column', alignItems: 'center',
      opacity: op, transform: `translateY(${(1 - e) * 70}px) scale(${scale})`, transformOrigin: '50% 40%' }}>
      {rows.map((r, i) => (
        <div key={i} style={{ fontFamily: face.family, fontWeight: look?.font ? face.weight : 900, fontStyle: face.italic ? 'italic' : undefined, fontSize: size, lineHeight: 0.92, letterSpacing: look?.font ? '-0.01em' : '-0.035em', whiteSpace: 'nowrap',
          ...(look?.glass
            ? { color: 'transparent', backgroundImage: 'linear-gradient(170deg, rgba(255,255,255,0.62) 0%, rgba(255,255,255,0.18) 45%, rgba(255,255,255,0.34) 100%)',
                WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextStroke: '2.5px rgba(255,255,255,0.8)' }
            : { color: lookColor(look?.color, GOLD.yellow), WebkitTextStroke: `${look?.outline ?? 6}px rgba(18,14,4,0.55)` }),
          paintOrder: 'stroke fill',
          ...(look?.glass ? { filter: 'drop-shadow(0 10px 28px rgba(0,0,0,0.35))' } : { textShadow: '0 6px 0 rgba(0,0,0,0.3), 0 12px 44px rgba(0,0,0,0.55)' }) } as React.CSSProperties}>{r}</div>
      ))}
    </div>
  );
};
