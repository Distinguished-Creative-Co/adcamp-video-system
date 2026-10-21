// Frame-by-frame checks of the engine's pure state machine against one real config.
//   node scripts/test_layout.mjs <name>
// Bundles src/methodology/{timeline,layout,ReelConfig}.ts with the esbuild Remotion ships,
// then walks every frame. This is geometry, not taste: the rendered stills are the review.
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const name = process.argv[2];
if (!name) { console.error('usage: test_layout.mjs <name>'); process.exit(2); }

const entry = `
import cfg from './src/methodology/reels/${name}.config';
import { validateReel } from './src/methodology/ReelConfig';
import * as L from './src/methodology/layout';
import * as T from './src/methodology/timeline';
export { cfg, validateReel, L, T };
`;
const out = await build({ stdin: { contents: entry, resolveDir: root, loader: 'ts' }, bundle: true, platform: 'node', format: 'esm', write: false, logLevel: 'silent' });
const { cfg, validateReel, L, T } = await import('data:text/javascript;base64,' + Buffer.from(out.outputFiles[0].text).toString('base64'));

const fails = [];
const check = (ok, msg) => { if (!ok) fails.push(msg); };
const { CANVAS, SAFE, CARD, PANEL, INSET, CAP_FULL, CAP_STAGE, CAP_PANEL } = L;

// 1. static geometry inside the Instagram safe region
check(CARD.x + CARD.w <= SAFE.xMax && CARD.y + CARD.h <= SAFE.yMax, 'card outside safe region');
check(PANEL.x + PANEL.w <= SAFE.xMax && PANEL.y + PANEL.h <= SAFE.yMax, 'panel outside safe region');
check(CAP_FULL.x + CAP_FULL.w <= SAFE.xMax && CAP_FULL.cy + CAP_FULL.size * 1.3 <= SAFE.yMax, 'full captions outside safe region');
check(CAP_STAGE.x + CAP_STAGE.w <= SAFE.xMax && CAP_STAGE.bottom <= CARD.y, 'stage captions overlap the card or the right rail');
check(PANEL.x + CAP_PANEL.x + CAP_PANEL.w <= SAFE.xMax, 'panel captions hit the right rail');
check(PANEL.y + PANEL.h - 64 <= SAFE.yMax, 'CTA button under the IG caption bar');

// 2. every frame
const insetArea = INSET.w * INSET.h;
const onScreen = (x, y, w, h) => Math.max(0, Math.min(x + w, CANVAS.w) - Math.max(x, 0)) * Math.max(0, Math.min(y + h, CANVAS.h) - Math.max(y, 0));
let prev = null, minPresence = Infinity, capGaps = 0, spokenFrames = 0;
const lines = T.buildLines(cfg.words);
for (let f = 0; f < cfg.frames; f++) {
  const s = T.stateAt(cfg, f);
  const p = L.place(s.view, s.zoom, cfg.faceX, cfg.faceY, cfg.source.w, cfg.source.h);
  check(p.left <= 1e-6 && p.top <= 1e-6 && p.left + p.width >= s.view.w - 1e-6 && p.top + p.height >= s.view.h - 1e-6, `f${f}: footage edge visible in the main view`);
  const q = L.place(INSET, s.zoom, cfg.faceX, cfg.faceY, cfg.source.w, cfg.source.h);
  check(q.left <= 1e-6 && q.top <= 1e-6 && q.left + q.width >= INSET.w - 1e-6 && q.top + q.height >= INSET.h - 1e-6, `f${f}: footage edge visible in the inset`);
  // always on screen: main avatar area + inset area (when the panel is up)
  let area = s.swap && s.swap.ps >= 0.999 ? 0 : onScreen(s.view.x + s.cardDx, s.view.y + s.floatY, s.view.w, s.view.h);
  if (s.swap) area += onScreen(s.swap.panelX + INSET.x, PANEL.y + INSET.y, INSET.w, INSET.h);
  minPresence = Math.min(minPresence, area / insetArea);
  check(area >= 0.6 * insetArea, `f${f}: avatar presence ${(area / insetArea).toFixed(2)} of an inset`);
  if (prev) {
    const dz = Math.abs(s.zoom - prev.zoom);
    const zmax = f <= cfg.open.frames ? 0.06 : 0.03;   // the open is a deliberate fast pull-out
    check(dz <= zmax, `f${f}: zoom jumps ${dz.toFixed(3)}`);
    const dv = Math.abs(s.view.x - prev.view.x) + Math.abs(s.view.y - prev.view.y) + Math.abs(s.view.w - prev.view.w);
    check(dv <= 260, `f${f}: view jumps ${dv.toFixed(0)}px`);
  }
  // captions track speech: a spoken word's line is on screen unless a move is mid-flight
  const now = f / 30;
  const speaking = cfg.words.find((w) => w.t && w.s <= now && now <= w.e);
  if (speaking) {
    spokenFrames++;
    // captions lead the voice by LEAD_F, so a line's last word may finish while the next line
    // is already up: the word counts as shown if its line was on screen within those lead frames
    let shown = false;
    for (let k = 0; k <= L.LEAD_F + 1 && !shown; k++) {
      const sk = k === 0 ? s : T.stateAt(cfg, Math.max(0, f - k));
      shown = T.visibleLines(lines, Math.max(0, f - k) / 30, sk.capRegion).some((l) => l.words.includes(speaking)) && sk.capOpacity > 0;
    }
    if (!shown) capGaps++;
  }
  prev = s;
}

