// Frame-by-frame checks of the engine's pure state machine against one real config.
//   node scripts/test_layout.mjs <name>              this reel's own checks (what every build runs)
//   node scripts/test_layout.mjs <name> --self-test  plus the planted faults: broken copies of this reel that the
//                                                    validator must refuse, each by its own rule
// The planted faults test the validator, not the video: they run in the install test and the engine's own test runs,
// never in a member's build, so a fault that can't be placed on their reel never prints a FAIL there.
// Bundles src/methodology/{timeline,layout,ReelConfig}.ts with the esbuild Remotion ships,
// then walks every frame. This is geometry, not taste: the rendered stills are the review.
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const name = process.argv[2];
const SELF = process.argv.includes('--self-test');
if (!name || name.startsWith('-')) { console.error('usage: test_layout.mjs <name> [--self-test]'); process.exit(name === '--help' || name === '-h' ? 0 : 2); }

const entry = `
import cfg from './src/methodology/reels/${name}.config';
import { validateReel } from './src/methodology/ReelConfig';
import * as L from './src/methodology/layout';
import * as T from './src/methodology/timeline';
import * as A from './src/methodology/adsafe';
export { cfg, validateReel, L, T, A };
`;
const out = await build({ stdin: { contents: entry, resolveDir: root, loader: 'ts' }, bundle: true, platform: 'node', format: 'esm', write: false, logLevel: 'silent' });
const { cfg, validateReel, L, T, A } = await import('data:text/javascript;base64,' + Buffer.from(out.outputFiles[0].text).toString('base64'));

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
let adNote = '', cutNote = `no cut at public/${cfg.src} to measure`;
const skipped = [];   // planted faults this reel has no place for (the install test runs two reels so each rule is tried)
if (SELF) {
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
if (!hasWindow) skipped.push('window scene faults');
if (!cfg.swaps.length) skipped.push('swap timing');
if (hasWindow) bad((c) => { const w = [...c.scenes].reverse().find((x) => x.mode === 'window'); w.tone = 'light'; }, 'the ending is light');
bad((c) => { c.scenes[0].tone = 'light'; }, 'a full scene marked light');
if (hasWindow) bad((c) => { const w = [...c.scenes].find((x) => x.mode === 'window'); c.swaps = [{ in: w.from + 30, out: w.from + 120, content: { kind: 'shot', src: 'proof/x.png', w: 1000, h: 800, focus: { x: 900, y: 10, w: 300, h: 50 }, at: w.from + 60, source: 'ChatGPT, 2026-09-22' } }]; }, 'proof focus outside the image');
bad((c) => { c.placement = 'organic'; c.post = { keyword: 'two words', gets: 'x' }; }, 'post keyword not one word');
bad((c) => { c.placement = 'paid'; c.post = { keyword: '', gets: '', link: 'https://example.com' }; const k = c.swaps.find((x) => x.content.kind === 'cta'); if (k) k.content.button = 'Comment CHECK'; else c.frames = -1; }, 'paid ad asking for a comment');

// 4. Meta's ad safe zone (adsafe.ts): a paid reel draws every word inside x 60-1020, y 250-1250. This reel's own content,
// made paid, must pass; planted faults must be caught BY THE AD-SAFE RULE (the error names it), not by some other rule;
// and the same fault on an organic reel must not trip it (organic layout is untouched).
const asPaid = (c) => {
  c.placement = 'paid'; c.post = { keyword: '', gets: '', link: '' };
  if (c.cover?.back) { const { back, backY, ...rest } = c.cover; c.cover = rest; }   // a paid ad's cover is a frame and a title, as cover_options.py makes it
  c.effects = (c.effects ?? []).filter((e) => e.kind !== 'comment-box').map((e) => (e.kind === 'pinned-line' && /\bcomment\b/i.test(e.text) ? { ...e, text: 'Click Learn More' } : e));
  for (const s of c.swaps) if (s.content.kind === 'cta' && /\bcomment\b/i.test(`${s.content.title} ${s.content.button} ${s.content.sub ?? ''}`)) s.content = { ...s.content, button: 'Click Learn More', title: 'See how it works', sub: undefined };
  return c;
};
// a clear stretch of a full-screen scene (nothing else in the top band), for planting one effect; null when the reel has none
const plant = (c, fx) => {
  c.effects = (c.effects ?? []).filter((e) => e.kind === 'transition'); c.backText = []; c.inserts = [];
  const len = fx.out - fx.in;
  for (const [i, sc] of c.scenes.entries()) {
    const from = sc.from + (i === 0 ? c.open.frames + 6 : 6), to = (c.scenes[i + 1]?.from ?? c.frames) - 6;
    if (sc.mode === 'full' && to - from >= len) { const d = from - fx.in; const moved = { ...fx, in: fx.in + d, out: fx.out + d };
    for (const k of ['items', 'notes', 'lines']) if (fx[k]) moved[k] = fx[k].map((it) => ({ ...it, at: it.at + d }));
    c.effects.push(moved); return c; }
  }
  return null;
};
const tryValidate = (c) => { try { validateReel(c); return ''; } catch (e) { return String(e.message || e); } };
// lights-down across a picture join: placed in a clear full-screen stretch (after the hook, no transition in it), then a
// join set inside it must be caught by its own rule
{
  const ld = (join) => {
    const c = structuredClone(cfg); c.backText = []; c.effects = (c.effects ?? []).filter((e) => e.kind === 'transition');
    for (const [i, sc] of c.scenes.entries()) {
      const to = (c.scenes[i + 1]?.from ?? c.frames) - 6;
      const glide = i > 0 && c.scenes[i - 1].mode === 'window' ? L.GLIDE_F : 0;   // only its own rule may trip: past the glide back
      for (let f = Math.max(sc.from + glide + 6, 51); sc.mode === 'full' && f + 60 <= to; f += 10) {
        if (c.effects.some((t) => t.at >= f - 6 && t.at <= f + 66)) continue;
        c.effects.push({ kind: 'lights-down', in: f, out: f + 60 });
        if (join) c.videoJoins = [(f + 30) / 30];
        return c;
      }
    }
    return null;
  };
  const clean = ld(false);
  if (!clean) skipped.push('lights-down join');
  if (clean) {
    const ok = tryValidate(clean), msg = tryValidate(ld(true));
    check(!ok, `a lights-down inside one take fails: ${ok}`);
    check(/picture join/.test(msg), `lights-down across a picture join was not caught by its rule${msg ? ` (failed for another reason instead: ${msg})` : ' (accepted)'}`);
    // in cards and panels it shows only once the picture has glided back to full screen
    const back = cfg.scenes.find((x, k) => k > 0 && x.mode === 'full' && cfg.scenes[k - 1].mode === 'window' && x.from >= 45
      && (cfg.scenes[k + 1]?.from ?? cfg.frames) - x.from >= 30);
    if (!back) skipped.push('lights-down glide');
    if (back) {
      const c = structuredClone(cfg); c.backText = []; c.effects = []; c.effects.push({ kind: 'lights-down', in: back.from, out: back.from + 30 });
      const m = tryValidate(c);
      check(/still gliding back to full screen/.test(m), `a lights-down that starts during the glide back was not refused by its rule${m ? ` (failed for another reason instead: ${m})` : ' (accepted)'}`);
    }
    // every other rule of its own, each planted on the clean placement and caught by name
    const ldFault = (mut, rx, label) => {
      const c = structuredClone(clean); const e = c.effects.at(-1); mut(c, e);
      const m = tryValidate(c);
      check(rx.test(m), `a lights-down ${label} was not refused by its rule${m ? ` (failed for another reason instead: ${m})` : ' (accepted)'}`);
    };
    for (const d of ['x', 0.2, 0.9]) ldFault((c, e) => { e.depth = d; }, /lights-down depth must be a number from 0.35 to 0.7/, `with depth ${JSON.stringify(d)}`);
    ldFault((c, e) => { c.effects.push({ ...e }, { ...e }); }, /at most two lights-down/, 'that is the third in the video');
    ldFault((c, e) => { const n = e.out - e.in; e.in = 40; e.out = 40 + n; c.videoJoins = []; }, /starts at frame 45 or later/, 'starting before frame 45');
    ldFault((c, e) => { c.backText = [{ text: 'TEST', in: e.in, out: e.out }]; }, /lights-down overlaps back text/, 'over words behind');
    ldFault((c, e) => { c.backText = [{ text: 'TEST', in: e.in, out: e.out, glass: true }]; }, /lights-down overlaps the glass word/, 'over a glass word');
    ldFault((c, e) => { c.effects.push({ kind: 'card', layout: 'statement', in: e.in, out: e.in + 50, headline: 'Test' }); }, /lights-down overlaps a card/, 'over a card');
    ldFault((c, e) => { c.effects.push({ kind: 'giant-number', in: e.in, out: e.in + 30, value: '4' }); }, /lights-down overlaps a giant-number/, 'over a giant number');
    { // full-frame scenes only: inside a window scene it is refused (the generic full-screen rule names it)
      const w = cfg.scenes.find((x) => x.mode === 'window');
      if (!w) skipped.push('lights-down in a window scene');
      else ldFault((c, e) => { c.swaps = []; e.in = w.from + 40; e.out = w.from + 80; c.videoJoins = []; }, /lights-down\) must sit inside one full-screen scene/, 'in a window scene');
    }
    // its length: one spoken line, 30-150 frames
    for (const [n, rx] of [[20, /at least 30 frames/], [151, /lights-down holds 30-150 frames/]]) {
      const c = structuredClone(clean); const e = c.effects.at(-1); e.out = e.in + n;
      const m = tryValidate(c);
      if (n > 150 && /full-screen scene|overlaps|picture join/.test(m)) { skipped.push('lights-down over 150 frames'); continue; }   // no 151-frame stretch here: the long case needs room
      check(rx.test(m), `a lights-down of ${n} frames was not refused by its length rule${m ? ` (failed for another reason instead: ${m})` : ' (accepted)'}`);
    }
  }
}
const paidCopy = asPaid(structuredClone(cfg));
const paidErr = tryValidate(paidCopy);
check(!paidErr, `this reel made paid fails validation: ${paidErr}`);
// covers (scripts/cover_options.py): words behind the host are for regular posts; on a paid ad its own rule refuses them
{
  const behind = { frame: 10, title: 'Does AI name you?', back: 'name you' };
  const org = tryValidate(Object.assign(structuredClone(cfg), { placement: 'organic', cover: behind }));
  check(!org, `a words-behind cover on a regular post fails: ${org}`);
  const paidC = tryValidate(Object.assign(asPaid(structuredClone(cfg)), { cover: behind }));
  check(/paid ad cover is a frame and a title/.test(paidC), `a paid ad accepted a words-behind cover${paidC ? ` (failed for another reason instead: ${paidC})` : ''}`);
  bad((c) => { c.cover = { frame: 10, title: '', back: 'name you' }; }, 'words behind with no title');
}
const adBoxes = A.adTextBoxes(paidCopy).length;
const cramped = { kind: 'card', layout: 'content', in: 0, out: 60, label: 'Before you book', headline: 'Five things that\nkeep you up at night',
  sub: 'And the one change that fixes most of them for good', callout: 'Most people never hear this from their doctor',
  items: ['Racing thoughts', 'A sore lower back', 'Waking at 3 a.m.', 'Tight shoulders', 'Restless legs'].map((t, j) => ({ t, at: 6 + 10 * j })) };
