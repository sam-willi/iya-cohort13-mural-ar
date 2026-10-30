import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const data = JSON.parse(fs.readFileSync(new URL('../data/objects.json', import.meta.url), 'utf8'));
const placed = data.objects.filter((o) => o.location);

// mural inches -> target image pixels, as js/app.js does for pre-tilted targets
const apply = ([[a, b, c], [d, e, f], [g, h, i]], x, y) => {
  const z = g * x + h * y + i;
  return [(a * x + b * y + c) / z, (d * x + e * y + f) / z];
};

test('every placed object has its own recognition file and a straight-on target around it', () => {
  for (const o of placed) {
    assert.ok(o.ar?.mind && fs.existsSync(new URL(`../${o.ar.mind}`, import.meta.url)), `${o.id}: ${o.ar?.mind} missing`);
    const [t] = o.ar.targets, c = { x: o.location.x + o.location.w / 2, y: o.location.y + o.location.h / 2 };
    assert.ok(!t.H && c.x > t.x && c.x < t.x + t.w && c.y > t.y && c.y < t.y + t.h, `${o.id}: not inside its first target`);
    assert.ok(o.ar.targets.length <= 3, `${o.id}: the game has three target slots`);
  }
});

test('a pre-tilted target maps its patch of wall onto its whole image', () => {
  const tilted = placed.flatMap((o) => o.ar.targets.filter((t) => t.H).map((t) => [o.id, t]));
  assert.ok(tilted.length > 0);
  for (const [id, t] of tilted) {
    const [w, h] = t.px;
    const close = ([u, v], [eu, ev]) => Math.hypot(u - eu, v - ev) < 1.5; // positions are stored to 0.1 in, about 1 px
    // the wide top edge of the patch runs along the top of the image; the bottom edge is centred under it
    assert.ok(close(apply(t.H, t.x, t.y), [0, 0]), `${id}: top-left`);
    assert.ok(close(apply(t.H, t.x + t.w, t.y), [w, 0]), `${id}: top-right`);
    assert.ok(close(apply(t.H, t.x + t.w / 2, t.y + t.h), [w / 2, h]), `${id}: bottom-centre`);
  }
});

test('objects not found on the painted wall are left out rather than guessed', () => {
  for (const o of data.objects.filter((x) => !x.location)) assert.equal(o.ar, undefined, o.id);
});
