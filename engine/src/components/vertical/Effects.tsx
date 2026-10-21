import React from 'react';
import { Img, staticFile } from 'remotion';
import { Ban, Calendar, Clock, DollarSign, Globe, MapPin, Megaphone, MessageCircle, Phone, Search, Star, ThumbsDown } from 'lucide-react';
import { CREME_DARK, GOLD, glow } from '../vc/style';
import { SANS, accentFace } from '../vc/fonts';
import { easeOutCubic } from '../../methodology/layout';
import type { Effect, Word } from '../../methodology/ReelConfig';

/**
 * EFFECTS: short motion graphics on full-screen shots, each anchored to the frames of the words
 * it illustrates. They live in the TOP BAND (x 160-920, y 130-650) where the face never sits, or
 * over the footage without covering the face, so the person stays on screen. Every colour and
 * font comes from the brand. Kinds:
 *   word-stamp     one spoken word slammed on like a rubber stamp
 *   giant-captions the spoken words, one at a time, huge, in place of the normal captions
 *   icon-strike    an icon with a line struck through it ("no ads", "no calls")
 *   page-scroll    a real screenshot of a long page scrolling in a browser frame
 *   live-markup    a real screenshot with a circle, underline or arrow drawn onto it
 *   keycaps        keyboard keys pressed one after another, spelling a word
 *   receipt        a receipt printing a short list, one line per cue
 *   intertitle     a title card with one line of text
 *   counter        one big number under a loupe ring (it pops whole, never counts up)
 *   pie            a share drawn as a pie, with its label
 *   transition     at a picture join: a camera move (whip, zoom, spin) or a shape (iris, bars)
 * Numbers and words on screen pass the same spoken-words guard as every other text.
 */
const BAND = { x: 160, y: 130, w: 760, h: 520 } as const;
const ICONS = { megaphone: Megaphone, ban: Ban, calendar: Calendar, clock: Clock, dollar: DollarSign, globe: Globe, pin: MapPin,
  message: MessageCircle, phone: Phone, search: Search, star: Star, thumbsdown: ThumbsDown } as const;
export type IconName = keyof typeof ICONS;
const PLATE = 'rgba(20,21,26,0.86)';
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

/** in/out envelope shared by every card: ease in over `enter` frames, fade out over the last 8 */
const env = (lf: number, len: number, enter = 10) => ({ e: easeOutCubic(lf / enter), out: clamp01((len - lf) / 8) });

const Card: React.FC<{ lf: number; len: number; h?: number; children: React.ReactNode; pad?: number }> = ({ lf, len, h = BAND.h, children, pad = 28 }) => {
  const { e, out } = env(lf, len);
  return (
    <div style={{ position: 'absolute', left: BAND.x, top: BAND.y, width: BAND.w, height: h, borderRadius: 30, background: PLATE,
      border: '1px solid rgba(255,255,255,0.14)', boxShadow: '0 28px 70px rgba(0,0,0,0.5)', overflow: 'hidden', padding: pad, boxSizing: 'border-box',
      opacity: e * out, transform: `translateY(${(1 - e) * -36}px) scale(${0.96 + 0.04 * e})`, transformOrigin: '50% 0%' }}>
      {children}
    </div>
  );
};