const awayX = cfg.faceX < 540 ? 900 : 180;   // planted arrows point beside the face, never into it, wherever the face sits
const pointLow = { kind: 'arrow-note', in: 0, out: 40, text: 'right here', x: awayX, y: 1400 };
let adPlanted = 0;
const adFault = (fx, label) => {
  const planted = plant(asPaid(structuredClone(cfg)), fx);
  if (!planted) { skipped.push('ad-safe: ' + label); return; }   // a reel this short has no full-screen stretch to plant it in
  adPlanted++;
  const msg = tryValidate(planted);
  check(/ad safe zone/.test(msg), `ad-safe check missed a planted fault: ${label}${msg ? ` (failed for another reason instead: ${msg})` : ' (accepted)'}`);
  const org = tryValidate(plant(Object.assign(structuredClone(cfg), { placement: 'organic' }), fx));
  check(!/ad safe zone/.test(org), `ad-safe rule fired on an organic reel: ${label}`);
};
adFault(cramped, 'a paid card too full for the zone (its words spill above y 250)');
adFault(pointLow, "a paid arrow note pointing into Meta's bottom bar (y 1400)");
const plain = plant(asPaid(structuredClone(cfg)), { kind: 'card', layout: 'statement', in: 0, out: 60, headline: 'Sleep comes ==first==' });
const fine = plain ? tryValidate(plain) : '';
check(!fine, `a plain paid card fails: ${fine}`);
const longest = tryValidate(Object.assign(asPaid(structuredClone(cfg)), { cover: { frame: 10, title: 'Unquestionably Unforgettable' } }));
check(!longest, `the longest paid cover title fails: ${longest}`);
// an entry's own place (back text y/x, pinned-line y, note-wall y, arrow-note noteY): a paid reel holds it inside the zone
// wherever it is set; a place off the frame is refused for any reel
if (!paidCopy.backText?.length) skipped.push('paid back text');
if (paidCopy.backText?.length) {
  const far = asPaid(structuredClone(cfg)); far.backText[0] = { ...far.backText[0], y: 1580, x: 960 };
  const farErr = tryValidate(far);
  check(!farErr, `a paid back text set low and right is not held inside the zone: ${farErr}`);
  bad((c) => { c.backText[0].y = 1700; }, 'back text centred off the frame (y 1700)');
}
for (const fx of [{ kind: 'pinned-line', in: 0, out: 60, text: 'Click Learn More', y: 1580 },
  { kind: 'note-wall', in: 0, out: 60, notes: [{ t: 'Low back', at: 4 }, { t: 'Tight hips', at: 20 }], y: 1500 },
  { kind: 'arrow-note', in: 0, out: 40, text: 'this one', x: awayX, y: 1100, noteY: 1580 }]) {
  const placed = plant(asPaid(structuredClone(cfg)), fx);
  if (placed) { const err = tryValidate(placed); check(!err, `a paid ${fx.kind} set low is not held inside the zone: ${err}`); }
}

