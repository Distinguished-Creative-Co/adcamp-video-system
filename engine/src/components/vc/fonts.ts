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
