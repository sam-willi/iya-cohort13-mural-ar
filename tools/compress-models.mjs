// Compresses the 3D renderings so they download fast on phones.
//
// Put the original exports in models/incoming/ (not committed), named by object id, e.g. typewriter.glb,
// then run:   npm install   (once)   and   npm run models
// Each one is written to models/<id>.glb: Draco-compressed geometry, WebP textures at most 1024 px,
// unused data removed, and meshes simplified where it doesn't visibly change the shape.
// See docs/compression.md.

import { existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { join, parse } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const incoming = join(root, 'models', 'incoming');
const cli = join(root, 'node_modules', '@gltf-transform', 'cli', 'bin', 'cli.js');

// Draco: the app is set up to decode it (dracoDecoderPath in index.html). WebP: smallest download, works on every phone.
// --palette false: keep plain colours as material colours. Merging them into a tiny palette texture lets WebP's lossy
// compression shift the colours (flat-coloured models came out grey).
const SETTINGS = ['--compress', 'draco', '--texture-compress', 'webp', '--texture-size', '1024', '--palette', 'false'];

if (!existsSync(cli)) {
  console.error('glTF Transform is not installed yet. Run:  npm install');
  process.exit(1);
}
mkdirSync(incoming, { recursive: true });
const files = readdirSync(incoming).filter((f) => /\.(glb|gltf)$/i.test(f));
if (files.length === 0) {
  console.log('Nothing to do. Put the original .glb files in models/incoming/, named by object id (e.g. typewriter.glb).');
  process.exit(0);
}

const kb = (bytes) => (bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`);
const failed = [];
for (const file of files) {
  const src = join(incoming, file);
  const dest = join(root, 'models', `${parse(file).name.toLowerCase()}.glb`);
  console.log(`\n${file}`);
  const result = spawnSync(process.execPath, [cli, 'optimize', src, dest, ...SETTINGS], { stdio: 'inherit' });
  if (result.status !== 0) {
    failed.push(file);
    continue;
  }
  console.log(`  ${kb(statSync(src).size)} -> ${kb(statSync(dest).size)}  (models/${parse(dest).base})`);
}

if (failed.length) {
  console.error(`\nCould not compress: ${failed.join(', ')}`);
  process.exit(1);
}
console.log('\nDone. Check them with tools/preview-model.html, then run: npm run sizes');
