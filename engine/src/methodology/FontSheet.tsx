import React from 'react';
import { AbsoluteFill } from 'remotion';
import { accentFace, displayFace, type AccentFont, type SansFont } from '../components/vc/fonts';
import { readableAccent } from '../components/vc/style';

/**
 * The font pairs on one still, so a person picks by looking, not by name: each pair sets their own name in
 * the italic serif and a caption line in the sans, the way a reel would. scripts/font_sheet.py renders it.
 */
export const FONT_PAIRS: { n: number; sans: SansFont; serif: AccentFont; label: string }[] = [
  { n: 1, sans: 'hanken', serif: 'playfair', label: 'Clean and editorial' },
  { n: 2, sans: 'inter', serif: 'instrument', label: 'Light and airy' },
  { n: 3, sans: 'montserrat', serif: 'fraunces', label: 'Bold and warm' },
  { n: 4, sans: 'dmsans', serif: 'dmserif', label: 'Modern and friendly' },
];

export const FontSheet: React.FC<{ name: string; accent: string }> = ({ name, accent }) => (
  <AbsoluteFill style={{ background: '#16171C', padding: 48, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28 }}>
    {FONT_PAIRS.map((p) => {
      const sans = displayFace(p.sans), serif = accentFace(p.serif);
      const nm = name || 'Your Name';
      return (
        <div key={p.n} style={{ background: '#22232A', borderRadius: 26, padding: '34px 34px 30px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ fontFamily: sans.family, fontWeight: 800, fontSize: 30, color: 'rgba(255,255,255,0.55)' }}>{p.n}. {p.label}</div>
          <div>
            <div style={{ fontFamily: serif.family, fontStyle: 'italic', fontWeight: serif.weight, fontSize: Math.min(92, 420 / (serif.width * Math.max(nm.length, 6)) * 1.9), color: readableAccent(accent), lineHeight: 1.05 }}>{nm}</div>
            <div style={{ fontFamily: sans.family, fontWeight: 800, fontSize: 44, color: '#fff', textTransform: 'uppercase', letterSpacing: '-0.01em', lineHeight: 1.08, marginTop: 18 }}>Your captions<br />look like this</div>
            <div style={{ fontFamily: sans.family, fontWeight: 600, fontSize: 27, color: 'rgba(255,255,255,0.75)', marginTop: 16, whiteSpace: 'nowrap' }}>and the key word gets <span style={{ fontFamily: serif.family, fontStyle: 'italic', fontWeight: serif.weight, color: readableAccent(accent), fontSize: 40 }}>this</span></div>
          </div>
        </div>
      );
    })}
  </AbsoluteFill>
);
