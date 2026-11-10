// The camera push into screenshots and the idle drift on held graphics (AVS 2.2), checked as pure math, plus the
// validator rules for a page-scroll focus and push. No render: the look test and the stills are the review.
//   node scripts/test_motion.mjs [<base reel>]     base reel for the validator checks (default zz-avs-sample-clean-talk)
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import path from 'node:path';

if (process.argv.includes('--help') || process.argv.includes('-h')) {
  console.log('usage: node scripts/test_motion.mjs [<base reel>]\nChecks pushCam, pushMaxFor, pushWindow and drift (layout.ts) and the page-scroll focus and push rules (ReelConfig.ts).');
  process.exit(0);
}
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const given = process.argv[2];
if (given && !existsSync(path.join(root, 'src/methodology/reels', given + '.config.ts'))) { console.error(`test_motion: no reel named ${given}`); process.exit(2); }
const base = given || ['zz-avs-sample-clean-talk', 'sample', 'zz-avs-sample'].find((b) => existsSync(path.join(root, 'src/methodology/reels', b + '.config.ts')));
const entry = `
import * as L from './src/methodology/layout';
import { validateReel } from './src/methodology/ReelConfig';
${base ? `import cfg from './src/methodology/reels/${base}.config';` : 'const cfg = null;'}
export { L, validateReel, cfg };
`;
const out = await build({ stdin: { contents: entry, resolveDir: root, loader: 'ts' }, bundle: true, platform: 'node', format: 'esm', write: false, logLevel: 'silent' });
const { L, validateReel, cfg } = await import('data:text/javascript;base64,' + Buffer.from(out.outputFiles[0].text).toString('base64'));

const fails = [];
const check = (ok, msg) => { if (!ok) fails.push(msg); };
const EPS = 1e-6;

