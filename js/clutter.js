// Draws a packed pile of toys (marbles, ABC blocks, dice, crayons, beach balls, toy cars...)
// behind the cover screens, like the photographs on the I Spy book covers.
// It's seeded, so the pile looks the same on every visit.

const SVG_NS = 'http://www.w3.org/2000/svg';
const SIZE = 600; // the pile is drawn on a 600x600 canvas that is cropped to fill the screen
const GRID = 18;  // one toy per grid cell (plus extras on top) so no background shows through
const PAINT = ['#e3262b', '#f7c325', '#1e9a4c', '#2160b8', '#f17a1c', '#8a3fb0', '#18a9b8', '#ee5a9c'];
const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

let drawn = 0; // keeps gradient/filter ids unique when there's more than one pile on the page

export function drawClutter(svg, { seed = 13 } = {}) {
  const id = `clutter${drawn++}`;
  const rand = mulberry32(seed);
  const ctx = {
    id,
    rand,
    pick: (list) => list[Math.floor(rand() * list.length)],
    shine: `url(#${id}-shine)`,
    sheen: `url(#${id}-sheen)`,
  };

  svg.setAttribute('viewBox', `0 0 ${SIZE} ${SIZE}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
  svg.innerHTML = `
    <defs>
      <filter id="${id}-shadow" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="2" dy="3" stdDeviation="2.5" flood-color="#1a0d05" flood-opacity="0.6" />
      </filter>
      <!-- highlight for round things: a bright spot top-left, darker edges -->
      <radialGradient id="${id}-shine" cx="35%" cy="30%" r="70%">
        <stop offset="0" stop-color="#fff" stop-opacity="0.95" />
        <stop offset="0.18" stop-color="#fff" stop-opacity="0.25" />
        <stop offset="0.6" stop-color="#fff" stop-opacity="0" />
        <stop offset="1" stop-color="#000" stop-opacity="0.45" />
      </radialGradient>
      <!-- soft light from the top-left for flat things -->
      <linearGradient id="${id}-sheen" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#fff" stop-opacity="0.4" />
        <stop offset="0.45" stop-color="#fff" stop-opacity="0" />
        <stop offset="1" stop-color="#000" stop-opacity="0.3" />
      </linearGradient>
    </defs>
    <rect width="${SIZE}" height="${SIZE}" fill="#5a3a22" />`;

  // Big toys on a jittered grid so the whole picture is covered, then small ones sprinkled on top.
  const cell = SIZE / GRID;
  const big = [abcBlock, abcBlock, paintedBlock, marble, die, beachBall, car, crayon, star, button, ring, heart];
  const small = [marble, marble, jack, button, die, star];
  const items = [];
  for (let gx = -1; gx <= GRID; gx++) {
    for (let gy = -1; gy <= GRID; gy++) {
      const x = (gx + 0.5) * cell + (rand() - 0.5) * cell;
      const y = (gy + 0.5) * cell + (rand() - 0.5) * cell;
      items.push([x, y, cell * (1.15 + rand() * 0.75), ctx.pick(big)]);
    }
  }
  items.sort(() => rand() - 0.5);
  for (let i = 0; i < 110; i++) {
    items.push([rand() * SIZE, rand() * SIZE, cell * (0.55 + rand() * 0.4), ctx.pick(small)]);
  }

  for (const [x, y, s, draw] of items) {
    const g = el('g', {
      transform: `translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${Math.round(rand() * 360)})`,
      filter: `url(#${id}-shadow)`,
    });
    draw(g, s, ctx);
    svg.appendChild(g);
  }
}

// ---------- Toys (each is drawn centred on 0,0 at size s) ----------

function marble(g, s, { pick, rand, shine }) {
  const r = s * 0.4;
  const color = pick(PAINT);
  g.append(el('circle', { r, fill: color }));
  // a swirl of a second colour inside the glass
  g.append(el('path', {
    d: `M ${-r * 0.6} ${r * 0.2} Q 0 ${-r * (0.4 + rand() * 0.6)} ${r * 0.6} ${-r * 0.1}`,
    fill: 'none', stroke: pick(PAINT), 'stroke-width': r * 0.28, 'stroke-linecap': 'round', opacity: 0.85,
  }));
  g.append(el('circle', { r, fill: shine }));
}

