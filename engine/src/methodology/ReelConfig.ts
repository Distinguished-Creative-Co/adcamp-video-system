import type { DisplayFont } from '../components/vc/fonts';
import brand from '../brand.json';
/**
 * THE CONTRACT. Every short is one ReelConfig in src/methodology/reels/<name>.config.ts,
 * rendered by the one engine (VerticalReel.tsx). Nothing per video lives anywhere else.
 *
 * Units, on purpose:
 *   words: SECONDS on the cut timeline (whisperX truth, 2 dp)
 *   scenes, swaps, frames, open: integer FRAMES at 30 fps (what a human edits, what Remotion consumes)
 *
 * The generator (scripts/gen_reel_config.py) fills everything. A human edits only
 * scenes / swaps / big flags / open.scale. The body of a config file stays JSON so the
 * Python tools read it without executing TypeScript (trailing // comments are allowed).
 */
import { GLIDE_F, SWAP_F, CANVAS, BREATH_F, completionTimes } from './layout';
import { adSafeFaults } from './adsafe';

export type Frame = number;
export type Sec = number;

export type ReelWord = {
  t: string;       // WRITER'S spelling incl. punctuation ('ChatGPT', 'seconds.'); '' = absorbed ASR token (timing only)
  s: Sec;          // start in the cut
  e: Sec;          // end in the cut
  line: number;    // caption line index (generator-chunked), non-decreasing
  sent: number;    // script sentence index, non-decreasing
  big?: boolean;   // emphasis (yellow glow); at most one per line
  key?: boolean;   // dynamic captions: the line's accent word (falls back to big)
};

export type SceneMode = 'full' | 'window';
/** Stage tone for window scenes: light "paper" runs break up a dark reel. The hook and the
 *  ending stay dark. A tone change is a hard cut at a scene change, never a fade. */
export type Tone = 'dark' | 'light';
export type Scene = { from: Frame; mode: SceneMode; tone?: Tone; note?: string };

export type Timed = { t: string; at: Frame };   // a panel element and the frame it enters (word-anchored)

export type SwapContent =
  | { kind: 'words' }                                                // the spoken lines, large, on the panel
  | { kind: 'stat'; value: string; label: string; at?: Frame }       // big figure, pops on `at`
  | { kind: 'cta'; title: string; button: string; sub?: string; at?: Frame }
  | { kind: 'checklist'; items: Timed[] }                            // 2-5 steps, each ticks in on its word
  | { kind: 'funnel'; stages: (Timed & { value?: string })[] }       // 2-5 stages narrowing top to bottom
  | { kind: 'decision'; question?: string; options: Timed[]; pick: number; pickAt: Frame } // 2-3 options narrowing to one
  // PROOF: a REAL, unedited capture (under public/proof/), shown whole, then a hard punch-in on
  // the exact line or number at `at`, with a highlight. `focus` is a rectangle in the image's
  // own pixels. `source` says where and when it was captured (shown small under the image).
  | { kind: 'shot'; src: string; w: number; h: number; focus: { x: number; y: number; w: number; h: number }; at: Frame; source: string };

/** GRADE: a per-reel look on the host footage, applied wherever the footage is drawn (reel,
 *  cover, companion pack) so every format matches. 1 = unchanged. warmth is a sepia mix
 *  (0-0.35), vignette darkens the edges of the frame (0-0.6). Real footage only: the grade
 *  shifts tone, it never retouches. */
export type Grade = { exposure?: number; contrast?: number; saturation?: number; warmth?: number; vignette?: number; film?: number };  // film 0-1: teal/orange tone curves (Grade.tsx)
export const gradeFilter = (g?: Grade | null): string | undefined => {
  if (!g) return undefined;
  const f = [`brightness(${g.exposure ?? 1})`, `contrast(${g.contrast ?? 1})`, `saturate(${g.saturation ?? 1})`];
  if (g.warmth) f.push(`sepia(${g.warmth})`);
  return f.join(' ');
};
export const vignetteBg = (g?: Grade | null): string | undefined =>
  g?.vignette ? `radial-gradient(ellipse 75% 65% at 50% 42%, rgba(0,0,0,0) 55%, rgba(0,0,0,${g.vignette}) 100%)` : undefined;

/** BACK TEXT: a word or two the host says, drawn huge between the room and the host (the host
 *  is matted out of the cut by scripts/matte_reel.py over these frames only), so it reads as
 *  standing behind them. Full-screen shots only. Words must be spoken (scene map check). */
export type BackText = { text: string; in: Frame; out: Frame; glass?: boolean; y?: number; x?: number };   // glass: a frosted-glass word instead of the solid one. y, x: the row's centre in canvas px, to set it behind the head wherever the head is in that shot (a paid ad holds it inside Meta's ad safe zone)
/** INSERT: a floating UI card over a full-screen scene. 'follow' = the person's photo, name,
 *  handle and a Follow pill that flips to Following (identity from src/brand.json unless set here). */
export type FollowInsert = { kind: 'follow'; in: Frame; out: Frame; handle?: string; name?: string; avatar?: string };
/** CLIP: a cutaway from the person's OWN footage (public/inserts/<name>.mp4 via scripts/prep_insert.py),
 *  playing muted in a 16:9 card in the top band while they keep talking. start: seconds into the clip. */
export type ClipInsert = { kind: 'clip'; in: Frame; out: Frame; src: string; start?: number; label?: string };
export type Insert = FollowInsert | ClipInsert;
export type Word = ReelWord;
/** EFFECTS (src/components/vertical/Effects.tsx): motion graphics on full-screen shots, anchored to
 *  the frames of the words they illustrate. Top-band kinds never overlap inserts, back text or each
 *  other. transition sits on a picture join (`at`): camera (whip, zoom, spin), a warm flash, or shape (iris, bars). */
