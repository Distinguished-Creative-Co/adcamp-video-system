import React from 'react';
import { Composition, staticFile } from 'remotion';
import { VerticalReel } from './VerticalReel';
import { Companion, COMPANION_SIZES, type CompanionFormat } from '../components/vertical/Companion';
import { validateReel, type ReelConfig } from './ReelConfig';

/**
 * One line per short. Duration and props come from the config (calculateMetadata), so a
 * new short is its config file plus one <Reel .../> line below, nothing else.
 */
const loadChecked = async (id: string, load: () => Promise<{ default: ReelConfig }>) => {
  const cfg = (await load()).default;
  if (cfg.id !== id) throw new Error(`reel ${id}: config id is ${cfg.id}`);
  validateReel(cfg);
  // the full-resolution twin of the cut (scripts/hires_cut.py) is used for the host when it exists
  let out: ReelConfig = cfg;
  // the cut's sidecar: where the picture changes (J-cuts move it off the sound join)
  const side = cfg.src.replace(/\.mp4$/, '.json');
  const sj = await fetch(staticFile(side)).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  if (sj && Array.isArray(sj.videoJoins)) out = { ...out, videoJoins: sj.videoJoins };
  const hi = cfg.src.replace(/-cut\.mp4$/, '-cut-hi.mp4');
  if (hi !== cfg.src) {
    const ok = await fetch(staticFile(hi), { method: 'HEAD' }).then((r) => r.ok).catch(() => false);
    if (ok) return { ...out, srcHi: hi };
  }
  return out;
};

/** One line per short registers the reel AND its companion stills (id--cover-feed, ...). */
const Reel: React.FC<{ id: string; load: () => Promise<{ default: ReelConfig }> }> = ({ id, load }) => (
  <>
  {(Object.keys(COMPANION_SIZES) as CompanionFormat[]).map((fmt) => (
    <Composition key={fmt} id={`${id}--${fmt}`} component={Companion} width={COMPANION_SIZES[fmt][0]} height={COMPANION_SIZES[fmt][1]}
      fps={30} durationInFrames={1} defaultProps={{ cfg: null as ReelConfig | null, format: fmt }}
      calculateMetadata={async () => ({ props: { cfg: await loadChecked(id, load), format: fmt } })} />
  ))}
  <Composition
    id={id}
    component={VerticalReel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    defaultProps={{ cfg: null as ReelConfig | null }}
    calculateMetadata={async () => {
      const cfg = await loadChecked(id, load);
      return { durationInFrames: cfg.frames, props: { cfg } };
    }}
  />
  </>
);

export const RemotionRoot: React.FC = () => (
  <>
    {/* REELS (one line each; scripts/gen_reel_config.py appends here) */}
  </>
);
