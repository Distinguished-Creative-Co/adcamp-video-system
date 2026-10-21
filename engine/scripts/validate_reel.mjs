// Run the engine's validateReel (src/methodology/ReelConfig.ts) against one config, under
// Node, by bundling with the esbuild Remotion already ships. One source of structural rules.
//   node scripts/validate_reel.mjs <name>
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const name = process.argv[2];
if (!name) { console.error('usage: validate_reel.mjs <name>'); process.exit(2); }

const entry = `
import { validateReel } from './src/methodology/ReelConfig';
import cfg from './src/methodology/reels/${name}.config';
validateReel(cfg);
console.log('validateReel: ' + cfg.id + ' OK (' + cfg.frames + ' frames, ' + cfg.scenes.length + ' scenes, ' + cfg.swaps.length + ' swaps)');
`;
const out = await build({
  stdin: { contents: entry, resolveDir: root, loader: 'ts' },
  bundle: true, platform: 'node', format: 'esm', write: false, logLevel: 'silent',
});
const code = out.outputFiles[0].text;
try {
  await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
} catch (e) {
  console.error(String(e.message || e));
  process.exit(1);
}
