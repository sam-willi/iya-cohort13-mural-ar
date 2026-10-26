// I Spy AR game for the IYA Cohort 13 mural.
//
// Flow: show a riddle -> player points the camera at the mural -> MindAR recognises which part of the
// mural they're looking at (a "target") -> if the answer is in that part, a magnifying glass lands on the
// object's exact spot, the object pops out of the wall there, and we link to the student's page.
// Every object and target has a position on the mural in inches, so we always know where things are.
// See docs/how-it-works.md.
//
// All content (student names, links, pop-out art) lives in data/objects.json, so most changes
// never need to touch this file. Riddles come live from the riddle team's Google Sheet (see loadSheetRiddles).

const OBJECTS_URL = 'data/objects.json';
const TOAST_COOLDOWN_MS = 3000;
const SHEET_TIMEOUT_MS = 5000; // give up on the riddle sheet after this and use objects.json
const WRONG_SCANS_BEFORE_ARROW = 3; // after this many wrong spots, point the player toward the answer
const MIN_OVERLAP = 0.6; // how much of an object must be inside a target for that target to "contain" it
const CARD_DELAY_MS = 1200; // let the object pop out before the "You spied it!" card covers the screen
const THREE = AFRAME.THREE;

const sceneEl = document.getElementById('ar-scene');
const ui = {
  startScreen: document.getElementById('start-screen'),
  startButton: document.getElementById('start-button'),
  riddleCard: document.getElementById('riddle-card'),
  riddleText: document.getElementById('riddle-text'),
  hintText: document.getElementById('hint-text'),
  hintButton: document.getElementById('hint-button'),
  skipButton: document.getElementById('skip-button'),
  progress: document.getElementById('progress'),
  foundCard: document.getElementById('found-card'),
  foundName: document.getElementById('found-name'),
  foundStudent: document.getElementById('found-student'),
  studentLink: document.getElementById('student-link'),
  nextButton: document.getElementById('next-button'),
  doneScreen: document.getElementById('done-screen'),
  restartButton: document.getElementById('restart-button'),
  toast: document.getElementById('toast'),
  magnifier: document.getElementById('magnifier'),
  direction: document.getElementById('direction'),
  directionArrow: document.getElementById('direction-arrow'),
  directionText: document.getElementById('direction-text'),
  foundWhere: document.getElementById('found-where'),
  miniMap: document.getElementById('mini-map'),
};

let mural;             // size of the painted wall, in inches
let targets = [];      // parts of the mural MindAR can recognise, each with its position on the mural
let objects = [];      // objects that have a riddle
let queue = [];        // riddles still to play, in order
let current = null;    // the object the current riddle is about
let foundCount = 0;
let reveal = null;     // { group, target }: the magnifier ring + pop-out currently on the wall
let visibleTarget = null;
let wrongScans = 0;    // wrong parts of the mural scanned for the current riddle
let hintUsed = false;
let cardTimer;

init().catch((err) => {
  console.error(err);
  ui.startButton.textContent = 'Something went wrong';
  showToast('Could not load the game. Please refresh the page.');
});

async function init() {
  ({ mural, targets, objects } = await loadData());
  if (objects.length === 0) {
    ui.startButton.textContent = 'No riddles yet';
    return;
  }
  await sceneLoaded();
  targets.forEach(addAnchor);

  sceneEl.addEventListener('arError', () => showToast('Camera could not start. Check camera permissions and try again.'));

  ui.startButton.addEventListener('click', startGame);
  ui.hintButton.addEventListener('click', showHint);
  ui.skipButton.addEventListener('click', skipRiddle);
  ui.nextButton.addEventListener('click', nextRiddle);
  ui.restartButton.addEventListener('click', () => {
    ui.doneScreen.hidden = true;
    resetQueue();
    nextRiddle();
  });

  ui.startButton.textContent = 'Start';
  ui.startButton.disabled = false;
}

