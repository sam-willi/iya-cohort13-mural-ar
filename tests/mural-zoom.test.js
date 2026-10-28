import test from 'node:test';
import assert from 'node:assert/strict';
import { setupMuralZoom } from '../js/mural-zoom.js';

function setup() {
  let zoom = 2;
  let gestures = 0;
  const handlers = new Map();
  const calls = [];
  const viewport = {
    clientWidth: 400, clientHeight: 300,
    getBoundingClientRect: () => ({ left: 20, top: 30, right: 420, bottom: 330 }),
    addEventListener(type, handler, options) {
      assert.equal(options.passive, false);
      handlers.set(type, handler);
    },
    removeEventListener: (type) => handlers.delete(type),
  };
  const cleanup = setupMuralZoom({
    viewport,
    getZoom: () => zoom,
    setZoom(value, anchor, previousAnchor) {
      zoom = Math.max(1, Math.min(4, value));
      calls.push({ zoom, anchor, previousAnchor });
    },
    onGesture: () => { gestures++; },
  });
  const send = (type, values = {}) => {
    const event = {
      deltaX: 0, deltaY: 0, deltaMode: 0, clientX: 210, clientY: 160,
      ctrlKey: false, metaKey: false, shiftKey: false, touches: [], prevented: false,
      preventDefault() { this.prevented = true; },
      ...values,
    };
    handlers.get(type)?.(event);
    return event;
  };
  return { send, calls, handlers, cleanup, get zoom() { return zoom; }, get gestures() { return gestures; } };
}

test('trackpad pinch zooms around the pointer; ordinary scrolling stays native in every direction', () => {
  const app = setup();
  for (const delta of [{deltaY:-50},{deltaY:50},{deltaX:-80},{deltaX:80},{deltaX:10,deltaY:-40}]) {
    assert.equal(app.send('wheel', delta).prevented, false);
  }
  assert.equal(app.calls.length, 0);
  assert.equal(app.zoom, 2);
  assert.equal(app.send('wheel', { deltaY: -50, ctrlKey: true }).prevented, true);
  assert.ok(app.zoom > 2);
  assert.deepEqual(app.calls.at(-1).anchor, { x: 210, y: 160 });
  const previous = app.zoom;
  app.send('wheel', { deltaY: 40, ctrlKey: true });
  assert.ok(app.zoom < previous);
  const count = app.calls.length;
  assert.equal(app.send('wheel', { deltaX: 80, deltaY: 1 }).prevented, false);
  assert.equal(app.send('wheel', { deltaY: 80, shiftKey: true }).prevented, false);
  assert.equal(app.calls.length, count);
  assert.equal(app.send('wheel', { deltaY: -8, ctrlKey: true }).prevented, true);
  assert.equal(app.calls.length, count + 1);
  for (let i = 0; i < 30; i++) app.send('wheel', { deltaY: -100, ctrlKey: true });
  assert.equal(app.zoom, 4);
  assert.equal(app.send('wheel', { deltaY: -50 }).prevented, false);
  assert.equal(app.send('wheel', { deltaY: 50 }).prevented, false);
  assert.equal(app.zoom, 4);
  for (let i = 0; i < 30; i++) app.send('wheel', { deltaY: 100, ctrlKey: true });
  assert.equal(app.zoom, 1);
  assert.equal(app.send('wheel', { deltaY: -50 }).prevented, false);
  assert.equal(app.send('wheel', { deltaY: 50 }).prevented, false);
  assert.equal(app.zoom, 1);
  app.cleanup();
  assert.equal(app.handlers.size, 0);
});

test('phone pinch zooms artwork and follows the moving midpoint; single-finger pan stays native', () => {
  const app = setup();
  const touches = (x1, x2) => [{ clientX: x1, clientY: 160 }, { clientX: x2, clientY: 160 }];
  assert.equal(app.send('touchstart', { touches: touches(110, 210).slice(0, 1) }).prevented, false);
  assert.equal(app.send('touchmove', { touches: touches(100, 200).slice(0, 1) }).prevented, false);
  assert.equal(app.calls.length, 0);
  assert.equal(app.send('touchstart', { touches: touches(110, 210) }).prevented, true);
  assert.equal(app.send('touchmove', { touches: touches(90, 230) }).prevented, true);
  assert.equal(app.zoom, 2.8);
  app.send('touchmove', { touches: touches(110, 250) });
  assert.equal(app.zoom, 2.8);
  assert.deepEqual(app.calls.at(-1).previousAnchor, { x: 160, y: 160 });
  assert.deepEqual(app.calls.at(-1).anchor, { x: 180, y: 160 });
  const gestures = app.gestures;
  app.send('touchend');
  assert.ok(app.gestures > gestures, 'pinch end suppresses the follow-up answer tap');
  app.send('touchstart', { touches: touches(110, 210) });
  app.send('touchcancel');
  assert.equal(app.send('wheel', { deltaY: -5, ctrlKey: true }).prevented, true);
  app.cleanup();
});

test('Safari gesture events zoom without double-applying wheel or touch pinch', () => {
  const app = setup();
  assert.equal(app.send('gesturestart').prevented, true);
  app.send('gesturechange', { scale: 1.5 });
  assert.equal(app.zoom, 3);
  const count = app.calls.length;
  app.send('wheel', { ctrlKey: true, deltaY: -10 });
  assert.equal(app.calls.length, count);
  app.send('gestureend');
  app.send('touchstart', { touches: [{ clientX: 100, clientY: 100 }, { clientX: 200, clientY: 100 }] });
  app.send('gesturestart');
  app.send('gesturechange', { scale: 2 });
  assert.equal(app.calls.length, count);
  app.send('touchcancel');
  app.send('wheel', { ctrlKey: true, deltaY: -10 });
  assert.equal(app.calls.length, count + 1);
  app.cleanup();
});
