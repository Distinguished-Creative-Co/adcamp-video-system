/**
 * The type system. brand.json picks one sans (captions, panels, every label) and one italic
 * serif (the accent word in dynamic captions). Only the faces actually used are loaded.
 */
import brand from '../../brand.json';
import { loadFont as loadHanken } from '@remotion/google-fonts/HankenGrotesk';
import { loadFont as loadInter } from '@remotion/google-fonts/Inter';
import { loadFont as loadMontserrat } from '@remotion/google-fonts/Montserrat';
import { loadFont as loadDMSans } from '@remotion/google-fonts/DMSans';
import { loadFont as loadPoppins } from '@remotion/google-fonts/Poppins';
import { loadFont as loadInstrument } from '@remotion/google-fonts/InstrumentSerif';
import { loadFont as loadPlayfair } from '@remotion/google-fonts/PlayfairDisplay';
import { loadFont as loadDMSerif } from '@remotion/google-fonts/DMSerifDisplay';
import { loadFont as loadFraunces } from '@remotion/google-fonts/Fraunces';
import { loadFont as loadAnton } from '@remotion/google-fonts/Anton';
import { loadFont as loadBebas } from '@remotion/google-fonts/BebasNeue';
import { loadFont as loadOswald } from '@remotion/google-fonts/Oswald';
import { loadFont as loadArchivo } from '@remotion/google-fonts/Archivo';
import { loadFont as loadInterTight } from '@remotion/google-fonts/InterTight';
import { loadFont as loadBarlowCond } from '@remotion/google-fonts/BarlowCondensed';
import { loadFont as loadCaveat } from '@remotion/google-fonts/Caveat';

const SANS_FACES = {
  hanken: () => loadHanken('normal', { weights: ['500', '600', '700', '800'], subsets: ['latin'] }).fontFamily,
  inter: () => loadInter('normal', { weights: ['500', '600', '700', '800'], subsets: ['latin'] }).fontFamily,
  montserrat: () => loadMontserrat('normal', { weights: ['500', '600', '700', '800'], subsets: ['latin'] }).fontFamily,
  dmsans: () => loadDMSans('normal', { weights: ['500', '600', '700', '800'], subsets: ['latin'] }).fontFamily,
  poppins: () => loadPoppins('normal', { weights: ['500', '600', '700', '800'], subsets: ['latin'] }).fontFamily,
};
export type SansFont = keyof typeof SANS_FACES;

const sansKey: SansFont = brand.sans in SANS_FACES ? (brand.sans as SansFont) : 'hanken';
export const SANS: string = SANS_FACES[sansKey]();

/** Italic display serifs. `width` is the average glyph width in em, used to fit a row. */
const SERIF_FACES = {
  playfair: { weight: 800, width: 0.6, load: () => loadPlayfair('italic', { weights: ['800'], subsets: ['latin'] }).fontFamily },
  instrument: { weight: 400, width: 0.46, load: () => loadInstrument('italic', { weights: ['400'], subsets: ['latin'] }).fontFamily },
  dmserif: { weight: 400, width: 0.52, load: () => loadDMSerif('italic', { weights: ['400'], subsets: ['latin'] }).fontFamily },
  fraunces: { weight: 800, width: 0.6, load: () => loadFraunces('italic', { weights: ['800'], subsets: ['latin'] }).fontFamily },
};
export type AccentFont = keyof typeof SERIF_FACES;

export const BRAND_SERIF: AccentFont = brand.serif in SERIF_FACES ? (brand.serif as AccentFont) : 'playfair';

const loadedSerif: Partial<Record<AccentFont, string>> = {};

export const accentFace = (k: AccentFont = BRAND_SERIF): { family: string; weight: number; width: number } => {
  const face = SERIF_FACES[k];
  if (loadedSerif[k] === undefined) loadedSerif[k] = face.load();
  return { family: loadedSerif[k] as string, weight: face.weight, width: face.width };
};

// the brand serif is ready before the first frame
accentFace(BRAND_SERIF);

/** Display faces a saved style can pick for captions and back text (all open-licensed Google Fonts).
 *  `width` is the average glyph width in em at the face's weight, used to fit a line. Loaded on first use. */
const DISPLAY_FACES = {
  anton: { weight: 400, width: 0.47, load: () => loadAnton('normal', { weights: ['400'], subsets: ['latin'] }).fontFamily },
  bebas: { weight: 400, width: 0.42, load: () => loadBebas('normal', { weights: ['400'], subsets: ['latin'] }).fontFamily },
  oswald: { weight: 700, width: 0.5, load: () => loadOswald('normal', { weights: ['500', '700'], subsets: ['latin'] }).fontFamily },
  archivo: { weight: 900, width: 0.62, load: () => loadArchivo('normal', { weights: ['800', '900'], subsets: ['latin'] }).fontFamily },
  archivoitalic: { weight: 900, width: 0.6, italic: true, load: () => loadArchivo('italic', { weights: ['900'], subsets: ['latin'] }).fontFamily },
  intertight: { weight: 800, width: 0.55, load: () => loadInterTight('normal', { weights: ['700', '800'], subsets: ['latin'] }).fontFamily },
  barlowcond: { weight: 800, width: 0.46, load: () => loadBarlowCond('normal', { weights: ['700', '800'], subsets: ['latin'] }).fontFamily },
};
export type DisplayFont = keyof typeof DISPLAY_FACES | SansFont;
export const DISPLAY_KEYS = [...Object.keys(DISPLAY_FACES), ...Object.keys(SANS_FACES)] as DisplayFont[];

const loadedDisplay: Partial<Record<string, string>> = {};

/** The face a style asked for, or the brand sans when it asked for none. */
export const displayFace = (k?: DisplayFont): { family: string; weight: number; width: number; italic: boolean } => {
  if (!k || !(k in DISPLAY_FACES)) {
    if (k && k in SANS_FACES && k !== sansKey) {
      if (loadedDisplay[k] === undefined) loadedDisplay[k] = SANS_FACES[k as SansFont]();
      return { family: loadedDisplay[k] as string, weight: 800, width: 0.56, italic: false };
    }
    return { family: SANS, weight: 800, width: 0.56, italic: false };
  }
  const f = DISPLAY_FACES[k as keyof typeof DISPLAY_FACES];
  if (loadedDisplay[k] === undefined) loadedDisplay[k] = f.load();
  return { family: loadedDisplay[k] as string, weight: f.weight, width: f.width, italic: 'italic' in f && !!f.italic };
};

let hand: string | undefined;
let roman: string | undefined;
/** A handwriting face for notes and arrows (Caveat, open licence). */
export const handFace = (): string => (hand ??= loadCaveat('normal', { weights: ['700'], subsets: ['latin'] }).fontFamily);
/** A plain (upright) display serif for magazine-style titles (Playfair Display 400). */
export const romanSerif = (): string => (roman ??= loadPlayfair('normal', { weights: ['400'], subsets: ['latin'] }).fontFamily);
