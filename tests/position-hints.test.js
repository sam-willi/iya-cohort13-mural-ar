import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { positionHint, landmarkClue, visibleMuralRegion } from '../js/position-hints.js';

const data = JSON.parse(readFileSync(new URL('../data/objects.json', import.meta.url), 'utf8'));
const placed = data.objects.filter((object) => object.location);

test('every located product has a bounded search region containing its whole answer box', () => {
  for (const object of placed) {
    const hint = positionHint(data.mural, object.location, data.landmarks);
    assert.ok(hint, object.id);
    const r = hint.region, box = object.location;
    assert.ok(r.x >= 0 && r.y >= 0 && r.x + r.w <= data.mural.width && r.y + r.h <= data.mural.height, object.id);
    assert.ok(r.x <= box.x && r.y <= box.y && r.x + r.w >= box.x + box.w && r.y + r.h >= box.y + box.h, object.id);
    assert.ok(r.w >= 2 * data.mural.panelSize, 'hint should cover an area, not an exact answer pin');
    assert.ok(!/\b(?:ft|feet|foot)\b/.test(hint.text));
    assert.ok(!hint.landmark || data.landmarks.some((lm) => hint.landmark.includes(lm.name)), object.id);
  }
});

test('the two lamps resolve to distinct regions and the vintage lamp aligns with the staircase window edge', () => {
  const hintFor = (id) => positionHint(data.mural, data.objects.find((o) => o.id === id).location, data.landmarks);
  const vintage = hintFor('art-nouveau-desk-lamp');
  const modern = hintFor('lamp');
  assert.equal(vintage.label, 'Lower-left area');
  assert.match(vintage.landmark, /bottom edge of the big window by the staircase/);
  assert.equal(modern.label, 'Lower-middle area');
  assert.ok(vintage.region.x + vintage.region.w < modern.region.x);
});

test('landmark text distinguishes inside, overlapping an edge, and outside without inventing distances', () => {
  const landmarks = [{ name: 'the test window', x: 100, y: 20, w: 60, h: 60 }];
  assert.equal(landmarkClue({ x: 110, y: 30, w: 10, h: 10 }, landmarks, 48), 'inside the test window');
  assert.equal(landmarkClue({ x: 115, y: 75, w: 10, h: 10 }, landmarks, 48), 'near the bottom edge of the test window');
  assert.equal(landmarkClue({ x: 110, y: 90, w: 10, h: 10 }, landmarks, 48), 'just below the test window');
  assert.equal(landmarkClue({ x: 300, y: 120, w: 10, h: 10 }, landmarks, 48), null);
});

test('objects spanning panels and objects against mural edges remain fully inside the highlight', () => {
  for (const location of [{ x: 0, y: 0, w: 4, h: 4 }, { x: 570, y: 140, w: 6, h: 4 },
    { x: 40, y: 40, w: 130, h: 60 }, { x: 48, y: 48, w: 48, h: 48 }]) {
    const { region: r } = positionHint(data.mural, location);
    assert.ok(r.x <= location.x && r.y <= location.y);
    assert.ok(r.x + r.w >= location.x + location.w && r.y + r.h >= location.y + location.h);
    assert.ok(r.x + r.w <= data.mural.width && r.y + r.h <= data.mural.height);
  }
  assert.equal(positionHint(data.mural, { x: 575, y: 0, w: 10, h: 10 }), null);
  assert.equal(positionHint(data.mural, { x: 0, y: 0, w: 0, h: 10 }), null);
});

test('blue current-view outline uses the actual visible crop at different zoom and pan positions', () => {
  const mural = { width: 576, height: 144 };
  const view = { left: 20, top: 30, width: 200, height: 100 };
  assert.deepEqual(visibleMuralRegion(mural, { left: 20, top: 30, width: 800, height: 200 }, view),
    { x: 0, y: 0, w: 144, h: 72 });
  assert.deepEqual(visibleMuralRegion(mural, { left: -380, top: -70, width: 1600, height: 400 }, view),
    { x: 144, y: 36, w: 72, h: 36 });
  assert.equal(visibleMuralRegion(mural, { left: 800, top: 800, width: 800, height: 200 }, view), null);
});