async function loadData() {
  const res = await fetch(OBJECTS_URL);
  if (!res.ok) throw new Error(`Failed to load ${OBJECTS_URL}: ${res.status}`);
  const data = await res.json();
  const sheet = await loadSheetRiddles(data.riddleSheet);

  const objects = data.objects
    .map((obj) => {
      const row = sheet?.get(normalize(obj.product ?? obj.name));
      return row ? { ...obj, riddle: row.riddle, hint: row.hint || obj.hint } : obj;
    })
    // objects with no riddle or no position yet are left out of the game
    .filter((obj) => obj.riddle && obj.location);
  return { mural: data.mural, targets: data.targets, objects };
}

// ---------- Riddles from the Google Sheet ----------

// The riddle team writes riddles in a Google Sheet that's published to the web as CSV.
// Each row's "Products" cell is matched to an object's `product` in objects.json.
// If the sheet isn't set up, can't be reached, or is missing a riddle, objects.json's own riddle is used.
async function loadSheetRiddles(sheet) {
  if (!sheet?.csvUrl) return null;
  try {
    const res = await fetch(sheet.csvUrl, { signal: AbortSignal.timeout(SHEET_TIMEOUT_MS) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const [header = [], ...rows] = parseCsv(await res.text());

    const column = (name) => header.findIndex((h) => normalize(h) === normalize(name));
    const productCol = column(sheet.productColumn ?? 'Products');
    const riddleCol = column(sheet.riddleColumn ?? 'Riddle');
    const hintCol = column(sheet.hintColumn ?? 'Hint'); // optional
    if (productCol < 0 || riddleCol < 0) throw new Error(`Sheet is missing a "${sheet.productColumn ?? 'Products'}" or "${sheet.riddleColumn ?? 'Riddle'}" column`);

    const riddles = new Map();
    for (const row of rows) {
      const product = normalize(row[productCol]);
      const riddle = cleanText(row[riddleCol]);
      // If a product is listed twice, the first row that has a riddle wins.
      if (product && riddle && !riddles.has(product)) {
        riddles.set(product, { riddle, hint: hintCol >= 0 ? cleanText(row[hintCol]) : '' });
      }
    }
    return riddles;
  } catch (err) {
    console.warn('Could not load riddles from the sheet, using objects.json instead.', err);
    return null;
  }
}

// Parses CSV text into rows of cells. Handles quoted cells containing commas, quotes and line breaks.
function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') quoted = false;
      else cell += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

const normalize = (s = '') => s.trim().toLowerCase().replace(/\s+/g, ' ');
const cleanText = (s = '') => s.trim().replace(/^["“”]+|["“”]+$/g, '').trim(); // some cells wrap the riddle in quotes

function sceneLoaded() {
  return new Promise((resolve) => {
    if (sceneEl.hasLoaded) resolve();
    else sceneEl.addEventListener('loaded', resolve, { once: true });
  });
}

// ---------- AR: where things are on the mural ----------
//
// Positions are in inches from the top-left corner of the painted area (x right, y down).
// MindAR places each target 1 unit wide, centred on its anchor, with y pointing up,
// so a mural position converts to anchor coordinates like this:
function toAnchor(target, x, y) {
  return {
    x: (x - (target.x + target.w / 2)) / target.w,
    y: -(y - (target.y + target.h / 2)) / target.w,
  };
}

const centre = (r) => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 });

// True when most of the object is inside the part of the mural this target covers.
function contains(target, loc) {
  const w = Math.min(target.x + target.w, loc.x + loc.w) - Math.max(target.x, loc.x);
  const h = Math.min(target.y + target.h, loc.y + loc.h) - Math.max(target.y, loc.y);
  return w > 0 && h > 0 && (w * h) / (loc.w * loc.h) >= MIN_OVERLAP;
}

// One anchor per target. MindAR moves it to wherever it sees that part of the mural.
// Anchors must be added before arSystem.start() is called.
function addAnchor(target) {
  const anchor = document.createElement('a-entity');
  anchor.setAttribute('mindar-image-target', `targetIndex: ${target.index}`);
  anchor.addEventListener('targetFound', () => onTargetFound(target, anchor));
  anchor.addEventListener('targetLost', () => onTargetLost(target));
  sceneEl.appendChild(anchor);
}