const WordStamp: React.FC<{ fx: Extract<Effect, { kind: 'word-stamp' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const p = clamp01(lf / 7);
  const slam = p < 1 ? 1.7 - 0.7 * easeOutCubic(p) : 1 + 0.03 * Math.exp(-(lf - 7) / 4) * Math.sin((lf - 7) * 1.4);
  const out = clamp01((len - lf) / 8);
  const size = Math.min(170, 720 / (0.66 * Math.max(fx.word.length, 4)));
  return (
    <div style={{ position: 'absolute', left: BAND.x, top: BAND.y + 40, width: BAND.w, display: 'flex', justifyContent: 'center', opacity: clamp01(lf / 2) * out }}>
      <div style={{ transform: `rotate(${fx.tilt ?? -6}deg) scale(${slam})`, border: `10px solid ${GOLD.yellow}`, borderRadius: 18, padding: '6px 34px 2px',
        color: GOLD.yellow, fontFamily: SANS, fontWeight: 900, fontSize: size, letterSpacing: '0.02em', textTransform: 'uppercase',
        background: 'rgba(15,15,18,0.35)', boxShadow: `0 0 40px ${glow(0.35)}`, whiteSpace: 'nowrap' }}>{fx.word}</div>
    </div>
  );
};

/** the word being spoken now, huge; key words in the accent serif */
export const GiantCaptions: React.FC<{ words: Word[]; now: number; lf: number; len: number }> = ({ words, now, lf, len }) => {
  const live = words.filter((w) => w.t && w.s <= now + 0.04);
  const w = live[live.length - 1];
  if (!w) return null;
  const pop = easeOutCubic(clamp01((now - w.s) * 30 / 4));
  const face = accentFace();
  const accent = !!(w.key ?? w.big);
  const text = w.t.replace(/[.,!?]+$/, '');
  const size = Math.min(accent ? 260 : 210, 820 / ((accent ? face.width : 0.62) * Math.max(text.length, 3)));
  return (
    <div style={{ position: 'absolute', left: 120, width: 840, top: 1080, height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center',
      opacity: clamp01((len - lf) / 6) }}>
      <span style={{ fontFamily: accent ? face.family : SANS, fontStyle: accent ? 'italic' : 'normal', fontWeight: accent ? face.weight : 900,
        fontSize: size, lineHeight: 1, color: accent ? GOLD.yellow : '#fff', textTransform: accent ? 'none' : 'uppercase',
        transform: `scale(${0.7 + 0.3 * pop})`, textShadow: '0 6px 0 rgba(0,0,0,0.35), 0 12px 40px rgba(0,0,0,0.6)', whiteSpace: 'nowrap' }}>{text}</span>
    </div>
  );
};

const IconStrike: React.FC<{ fx: Extract<Effect, { kind: 'icon-strike' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const Icon = ICONS[fx.icon] ?? Ban;
  const strike = easeOutCubic(clamp01((lf - (fx.strikeAt ?? 10)) / 8));
  return (
    <Card lf={lf} len={len} h={420}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, paddingTop: 10 }}>
        <div style={{ position: 'relative', width: 230, height: 230 }}>
          <Icon size={230} color={CREME_DARK.ink} strokeWidth={1.6} />
          <svg width={230} height={230} viewBox="0 0 100 100" style={{ position: 'absolute', inset: 0 }}>
            <line x1={10} y1={90} x2={10 + 80 * strike} y2={90 - 80 * strike} stroke={GOLD.yellow} strokeWidth={9} strokeLinecap="round" />
          </svg>
        </div>
        {fx.label ? <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 52, color: CREME_DARK.ink, textAlign: 'center' }}>{fx.label}</div> : null}
      </div>
    </Card>
  );
};

const PageScroll: React.FC<{ fx: Extract<Effect, { kind: 'page-scroll' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const viewW = BAND.w - 40, viewH = BAND.h - 96;
  const imgH = viewW * (fx.h / fx.w);
  const travel = Math.max(0, imgH - viewH);
  const t = clamp01((lf - 8) / Math.max(1, len - 22));
  const y = -travel * (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
  return (
    <Card lf={lf} len={len} pad={20}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, height: 36, marginBottom: 10 }}>
        {[0, 1, 2].map((i) => <span key={i} style={{ width: 13, height: 13, borderRadius: 7, background: 'rgba(255,255,255,0.28)' }} />)}
        <span style={{ flex: 1, marginLeft: 10, height: 30, borderRadius: 15, background: 'rgba(255,255,255,0.08)', color: CREME_DARK.inkDim,
          fontFamily: SANS, fontSize: 20, display: 'flex', alignItems: 'center', paddingLeft: 14, overflow: 'hidden', whiteSpace: 'nowrap' }}>{fx.url ?? ''}</span>
      </div>
      <div style={{ position: 'relative', width: viewW, height: viewH, overflow: 'hidden', borderRadius: 14, background: '#fff' }}>
        <Img src={staticFile(fx.src)} style={{ position: 'absolute', left: 0, top: y, width: viewW, height: imgH }} />
      </div>
      <div style={{ fontFamily: SANS, fontSize: 18, color: CREME_DARK.inkDim, marginTop: 8 }}>{fx.source}</div>
    </Card>
  );
};