// 3. the validator rejects broken configs
const bad = (mut, label) => {
  const c = structuredClone(cfg); mut(c);
  let threw = false; try { validateReel(c); } catch { threw = true; }
  check(threw, `validator accepted a bad config: ${label}`);
};
validateReel(cfg);
bad((c) => { c.scenes[0].mode = 'window'; }, 'first scene not full');
if (cfg.scenes.length > 1) bad((c) => { c.scenes[1].mode = c.scenes[0].mode; }, 'repeated scene mode');
if (cfg.swaps.length) bad((c) => { const sc = [...c.scenes].reverse().find((x) => x.from <= c.swaps[0].in); c.swaps[0].in = sc.from + 2; }, 'swap before the glide settles');
bad((c) => { c.words[1].s = c.words[0].s - 1; }, 'words out of order');
bad((c) => { c.words.slice(0, 8).forEach((w) => { w.line = 0; }); }, 'caption line too long');
bad((c) => { c.source = { w: 1920, h: 1080 }; }, 'landscape source');
if (cfg.swaps.length > 1) bad((c) => { c.swaps[1].in = c.swaps[0].out + 20; }, 'under 3s of plain speaker between swaps');
bad((c) => { const s = c.swaps.find((x) => x.content.kind === 'checklist' && x.out < c.frames); if (s) { const n = s.content.items.length; s.content.items.forEach((it, i) => { it.at = s.in + 10 + Math.round(((s.out - 18 - s.in) * i) / (n - 1)); }); } else c.frames = -1; }, 'build cannot settle 1s before the panel leaves');
bad((c) => { c.cover = { frame: 10, title: 'This title is far too long for a cover' }; }, 'cover title over 4 words');
bad((c) => { c.cover = { frame: 10, title: 'Does AI name you?', accent: 'Nope' }; }, 'cover accent not in title');
const hasWindow = cfg.scenes.some((x) => x.mode === 'window');
if (hasWindow) bad((c) => { const w = [...c.scenes].reverse().find((x) => x.mode === 'window'); w.tone = 'light'; }, 'the ending is light');
bad((c) => { c.scenes[0].tone = 'light'; }, 'a full scene marked light');
if (hasWindow) bad((c) => { const w = [...c.scenes].find((x) => x.mode === 'window'); c.swaps = [{ in: w.from + 30, out: w.from + 120, content: { kind: 'shot', src: 'proof/x.png', w: 1000, h: 800, focus: { x: 900, y: 10, w: 300, h: 50 }, at: w.from + 60, source: 'ChatGPT, 2026-09-22' } }]; }, 'proof focus outside the image');
bad((c) => { c.placement = 'organic'; c.post = { keyword: 'two words', gets: 'x' }; }, 'post keyword not one word');
bad((c) => { c.placement = 'paid'; c.post = { keyword: '', gets: '', link: 'https://example.com' }; const k = c.swaps.find((x) => x.content.kind === 'cta'); if (k) k.content.button = 'Comment CHECK'; else c.frames = -1; }, 'paid ad asking for a comment');

const capPct = spokenFrames ? (100 * (spokenFrames - capGaps) / spokenFrames) : 100;
check(capPct >= 95, `captions visible on only ${capPct.toFixed(1)}% of spoken frames`);
console.log(`test_layout ${name}: ${cfg.frames} frames walked; min avatar presence ${minPresence.toFixed(2)} of an inset; captions on ${capPct.toFixed(1)}% of spoken frames (the rest are the mid-move dips)`);
if (fails.length) {
  console.log(`FAIL (${fails.length})`);
  for (const m of fails.slice(0, 20)) console.log('  - ' + m);
  process.exit(1);
}
console.log('PASS: no footage edges, avatar always on screen, safe zones, no jumps, validator rejects every planted fault that applies to this reel');