type FxBase = { in: Frame; out: Frame };
export type Effect =
  | (FxBase & { kind: 'word-stamp'; word: string; tilt?: number })
  | (FxBase & { kind: 'giant-captions' })
  | (FxBase & { kind: 'icon-strike'; icon: 'megaphone' | 'ban' | 'calendar' | 'clock' | 'dollar' | 'globe' | 'pin' | 'message' | 'phone' | 'search' | 'star' | 'thumbsdown'; label?: string; strikeAt?: number })
  | (FxBase & { kind: 'page-scroll'; src: string; w: number; h: number; url?: string; source: string })
  | (FxBase & { kind: 'live-markup'; src: string; w: number; h: number; source: string; mark: { shape: 'circle' | 'underline' | 'arrow'; x: number; y: number; w: number; h: number }; markAt?: number })
  | (FxBase & { kind: 'keycaps'; keys: string })
  | (FxBase & { kind: 'receipt'; title?: string; lines: { t: string; value?: string; at: Frame }[] })
  | (FxBase & { kind: 'intertitle'; text: string })
  | (FxBase & { kind: 'counter'; value: string; label: string })
  | (FxBase & { kind: 'pie'; pct: number; value?: string; label: string })
  | (FxBase & { kind: 'list-tracker'; title: string; items: { t: string; at: Frame }[] })   // a header that steps through a list and stays up
  | (FxBase & { kind: 'snap-zoom'; at: Frame; scale?: number })                         // creep in, then snap tighter on the word at `at`
  | (FxBase & { kind: 'quote-card'; text: string; who?: string })                        // words someone said, typed on in quote marks
  | (FxBase & { kind: 'pinned-line'; text: string; y?: number; point?: 'down' })        // one short line pinned at the top (steps aside for other top-band effects); y: its centre, canvas px; point "down": a bouncing arrow instead of the dot
  | (FxBase & { kind: 'cover-story'; title: string; lines?: string[]; strap?: string })  // the frame as a magazine cover
  | (FxBase & { kind: 'highlighter'; src: string; w: number; h: number; source: string; mark: { x: number; y: number; w: number; h: number }; markAt?: number })
  | (FxBase & { kind: 'note-wall'; notes: { t: string; at: Frame }[]; y?: number })     // paper notes stick up around the head, one per beat; y: the wall's centre, canvas px
  | (FxBase & { kind: 'arrow-note'; text: string; x: number; y: number; noteY?: number }) // a handwritten note with an arrow drawn to (x, y); noteY: the note's centre, canvas px
  | (FxBase & { kind: 'comment-box'; keyword: string; lead?: string })                  // the keyword types into a comment field, a heart pops
  | (FxBase & { kind: 'giant-number'; value: string })                                  // a list number slammed in huge, in front of everything: covers the host for a split second on purpose
  | (FxBase & { kind: 'lights-down'; depth?: number })                                  // the room behind the host dims and softens for one line, the host stays lit (cutout: scripts/matte_reel.py). depth 0.35-0.7 (default 0.6), how far the room dims
  | (FxBase & { kind: 'card'; layout: 'statement' | 'content'; label?: string; headline: string; sub?: string;
      items?: { t: string; at?: Frame }[]; list?: 'check' | 'number'; callout?: string; theme?: 'paper' | 'ink' })   // a full-frame slide (Slide.tsx), the host in a corner window
  | { kind: 'transition'; at: Frame; style: 'whip' | 'zoom' | 'spin' | 'iris' | 'bars' | 'flash' };
export const TOP_BAND_FX = ['icon-strike', 'page-scroll', 'live-markup', 'keycaps', 'receipt', 'intertitle', 'counter', 'pie', 'word-stamp',
  'list-tracker', 'quote-card', 'cover-story', 'highlighter', 'note-wall', 'arrow-note', 'comment-box'] as const;
/** Camera punch from cfg.zooms at `frame`: eases to each entry's scale over 4 frames, holds. */
export const zoomAt = (c: ReelConfig, frame: number) => {
  const z = c.zooms ?? [];
  let prev = 1, cur = 1, at = -1;
  for (const e of z) { if (e.at > frame) break; prev = cur; cur = e.scale; at = e.at; }
  if (at < 0) return 1;
  const p = Math.min(1, (frame - at) / 4);
  return prev + (cur - prev) * (1 - Math.pow(1 - p, 3));
};
/** Second framing at this frame: 1 on the first take, framing.tight on the next, alternating at
 *  every picture join. 1 when the reel has no framing or no join list. */
export const framingAt = (c: ReelConfig, frame: Frame): number => {
  if (!c.framing || !c.videoJoins) return 1;
  const n = c.videoJoins.filter((t) => Math.round(t * c.fps) <= frame).length;
  return n % 2 === 1 ? c.framing.tight : 1;
};
// the cutouts are named from the cut's stem, whichever copy the renderer draws (the cut, its color-graded copy, the hi twins)
export const backFgSrc = (src: string, b: BackText) => `${src.replace(/-cut(-hi)?(-c)?\.mp4$/, '').replace(/\.mp4$/, '')}-fg-${b.in}-${b.out}.webm`;
/** The lights-down cutout: its own file (an edge pulled in for a dark room), named under -fg- so the render staging copies it. */
export const lightsFgSrc = (src: string, e: { in: Frame; out: Frame }) => `${src.replace(/-cut(-hi)?(-c)?\.mp4$/, '').replace(/\.mp4$/, '')}-fg-ld-${e.in}-${e.out}.webm`;
export const LIGHTS_DEPTH = 0.6;   // the default dim (Chris picked the deeper look, 2026-11-09); validateReel holds depth to 0.35-0.7 (never to black: the cutout edge shows in a dark room)

/** THUMBNAIL: an uploadable cover (companion format "thumbnail", 1080x1920). The host at
 *  `frame` is matted out (scripts/matte_reel.py), set lower, with `back` (2-5 spoken words)
 *  huge behind them and `front` (one short line) in front. All copy obeys the claims guard. */
export type Thumbnail = { frame: Frame; back: string; front?: string };
export const thumbFgSrc = (src: string, frame: Frame) => `${src.replace(/-cut(-hi)?(-c)?\.mp4$/, '').replace(/\.mp4$/, '')}-thumb-${frame}.png`;