const LiveMarkup: React.FC<{ fx: Extract<Effect, { kind: 'live-markup' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const viewW = BAND.w - 40, viewH = BAND.h - 70;
  const s = Math.min(viewW / fx.w, viewH / fx.h);
  const dw = fx.w * s, dh = fx.h * s;
  const draw = easeOutCubic(clamp01((lf - (fx.markAt ?? 14)) / 12));
  const m = fx.mark;
  const X = m.x * s, Y = m.y * s, MW = m.w * s, MH = m.h * s;
  return (
    <Card lf={lf} len={len} pad={20}>
      <div style={{ position: 'relative', width: dw, height: dh, margin: '0 auto', borderRadius: 12, overflow: 'hidden' }}>
        <Img src={staticFile(fx.src)} style={{ width: dw, height: dh, display: 'block' }} />
        <svg width={dw} height={dh} style={{ position: 'absolute', inset: 0 }}>
          {m.shape === 'circle' ? (
            <ellipse cx={X + MW / 2} cy={Y + MH / 2} rx={MW / 2 + 14} ry={MH / 2 + 12} fill="none" stroke={GOLD.yellow} strokeWidth={7}
              pathLength={1} strokeDasharray="1" strokeDashoffset={1 - draw} strokeLinecap="round" transform={`rotate(-4 ${X + MW / 2} ${Y + MH / 2})`} />
          ) : m.shape === 'underline' ? (
            <path d={`M ${X - 6} ${Y + MH + 10} Q ${X + MW / 2} ${Y + MH + 22} ${X + MW + 6} ${Y + MH + 8}`} fill="none" stroke={GOLD.yellow} strokeWidth={8}
              pathLength={1} strokeDasharray="1" strokeDashoffset={1 - draw} strokeLinecap="round" />
          ) : (
            <g>
              <path d={`M ${X + MW + 90} ${Y - 70} Q ${X + MW + 70} ${Y + MH / 2} ${X + MW + 10} ${Y + MH / 2}`} fill="none" stroke={GOLD.yellow} strokeWidth={8}
                pathLength={1} strokeDasharray="1" strokeDashoffset={1 - draw} strokeLinecap="round" />
              <path d={`M ${X + MW + 30} ${Y + MH / 2 - 18} L ${X + MW + 8} ${Y + MH / 2} L ${X + MW + 30} ${Y + MH / 2 + 18}`} fill="none" stroke={GOLD.yellow}
                strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" opacity={draw > 0.95 ? 1 : 0} />
            </g>
          )}
        </svg>
      </div>
      <div style={{ fontFamily: SANS, fontSize: 18, color: CREME_DARK.inkDim, marginTop: 8 }}>{fx.source}</div>
    </Card>
  );
};

const Keycaps: React.FC<{ fx: Extract<Effect, { kind: 'keycaps' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const keys = fx.keys.toUpperCase().split('');
  const size = Math.min(140, (BAND.w - 40) / Math.max(keys.length, 3) - 14);
  return (
    <Card lf={lf} len={len} h={300}>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 14, height: '100%' }}>
        {keys.map((k, i) => {
          const at = 4 + 5 * i;
          const press = lf >= at && lf < at + 4 ? 1 : 0;
          const lit = lf >= at;
          return (
            <div key={i} style={{ width: size, height: size, borderRadius: 18, display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: lit ? GOLD.yellow : 'rgba(255,255,255,0.1)', color: lit ? GOLD.ink : CREME_DARK.ink, fontFamily: SANS, fontWeight: 800,
              fontSize: size * 0.5, boxShadow: press ? 'inset 0 4px 0 rgba(0,0,0,0.25)' : '0 8px 0 rgba(0,0,0,0.35)',
              transform: `translateY(${press ? 6 : 0}px)` }}>{k === ' ' ? '' : k}</div>
          );
        })}
      </div>
    </Card>
  );
};