function onTargetFound(target, anchor) {
  visibleTarget = target;
  if (!current) return;

  if (contains(target, current.location)) {
    hideDirection();
    revealAt(current, target, anchor);
    if (ui.foundCard.hidden && !cardTimer) {
      const found = current;
      cardTimer = setTimeout(() => showFound(found), CARD_DELAY_MS);
    }
  } else if (ui.foundCard.hidden) {
    wrongScans++;
    showDirection(target);
  }
}

function onTargetLost(target) {
  if (visibleTarget === target) visibleTarget = null;
  if (reveal?.target === target) removeReveal();
  hideDirection();
}

// The magnifying glass lands on the object's exact spot, then the object pops out of the wall there.
async function revealAt(obj, target, anchor) {
  removeReveal();
  const loc = obj.location;
  const c = centre(loc);
  const p = toAnchor(target, c.x, c.y);
  const w = loc.w / target.w;
  const h = loc.h / target.w;
  const r = Math.max(w, h) * 0.62; // lens radius, just big enough to frame the object

  const group = document.createElement('a-entity');
  group.setAttribute('position', `${p.x} ${p.y} 0`);
  reveal = { group, target };

  // the lens: faint blue glass, ink edge, red-brown rim (like the mural's magnifier)
  const lens = document.createElement('a-entity');
  lens.innerHTML = `
    <a-circle radius="${r}" material="shader: flat; color: #a9d6ee; opacity: 0.22; transparent: true"
      animation="property: components.material.material.opacity; from: 0.22; to: 0.4; dur: 900; dir: alternate; loop: true; delay: 600"></a-circle>
    <a-ring radius-inner="${r}" radius-outer="${r * 1.16}" material="shader: flat; color: #8a2a1e"></a-ring>
    <a-ring radius-inner="${r * 1.16}" radius-outer="${r * 1.2}" material="shader: flat; color: #1b120b"></a-ring>
    <a-ring radius-inner="${r * 0.97}" radius-outer="${r}" material="shader: flat; color: #1b120b"></a-ring>`;
  lens.setAttribute('animation__land', {
    property: 'scale', from: '2.4 2.4 2.4', to: '1 1 1', dur: 550, easing: 'easeOutBack',
  });
  group.appendChild(lens);
  anchor.appendChild(group);
  landMagnifier(anchor, p, r);

  // the object, rising out of the wall once the lens has landed
  // (until its pop-out art exists, the lens alone marks the spot)
  let popout = null;
  try {
    if (obj.popout?.model) popout = createModelPopout(obj, w);
    else if (obj.popout?.image) popout = await createImagePopout(obj, w);
  } catch (err) {
    console.warn(`No pop-out for ${obj.id}:`, err);
  }
  if (!popout || reveal?.group !== group) return; // nothing to show, or a newer reveal started while loading
  const lift = Math.max(w, h) * 0.9;
  popout.setAttribute('position', '0 0 0.002');
  popout.setAttribute('animation__rise', {
    property: 'position', from: '0 0 0.002', to: `0 0 ${lift}`, dur: 900, delay: 450, easing: 'easeOutElastic',
  });
  popout.setAttribute('animation__grow', {
    property: 'scale', from: '0.8 0.8 0.8', to: '1.35 1.35 1.35', dur: 900, delay: 450, easing: 'easeOutElastic',
  });
  popout.setAttribute('animation__sway', {
    property: 'rotation', from: '0 -12 0', to: '0 12 0', dur: 1600, delay: 1350, dir: 'alternate', loop: true, easing: 'easeInOutSine',
  });
  group.appendChild(popout);
}

function removeReveal() {
  reveal?.group.remove();
  reveal = null;
}

// A flat cut-out of the object, as wide as the object is on the mural.
async function createImagePopout(obj, width) {
  const img = await loadImage(obj.popout.image);
  const plane = document.createElement('a-plane');
  plane.setAttribute('width', width);
  plane.setAttribute('height', width * (img.naturalHeight / img.naturalWidth));
  plane.setAttribute('material', { src: obj.popout.image, transparent: true, alphaTest: 0.01, side: 'double', shader: 'flat' });
  return plane;
}

