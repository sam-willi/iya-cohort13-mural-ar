// Draws a busy pile of toys (marbles, dice, letter blocks, stars, buttons, rings, pegs)
// behind the cover screens, like the photos on the I Spy book covers.
// It's seeded, so the pile looks the same on every visit.

const SVG_NS = 'http://www.w3.org/2000/svg';
const SIZE = 600; // the pile is drawn on a 600x600 canvas that is cropped to fill the screen
const COLORS = ['#d42a2a', '#f6b730', '#1d8a4a', '#2357a6', '#ef7d1a', '#7b3fa0', '#19a7b5', '#fff8e7'];
const LETTERS = 'IYASPYC13ABCDEFGHIJKLMNOPQRSTUVWXYZ';

let drawn = 0; // keeps gradient/filter ids unique when there's more than one pile on the page

export function drawClutter(svg, { count = 150, seed = 13 } = {}) {
  const id = `clutter${drawn++}`;
  const rand = mulberry32(seed);
  const pick = (list) => list[Math.floor(rand() * list.length)];

  svg.setAttribute('viewBox', `0 0 ${SIZE} ${SIZE}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
  svg.innerHTML = `
    <defs>
      <filter id="${id}-shadow" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="2" dy="4" stdDeviation="3" flood-color="#000" flood-opacity="0.55" />
      </filter>
      <radialGradient id="${id}-shine" cx="35%" cy="30%" r="65%">
        <stop offset="0" stop-color="#fff" stop-opacity="0.9" />
        <stop offset="0.25" stop-color="#fff" stop-opacity="0.15" />
        <stop offset="1" stop-color="#000" stop-opacity="0.35" />
      </radialGradient>
    </defs>`;

  const shapes = [marble, die, block, star, button, ring, peg];
  for (let i = 0; i < count; i++) {
    const x = rand() * (SIZE + 60) - 30;
    const y = rand() * (SIZE + 60) - 30;
    const s = 26 + rand() * 38;
    const g = el('g', {
      transform: `translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${Math.round(rand() * 360)})`,
      filter: `url(#${id}-shadow)`,
    });
    pick(shapes)(g, s, pick, id);
    svg.appendChild(g);
  }
}

function marble(g, s, pick, id) {
  const r = s * 0.42;
  g.append(el('circle', { r, fill: pick(COLORS) }), el('circle', { r, fill: `url(#${id}-shine)` }));
}

function die(g, s) {
  const h = s / 2;
  g.append(el('rect', { x: -h, y: -h, width: s, height: s, rx: s * 0.18, fill: '#fffdf6', stroke: '#d8cdb5', 'stroke-width': 1 }));
  const p = s * 0.27;
  for (const [dx, dy] of [[-p, -p], [p, p], [0, 0], [p, -p], [-p, p]]) {
    g.append(el('circle', { cx: dx, cy: dy, r: s * 0.08, fill: '#1d1a17' }));
  }
}

function block(g, s, pick) {
  const h = s / 2;
  const fill = pick(COLORS.slice(0, 7));
  g.append(el('rect', { x: -h, y: -h, width: s, height: s, rx: 3, fill }));
  g.append(el('rect', { x: -h + 4, y: -h + 4, width: s - 8, height: s - 8, rx: 2, fill: 'none', stroke: '#fff8e7', 'stroke-opacity': 0.6, 'stroke-width': 2 }));
  const letter = el('text', {
    'text-anchor': 'middle', 'dominant-baseline': 'central',
    'font-family': 'Libre Baskerville, Georgia, serif', 'font-weight': 700, 'font-size': s * 0.62, fill: '#fff8e7',
  });
  letter.textContent = pick(LETTERS);
  g.append(letter);
}

function star(g, s, pick) {
  const pts = [];
  for (let i = 0; i < 10; i++) {
    const r = i % 2 ? s * 0.22 : s * 0.5;
    const a = (Math.PI / 5) * i - Math.PI / 2;
    pts.push(`${(Math.cos(a) * r).toFixed(1)},${(Math.sin(a) * r).toFixed(1)}`);
  }
  g.append(el('polygon', { points: pts.join(' '), fill: pick(COLORS.slice(0, 7)), stroke: '#00000033', 'stroke-width': 1 }));
}

function button(g, s, pick) {
  const r = s * 0.4;
  g.append(el('circle', { r, fill: pick(COLORS), stroke: '#00000040', 'stroke-width': 2 }));
  g.append(el('circle', { r: r * 0.7, fill: 'none', stroke: '#00000030', 'stroke-width': 1.5 }));
  const d = r * 0.22;
  for (const [dx, dy] of [[-d, -d], [d, -d], [-d, d], [d, d]]) {
    g.append(el('circle', { cx: dx, cy: dy, r: r * 0.11, fill: '#1d1a17', 'fill-opacity': 0.7 }));
  }
}

function ring(g, s, pick) {
  g.append(el('circle', { r: s * 0.36, fill: 'none', stroke: pick(COLORS.slice(0, 7)), 'stroke-width': s * 0.16 }));
}

function peg(g, s, pick) {
  const w = s * 0.28;
  g.append(el('rect', { x: -w / 2, y: -s * 0.6, width: w, height: s * 1.2, rx: w / 2, fill: pick(COLORS.slice(0, 7)) }));
  g.append(el('rect', { x: -w / 2 + 2, y: -s * 0.55, width: w * 0.3, height: s * 1.0, rx: 2, fill: '#fff', 'fill-opacity': 0.35 }));
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