const Receipt: React.FC<{ fx: Extract<Effect, { kind: 'receipt' }>; lf: number; len: number; from: number }> = ({ fx, lf, len, from }) => {
  const shown = fx.lines.filter((l) => from + lf >= l.at);
  const paperH = 140 + shown.length * 74;
  return (
    <div style={{ position: 'absolute', left: BAND.x + 80, top: BAND.y, width: BAND.w - 160, height: BAND.h, overflow: 'hidden', opacity: clamp01((len - lf) / 8) }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: -BAND.h + Math.min(BAND.h, paperH * easeOutCubic(clamp01(lf / 8)) + 40),
        height: BAND.h, background: '#FBF8F1', borderRadius: '0 0 6px 6px', boxShadow: '0 20px 50px rgba(0,0,0,0.45)', padding: '0 34px',
        boxSizing: 'border-box', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', paddingBottom: 30, fontFamily: '"Courier New", monospace', color: '#222' }}>
        {fx.title ? <div style={{ fontSize: 38, fontWeight: 700, textAlign: 'center', borderBottom: '2px dashed #999', paddingBottom: 12, marginBottom: 10 }}>{fx.title}</div> : null}
        {shown.map((l, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 40, lineHeight: '74px', gap: 12 }}>
            <span>{l.t}</span>{l.value ? <span style={{ fontWeight: 700 }}>{l.value}</span> : null}
          </div>
        ))}
      </div>
    </div>
  );
};

const Intertitle: React.FC<{ fx: Extract<Effect, { kind: 'intertitle' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const face = accentFace();
  return (
    <Card lf={lf} len={len} h={360} pad={40}>
      <div style={{ height: '100%', border: `3px solid ${GOLD.yellow}`, borderRadius: 18, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 30px' }}>
        <div style={{ fontFamily: face.family, fontStyle: 'italic', fontWeight: face.weight, fontSize: Math.min(86, 1500 / Math.max(fx.text.length, 12)),
          color: CREME_DARK.ink, textAlign: 'center', lineHeight: 1.12 }}>{fx.text}</div>
      </div>
    </Card>
  );
};

const Counter: React.FC<{ fx: Extract<Effect, { kind: 'counter' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const ring = easeOutCubic(clamp01((lf - 4) / 12));
  const pop = easeOutCubic(clamp01((lf - 10) / 6));
  const size = Math.min(150, 560 / (0.6 * Math.max(fx.value.length, 2)));
  const tw = 0.6 * size * fx.value.length;
  const rx = tw / 2 + 50, ry = size * 0.78;                      // the loupe ring wraps the value, whatever its length
  return (
    <Card lf={lf} len={len}>
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 26 }}>
        <div style={{ position: 'relative', width: rx * 2 + 40, height: ry * 2 + 40, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width={rx * 2 + 40} height={ry * 2 + 40} style={{ position: 'absolute', inset: 0 }}>
            <ellipse cx={rx + 20} cy={ry + 20} rx={rx} ry={ry} fill="none" stroke={GOLD.yellow} strokeWidth={6} pathLength={1} strokeDasharray="1" strokeDashoffset={1 - ring} />
          </svg>
          <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: size, lineHeight: 1, color: GOLD.yellow, whiteSpace: 'nowrap', transform: `scale(${0.6 + 0.4 * pop})`,
            opacity: pop, textShadow: `0 0 40px ${glow(0.35)}` }}>{fx.value}</div>
        </div>
        <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 40, color: CREME_DARK.ink, textAlign: 'center', maxWidth: 640, lineHeight: 1.15 }}>{fx.label}</div>
      </div>
    </Card>
  );
};

const Pie: React.FC<{ fx: Extract<Effect, { kind: 'pie' }>; lf: number; len: number }> = ({ fx, lf, len }) => {
  const sweep = easeOutCubic(clamp01((lf - 6) / 16)) * clamp01(fx.pct / 100);
  const a = sweep * 2 * Math.PI;
  const x = 50 + 40 * Math.sin(a), y = 50 - 40 * Math.cos(a);
  const path = sweep >= 0.999 ? 'M50 10 A40 40 0 1 1 49.99 10 Z' : `M50 50 L50 10 A40 40 0 ${sweep > 0.5 ? 1 : 0} 1 ${x} ${y} Z`;
  return (
    <Card lf={lf} len={len}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 34, height: '100%' }}>
        <svg width={300} height={300} viewBox="0 0 100 100" style={{ flex: 'none' }}>
          <circle cx={50} cy={50} r={40} fill="rgba(255,255,255,0.1)" />
          {sweep > 0 ? <path d={path} fill={GOLD.yellow} /> : null}
        </svg>
        <div>
          <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: Math.min(110, 380 / (0.6 * Math.max((fx.value ?? `${fx.pct}%`).length, 3))), lineHeight: 1.05, whiteSpace: 'nowrap', color: GOLD.yellow, opacity: clamp01((lf - 14) / 6) }}>{fx.value ?? `${fx.pct}%`}</div>
          <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 38, color: CREME_DARK.ink, lineHeight: 1.15 }}>{fx.label}</div>
        </div>
      </div>
    </Card>
  );
};