// A 3D model (.glb). Its "up" should match the mural's up; z points out of the wall.
// modelScale 1 = as wide as the object on the mural.
function createModelPopout(obj, width) {
  const model = document.createElement('a-gltf-model');
  const s = width * (obj.popout.modelScale ?? 1);
  model.setAttribute('src', obj.popout.model);
  model.setAttribute('scale', `${s} ${s} ${s}`);
  return model;
}

// The on-screen magnifying glass flies to the object's spot and hands over to the lens in AR.
function landMagnifier(anchor, p, r) {
  const centrePx = toScreen(anchor, p.x, p.y);
  const edgePx = toScreen(anchor, p.x + r, p.y);
  if (!centrePx || !edgePx || ui.magnifier.hidden) {
    ui.magnifier.hidden = true;
    return;
  }
  const box = ui.magnifier.getBoundingClientRect();
  const size = 2 * Math.hypot(edgePx.x - centrePx.x, edgePx.y - centrePx.y);
  ui.magnifier.style.setProperty('--fly-x', `${centrePx.x - (box.left + box.width / 2)}px`);
  ui.magnifier.style.setProperty('--fly-y', `${centrePx.y - (box.top + box.height / 2)}px`);
  ui.magnifier.style.setProperty('--fly-scale', Math.max(0.2, size / box.width).toFixed(3));
  ui.magnifier.classList.add('landing');
  setTimeout(() => (ui.magnifier.hidden = true), 550);
}

// Where a point on an anchor appears on the phone screen, in CSS pixels.
function toScreen(anchor, x, y) {
  anchor.object3D.updateMatrixWorld(true);
  const v = new THREE.Vector3(x, y, 0).applyMatrix4(anchor.object3D.matrixWorld).project(sceneEl.camera);
  if (![v.x, v.y, v.z].every(Number.isFinite) || v.z > 1) return null;
  const rect = sceneEl.canvas.getBoundingClientRect();
  return { x: rect.left + ((v.x + 1) / 2) * rect.width, y: rect.top + ((1 - v.y) / 2) * rect.height };
}

// Looking at the wrong part of the mural: say so, and after a few tries (or after a hint) point the way.
function showDirection(target) {
  const pointTheWay = hintUsed || wrongScans >= WRONG_SCANS_BEFORE_ARROW;
  ui.directionArrow.hidden = !pointTheWay;
  if (pointTheWay) {
    const from = centre(target);
    const to = centre(current.location);
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    ui.directionArrow.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
    ui.directionText.textContent = `Not here. Try ${describeOffset(dx, dy)}.`;
  } else {
    ui.directionText.textContent = "Good eye, but it's not here. Keep looking!";
  }
  ui.direction.hidden = false;
}

function hideDirection() {
  ui.direction.hidden = true;
}

// e.g. "about 9 ft to the right and higher up"
function describeOffset(dx, dy) {
  const parts = [];
  if (Math.abs(dx) > 12) parts.push(dx > 0 ? 'to the right' : 'to the left');
  if (Math.abs(dy) > 12) parts.push(dy > 0 ? 'lower down' : 'higher up');
  if (parts.length === 0) return 'looking a little closer around here';
  const feet = Math.max(1, Math.round(Math.hypot(dx, dy) / 12));
  return `about ${feet} ft ${parts.join(' and ')}`;
}

// e.g. "Right side of the mural: 9th panel from the left, top row"
// The panel seams are visible on the wall, so players can count along to it.
function describeLocation(loc) {
  if (loc.label) return loc.label;
  const c = centre(loc);
  const side = ['Left side', 'Middle', 'Right side'][Math.min(2, Math.floor((c.x / mural.width) * 3))];
  const rows = Math.round(mural.height / mural.panelSize);
  const rowIndex = Math.min(rows - 1, Math.floor(c.y / mural.panelSize));
  const row = rows === 3 ? ['top', 'middle', 'bottom'][rowIndex] : ordinal(rowIndex + 1);
  return `${side} of the mural: ${ordinal(Math.floor(c.x / mural.panelSize) + 1)} panel from the left, ${row} row`;
}

function ordinal(n) {
  const suffix = n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] ?? 'th');
  return `${n}${suffix}`;
}