// Classic wooden alphabet block: natural wood, coloured border and letter, darker side showing.
function abcBlock(g, s, { pick, sheen }) {
  const h = s / 2;
  const color = pick(PAINT);
  g.append(el('rect', { x: -h + s * 0.08, y: -h + s * 0.08, width: s, height: s, rx: s * 0.08, fill: '#b07a3e' }));
  g.append(el('rect', { x: -h, y: -h, width: s, height: s, rx: s * 0.08, fill: '#ecc88e' }));
  g.append(el('rect', { x: -h + s * 0.09, y: -h + s * 0.09, width: s * 0.82, height: s * 0.82, rx: s * 0.04, fill: 'none', stroke: color, 'stroke-width': s * 0.06 }));
  g.append(text(pick(LETTERS), s * 0.6, color));
  g.append(el('rect', { x: -h, y: -h, width: s, height: s, rx: s * 0.08, fill: sheen }));
}

function paintedBlock(g, s, { pick, sheen }) {
  const h = s / 2;
  const color = pick(PAINT);
  g.append(el('rect', { x: -h + s * 0.08, y: -h + s * 0.08, width: s, height: s, rx: s * 0.06, fill: shade(color) }));
  g.append(el('rect', { x: -h, y: -h, width: s, height: s, rx: s * 0.06, fill: color }));
  g.append(text(pick(LETTERS), s * 0.6, '#fff8e7'));
  g.append(el('rect', { x: -h, y: -h, width: s, height: s, rx: s * 0.06, fill: sheen }));
}

function die(g, s, { rand, sheen }) {
  const d = s * 0.7;
  const h = d / 2;
  g.append(el('rect', { x: -h, y: -h, width: d, height: d, rx: d * 0.2, fill: '#fbf8f1', stroke: '#cfc6b3', 'stroke-width': 1 }));
  const p = d * 0.27;
  const faces = {
    1: [[0, 0]], 2: [[-p, -p], [p, p]], 3: [[-p, -p], [0, 0], [p, p]],
    4: [[-p, -p], [p, -p], [-p, p], [p, p]], 5: [[-p, -p], [p, -p], [0, 0], [-p, p], [p, p]],
    6: [[-p, -p], [p, -p], [-p, 0], [p, 0], [-p, p], [p, p]],
  };
  for (const [dx, dy] of faces[1 + Math.floor(rand() * 6)]) {
    g.append(el('circle', { cx: dx, cy: dy, r: d * 0.085, fill: '#1d1a17' }));
  }
  g.append(el('rect', { x: -h, y: -h, width: d, height: d, rx: d * 0.2, fill: sheen }));
}

function beachBall(g, s, { pick, shine }) {
  const r = s * 0.48;
  const colors = [pick(PAINT), '#fffdf6', pick(PAINT), '#fffdf6', pick(PAINT), '#fffdf6'];
  colors.forEach((fill, i) => {
    const a1 = (i / 6) * Math.PI * 2;
    const a2 = ((i + 1) / 6) * Math.PI * 2;
    g.append(el('path', {
      d: `M 0 0 L ${r * Math.cos(a1)} ${r * Math.sin(a1)} A ${r} ${r} 0 0 1 ${r * Math.cos(a2)} ${r * Math.sin(a2)} Z`,
      fill,
    }));
  });
  g.append(el('circle', { r: r * 0.12, fill: '#fffdf6' }));
  g.append(el('circle', { r, fill: shine }));
}

// Toy car seen from above.
function car(g, s, { pick, sheen }) {
  const w = s * 0.55;
  const l = s * 1.05;
  for (const [x, y] of [[-w / 2, -l * 0.3], [w / 2, -l * 0.3], [-w / 2, l * 0.3], [w / 2, l * 0.3]]) {
    g.append(el('rect', { x: x - s * 0.07, y: y - s * 0.11, width: s * 0.14, height: s * 0.22, rx: s * 0.04, fill: '#1d1a17' }));
  }
  g.append(el('rect', { x: -w / 2, y: -l / 2, width: w, height: l, rx: w * 0.35, fill: pick(PAINT) }));
  g.append(el('rect', { x: -w * 0.36, y: -l * 0.22, width: w * 0.72, height: l * 0.16, rx: 3, fill: '#2b3a4a' }));
  g.append(el('rect', { x: -w * 0.36, y: l * 0.12, width: w * 0.72, height: l * 0.12, rx: 3, fill: '#2b3a4a' }));
  g.append(el('rect', { x: -w / 2, y: -l / 2, width: w, height: l, rx: w * 0.35, fill: sheen }));
}