/** One top-band or over-footage effect at this frame (transitions are handled in TransitionLayer). */
export const EffectLayer: React.FC<{ fx: Effect; frame: number; words: Word[]; now: number }> = ({ fx, frame, words, now }) => {
  if (fx.kind === 'transition') return null;
  const lf = frame - fx.in, len = fx.out - fx.in;
  switch (fx.kind) {
    case 'word-stamp': return <WordStamp fx={fx} lf={lf} len={len} />;
    case 'giant-captions': return <GiantCaptions words={words} now={now} lf={lf} len={len} />;
    case 'icon-strike': return <IconStrike fx={fx} lf={lf} len={len} />;
    case 'page-scroll': return <PageScroll fx={fx} lf={lf} len={len} />;
    case 'live-markup': return <LiveMarkup fx={fx} lf={lf} len={len} />;
    case 'keycaps': return <Keycaps fx={fx} lf={lf} len={len} />;
    case 'receipt': return <Receipt fx={fx} lf={lf} len={len} from={fx.in} />;
    case 'intertitle': return <Intertitle fx={fx} lf={lf} len={len} />;
    case 'counter': return <Counter fx={fx} lf={lf} len={len} />;
    case 'pie': return <Pie fx={fx} lf={lf} len={len} />;
    default: return null;
  }
};

/** Camera transitions move the footage around a picture join: returns a CSS transform and blur. */
export const cameraMove = (fx: Extract<Effect, { kind: 'transition' }>, frame: number): { transform: string; filter: string } | null => {
  if (fx.style !== 'whip' && fx.style !== 'zoom' && fx.style !== 'spin') return null;
  const half = 6, d = frame - fx.at;
  if (d < -half || d > half) return null;
  const u = d < 0 ? (d + half) / half : 1 - d / half;          // 0 -> 1 into the join, 1 -> 0 out of it
  const k = u * u;
  const blur = 'blur(' + (14 * k).toFixed(1) + 'px)';
  if (fx.style === 'whip') return { transform: `translateX(${(d < 0 ? -1 : 1) * 380 * k}px)`, filter: blur };
  if (fx.style === 'zoom') return { transform: `scale(${1 + 0.35 * k})`, filter: blur };
  return { transform: `rotate(${(d < 0 ? -1 : 1) * 9 * k}deg) scale(${1 + 0.18 * k})`, filter: blur };
};

/** Shape transitions draw over the footage around a join, never over the face. */
export const ShapeTransition: React.FC<{ fx: Extract<Effect, { kind: 'transition' }>; frame: number; faceX: number; faceY: number }> = ({ fx, frame, faceX, faceY }) => {
  if (fx.style !== 'iris' && fx.style !== 'bars') return null;
  const half = 8, d = frame - fx.at;
  if (d < -half || d > half) return null;
  const u = d < 0 ? (d + half) / half : 1 - d / half;
  if (fx.style === 'iris') {
    const r = 1300 - 900 * easeOutCubic(u);                       // closes to a ring around the face, then opens
    return (
      <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0 }}>
        <defs><mask id={`iris-${fx.at}`}><rect width={1080} height={1920} fill="white" /><circle cx={faceX} cy={faceY - 60} r={r} fill="black" /></mask></defs>
        <rect width={1080} height={1920} fill="#121317" mask={`url(#iris-${fx.at})`} />
        <circle cx={faceX} cy={faceY - 60} r={r} fill="none" stroke={GOLD.yellow} strokeWidth={10} />
      </svg>
    );
  }
  const bars = [80, 260, 440, 1440, 1620, 1800];                 // top and bottom bands, the face band stays clear
  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {bars.map((y, i) => {
        const w = 1080 * easeOutCubic(clamp01(u * 1.6 - i * 0.08));
        return <div key={i} style={{ position: 'absolute', top: y - 80, height: 170, left: i % 2 ? 1080 - w : 0, width: w, background: i % 2 ? GOLD.yellow : '#121317' }} />;
      })}
    </div>
  );
};