// 1. pushCam: starts as the picture at rest, a picture larger than its frame never shows an edge, a smaller one stays
// centred, the scale stays under its cap and never backs off, nothing jumps, the region ends in frame
const frames = [{ vw: 720, vh: 450 }, { vw: 720, vh: 347 }, { vw: 720, vh: 404 }];
let cases = 0;
const pics = (vw, vh) => [
  { x: 0, y: 0, w: vw, h: vh },                         // fills the frame (a wide screenshot, a page)
  { x: (vw - vh * 0.46) / 2, y: 0, w: vh * 0.46, h: vh }, // a tall phone screenshot standing in the middle
  { x: (vw - 300) / 2, y: 0, w: 300, h: vh },
];
for (const { vw, vh } of frames) {
  for (const pic of pics(vw, vh)) {
    const boxes = [
      { x: pic.x + 5, y: 5, w: Math.min(200, pic.w - 10), h: 40 }, { x: pic.x + pic.w - 60, y: vh - 30, w: 55, h: 25 },
      { x: pic.x + pic.w / 2 - 40, y: vh / 2 - 20, w: 80, h: 40 }, { ...pic }, { x: pic.x + 4, y: vh * 0.6, w: pic.w - 8, h: 30 },
      { x: pic.x + 2, y: 2, w: 4, h: 4 },
    ];
    for (const kMax of [L.PUSH_MAX, L.PUSH_MAX_HI]) for (const b of boxes) {
      cases++;
      const tag = `push ${vw}x${vh} pic ${pic.w.toFixed(0)} kMax ${kMax} ${JSON.stringify(b)}`;
      const p0 = L.pushCam(vw, vh, pic, b, 0, kMax);
      check(Math.abs(p0.k - 1) < EPS && Math.abs(p0.tx) < EPS && Math.abs(p0.ty) < EPS, `${tag}: p=0 is not the picture at rest`);
      let prev = p0;
      for (let i = 1; i <= 40; i++) {
        const P = L.pushCam(vw, vh, pic, b, i / 40, kMax);
        check(P.k >= 1 - EPS && P.k <= kMax + EPS, `${tag}: scale ${P.k.toFixed(3)} outside 1-${kMax}`);
        const ax = [[P.tx, pic.x, pic.w, vw], [P.ty, pic.y, pic.h, vh]];
        for (const [t, o, d, v] of ax) {
          const lo = t + o * P.k, hi = t + (o + d) * P.k;
          if (d * P.k >= v - 1e-6) check(lo <= EPS && hi >= v - EPS, `${tag} p=${i / 40}: an edge of the picture shows inside the frame`);
          else check(Math.abs(lo - (v - hi)) < 1e-6, `${tag} p=${i / 40}: a picture smaller than its frame is off centre`);
        }
        check(P.k >= prev.k - EPS, `${tag}: the scale backs off mid-push`);
        check(Math.abs(P.k - prev.k) < 0.1 && Math.abs(P.tx - prev.tx) < 0.08 * vw && Math.abs(P.ty - prev.ty) < 0.08 * vh, `${tag} p=${i / 40}: jumps`);
        prev = P;
      }
      const P = L.pushCam(vw, vh, pic, b, 1, kMax);
      const x0 = P.tx + b.x * P.k, y0 = P.ty + b.y * P.k, x1 = x0 + b.w * P.k, y1 = y0 + b.h * P.k;
      if (b.w * P.k <= vw && b.h * P.k <= vh) check(x0 >= -0.5 && y0 >= -0.5 && x1 <= vw + 0.5 && y1 <= vh + 0.5, `${tag}: the region ends outside the frame`);
    }
  }
}
// a small region gets a real push, a full-frame one none; the cap follows the screenshot's own pixels
check(L.pushTarget(720, 450, { x: 100, y: 100, w: 200, h: 40 }) > 1.5, 'a small region gets no real push');
check(Math.abs(L.pushTarget(720, 450, { x: 0, y: 0, w: 720, h: 450 }) - 1) < EPS, 'the whole picture is pushed into');
check(Math.abs(L.pushMaxFor(1080, 720) - 2.55) < 0.01, `a desktop capture shown at two thirds should go to about 2.55x, got ${L.pushMaxFor(1080, 720)}`);
check(L.pushMaxFor(1179, 207) === L.PUSH_MAX_HI, `a phone capture shown small should reach the ${L.PUSH_MAX_HI}x ceiling`);
check(L.pushMaxFor(400, 720) === 1, 'a capture already blown up at rest should get no push');
for (const [sw, shown] of [[1080, 720], [1179, 207], [800, 720], [3000, 720]]) check(L.pushMaxFor(sw, shown) * shown / sw <= L.PUSH_UPSCALE + EPS || L.pushMaxFor(sw, shown) === 1, `the push blows a ${sw} px capture past ${L.PUSH_UPSCALE}x`);