adNote = `ad safe zone: this reel made paid keeps all ${adBoxes} blocks of words inside x 60-1020, y 250-1250; ` +
  (adPlanted ? `${adPlanted} planted faults caught by the ad-safe rule, none trips it on the organic reel` : 'no full-screen stretch long enough to plant a fault in');
}

// 5. the scene map refuses a config whose frames no longer match its cut (scene_map.py cut_length_error, the one rule).
// This reel as it is must pass. A config 36 frames longer than its cut (the last picture frozen on screen, True Life's
// mood-regulation-ad after a re-cut) and one 36 frames shorter (the end of what is said dropped) must be refused by name.
if (existsSync(path.join(root, 'public', cfg.src))) {
  const py = 'import json, sys\nsys.path.insert(0, "scripts")\nimport scene_map\nname, src, frames = sys.argv[1], sys.argv[2], int(sys.argv[3])\n' +
    'n = scene_map.cut_frames({"src": src})\nprint(json.dumps([n] + [scene_map.cut_length_error(name, f, n) for f in (frames, n + 36, n - 36)]))';
  const [cutF, asIs, long, short] = JSON.parse(execFileSync(process.platform === 'win32' ? (process.env.AVS_PYTHON || 'python') : 'python3', ['-c', py, name, cfg.src, String(cfg.frames)], { cwd: root, encoding: 'utf8' }));
  check(!asIs, `the scene map refuses this reel's length: ${asIs}`);
  for (const [err, f, label] of SELF ? [[long, cutF + 36, 'longer'], [short, cutF - 36, 'shorter']] : []) {
    check(err && err.includes(`"frames" is ${f} `) && err.includes(`runs ${cutF} frames`),
      `the length check missed a config 36 frames ${label} than its cut (${f} vs ${cutF})${err ? `: ${err}` : ' (accepted)'}`);
  }
  cutNote = `this reel's ${cfg.frames} frames match its cut (${cutF})` + (SELF ? '; configs 36 frames longer and shorter are refused' : '');
}

const capPct = spokenFrames ? (100 * (spokenFrames - capGaps) / spokenFrames) : 100;
check(capPct >= 95, `captions visible on only ${capPct.toFixed(1)}% of spoken frames`);
console.log(`test_layout ${name}: ${cfg.frames} frames walked; min avatar presence ${minPresence.toFixed(2)} of an inset; captions on ${capPct.toFixed(1)}% of spoken frames (the rest are the mid-move dips)`);
if (fails.length) {
  console.log(`FAIL (${fails.length})`);
  for (const m of fails.slice(0, 20)) console.log('  - ' + m);
  process.exit(1);
}
if (adNote) console.log(adNote);
if (SELF && skipped.length) console.log(`planted faults with no place on this reel (skipped): ${skipped.join('; ')}`);
console.log(`cut length: ${cutNote}`);
console.log('PASS: no footage edges, avatar always on screen, safe zones, no jumps' + (SELF ? ', validator rejects every planted fault that applies to this reel' : ', the config passes the validator'));