/** The frame-0 cover: a chosen frame of the host plus a 2-4 word title. Instagram shows
 *  frame 0 as the default cover, so this replaces a mid-blink first frame. back: 1-4 spoken words drawn huge behind
 *  the host (their one-frame cutout, scripts/matte_reel.py, thumbFgSrc), the title in front: regular posts only.
 *  title "": the frame alone (a captions-only look has no title). scripts/cover_options.py writes the three options. */
export type Cover = { frame: Frame; title: string; accent?: string; back?: string; backY?: number };   // backY: the top of the head in canvas px, where the words behind tuck in (cover_options.py measures it)

export type Swap = {
  in: Frame;       // panel starts sliding in (card starts sliding off left)
  out: Frame;      // panel starts sliding back; === frames means hold to the end
  kicker?: string; // small line at the top of the panel
  content: SwapContent;
  note?: string;
};

/** LOOK: how a saved style draws the words (scripts/my_styles.py writes it from the style's style.json).
 *  Every field is optional; a reel without a look draws exactly as before. Colors are #RRGGBB. */
export type CaptionLook = {
  font?: DisplayFont;                  // caption face (default: brand.json sans)
  weight?: number;                     // 300-900 (default: the face's display weight)
  case?: 'upper' | 'lower' | 'none';
  size?: number;                       // base size in px (lines 74, punch 128, word 150 by default)
  color?: string;                      // the words
  keyColor?: string;                   // emphasized words (default: brand accent). Any look color may be "accent": the brand accent
  outline?: number;                    // dark outline width in px (0 = none)
  shadow?: 'soft' | 'hard' | 'none';
  plate?: 'dark' | 'none';             // backing plate behind full-screen lines
  y?: number;                          // center of the caption block on full-screen shots, 300-1460
  motion?: 'pop' | 'rise' | 'cut';     // how each word arrives: spring pop (default), slide up, or hard cut
  money?: string;                      // a dollar amount in the captions ($200, $1,200) is drawn in this color. Off unless a look sets it
};
export type Look = { captions?: CaptionLook; backText?: { font?: DisplayFont; color?: string; outline?: number; over?: boolean } };   // backText.over: drawn in front of the host (a close shot hides words behind the head)

export type ReelConfig = {
  id: string;                        // == file stem == Composition id (kebab-case)
  src: string;                       // 'host/<name>-cut.mp4', under public/
  framing?: { tight: number };        // second framing: every other take (between picture joins) is drawn this much tighter, full-screen shots only, so joins read as a camera change
  videoJoins?: number[];             // seconds on the cut where the picture changes (from <cut>.json, set by Root, never by hand)
  srcHi?: string;                    // 'host/<name>-cut-hi.mp4' when scripts/hires_cut.py made one: the same cut at 2160x3840, drawn in place of src so zooms stay sharp (set by Root, never by hand)
  source: { w: number; h: number };  // 1080x1920 after normalize (vertical only)
  faceX: number;                     // face center in source px
  faceY: number;
  fps: 30;
  frames: Frame;
  open: { scale: number; frames: Frame };
  words: ReelWord[];
  scenes: Scene[];
  swaps: Swap[];
  cover?: Cover | null;
  fullCaptionY?: number;             // optional center for full-screen captions, canvas pixels
  captionStyle?: 'lines' | 'punch' | 'dynamic' | 'word' | 'bigword' | 'pill' | 'editorial' | 'steps';   // dynamic: stacked two-font captions, key word in the accent serif. word: one word at a time. bigword, pill, editorial, steps: CaptionStyles.tsx
  look?: Look;                         // a saved style's type and color (my_styles.py), see CaptionLook
  captionAccent?: 'playfair' | 'instrument' | 'dmserif' | 'fraunces';   // accent serif for dynamic captions (default: brand.json serif)
  zooms?: { at: Frame; scale: number }[];      // punch-in camera moves in full-screen shots (scale holds until the next entry)   // lines: short lines (default). punch: 1-2 words at a time, bigger
  music?: string | null | false;       // pin a bed from sounds.json music_beds (else least recently used); false = no bed at all
  musicUnderLu?: number;               // this reel's bed level, LU under the voice (overrides sounds.json music_under_voice_lu)
  sfx?: false;                         // no cue sounds on this reel (a saved style's choice; mix_master.py)
  musicStart?: number;                 // seconds into the bed to start (skip a quiet intro, start on a strong entrance)
  grade?: Grade | null;
  color?: string;                     // a color look: luts/<key>.cube graded onto the host footage by scripts/color_lut.py ("natural" = as shot)
  backText?: BackText[];
  needs?: { beat: string; what: string }[];   // what the edit still needs from the person, per storyboard beat (b01, b02...): shown on top of the storyboard, never blocks the preview
  inserts?: Insert[];
  effects?: Effect[];                 // motion graphics and transitions (Studio and Hype; Minimal keeps camera transitions only)                  // floating cards (follow card) over full-screen scenes, in the top band, never over back text
  thumbnail?: Thumbnail | null;        // custom cover: big spoken words BEHIND the host cutout, a short line in front               // big highlighted words BEHIND the host, full-screen shots only (cutouts: scripts/matte_reel.py)                // optional look on the HOST footage only (panels, captions, proof shots untouched)
  post?: { keyword: string; gets: string; link?: string };  // comment keyword, what the DM sends, link for no-DM platforms
  placement?: 'organic' | 'paid';      // paid Meta ad: graphic CTA "Click Learn More", no comment keyword, ad copy instead of captions, every word inside Meta's ad safe zone (adsafe.ts)
  meta: { raw: string; script: string; cutWx: string; generated: string; look?: string };   // look: the style it was last built in (make_style.py)
};

