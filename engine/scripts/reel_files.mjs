// The files a reel's render loads from public/, one per line: "need|maybe <path>" ("hi" added for full-resolution only).
//   node scripts/reel_files.mjs <name>
// The list is reelFiles() in src/methodology/ReelConfig.ts, built from the same path helpers the components draw with.
// make_reel.sh stages exactly these, so the draft and the render see what the stills see.
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const name = process.argv[2];
if (name === '--help' || name === '-h') { console.log('usage: reel_files.mjs <name>'); process.exit(0); }   // --help: the usage, nothing else
if (!name) { console.error('usage: reel_files.mjs <name>'); process.exit(2); }
const entry = `
import cfg from './src/methodology/reels/${name}.config';
import { reelFiles } from './src/methodology/ReelConfig';
export { cfg, reelFiles };
`;
const out = await build({ stdin: { contents: entry, resolveDir: root, loader: 'ts' }, bundle: true, platform: 'node', format: 'esm', write: false, logLevel: 'silent' });
const { cfg, reelFiles } = await import('data:text/javascript;base64,' + Buffer.from(out.outputFiles[0].text).toString('base64'));
for (const f of reelFiles(cfg)) console.log(`${f.need ? 'need' : 'maybe'}${f.hi ? ' hi' : ''} ${f.path}`);