function crayon(g, s, { pick, sheen }) {
  const w = s * 0.22;
  const l = s * 1.1;
  const color = pick(PAINT);
  g.append(el('path', { d: `M ${-w / 2} ${-l / 2 + w} L 0 ${-l / 2 - w * 0.4} L ${w / 2} ${-l / 2 + w} Z`, fill: shade(color) }));
  g.append(el('rect', { x: -w / 2, y: -l / 2 + w, width: w, height: l - w, rx: w * 0.15, fill: color }));
  for (const y of [-l * 0.15, l * 0.25]) {
    g.append(el('rect', { x: -w / 2, y, width: w, height: w * 0.4, fill: '#1d1a17', 'fill-opacity': 0.55 }));
  }
  g.append(el('rect', { x: -w / 2, y: -l / 2 + w, width: w, height: l - w, rx: w * 0.15, fill: sheen }));
}

function star(g, s, { pick, sheen }) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const r = i % 2 ? s * 0.22 : s * 0.5;
    const a = (Math.PI / 5) * i - Math.PI / 2;
    pts.push(`${(Math.cos(a) * r).toFixed(1)},${(Math.sin(a) * r).toFixed(1)}`);
  }
  const points = pts.join(' ');
  g.append(el('polygon', { points, fill: pick(PAINT), 'stroke-linejoin': 'round' }));
  g.append(el('polygon', { points, fill: sheen }));
}

function heart(g, s, { pick, sheen }) {
  const k = s / 2;
  const d = `M 0 ${k * 0.8} C ${-k * 1.2} ${-k * 0.1} ${-k * 0.6} ${-k * 0.95} 0 ${-k * 0.35} C ${k * 0.6} ${-k * 0.95} ${k * 1.2} ${-k * 0.1} 0 ${k * 0.8} Z`;
  g.append(el('path', { d, fill: pick(['#e3262b', '#ee5a9c', '#8a3fb0']) }));
  g.append(el('path', { d, fill: sheen }));
}

function button(g, s, { pick, sheen }) {
  const r = s * 0.36;
  g.append(el('circle', { r, fill: pick(PAINT) }));
  g.append(el('circle', { r: r * 0.72, fill: 'none', stroke: '#000', 'stroke-opacity': 0.2, 'stroke-width': r * 0.08 }));
  const d = r * 0.22;
  for (const [dx, dy] of [[-d, -d], [d, -d], [-d, d], [d, d]]) {
    g.append(el('circle', { cx: dx, cy: dy, r: r * 0.11, fill: '#1d1a17', 'fill-opacity': 0.7 }));
  }
  g.append(el('circle', { r, fill: sheen }));
}

// A ring from a stacking toy.
function ring(g, s, { pick, shine }) {
  const r = s * 0.34;
  g.append(el('circle', { r, fill: 'none', stroke: pick(PAINT), 'stroke-width': s * 0.2 }));
  g.append(el('circle', { r, fill: 'none', stroke: shine, 'stroke-width': s * 0.2 }));
}

// A metal jack.
function jack(g, s, { shine }) {
  const a = s * 0.45;
  for (const deg of [0, 60, 120]) {
    const t = (deg * Math.PI) / 180;
    const x = Math.cos(t) * a;
    const y = Math.sin(t) * a;
    g.append(el('line', { x1: -x, y1: -y, x2: x, y2: y, stroke: '#9aa3ab', 'stroke-width': s * 0.1, 'stroke-linecap': 'round' }));
    for (const k of [-1, 1]) g.append(el('circle', { cx: x * k, cy: y * k, r: s * 0.09, fill: '#b9c1c8' }));
  }
  g.append(el('circle', { r: s * 0.12, fill: shine }));
}

// ---------- Helpers ----------

function text(content, size, fill) {
  const t = el('text', {
    'text-anchor': 'middle', 'dominant-baseline': 'central',
    'font-family': 'Noto Serif Display, Georgia, serif', 'font-weight': 900, 'font-size': size, fill,
  });
  t.textContent = content;
  return t;
}

// A darker version of a hex colour, for the shadowed side of a block.
function shade(hex) {
  const n = parseInt(hex.slice(1), 16);
  const f = (c) => Math.round(c * 0.62).toString(16).padStart(2, '0');
  return `#${f(n >> 16)}${f((n >> 8) & 255)}${f(n & 255)}`;
}

function el(tag, attrs) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

// Small seeded random number generator, so the layout never changes between visits.
function mulberry32(a) {
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
