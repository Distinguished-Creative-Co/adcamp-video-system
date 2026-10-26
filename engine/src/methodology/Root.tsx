import React from 'react';
import { Composition, staticFile } from 'remotion';
import { VerticalReel } from './VerticalReel';
import { Companion, COMPANION_SIZES, type CompanionFormat } from '../components/vertical/Companion';
import { validateReel, type ReelConfig } from './ReelConfig';
import { Carousel, CAROUSEL_SIZE, type CarouselDoc } from './Carousel';
import { FontSheet } from './FontSheet';

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
  // a color look: the host footage graded by scripts/color_lut.py, drawn instead of the plain cut (and never the plain
  // full-resolution twin under it)
  if (cfg.color && cfg.color !== 'natural') {
    const graded = cfg.src.replace(/-cut\.mp4$/, '-cut-c.mp4');
    const head = (f: string) => fetch(staticFile(f), { method: 'HEAD' }).then((r) => r.ok).catch(() => false);
    if (graded !== cfg.src && (await head(graded))) {
      out = { ...out, src: graded };
      const gHi = cfg.src.replace(/-cut\.mp4$/, '-cut-hi-c.mp4');
      return (await head(gHi)) ? { ...out, srcHi: gHi } : out;
    }
  }
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
    <Composition id="FontSheet" component={FontSheet} width={1080} height={1350} fps={30} durationInFrames={1}
      defaultProps={{ name: '', accent: '#F7C715' }} />
    <Composition id="Carousel" component={Carousel} width={1080} height={1350} fps={30} durationInFrames={1}
      defaultProps={{ doc: null as CarouselDoc | null }}
      calculateMetadata={({ props }) => {
        const doc = props.doc;
        if (!doc || !doc.slides?.length) throw new Error('carousel: no slides (render it with scripts/carousel.py)');
        const [width, height] = CAROUSEL_SIZE[doc.size ?? '4:5'];
        return { width, height, durationInFrames: doc.slides.length };
      }} />
    {/* REELS (one line each; scripts/gen_reel_config.py appends here) */}
  </>
);