/** Every timed element of a swap's content, in entrance order (for the completion rule). */
export const contentCues = (s: Swap): number[] => {
  const k = s.content;
  const def = s.in + SWAP_F;
  if (k.kind === 'stat' || k.kind === 'cta') return [k.at ?? def];
  if (k.kind === 'shot') return [k.at];
  if (k.kind === 'checklist') return k.items.map((x) => x.at);
  if (k.kind === 'funnel') return k.stages.map((x) => x.at);
  if (k.kind === 'decision') return [...k.options.map((x) => x.at), k.pickAt];
  return [];
};

/** Cue frames after the completion rule (what the engine actually draws). */
export const settledCues = (s: Swap, frames: number): number[] | null => {
  const cues = contentCues(s);
  if (s.out >= frames) return cues;              // held to the end: nothing leaves, nothing to settle
  return completionTimes(cues, s.out, s.in + 6);
};

const fail = (id: string, msg: string): never => {
  throw new Error(`reel ${id}: ${msg}`);
};

/** Every file under public/ a reel's render can load, named by the same path helpers the components draw with
 *  (backFgSrc, lightsFgSrc, thumbFgSrc, the config's own src fields). make_reel.sh stages exactly this list through
 *  scripts/reel_files.mjs, so a new kind of file is added here once and the draft and the render both get it.
 *  need: the picture is wrong without it (staging stops). hi: only the full-resolution render reads it. */
export type ReelFile = { path: string; need: boolean; hi?: boolean };
export const reelFiles = (c: ReelConfig): ReelFile[] => {
  const files: ReelFile[] = [{ path: c.src, need: true }, { path: c.src.replace(/\.mp4$/, '.json'), need: false }];
  if (/-cut\.mp4$/.test(c.src)) {
    files.push({ path: c.src.replace(/-cut\.mp4$/, '-cut-hi.mp4'), need: false, hi: true });
    if (c.color && c.color !== 'natural') {
      files.push({ path: c.src.replace(/-cut\.mp4$/, '-cut-c.mp4'), need: false });
      files.push({ path: c.src.replace(/-cut\.mp4$/, '-cut-hi-c.mp4'), need: false, hi: true });
    }
  }
  if (!c.look?.backText?.over) for (const b of c.backText ?? []) files.push({ path: backFgSrc(c.src, b), need: true });
  for (const e of c.effects ?? []) {
    if (e.kind === 'lights-down') files.push({ path: lightsFgSrc(c.src, e), need: true });
    if ('src' in e && typeof (e as { src?: unknown }).src === 'string') files.push({ path: (e as { src: string }).src, need: true });
  }
  if (c.cover?.back) files.push({ path: thumbFgSrc(c.src, c.cover.frame), need: true });
  if (c.thumbnail) files.push({ path: thumbFgSrc(c.src, c.thumbnail.frame), need: true });
  for (const s of c.swaps) if (s.content.kind === 'shot') files.push({ path: s.content.src, need: true });
  for (const b of c.inserts ?? []) {
    if (b.kind === 'clip') files.push({ path: b.src, need: true });
    if (b.kind === 'follow' && (b.avatar ?? brand.avatar)) files.push({ path: (b.avatar ?? brand.avatar) as string, need: true });   // FollowCard's own fallback
  }
  const seen = new Set<string>();
  return files.filter((f) => (seen.has(f.path) ? false : (seen.add(f.path), true)));
};