// 1b. the geometry Effects.tsx draws: every point a mark's pen draws lies inside its push region, a box that misses the
// picture gives no push, Page Scroll stops with the focus mid-view as far as the page allows
const quad = (p0, p1, p2, t) => (1 - t) * (1 - t) * p0 + 2 * (1 - t) * t * p1 + t * t * p2;
const inside = (r, x, y, pen) => x - pen >= r.x - 0.5 && x + pen <= r.x + r.w + 0.5 && y - pen >= r.y - 0.5 && y + pen <= r.y + r.h + 0.5;
for (const [X, Y, MW, MH] of [[40, 73, 228, 28], [10, 10, 600, 20], [300, 200, 30, 12], [5, 5, 700, 300]]) {
  const c = L.markReach('circle', X, Y, MW, MH), cx = X + MW / 2, cy = Y + MH / 2, rx = MW / 2 + 14, ry = MH / 2 + 12, t = (-4 * Math.PI) / 180;
  for (let a = 0; a < 2 * Math.PI; a += 0.05) {
    const ex = rx * Math.cos(a), ey = ry * Math.sin(a);
    check(inside(c, cx + ex * Math.cos(t) - ey * Math.sin(t), cy + ex * Math.sin(t) + ey * Math.cos(t), 3.5), `circle pen at ${a.toFixed(2)} outside its push region (${X},${Y},${MW},${MH})`);
  }
  const u = L.markReach('underline', X, Y, MW, MH);
  for (let k = 0; k <= 20; k++) check(inside(u, quad(X - 6, X + MW / 2, X + MW + 6, k / 20), quad(Y + MH + 10, Y + MH + 22, Y + MH + 8, k / 20), 4), 'underline pen outside its push region');
  const r = L.markReach('arrow', X, Y, MW, MH);
  for (let k = 0; k <= 20; k++) check(inside(r, quad(X + MW + 90, X + MW + 70, X + MW + 10, k / 20), quad(Y - 70, Y + MH / 2, Y + MH / 2, k / 20), 4), 'arrow shaft outside its push region');
  for (const [hx, hy] of [[X + MW + 30, Y + MH / 2 - 18], [X + MW + 8, Y + MH / 2], [X + MW + 30, Y + MH / 2 + 18]]) check(inside(r, hx, hy, 4), 'arrow head outside its push region');
}
const pic = { x: 256, y: 0, w: 208, h: 450 };
check(L.clipBox({ x: 0, y: 0, w: 100, h: 100 }, pic) === null, 'a box that misses the picture still aims a push');
const cb = L.clipBox({ x: 200, y: -10, w: 120, h: 60 }, pic);
check(cb && cb.x === 256 && cb.y === 0 && cb.w === 64 && cb.h === 50, `a box past the picture's edge is not cut to it: ${JSON.stringify(cb)}`);
const sc = 720 / 1080, viewH = 404, travel = 2600 * sc - viewH;
check(Math.abs(L.scrollStop(1300, 100, sc, viewH, travel) + ((1350 * sc) - viewH / 2)) < EPS, 'Page Scroll does not stop with the focus mid-view');
check(L.scrollStop(10, 50, sc, viewH, travel) === 0, 'a focus at the top of the page scrolls past the top');
check(Math.abs(L.scrollStop(2550, 50, sc, viewH, travel) + travel) < EPS, 'a focus at the bottom scrolls past the end of the page');

// 2. pushWindow: PUSH_F frames (at least PUSH_MIN_F), ending PUSH_HOLD_F before the end, none when there is no room
check(JSON.stringify(L.pushWindow(24, 90)) === JSON.stringify({ a: 24, b: 24 + L.PUSH_F }), 'push window in a roomy effect');
check(L.pushWindow(40, 60) === null, 'a push with no room left still runs');
const w = L.pushWindow(30, 60);
check(w && w.b <= 60 - L.PUSH_HOLD_F && w.b - w.a >= L.PUSH_MIN_F, 'a short push window breaks its own rule');
for (let len = 30; len < 160; len++) for (let from = 0; from < len; from++) {
  const x = L.pushWindow(from, len);
  if (x) check(x.b - x.a >= L.PUSH_MIN_F && x.b <= len - L.PUSH_HOLD_F && x.a === from, `push window ${from}/${len} breaks its rule`);
}

// 3. drift: still during the entrance, faint after, smooth every frame
let dprev = L.drift(0);
check(dprev.scale === 1 && dprev.dy === 0, 'drift moves during the entrance');
for (let lf = 1; lf < 900; lf++) {
  for (const ph of [0, 0.27, 0.54]) {
    const d = L.drift(lf, 10, ph), p = L.drift(lf - 1, 10, ph);
    check(d.scale >= 1 - EPS && d.scale <= 1 + L.DRIFT_SCALE + EPS && Math.abs(d.dy) <= L.DRIFT_Y + EPS, `drift f${lf}: past its bounds`);
    check(Math.abs(d.scale - p.scale) < 0.002 && Math.abs(d.dy - p.dy) < 0.5, `drift f${lf} phase ${ph}: jumps`);
    if (lf <= 10) check(Math.abs(d.scale - 1) < EPS || ph > 0, `drift f${lf}: moves before the entrance is done`);
  }
}
const sw = Array.from({ length: 300 }, (_, i) => L.drift(40 + i).scale);
check(Math.max(...sw) - Math.min(...sw) > L.DRIFT_SCALE * 0.8, 'drift never really moves');

