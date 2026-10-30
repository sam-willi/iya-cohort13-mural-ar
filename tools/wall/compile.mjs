// Compiles each product's target images (tools/wall/build/, made by build.py) into targets/objects/<id>.mind,
// using MindAR 1.2.5's own compiler in headless Chrome, the same version the game runs.
//
//   npm install          (once; brings puppeteer-core, which drives the Chrome you already have)
//   npm run targets      (or: node tools/wall/compile.mjs jukebox toaster   to rebuild just those)
//
// Set CHROME=/path/to/chrome if Chrome isn't in the usual macOS place.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const build = path.join(here, 'build');
const outDir = path.join(root, 'targets', 'objects');
const chrome = process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const manifest = JSON.parse(fs.readFileSync(path.join(build, 'manifest.json'), 'utf8'));
const only = process.argv.slice(2);
const ids = Object.keys(manifest).filter((id) => only.length === 0 || only.includes(id));
fs.mkdirSync(outDir, { recursive: true });

// serve tools/wall/build/ so the page can load the images
const server = http.createServer((req, res) => {
  const file = path.join(build, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (req.url === '/') { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end('<!doctype html><title>compile</title>'); return; }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': 'image/png' }); res.end(data);
  });
});
await new Promise((ok) => server.listen(0, ok));
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--use-angle=metal', '--enable-webgl', '--ignore-gpu-blocklist'], protocolTimeout: 0 });
const page = await browser.newPage();
await page.goto(`http://localhost:${server.address().port}/`);

let total = 0;
for (const [n, id] of ids.entries()) {
  const b64 = await page.evaluate(async (files) => {
    const { Compiler } = await import('https://cdn.jsdelivr.net/npm/mind-ar@1.2.5/dist/mindar-image.prod.js');
    const images = await Promise.all(files.map((f) => new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = f; })));
    const compiler = new Compiler();
    await compiler.compileImageTargets(images, () => {});
    const bytes = compiler.exportData();
    let s = ''; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return btoa(s);
  }, manifest[id]);
  const buf = Buffer.from(b64, 'base64');
  fs.writeFileSync(path.join(outDir, `${id}.mind`), buf);
  total += buf.length;
  console.log(`${String(n + 1).padStart(3)}/${ids.length} ${id}: ${manifest[id].length} target(s), ${(buf.length / 1024).toFixed(0)} KB`);
}
console.log(`Done: ${ids.length} files, ${(total / 1048576).toFixed(1)} MB in all.`);
await browser.close();
server.close();