/** Structural validation. Throws with the reel id. Timeline-vs-speech law lives in reel_config.py. */
export const validateReel = (c: ReelConfig): void => {
  const id = c?.id ?? '?';
  if (!/^[a-z][a-z0-9-]*$/.test(c.id)) fail(id, 'id must be kebab-case');
  if (!/^host\/.+\.mp4$/.test(c.src)) fail(id, 'src must be host/<name>.mp4');
  if (c.source.h <= c.source.w) fail(id, 'source must be vertical (h > w)');
  if (c.musicUnderLu !== undefined && (c.musicUnderLu < 8 || c.musicUnderLu > 24)) fail(id, 'musicUnderLu must be 8-24 LU under the voice');
  (c.zooms ?? []).forEach((z, i, a) => {
    if (z.scale < 1 || z.scale > 1.35) fail(id, `zoom ${i} scale must be 1-1.35`);
    if (z.at < 0 || z.at >= c.frames || (i && z.at <= a[i - 1].at)) fail(id, `zoom ${i} frames must rise inside the reel`);
  });
  if (c.grade) {
    const g = c.grade, inR = (v: number | undefined, lo: number, hi: number) => v === undefined || (v >= lo && v <= hi);
    if (!inR(g.exposure, 0.7, 1.15) || !inR(g.contrast, 0.8, 1.4) || !inR(g.saturation, 0.5, 1.3) || !inR(g.warmth, 0, 0.35) || !inR(g.vignette, 0, 0.6) || !inR(g.film, 0, 1))
      fail(id, 'grade out of range: exposure 0.7-1.15, contrast 0.8-1.4, saturation 0.5-1.3, warmth 0-0.35, vignette 0-0.6, film 0-1');
  }
  if (!Number.isInteger(c.frames) || c.frames < 60) fail(id, 'frames must be an integer >= 60');
  if (c.faceX < 0 || c.faceX > c.source.w || c.faceY < 0 || c.faceY > c.source.h) fail(id, 'face outside source');
  if (c.open.scale < 1 || c.open.scale > 1.8) fail(id, 'open.scale must be 1.0-1.8');
  if (c.open.frames < 12 || c.open.frames > 45) fail(id, 'open.frames must be 12-45');
  if (!c.scenes.length || c.scenes[0].from !== 0 || c.scenes[0].mode !== 'full') fail(id, 'scenes[0] must be full@0');
  for (let i = 1; i < c.scenes.length; i++) {
    const a = c.scenes[i - 1], b = c.scenes[i];
    if (b.from <= a.from) fail(id, `scenes not ascending at ${i}`);
    if (b.from - a.from < GLIDE_F + 6) fail(id, `scene ${i} starts ${b.from - a.from}f after the previous (min ${GLIDE_F + 6})`);
    if (b.mode === a.mode) fail(id, `scene ${i} repeats mode ${b.mode}`);
    if (b.from >= c.frames) fail(id, `scene ${i} starts after the end`);
  }
  if (c.scenes.length > 1 && c.scenes[1].from < c.open.frames + 6) fail(id, 'second scene starts inside the open');
  let prevS = -1, prevLine = 0, prevSent = 0;
  const perLine = new Map<number, { n: number; chars: number; big: number }>();
  for (const w of c.words) {
    if (w.s < prevS) fail(id, `words not sorted at "${w.t}"`);
    if (w.e < w.s) fail(id, `word "${w.t}" ends before it starts`);
    if (w.line < prevLine) fail(id, `line index decreases at "${w.t}"`);
    if (w.sent < prevSent) fail(id, `sentence index decreases at "${w.t}"`);
    prevS = w.s; prevLine = w.line; prevSent = w.sent;
    const L = perLine.get(w.line) ?? { n: 0, chars: 0, big: 0 };
    if (w.t) { L.n += 1; L.chars += w.t.length + (L.n > 1 ? 1 : 0); }
    if (w.big) L.big += 1;
    perLine.set(w.line, L);
  }
  for (const [ln, L] of perLine) {
    if (L.n > 6) fail(id, `line ${ln} has ${L.n} words (max 6)`);
    if (L.chars > 26) fail(id, `line ${ln} is ${L.chars} characters (max 26)`);
    if (L.big > 1) fail(id, `line ${ln} has ${L.big} emphasis words (max 1)`);
  }
  let prevOut = -Infinity;
  for (const [i, s] of c.swaps.entries()) {
    if (s.in < prevOut + SWAP_F + BREATH_F) fail(id, `swap ${i} leaves under ${BREATH_F / 30}s of plain speaker after the previous swap`);
    if (s.out <= s.in || (s.out !== c.frames && s.out - s.in < 60)) fail(id, `swap ${i} shorter than 60 frames`);
    if (s.out > c.frames) fail(id, `swap ${i} ends after the reel`);
    const sc = [...c.scenes].reverse().find((x) => x.from <= s.in);
    const next = c.scenes.find((x) => x.from > s.in);
    if (!sc || sc.mode !== 'window') fail(id, `swap ${i} is not inside a window scene`);
    if (sc && s.in < sc.from + GLIDE_F) fail(id, `swap ${i} starts before the glide settles`);
    if (next && s.out + SWAP_F > next.from) fail(id, `swap ${i} overlaps the next scene change`);
    const k = s.content;
    if (k.kind === 'stat' && (k.value.length > 12 || k.label.length > 70)) fail(id, `swap ${i} stat copy too long`);
    if (k.kind === 'cta' && (k.title.length > 60 || k.button.length > 28 || (k.sub ?? '').length > 90)) fail(id, `swap ${i} cta copy too long`);
    if (k.kind === 'checklist' && (k.items.length < 2 || k.items.length > 5 || k.items.some((x) => x.t.length > 34))) fail(id, `swap ${i} checklist needs 2-5 items of <= 34 characters`);
    if (k.kind === 'funnel' && (k.stages.length < 2 || k.stages.length > 5 || k.stages.some((x) => x.t.length > 28 || (x.value ?? '').length > 10))) fail(id, `swap ${i} funnel needs 2-5 stages (label <= 28, value <= 10 characters)`);
    if (k.kind === 'decision' && (k.options.length < 2 || k.options.length > 3 || k.pick < 0 || k.pick >= k.options.length || k.options.some((x) => x.t.length > 30) || (k.question ?? '').length > 60)) fail(id, `swap ${i} decision needs 2-3 options (<= 30 characters) and a valid pick`);
    if (k.kind === 'shot') {
      if (!/^proof\/.+\.(png|jpe?g|webp)$/i.test(k.src)) fail(id, `swap ${i} shot src must be proof/<file>.png|jpg|webp`);
      const f = k.focus;
      if (!(k.w > 0 && k.h > 0 && f.w > 0 && f.h > 0 && f.x >= 0 && f.y >= 0 && f.x + f.w <= k.w && f.y + f.h <= k.h)) fail(id, `swap ${i} shot focus must sit inside the image`);
      if (!k.source || k.source.length > 70) fail(id, `swap ${i} shot needs a source line (where and when it was captured, <= 70 chars)`);
    }
    const cues = contentCues(s);
    for (let j = 1; j < cues.length; j++) if (cues[j] < cues[j - 1]) fail(id, `swap ${i} element cues are out of order`);
    if (cues.some((f) => f < s.in || f > c.frames)) fail(id, `swap ${i} has an element cue outside the swap`);
    if (!settledCues(s, c.frames)) fail(id, `swap ${i}: its build plus a 1s settled hold does not fit before it slides out. Simplify it.`);
    if ((s.kicker ?? '').length > 60) fail(id, `swap ${i} kicker too long`);
    prevOut = s.out;
  }
  for (const [i, sc] of c.scenes.entries()) {
    if (sc.tone === 'light' && sc.mode !== 'window') fail(id, `scene ${i}: only window scenes can be light`);
  }
  const lastWin = [...c.scenes].reverse().find((x) => x.mode === 'window');
  if (lastWin && lastWin.tone === 'light') fail(id, 'the ending stays dark: the last window scene cannot be light');
  const paid = c.placement === 'paid';
  if (c.post && !paid) {
    // a comment keyword is optional (caption-only posts have none); when set it must be sayable
    if (c.post.keyword && !/^[A-Za-z]{3,12}$/.test(c.post.keyword)) fail(id, 'post keyword must be one word, 3-12 letters');
    if (c.post.keyword && (!c.post.gets || c.post.gets.length > 80)) fail(id, 'post.gets says what the DM sends (<= 80 chars)');
  }
  if (paid) {
    // the destination lives in Ads Manager, not in the video: a paid reel renders without one,
    // and its ad kit flags it until it is confirmed (never invented)
    for (const s of c.swaps) {
      const k = s.content;
      const txt = k.kind === 'cta' ? `${k.title} ${k.button} ${k.sub ?? ''}` : '';
      if (/\bcomment\b/i.test(txt)) fail(id, 'a paid ad CTA sends people to the destination, not the comments. Use "Click Learn More".');
    }
    // the same rule for on-screen effects: a full-frame look has no CTA panel, so its call to action is an effect
    for (const e of c.effects ?? []) {
      if (e.kind === 'comment-box') fail(id, 'a paid ad sends people to the destination: no comment box in a paid ad');
      if (e.kind === 'pinned-line' && /\bcomment\b/i.test(e.text)) fail(id, 'a paid ad pinned line says "Click Learn More", not "Comment"');
    }
  }
  (c.backText ?? []).forEach((b, i) => {
    const sc = [...c.scenes].reverse().find((x) => x.from <= b.in);
    const nxt = c.scenes.find((x) => x.from > b.in);
    if (!sc || sc.mode !== 'full' || (nxt && b.out > nxt.from)) fail(id, `backText ${i} must sit inside one full-screen scene`);
    if (b.out - b.in < 30 || b.out > c.frames) fail(id, `backText ${i} needs at least 30 frames inside the reel`);
    if (!b.text.trim() || b.text.length > 18 || b.text.trim().split(/\s+/).length > 3) fail(id, `backText ${i} is 1-3 words, <= 18 characters`);
    const prev = (c.backText ?? [])[i - 1];
    if (prev && b.in < prev.out) fail(id, `backText ${i} overlaps the one before it`);
    if (b.y !== undefined && (b.y < 150 || b.y > 1600)) fail(id, `backText ${i}: y (the row's centre) must be 150-1600`);
    if (b.x !== undefined && (b.x < 100 || b.x > 980)) fail(id, `backText ${i}: x (the row's centre) must be 100-980`);
  });
  if (c.framing && (c.framing.tight < 1.05 || c.framing.tight > 1.5)) fail(id, 'framing.tight must be 1.05-1.5');
  (c.needs ?? []).forEach((n, i) => {
    if (!/^b\d{2}$/.test(n.beat)) fail(id, `needs ${i}: beat must look like b01`);
    if (!n.what.trim() || n.what.length > 200) fail(id, `needs ${i}: say exactly what to send, in 200 characters or less`);
  });
  (c.inserts ?? []).forEach((b, i) => {
    if (b.kind !== 'follow' && b.kind !== 'clip') fail(id, `insert ${i}: unknown kind`);
    if (b.kind === 'clip') {
      if (!/^inserts\/.+\.(mp4|mov|m4v|webm)$/i.test(b.src)) fail(id, `insert ${i} clip src must be inserts/<name>.mp4 (scripts/prep_insert.py)`);
      if ((b.start ?? 0) < 0) fail(id, `insert ${i} clip start must be >= 0`);
      if ((b.label ?? '').length > 32) fail(id, `insert ${i} clip label <= 32 characters`);
    }
    const sc = [...c.scenes].reverse().find((s) => s.from <= b.in);
    const nxt = c.scenes.find((s) => s.from > b.in);
    if (!sc || sc.mode !== 'full' || (nxt && b.out > nxt.from)) fail(id, `insert ${i} must sit inside one full-screen scene`);
    if (b.out - b.in < 45 || b.out > c.frames || b.in < 0) fail(id, `insert ${i} needs at least 45 frames inside the reel`);
    (c.backText ?? []).forEach((t) => { if (b.in < t.out && t.in < b.out) fail(id, `insert ${i} overlaps back text "${t.text}" (same top band)`); });
    const prev = (c.inserts ?? [])[i - 1];
    if (prev && b.in < prev.out) fail(id, `insert ${i} overlaps the one before it`);
  });
  const band: { in: number; out: number; what: string }[] = [
    ...(c.backText ?? []).map((b) => ({ in: b.in, out: b.out, what: 'back text ' + b.text })),
    ...(c.inserts ?? []).map((b) => ({ in: b.in, out: b.out, what: b.kind + ' card' })),
  ];
  (c.effects ?? []).forEach((e, i) => {
    const known = ['word-stamp', 'giant-captions', 'icon-strike', 'page-scroll', 'live-markup', 'keycaps', 'receipt', 'intertitle', 'counter', 'pie', 'card',
      'list-tracker', 'snap-zoom', 'quote-card', 'pinned-line', 'cover-story', 'highlighter', 'note-wall', 'arrow-note', 'comment-box', 'giant-number', 'lights-down', 'transition'];
    if (!known.includes(e.kind)) { fail(id, `effect ${i}: unknown kind ${e.kind}`); return; }
    if (e.kind === 'transition') {
      if (e.at <= 0 || e.at >= c.frames) fail(id, `effect ${i}: transition must sit inside the reel`);
      // a camera move runs 6 frames each side of its join: two closer than 13 frames collide (stacked whips)
      const near = (c.effects ?? []).find((o) => o !== e && o.kind === 'transition' && Math.abs(o.at - e.at) < 13);
      if (near && near.kind === 'transition') fail(id, `effect ${i}: transitions at frames ${e.at} and ${near.at} are under 13 frames apart; keep one`);
      return;
    }
    const sc = [...c.scenes].reverse().find((s) => s.from <= e.in);
    const nxt = c.scenes.find((s) => s.from > e.in);
    if (!sc || sc.mode !== 'full' || (nxt && e.out > nxt.from)) fail(id, `effect ${i} (${e.kind}) must sit inside one full-screen scene`);
    const minF = e.kind === 'giant-number' ? 12 : 30;   // a list number lands on one short word, so it may be brief (12: room to pop and hold)
    if (e.out - e.in < minF || e.out > c.frames || e.in < 0) fail(id, `effect ${i} (${e.kind}) needs at least ${minF} frames inside the reel`);
    if ((TOP_BAND_FX as readonly string[]).includes(e.kind)) {
      const clash = band.find((b) => e.in < b.out && b.in < e.out);
      if (clash) fail(id, `effect ${i} (${e.kind}) overlaps ${clash.what} in the top band`);
      band.push({ in: e.in, out: e.out, what: 'effect ' + e.kind });
    }
    if (e.kind === 'list-tracker') {
      if (!e.title.trim() || e.title.length > 32) fail(id, `effect ${i}: list-tracker title is 1-32 characters`);
      if (e.items.length < 2 || e.items.length > 6) fail(id, `effect ${i}: list-tracker steps through 2-6 items`);
      e.items.forEach((it, j) => { if (it.at < e.in || it.at >= e.out || (j && it.at <= e.items[j - 1].at)) fail(id, `effect ${i}: list-tracker items must rise inside it`); });
    }
    if (e.kind === 'snap-zoom' && (e.at <= e.in || e.at >= e.out || (e.scale ?? 1.15) < 1.05 || (e.scale ?? 1.15) > 1.3)) fail(id, `effect ${i}: snap-zoom snaps inside it, scale 1.05-1.3`);
    if (e.kind === 'quote-card' && (!e.text.trim() || e.text.length > 90)) fail(id, `effect ${i}: quote-card text is 1-90 characters`);
    if (e.kind === 'pinned-line' && (!e.text.trim() || e.text.length > 40)) fail(id, `effect ${i}: pinned-line is 1-40 characters`);
    if (e.kind === 'pinned-line' && e.point !== undefined && e.point !== 'down') fail(id, `effect ${i}: pinned-line point is "down" or left out`);
    if ((e.kind === 'pinned-line' || e.kind === 'note-wall') && e.y !== undefined && (e.y < 150 || e.y > 1600)) fail(id, `effect ${i}: ${e.kind} y (its centre) must be 150-1600`);
    if (e.kind === 'arrow-note' && e.noteY !== undefined && (e.noteY < 150 || e.noteY > 1600)) fail(id, `effect ${i}: arrow-note noteY (the note's centre) must be 150-1600`);
    if (e.kind === 'cover-story' && (!e.title.trim() || e.title.length > 24 || (e.lines ?? []).length > 3)) fail(id, `effect ${i}: cover-story title 1-24 characters, up to 3 lines`);
    if (e.kind === 'highlighter' && !/^proof\/.+\.(png|jpe?g|webp)$/i.test(e.src)) fail(id, `effect ${i}: highlighter src must be a real capture under proof/`);
    if (e.kind === 'note-wall' && (e.notes.length < 1 || e.notes.length > 4 || e.notes.some((n) => n.t.length > 28 || n.at < e.in || n.at >= e.out))) fail(id, `effect ${i}: note-wall holds 1-4 notes of up to 28 characters, inside it`);
    if (e.kind === 'arrow-note' && (!e.text.trim() || e.text.length > 18 || e.x < 40 || e.x > 1040 || e.y < 220 || e.y > 1460)) fail(id, `effect ${i}: arrow-note text up to 18 characters, its target inside the safe area`);
    if (e.kind === 'arrow-note' && Math.abs(e.x - c.faceX) < 220 && Math.abs(e.y - c.faceY) < 300) fail(id, `effect ${i}: arrow-note points into the face; point at something beside it`);
    if (e.kind === 'comment-box' && !/^[A-Za-z0-9]{2,12}$/.test(e.keyword)) fail(id, `effect ${i}: comment-box keyword is 2-12 letters or digits`);
    if (e.kind === 'giant-number') {
      // it fills the frame in front of the host, so it stays brief and shares the screen with nothing else
      if (typeof e.value !== 'string' || !/^\d{1,3}$/.test(e.value)) fail(id, `effect ${i}: giant-number value is 1-3 digits, as text ("2")`);
      if (e.out - e.in > 45) fail(id, `effect ${i}: giant-number holds 12-45 frames (it covers the host, so it stays brief)`);
      const other = (c.effects ?? []).find((o) => o !== e && o.kind !== 'transition' && o.kind !== 'snap-zoom' && o.kind !== 'pinned-line' && e.in < o.out && o.in < e.out);
      if (other) fail(id, `effect ${i}: giant-number overlaps ${other.kind}: it fills the frame`);
      const held = [...(c.backText ?? []).map((b) => ({ ...b, what: 'back text ' + b.text })), ...(c.inserts ?? []).map((b) => ({ ...b, what: b.kind + ' card' }))]
        .find((b) => e.in < b.out && b.in < e.out);
      if (held) fail(id, `effect ${i}: giant-number overlaps ${held.what}: it fills the frame`);
    }
    if (e.kind === 'lights-down') {
      // the room dims behind the host's cutout: one take, nothing else drawn from the cutout or over the whole frame, after the hook
      if (e.out - e.in > 150) fail(id, `effect ${i}: lights-down holds 30-150 frames (one spoken line)`);
      if (e.in < 45) fail(id, `effect ${i}: lights-down starts at frame 45 or later (the hook title lives in the first 45)`);
      // it draws only on a settled full-screen shot: in cards and panels, the picture glides back from the card first
      const scn = [...c.scenes].reverse().find((x) => x.from <= e.in), prevSc = scn && c.scenes[c.scenes.indexOf(scn) - 1];
      if (scn && prevSc && prevSc.mode === 'window' && e.in < scn.from + GLIDE_F)
        fail(id, `effect ${i}: lights-down starts while the picture is still gliding back to full screen (scene at frame ${scn.from}). Start it at frame ${scn.from + GLIDE_F} or later, where it shows`);
      if (e.depth !== undefined && !(typeof e.depth === 'number' && Number.isFinite(e.depth) && e.depth >= 0.35 && e.depth <= 0.7)) fail(id, `effect ${i}: lights-down depth must be a number from 0.35 to 0.7`);
      const join = (c.videoJoins ?? []).map((t) => Math.round(t * c.fps)).find((f) => f > e.in && f < e.out);
      if (join !== undefined) fail(id, `effect ${i}: lights-down runs across the picture join at frame ${join}; keep it inside one take`);
      const lights = (c.effects ?? []).filter((o) => o.kind === 'lights-down');
      if (lights.length > 2) fail(id, 'at most two lights-down in a video');
      const clash = (c.effects ?? []).find((o) => o !== e && (o.kind === 'transition' ? o.at > e.in && o.at < e.out
        : (o.kind === 'lights-down' || o.kind === 'card' || o.kind === 'giant-number') && e.in < o.out && o.in < e.out));
      if (clash) fail(id, `effect ${i}: lights-down overlaps ${clash.kind === 'transition' ? 'a transition at frame ' + clash.at : 'a ' + clash.kind}`);
      const bt = (c.backText ?? []).find((b) => e.in < b.out && b.in < e.out);
      if (bt) fail(id, `effect ${i}: lights-down overlaps ${bt.glass ? 'the glass word' : 'back text'} "${bt.text}"`);
    }
    if (e.kind === 'card') {
      if (e.out - e.in < 45 || e.out - e.in > 300) fail(id, `effect ${i}: a card holds 45-300 frames (1.5-10 s)`);
      if (!e.headline.trim() || e.headline.replace(/==/g, '').length > 60) fail(id, `effect ${i}: card headline is 1-60 characters`);
      if ((e.items ?? []).length > 5) fail(id, `effect ${i}: card lists at most 5 items`);
      (e.items ?? []).forEach((it) => { if (it.at !== undefined && (it.at < e.in || it.at >= e.out)) fail(id, `effect ${i}: card item "${it.t}" ticks outside the card`); });
      const clash = band.find((b) => e.in < b.out && b.in < e.out);
      if (clash) fail(id, `effect ${i} (card) overlaps ${clash.what}: the card fills the frame`);
      band.push({ in: e.in, out: e.out, what: 'a card' });
    }
    if (e.kind === 'word-stamp' && (!e.word.trim() || e.word.length > 14)) fail(id, `effect ${i}: word-stamp is one word, 14 characters or less`);
    if (e.kind === 'keycaps' && (e.keys.length < 2 || e.keys.length > 8)) fail(id, `effect ${i}: keycaps spells 2-8 keys`);
    if (e.kind === 'receipt' && (e.lines.length < 1 || e.lines.length > 5)) fail(id, `effect ${i}: receipt prints 1-5 lines`);
    if ((e.kind === 'page-scroll' || e.kind === 'live-markup') && !/^proof\/.+\.(png|jpe?g|webp)$/i.test(e.src)) fail(id, `effect ${i}: ${e.kind} src must be a real capture under proof/`);
    if (e.kind === 'pie' && (e.pct <= 0 || e.pct > 100)) fail(id, `effect ${i}: pie pct must be 1-100`);
  });
  if (c.thumbnail) {
    const t = c.thumbnail, n = t.back.trim().split(/\s+/).length;
    if (n < 2 || n > 5 || t.back.length > 28) fail(id, 'thumbnail back text is 2-5 words, <= 28 characters');
    if ((t.front ?? '').length > 48) fail(id, 'thumbnail front line <= 48 characters');
    if (t.frame < 0 || t.frame >= c.frames) fail(id, 'thumbnail frame outside the reel');
  }
  if (c.cover) {
    const w = c.cover.title.trim().split(/\s+/);
    const frameOnly = !c.cover.title.trim() && !c.cover.back && !c.cover.accent;   // the frame alone: a captions-only look
    if (!frameOnly && (w.length < 2 || w.length > 4 || c.cover.title.length > 28)) fail(id, 'cover title must be 2-4 words, <= 28 characters');
    if (!Number.isInteger(c.cover.frame) || c.cover.frame < 0 || c.cover.frame >= c.frames) fail(id, 'cover frame outside the reel');
    if (c.cover.accent && !w.includes(c.cover.accent)) fail(id, 'cover accent must be one of the title words');
    if (c.cover.back !== undefined) {
      if (paid) fail(id, 'a paid ad cover is a frame and a title: no words behind the host on its cover');
      const b = c.cover.back.trim().split(/\s+/);
      if (!c.cover.back.trim() || b.length > 4 || c.cover.back.length > 28) fail(id, 'cover words behind the host are 1-4 words, <= 28 characters');
      if (c.cover.backY !== undefined && (c.cover.backY < 150 || c.cover.backY > 1600)) fail(id, 'cover backY (the top of the head) must be 150-1600');
    }
  }
  if (c.look) {
    const hex = (v: string | undefined, what: string) => { if (v !== undefined && v !== 'accent' && !/^#[0-9a-fA-F]{6}$/.test(v)) fail(id, `look ${what} must be #RRGGBB or "accent"`); };
    const L = c.look.captions ?? {};
    hex(L.color, 'captions.color'); hex(L.keyColor, 'captions.keyColor'); hex(L.money, 'captions.money'); hex(c.look.backText?.color, 'backText.color');
    if (L.size !== undefined && (L.size < 40 || L.size > 220)) fail(id, 'look captions.size must be 40-220');
    if (L.y !== undefined && (L.y < 300 || L.y > 1460)) fail(id, 'look captions.y must be 300-1460 (inside the Reels safe zone)');
    if (L.weight !== undefined && (L.weight < 300 || L.weight > 900)) fail(id, 'look captions.weight must be 300-900');
    if (L.outline !== undefined && (L.outline < 0 || L.outline > 12)) fail(id, 'look captions.outline must be 0-12 px');
  }
  if (paid) {
    // Meta lays its UI over the top 14%, the bottom 35% and the sides of a Reels ad: a paid reel draws every word inside
    // x 60-1020, y 250-1250. adsafe.ts places them there; this checks the same boxes for what this reel draws.
    const off = adSafeFaults(c);
    if (off.length) fail(id, `paid ad: words outside Meta's ad safe zone (x 60-1020, y 250-1250): ${off.join('; ')}`);
  }
  if (CANVAS.w !== 1080 || CANVAS.h !== 1920) fail(id, 'engine canvas must be 1080x1920');
};
