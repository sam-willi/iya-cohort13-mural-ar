import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { positionHint, visibleMuralRegion } from '../js/position-hints.js';

const source = readFileSync(new URL('../js/app.js', import.meta.url), 'utf8');
const data = JSON.parse(readFileSync(new URL('../data/objects.json', import.meta.url), 'utf8'));
const hintFunctions = source.slice(source.indexOf('function showHint()'), source.indexOf('function skipRiddle()'));
const zoomFunction = source.slice(source.indexOf('function setZoom('), source.indexOf('// Where a tap lands'));

function fixture(width, height) {
  const node = () => ({
    hidden: false, attributes: {},
    setAttribute(key, value) { this.attributes[key] = String(value); },
    toggleAttribute(key, force) { if (force) this.attributes[key] = ''; else delete this.attributes[key]; },
    classList: { add() {}, remove() {} },
  });
  const ui = Object.fromEntries(['hintMapButton', 'hintText', 'hintMap', 'hintMapImage', 'hintMapRegion',
    'hintMapViewport', 'hintMapCaption', 'hintButton', 'riddleCard'].map((id) => [id, node()]));
  let left = 0, top = 0;
  const context = vm.createContext({ ui, mural: data.mural, landmarks: data.landmarks, current: null,
    zoom: 4, mode: 'picture', visibleTarget: null, hintUsed: false, positionHint, visibleMuralRegion,
    centre: (r) => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 }),
    matchMedia: () => ({ matches: true }),
  });
  const wallRect = () => ({ left: 20 - left, top: 38 - top, width: height * 4 * context.zoom, height: height * context.zoom });
  ui.pictureWall = { getBoundingClientRect: wallRect };
  ui.pictureView = { style: { setProperty() {} } };
  ui.pictureScroll = {
    clientWidth: width, clientHeight: height,
    getBoundingClientRect: () => ({ left: 20, top: 30 }),
    get scrollLeft() { return left; },
    set scrollLeft(value) { left = Math.max(0, Math.min(height * 4 * context.zoom - width, value)); },
    get scrollTop() { return top; },
    set scrollTop(value) { top = Math.max(0, Math.min(height * context.zoom + 8 - height, value)); },
    scrollTo({ left: x, top: y }) { this.scrollLeft = x; this.scrollTop = y; },
  };
  vm.runInContext(hintFunctions + zoomFunction, context);
  return context;
}

test('show hint and tap overview center the right product area across all products, zooms and screen shapes', () => {
  for (const [width, height] of [[375, 600], [844, 280]]) {
    const context = fixture(width, height);
    for (const object of data.objects.filter((o) => o.location)) {
      for (const initialZoom of [1, 2, 4]) {
        context.current = object;
        context.zoom = initialZoom;
        context.ui.pictureScroll.scrollLeft = 0;
        context.ui.pictureScroll.scrollTop = 0;
        context.ui.hintMapButton.hidden = true;
        context.showHint();
        assert.equal(context.ui.hintMapButton.hidden, false);
        assert.equal(context.ui.hintMapButton.disabled, false);
        assert.ok(!('hidden' in context.ui.hintMapViewport.attributes), 'SVG view outline becomes visible');
        context.focusHintArea();
        context.updateHintViewport();
        const visible = visibleMuralRegion(data.mural, context.ui.pictureWall.getBoundingClientRect(),
          { left: 20, top: 30, width, height });
        const x = object.location.x + object.location.w / 2, y = object.location.y + object.location.h / 2;
        assert.ok(x >= visible.x && x <= visible.x + visible.w && y >= visible.y && y <= visible.y + visible.h,
          `${object.id}, ${width}x${height}, zoom ${initialZoom}: hint moved to wrong area`);
        const attributes = context.ui.hintMapViewport.attributes;
        assert.equal(Number(attributes.x), visible.x);
        assert.equal(Number(attributes.width), visible.w);
        context.showHint();
        assert.equal(context.ui.hintMapButton.hidden, true);
        assert.equal(context.ui.hintText.hidden, true);
      }
    }
  }
});

test('AR hints never pretend to know the full camera viewport or move the picture', () => {
  const context = fixture(375, 600);
  context.mode = 'camera';
  context.current = data.objects.find((o) => o.id === 'lamp');
  context.ui.hintMapButton.hidden = true;
  context.showHint();
  assert.equal(context.ui.hintMapButton.disabled, true);
  assert.ok('hidden' in context.ui.hintMapViewport.attributes);
  assert.match(context.ui.hintMapCaption.textContent, /Gold/);
  assert.ok(!context.ui.hintMapCaption.textContent.includes('Blue'));
  const zoom = context.zoom;
  context.focusHintArea();
  assert.equal(context.zoom, zoom);
  assert.equal(context.ui.pictureScroll.scrollLeft, 0);
});
