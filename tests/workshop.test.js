import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../js/lamps.js', import.meta.url), 'utf8');

async function start({ reduced = false, fail = false, legacy = false, width = 390, height = 844 } = {}) {
  const events = new Map(), timers = new Map();
  let timerId = 0, removed = false;
  const filter = { value: 'url(#rough)', parentElement: null,
    removeAttribute(name) { if (name === 'filter') this.value = null; } };
  const moving = { parentElement: filter };
  const calls = [];
  const light = { animate(frames, options) {
    calls.push({ frames, options });
    return { finished: Promise.resolve(), cancel() {} };
  } };
  const svg = { style: {}, attributes: {},
    setAttribute(k, v) { this.attributes[k] = v; },
    querySelectorAll(selector) {
      if (selector === '.lamp-light:not(.lamp-light-right)' || selector === '.lamp-light-right') return [light];
      return [moving];
    },
    remove() { removed = true; },
  };
  filter.parentElement = svg;
  const background = { clientWidth: width, clientHeight: height, append(node) { this.child = node; } };
  const screen = { hidden: false, querySelector: () => background };
  const media = { matches: reduced, addListener(fn) { events.set('motion', fn); } };
  if (!legacy) media.addEventListener = (_, fn) => events.set('motion', fn);
  const context = {
    document: { hidden: false, getElementById: () => screen, importNode: () => svg,
      addEventListener: (name, fn) => events.set(name, fn) },
    window: { matchMedia: () => media, addEventListener: (name, fn) => events.set(name, fn) },
    DOMParser: class { parseFromString() { return { querySelector: () => null, documentElement: svg }; } },
    MutationObserver: class { observe() {} },
    setTimeout(fn, delay) { const id = ++timerId; timers.set(id, { fn, delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
    fetch: async () => ({ ok: !fail, text: async () => '<svg/>' }),
    console: { warn() {} },
  };
  if (!legacy) context.ResizeObserver = class { observe() {} };
  vm.runInNewContext(source, context);
  // Flush the fetch/text/initialization promise chain, including failure cleanup.
  for (let i = 0; i < 8; i++) await Promise.resolve();
  return { svg, filter, background, events, timers, calls, removed: () => removed };
}

test('workshop covers portrait and landscape without a transformed root; moving objects have no filtered ancestor', async () => {
  for (const [width, height] of [[390, 844], [844, 390]]) {
    const app = await start({ width, height });
    const artWidth = Number.parseFloat(app.svg.style.width), artHeight = Number.parseFloat(app.svg.style.height);
    assert.ok(artWidth >= width && artHeight >= height);
    assert.ok(Math.abs(artWidth / artHeight - 900 / 1400) < 1e-12);
    assert.equal(Number.parseFloat(app.svg.style.left), (width - artWidth) / 2);
    assert.equal(Number.parseFloat(app.svg.style.top), (height - artHeight) * 0.4);
    assert.equal(app.svg.attributes.width, artWidth);
    assert.equal(app.filter.value, null);
    assert.equal(app.svg.style.transform, undefined);
    assert.equal(app.background.child, app.svg);
  }
});

test('lamp timers survive Safari page restoration and older observer/media APIs', async () => {
  const app = await start({ legacy: true });
  assert.equal(app.timers.size, 3);
  app.events.get('pageshow')();
  assert.equal(app.timers.size, 3, 'restoration replaces timers instead of duplicating cycles');
  const delays = [...app.timers.values()].map((t) => t.delay);
  assert.equal(delays.filter((d) => d === 9000).length, 1);
  assert.ok(Math.abs(delays[0] - delays[1]) >= 250);
  [...app.timers.values()][0].fn();
  assert.equal(app.calls[0].options.duration, 70);
  assert.ok(app.events.has('motion'));
});

test('reduced motion remains respected and load failures preserve the CSS artwork fallback', async () => {
  assert.equal((await start({ reduced: true })).timers.size, 0);
  const failed = await start({ fail: true });
  assert.equal(failed.background.child, undefined);
  assert.equal(failed.timers.size, 0);
  const css = readFileSync(new URL('../css/style.css', import.meta.url), 'utf8');
  assert.ok(!css.includes('.scene-bg.is-inline'), 'enhancement must not remove the static fallback');
});