// A little map of the whole wall, panel by panel, with the object's spot marked.
function drawMiniMap(loc) {
  const { width, height, panelSize } = mural;
  const lines = [];
  for (let x = panelSize; x < width; x += panelSize) lines.push(`M${x} 0V${height}`);
  for (let y = panelSize; y < height; y += panelSize) lines.push(`M0 ${y}H${width}`);
  const c = centre(loc);
  const ring = Math.max(loc.w, loc.h, panelSize * 0.35);
  ui.miniMap.setAttribute('viewBox', `-4 -4 ${width + 8} ${height + 8}`);
  ui.miniMap.innerHTML = `
    <rect width="${width}" height="${height}" rx="4" class="map-wall"/>
    <path d="${lines.join(' ')}" class="map-panels"/>
    <rect x="${loc.x}" y="${loc.y}" width="${loc.w}" height="${loc.h}" class="map-object"/>
    <circle cx="${c.x}" cy="${c.y}" r="${ring}" class="map-ring"/>`;
}

// ---------- Game flow ----------

function startGame() {
  ui.startButton.disabled = true;
  ui.startScreen.hidden = true;
  resetQueue();
  nextRiddle();
  sceneEl.systems['mindar-image-system'].start(); // asks for camera permission
}

function resetQueue() {
  foundCount = 0;
  queue = shuffle([...objects]);

  // A QR code can link straight to one riddle, e.g. index.html?object=demo-card
  const startId = new URLSearchParams(location.search).get('object');
  const i = queue.findIndex((o) => o.id === startId);
  if (i > 0) queue.unshift(...queue.splice(i, 1));
}

function nextRiddle() {
  if (current && (!ui.foundCard.hidden || cardTimer)) foundCount++;
  clearTimeout(cardTimer);
  cardTimer = null;
  removeReveal();
  hideDirection();
  wrongScans = 0;
  hintUsed = false;
  ui.foundCard.hidden = true;
  ui.magnifier.classList.remove('landing');

  current = queue.shift() ?? null;
  if (!current) {
    ui.riddleCard.hidden = true;
    ui.magnifier.hidden = true;
    ui.doneScreen.hidden = false;
    return;
  }

  ui.riddleText.textContent = current.riddle;
  ui.hintText.textContent = current.hint ?? '';
  ui.hintText.hidden = true;
  ui.hintButton.hidden = false; // even without a written hint, the hint turns on the "which way" arrow
  ui.progress.textContent = `(${foundCount + 1} of ${objects.length})`;
  ui.riddleCard.hidden = false;
  ui.magnifier.hidden = false; // "search here" cue while the riddle is open
}

function showHint() {
  hintUsed = true;
  ui.hintText.textContent = current.hint || "Point your camera at the mural and we'll show you which way to look.";
  ui.hintText.hidden = false;
  ui.hintButton.hidden = true;
  if (visibleTarget && !contains(visibleTarget, current.location)) showDirection(visibleTarget);
}

function skipRiddle() {
  queue.push(current); // try it again at the end
  current = null;
  nextRiddle();
}

function showFound(obj) {
  cardTimer = null;
  ui.riddleCard.hidden = true;
  if (!ui.magnifier.classList.contains('landing')) ui.magnifier.hidden = true;
  ui.foundName.textContent = obj.name;
  ui.foundStudent.replaceChildren();
  if (obj.student?.name) {
    const name = document.createElement('b');
    name.textContent = obj.student.name;
    ui.foundStudent.append('Art by ', name);
  }
  const url = obj.student?.pageUrl;
  ui.studentLink.hidden = !url;
  if (url) ui.studentLink.href = url;
  ui.foundWhere.textContent = describeLocation(obj.location);
  drawMiniMap(obj.location);
  ui.foundCard.hidden = false;
}

// ---------- Helpers ----------

let lastToastAt = 0;
let toastTimer;
function showToast(message) {
  const now = Date.now();
  if (now - lastToastAt < TOAST_COOLDOWN_MS) return;
  lastToastAt = now;
  ui.toast.textContent = message;
  ui.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (ui.toast.hidden = true), TOAST_COOLDOWN_MS);
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Could not load image ${src}`));
    img.src = src;
  });
}

function shuffle(list) {
  for (let i = list.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}