// 4. the validator: a focus outside the shot and a non-boolean push are refused, good ones pass
let at = -1;
const shot = { src: 'proof/kinds-test.png', w: 1080, h: 1600, source: 'a test capture' };
const keep = (cfg?.effects ?? []).filter((x) => x.kind === 'transition');
const withFx = (e) => ({ ...cfg, effects: [...keep, { in: at, out: at + 60, ...shot, ...e }] });
const tryV = (c) => { try { validateReel(c); return ''; } catch (e) { return String(e.message || e); } };
if (cfg) {
  // a clear stretch where a plain page-scroll is valid, so a refusal below can only come from the rule under test
  for (let f = 60; f < cfg.frames - 70 && at < 0; f += 10) { at = f; if (tryV(withFx({ kind: 'page-scroll' }))) at = -1; }
}
if (cfg && at < 0) {
  // a reel named on purpose (the install test) must carry the checks: skipping there would hide a hole
  if (given) fails.push(`${base}: no clear stretch for a screenshot effect, or the reel itself does not validate, so the validator checks could not run`);
  else console.log(`  (${base} has no clear stretch for a screenshot effect: validator checks skipped)`);
} else if (cfg) {
  const good = [
    { kind: 'page-scroll', focus: { x: 40, y: 900, w: 700, h: 300 }, push: true },
    { kind: 'page-scroll' },
    { kind: 'live-markup', mark: { shape: 'circle', x: 60, y: 110, w: 500, h: 70 }, push: false },
    { kind: 'highlighter', mark: { x: 60, y: 246, w: 600, h: 36 }, push: true, markAt: 20 },
  ];
  const bad = [
    [{ kind: 'page-scroll', focus: { x: 40, y: 1500, w: 700, h: 300 } }, 'focus must be a part of the screenshot'],
    [{ kind: 'page-scroll', focus: { x: -5, y: 10, w: 100, h: 50 } }, 'focus must be a part of the screenshot'],
    [{ kind: 'page-scroll', focus: { x: 10, y: 10, w: 0, h: 50 } }, 'focus must be a part of the screenshot'],
    [{ kind: 'live-markup', mark: { shape: 'circle', x: 60, y: 110, w: 500, h: 70 }, push: 'yes' }, 'push is true or false'],
    [{ kind: 'page-scroll', focus: null }, 'focus must be a part of the screenshot'],
    [{ kind: 'live-markup', mark: { shape: 'circle', x: 60, y: 110, w: 500, h: 70 }, markAt: -20 }, 'markAt counts frames from the effect'],
    [{ kind: 'highlighter', mark: { x: 60, y: 246, w: 600, h: 36 }, markAt: 300 }, 'markAt counts frames from the effect'],
  ];
  for (const g of good) { const r = tryV(withFx(g)); check(r === '', `validator refuses a good ${g.kind} at ${at}: ${r}`); }
  for (const [b, want] of bad) { const r = tryV(withFx(b)); check(r.includes(want), `validator lets through ${JSON.stringify(b)} (got: ${r || 'pass'})`); }
} else {
  console.log('  (no base reel: validator checks skipped)');
}

if (fails.length) {
  console.log(`test_motion: FAIL (${fails.length})`);
  for (const f of [...new Set(fails)].slice(0, 20)) console.log('  - ' + f);
  process.exit(1);
}
console.log(`test_motion: PASS (${cases} push cases, drift over 900 frames, pushWindow, validator${cfg && at >= 0 ? ' on ' + base + ' at frame ' + at : ' skipped'})`);
