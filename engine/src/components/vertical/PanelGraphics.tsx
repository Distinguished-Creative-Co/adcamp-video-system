import React from 'react';
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { ACCENT_RGB, CREME_DARK, GOLD } from '../vc/style';
import { SANS } from '../vc/fonts';
import { ENTER_F, LEAD_F } from '../../methodology/layout';
import type { SwapContent } from '../../methodology/ReelConfig';

/**
 * Data-driven panel graphics: a checklist that ticks, a funnel that narrows, a decision that
 * picks. Each element enters on its own cue frame (word-anchored, already settled by the
 * completion rule). Only what the config supplies is drawn, never placeholder content.
 */
const ACCENT = ACCENT_RGB;
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

const useEnter = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (at: number) =>
    spring({ frame: frame - (at - LEAD_F), fps, config: { damping: 200, stiffness: 200, mass: 0.6 }, durationInFrames: ENTER_F });
};

const Check: React.FC<{ p: number; size: number }> = ({ p, size }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" style={{ flexShrink: 0 }}>
    <circle cx={20} cy={20} r={18} stroke={GOLD.yellow} strokeWidth={2.5} fill={p > 0.5 ? GOLD.yellow : 'none'} opacity={0.4 + 0.6 * p} />
    <path d="M12 21 L18 27 L29 14" fill="none" stroke={GOLD.ink} strokeWidth={4} strokeLinecap="round" strokeLinejoin="round"
      pathLength={1} strokeDasharray={1} strokeDashoffset={1 - clamp01((p - 0.4) / 0.6)} />
  </svg>
);

const label = (size: number, weight: number, color: string, extra: React.CSSProperties = {}): React.CSSProperties => ({
  fontFamily: SANS, fontWeight: weight, fontSize: size, color, ...extra,
});

const Checklist: React.FC<{ items: { t: string }[]; cues: number[] }> = ({ items, cues }) => {
  const enter = useEnter();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 56 }}>
      {items.map((it, i) => {
        const p = enter(cues[i] ?? 0);
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 26, opacity: p, transform: `translateX(${(1 - p) * -18}px)` }}>
            <Check p={p} size={80} />
            <div style={label(62, 700, CREME_DARK.ink, { lineHeight: 1.1, textWrap: 'balance' } as React.CSSProperties)}>{it.t}</div>
          </div>
        );
      })}
    </div>
  );
};

const Funnel: React.FC<{ stages: { t: string; value?: string }[]; cues: number[]; width: number }> = ({ stages, cues, width }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = useEnter();
  const n = stages.length;
  const g = 0.35 + 0.2 * Math.sin((2 * Math.PI * frame) / fps / 2.2);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, alignItems: 'center' }}>
      {stages.map((st, i) => {
        const p = enter(cues[i] ?? 0);
        const last = i === n - 1;
        const surface: React.CSSProperties = last
          ? { background: `linear-gradient(180deg, ${GOLD.lite}, ${GOLD.deep})`, border: 'none', boxShadow: `0 0 60px rgba(${ACCENT},${g.toFixed(3)})` }
          : { background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.16)' };
        return (
          <div key={i} style={{
            ...surface, boxSizing: 'border-box', height: 104, borderRadius: 22, padding: '0 34px',
            width: width * (1 - (0.42 * i) / Math.max(n - 1, 1)), display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', opacity: p, transform: `scaleX(${0.86 + 0.14 * p})`,
          }}>
            <div style={label(42, 700, last ? GOLD.ink : CREME_DARK.ink, { whiteSpace: 'nowrap' })}>{st.t}</div>
            {st.value ? <div style={label(44, 800, last ? GOLD.ink : GOLD.yellow, { whiteSpace: 'nowrap' })}>{st.value}</div> : null}
          </div>
        );
      })}
    </div>
  );
};

const Decision: React.FC<{ question?: string; options: { t: string }[]; pick: number; cues: number[] }> = ({ question, options, pick, cues }) => {
  const enter = useEnter();
  const q = enter(cues[cues.length - 1] ?? 0);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {question ? (
        <div style={label(58, 800, CREME_DARK.ink, { lineHeight: 1.08, marginBottom: 10, textWrap: 'balance' } as React.CSSProperties)}>{question}</div>
      ) : null}
      {options.map((op, i) => {
        const p = enter(cues[i] ?? 0);
        const picked = i === pick;
        const box: React.CSSProperties = picked
          ? { background: `rgba(${ACCENT},${(0.08 + 0.9 * q).toFixed(3)})`, border: 'none', opacity: p,
              transform: `translateY(${(1 - p) * 14}px) scale(${1 + 0.04 * q})` }
          : { background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.16)', opacity: p * (1 - 0.68 * q),
              transform: `translateY(${(1 - p) * 14}px)` };
        return (
          <div key={i} style={{ ...box, display: 'flex', alignItems: 'center', gap: 22, padding: '26px 30px', borderRadius: 24, transformOrigin: 'left center' }}>
            {picked ? (
              <Check p={q} size={54} />
            ) : (
              <div style={{ width: 54, height: 54, borderRadius: '50%', boxSizing: 'border-box', border: '2.5px solid rgba(255,255,255,0.35)', flexShrink: 0 }} />
            )}
            <div style={label(46, 700, picked && q > 0.5 ? GOLD.ink : CREME_DARK.ink)}>{op.t}</div>
          </div>
        );
      })}
    </div>
  );
};

export const PanelGraphic: React.FC<{ content: SwapContent; cues: number[]; width: number }> = ({ content, cues, width }) => {
  if (content.kind === 'checklist') return <Checklist items={content.items} cues={cues} />;
  if (content.kind === 'funnel') return <Funnel stages={content.stages} cues={cues} width={width} />;
  if (content.kind === 'decision') return <Decision question={content.question} options={content.options} pick={content.pick} cues={cues} />;
  return null;
};
