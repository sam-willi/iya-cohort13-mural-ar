// I Spy AR game for the IYA Cohort 13 mural.
//
// Flow: show a riddle -> player looks at the mural through the camera -> MindAR watches for the part of the mural
// around the answer (the riddle's "targets") -> the player taps the screen when they spy the answer -> if it's in frame,
// a magnifying glass lands on the object's exact spot, a 3D rendering of the object rises out of the wall there
// and spins, and we link to the student's page; if not, we say so and point the way.
// Every object and target has a position on the mural in inches, so we always know where things are.
// See docs/how-it-works.md.
//
// All content (student names, links, pop-out art) lives in data/objects.json, so most changes
// never need to touch this file. Riddles come live from the riddle team's Google Sheet (see loadSheetRiddles),
// and student names and page links come live from the profiles website (see loadProfiles).

import { createSpinningModel, modelUrl, prefetchModel } from './popout.js';
import { addRoomEnvironment } from './environment.js';
import { setupMuralZoom } from './mural-zoom.js?v=pan-fix-14';
import { positionHint, landmarkClue, visibleMuralRegion } from './position-hints.js?v=position-hints-15';

const OBJECTS_URL = 'data/objects.json?v=wall-scan-18';
const TOAST_COOLDOWN_MS = 3000;
const SHEET_TIMEOUT_MS = 5000; // give up on the riddle sheet after this and use objects.json
const PROFILES_TIMEOUT_MS = 5000; // give up on the profiles website after this and use objects.json
const WRONG_SCANS_BEFORE_ARROW = 3; // after this many wrong spots, point the player toward the answer
const MIN_OVERLAP = 0.6; // how much of an object must be inside a target for that target to "contain" it
const MAX_TARGETS = 3;   // per object: a straight-on target, plus two pre-tilted ones for objects high on the wall
const CARD_DELAY_MS = 2600; // let the object pop out of the wall before the "You spied it!" card covers the screen
const FOUND_KEY = 'ispy-found'; // remembers what this phone has found, so the collection survives a refresh
const TAP_SLACK_IN = 3; // in no-camera mode, a tap this close (in inches) to the object still counts
const MODEL_VIEWER_SRC = 'https://unpkg.com/@google/model-viewer@3.5.0/dist/model-viewer.min.js'; // shows the 3D rendering in no-camera mode
const THREE = AFRAME.THREE;

// A-Frame and MindAR load with `defer` so the start screen shows straight away; now that they've loaded,
// add the AR scene to the page (see the <template> in index.html).
document.body.append(document.getElementById('ar-scene-template').content.cloneNode(true));
const sceneEl = document.getElementById('ar-scene');
addRoomEnvironment(sceneEl);
const ui = {
  startScreen: document.getElementById('start-screen'),
  startButton: document.getElementById('start-button'),
  menuDescription: document.getElementById('menu-description'),
  menuSecondary: document.getElementById('menu-secondary'),
  menuBack: document.getElementById('menu-back'),
  riddleCard: document.getElementById('riddle-card'),
  riddleText: document.getElementById('riddle-text'),
  hintText: document.getElementById('hint-text'),
  hintButton: document.getElementById('hint-button'),
  hintMapButton: document.getElementById('hint-map-button'),
  hintMap: document.getElementById('hint-map'),
  hintMapImage: document.getElementById('hint-map-image'),
  hintMapRegion: document.getElementById('hint-map-region'),
  hintMapViewport: document.getElementById('hint-map-viewport'),
  hintMapCaption: document.getElementById('hint-map-caption'),
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
  pictureButton: document.getElementById('picture-button'),
  pictureView: document.getElementById('picture-view'),
  pictureScroll: document.getElementById('picture-scroll'),
  pictureWall: document.getElementById('picture-wall'),
  pictureImg: document.getElementById('picture-img'),
  pictureLens: document.getElementById('picture-lens'),
  pictureMiss: document.getElementById('picture-miss'),
  zoomIn: document.getElementById('zoom-in'),
  zoomOut: document.getElementById('zoom-out'),
  foundModel: document.getElementById('found-model'),
  tapTip: document.getElementById('tap-tip'),
  foundModelTip: document.getElementById('found-model-tip'),
  foundButton: document.getElementById('found-button'),
  foundCount: document.getElementById('found-count'),
  collection: document.getElementById('collection'),
  collectionClose: document.getElementById('collection-close'),
  collectionEmpty: document.getElementById('collection-empty'),
  collectionList: document.getElementById('collection-list'),
  detail: document.getElementById('collection-detail'),
  detailBack: document.getElementById('detail-back'),
  detailName: document.getElementById('detail-name'),
  detailStudent: document.getElementById('detail-student'),
  detailModel: document.getElementById('detail-model'),
  detailRiddle: document.getElementById('detail-riddle'),
  detailMap: document.getElementById('detail-map'),
  detailWhere: document.getElementById('detail-where'),
  detailLink: document.getElementById('detail-link'),
};

let mural;             // size of the painted wall, in inches
let targets = [];      // the current riddle's AR targets (parts of the mural around the answer), with their positions
let landmarks = [];    // fixed things on the wall players can see, like the windows, used in directions
let objects = [];      // objects that have a riddle
let queue = [];        // riddles still to play, in order
let current = null;    // the object the current riddle is about
let foundCount = 0;
let reveal = null;     // { group, target }: the magnifier ring + pop-out currently on the wall
let visibleTarget = null;
let wrongScans = 0;    // wrong parts of the mural scanned for the current riddle
let hintUsed = false;
let cardTimer;
const anchors = new Map(); // target index -> its MindAR anchor
let arReady = false;   // MindAR has loaded its first targets and is watching the camera
let startedSrc = null; // the recognition file MindAR was started with
let swapping = Promise.resolve();
const found = loadFound(); // ids of the objects this player has spied
let mode = 'camera';   // 'camera' (AR at the wall) or 'picture' (tap the object on a picture of the mural)
let zoom = 1;
let pictureTapBlockedUntil = 0;
let directionTimer;

init().catch((err) => {
  console.error(err);
  ui.startButton.textContent = 'Something went wrong';
  showToast('Could not load the game. Please refresh the page.');
});

async function init() {
  ({ mural, landmarks, objects } = await loadData());
  if (objects.length === 0) {
    ui.startButton.textContent = 'No riddles yet';
    return;
  }
  await sceneLoaded();
  for (let i = 0; i < MAX_TARGETS; i++) addAnchor(i);
  sceneEl.addEventListener('arReady', () => {
    arReady = true;
    if (current?.ar && current.ar.mind !== startedSrc) useTargets(current); // the riddle changed while the camera was starting
  });

  document.addEventListener('click', onSpyTap);
  ui.foundButton.addEventListener('click', openCollection);
  // In camera mode the riddle can shrink to a small tab so the whole screen is camera
  document.getElementById('riddle-toggle').addEventListener('click', () => setRiddleCollapsed(!ui.riddleCard.classList.contains('collapsed')));
  ui.collectionClose.addEventListener('click', () => (ui.collection.hidden = true));
  ui.detailBack.addEventListener('click', showCollectionList);
  sceneEl.addEventListener('arError', () => showToast('Camera could not start. Check camera permissions and try again.'));

  ui.startButton.addEventListener('click', startGame);
  ui.hintButton.addEventListener('click', showHint);
  ui.hintMapButton.addEventListener('click', focusHintArea);
  ui.skipButton.addEventListener('click', skipRiddle);
  ui.nextButton.addEventListener('click', nextRiddle);
  ui.restartButton.addEventListener('click', () => {
    ui.doneScreen.hidden = true;
    found.clear(); // playing again starts a fresh collection
    saveFound();
    updateFoundButton();
    resetQueue();
    nextRiddle();
  });

  if (mural.picture) {
    ui.pictureButton.hidden = false;
    ui.pictureButton.addEventListener('click', startPictureGame);
    ui.pictureWall.addEventListener('click', onPictureTap);
    ui.zoomIn.addEventListener('click', () => setZoom(zoom * 1.6));
    ui.zoomOut.addEventListener('click', () => setZoom(zoom / 1.6));
    ui.pictureScroll.addEventListener('scroll', updateHintViewport, { passive: true });
    new ResizeObserver(updateHintViewport).observe(ui.pictureScroll);
    setupMuralZoom({
      viewport: ui.pictureScroll,
      getZoom: () => zoom,
      setZoom,
      onGesture: () => { pictureTapBlockedUntil = performance.now() + 400; },
    });
  }

  ui.startButton.textContent = 'Start';
  ui.startButton.disabled = false;
  ui.menuDescription.hidden = false;
  ui.menuSecondary.hidden = false;
}

async function loadData() {
  const res = await fetch(OBJECTS_URL, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`Failed to load ${OBJECTS_URL}: ${res.status}`);
  const data = await res.json();
  const [sheet, profiles] = await Promise.all([loadSheetRiddles(data.riddleSheet), loadProfiles(data.profiles)]);

  const objects = data.objects
    .map((obj) => {
      const row = obj.riddleSource === 'local' ? null : sheet?.get(normalize(obj.product ?? obj.name));
      return row ? { ...obj, riddle: row.riddle, hint: row.hint || obj.hint } : obj;
    })
    .map((obj) => {
      const profile = profiles?.get(obj.id);
      return profile ? { ...obj, student: { name: profile.studentName, pageUrl: profile.pageUrl } } : obj;
    })
    // objects with no riddle or no position yet are left out of the game
    .filter((obj) => obj.riddle && obj.location);
  return { mural: data.mural, landmarks: data.landmarks ?? [], objects };
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

// ---------- Student pages from the profiles website ----------

// Each student marks which product they drew when they edit their page on the profiles website, which publishes
// the list as JSON: { objects: [{ objectId, studentName, pageUrl }] }. objectId matches an object's `id` here.
// If the site isn't set up or can't be reached, the `student` written in objects.json is used.
async function loadProfiles(profiles) {
  if (!profiles?.url) return null;
  try {
    const res = await fetch(profiles.url, { signal: AbortSignal.timeout(PROFILES_TIMEOUT_MS) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const { objects } = await res.json();
    return new Map(objects.map((profile) => [profile.objectId, profile]));
  } catch (err) {
    console.warn('Could not load student pages from the profiles website, using objects.json instead.', err);
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
// MindAR places each target image 1 unit wide, centred on its anchor, with y pointing up.
// A straight-on target is a rectangle of the mural, so a mural position converts directly. A pre-tilted target
// (for objects high on the wall) carries H, which maps mural inches to its image pixels.
function toAnchor(target, x, y) {
  if (target.H) {
    const [[a, b, c], [d, e, f], [g, h, i]] = target.H;
    const z = g * x + h * y + i;
    const u = (a * x + b * y + c) / z, v = (d * x + e * y + f) / z;
    const [pw, ph] = target.px;
    return { x: (u - pw / 2) / pw, y: -(v - ph / 2) / pw };
  }
  return {
    x: (x - (target.x + target.w / 2)) / target.w,
    y: -(y - (target.y + target.h / 2)) / target.w,
  };
}

// How big a stretch of the mural is in anchor units, measured across a point (works for tilted targets too).
function anchorSpan(target, c, dx, dy) {
  const a = toAnchor(target, c.x - dx / 2, c.y - dy / 2), b = toAnchor(target, c.x + dx / 2, c.y + dy / 2);
  return Math.hypot(b.x - a.x, b.y - a.y);
}

const centre = (r) => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 });

// True when most of the object is inside the part of the mural this target covers.
function contains(target, loc) {
  const w = Math.min(target.x + target.w, loc.x + loc.w) - Math.max(target.x, loc.x);
  const h = Math.min(target.y + target.h, loc.y + loc.h) - Math.max(target.y, loc.y);
  return w > 0 && h > 0 && (w * h) / (loc.w * loc.h) >= MIN_OVERLAP;
}

// One anchor per target slot; each riddle's targets fill slots 0, 1, 2. MindAR moves an anchor to wherever it
// sees that part of the mural. Anchors must be added before arSystem.start() is called.
function addAnchor(index) {
  const anchor = document.createElement('a-entity');
  anchor.setAttribute('mindar-image-target', `targetIndex: ${index}`);
  anchors.set(index, anchor);
  anchor.addEventListener('targetFound', () => targets[index] && onTargetFound(targets[index]));
  anchor.addEventListener('targetLost', () => targets[index] && onTargetLost(targets[index]));
  sceneEl.appendChild(anchor);
}

// Each object has its own small recognition file (tools/wall/build.py): its targets only. Loading just the current
// riddle's keeps the download small, lets MindAR lock on quickly, and means the wrong object can never match.
function useTargets(obj) {
  const sys = sceneEl.systems['mindar-image-system'];
  if (arReady) for (const { el } of sys.anchorEntities) el.updateWorldMatrix(null); // let go of the last riddle's
  visibleTarget = null;
  ui.magnifier.classList.remove('ready');
  targets = (obj?.ar?.targets ?? []).slice(0, MAX_TARGETS).map((t, index) => ({ ...t, index }));
  const src = obj?.ar?.mind;
  if (!src) return;
  if (!arReady) { sys.imageTargetSrc = src; return; } // start() loads it
  swapping = swapping.then(() => swapTargets(sys, src)).catch((err) => console.error('Could not load targets', src, err));
}

// Replaces what MindAR looks for without restarting the camera.
async function swapTargets(sys, src) {
  const ctrl = sys.controller;
  if (ctrl.processingVideo) {
    // let MindAR's video loop finish the frame it's on before its targets change underneath it
    await new Promise((resolve) => {
      const before = ctrl.onUpdate;
      const finish = () => { ctrl.onUpdate = before; resolve(); };
      ctrl.onUpdate = (e) => { before?.(e); if (e.type === 'processDone') finish(); };
      setTimeout(finish, 1000);
      sys.pause(true);
    });
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  }
  const { dimensions } = await ctrl.addImageTargets(src);
  for (const { el, targetIndex } of sys.anchorEntities) {
    if (targetIndex < dimensions.length) el.setupMarker(dimensions[targetIndex]);
  }
  if (mode === 'camera') sys.unpause();
}

// The camera can see part of the mural. Nothing happens until the player taps (see onSpyTap);
// the magnifier just glows to show the mural is in view.
function onTargetFound(target) {
  visibleTarget = target;
  ui.magnifier.classList.add('ready');
}

// The player tapped the screen to say "I spy it!": check whether the answer is in frame right now.
function onSpyTap(event) {
  if (mode !== 'camera' || !current || !ui.foundCard.hidden || cardTimer) return;
  if (event.target.closest('.card, .direction, .screen, .collection, button, a')) return;

  if (!visibleTarget) {
    showMessage("We can't see the mural yet. Point your camera at it and hold steady.");
    return;
  }
  const anchor = anchors.get(visibleTarget.index);
  if (contains(visibleTarget, current.location) && inFrame(anchor, visibleTarget, current.location)) {
    hideDirection();
    revealAt(current, visibleTarget, anchor);
    const found = current;
    cardTimer = setTimeout(() => showFound(found), CARD_DELAY_MS);
  } else {
    wrongScans++;
    showDirection(visibleTarget, 'Nope, not in view.');
  }
}

// True when the middle of the object is on screen.
function inFrame(anchor, target, loc) {
  const c = centre(loc);
  const p = toAnchor(target, c.x, c.y);
  const px = toScreen(anchor, p.x, p.y);
  return Boolean(px) && px.x >= 0 && px.y >= 0 && px.x <= window.innerWidth && px.y <= window.innerHeight;
}

function showMessage(text) {
  ui.directionArrow.hidden = true;
  ui.directionText.textContent = text;
  ui.direction.hidden = false;
  clearTimeout(directionTimer);
  directionTimer = setTimeout(hideDirection, 3500);
}

function onTargetLost(target) {
  if (visibleTarget === target) {
    visibleTarget = null;
    ui.magnifier.classList.remove('ready');
  }
  if (reveal?.target === target) removeReveal();
  hideDirection();
}

// The magnifying glass lands on the object's exact spot, then the object pops out of the wall there.
async function revealAt(obj, target, anchor) {
  removeReveal();
  const loc = obj.location;
  const c = centre(loc);
  const p = toAnchor(target, c.x, c.y);
  const w = anchorSpan(target, c, loc.w, 0);
  const h = anchorSpan(target, c, 0, loc.h);
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

  // the object's 3D rendering rises out of the lens once it has landed, then spins
  // (until the object's model exists, the lens alone marks the spot)
  const url = modelUrl(obj);
  if (!(await prefetchModel(url)) || reveal?.group !== group) return;
  const size = Math.max(w, h) * (obj.popout?.scale ?? 1.3);
  const popout = createSpinningModel(url, { size, rotation: obj.popout?.rotation });
  popout.setAttribute('scale', '0.01 0.01 0.01');
  popout.setAttribute('animation__rise', {
    property: 'position', from: '0 0 0', to: `0 0 ${size * 0.8}`, dur: 900, delay: 450, easing: 'easeOutElastic',
  });
  popout.setAttribute('animation__grow', {
    property: 'scale', from: '0.01 0.01 0.01', to: '1 1 1', dur: 900, delay: 450, easing: 'easeOutElastic',
  });
  group.appendChild(popout);
}

function removeReveal() {
  reveal?.group.remove();
  reveal = null;
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
function showDirection(target, prefix = '') {
  const pointTheWay = hintUsed || wrongScans >= WRONG_SCANS_BEFORE_ARROW;
  ui.directionArrow.hidden = !pointTheWay;
  if (pointTheWay) {
    const from = centre(target);
    const to = centre(current.location);
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    ui.directionArrow.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
    const near = nearLandmark(current.location);
    ui.directionText.textContent = `${prefix || 'Not here.'} Try ${describeOffset(dx, dy)}${near ? `, ${near}` : ''}.`;
  } else {
    ui.directionText.textContent = `${prefix || "Good eye, but it's not here."} Keep looking!`;
  }
  ui.direction.hidden = false;
  clearTimeout(directionTimer);
  directionTimer = setTimeout(hideDirection, 5500);
}

function hideDirection() {
  ui.direction.hidden = true;
}

// Direction in the mural, without physical distances players cannot judge on a phone.
function describeOffset(dx, dy) {
  const parts = [];
  if (Math.abs(dx) > 12) parts.push(dx > 0 ? 'to the right' : 'to the left');
  if (Math.abs(dy) > 12) parts.push(dy > 0 ? 'lower down' : 'higher up');
  if (parts.length === 0) return 'looking a little closer around here';
  return `looking ${parts.join(' and ')}`;
}

// e.g. "Just left of the middle window: 9th panel from the left, top row"
// The panel seams and windows are real things on the wall, so players can find their way by them.
function describeLocation(loc) {
  if (loc.label) return loc.label;
  const c = centre(loc);
  const rows = Math.round(mural.height / mural.panelSize);
  const rowIndex = Math.min(rows - 1, Math.floor(c.y / mural.panelSize));
  const row = rows === 3 ? ['top', 'middle', 'bottom'][rowIndex] : ordinal(rowIndex + 1);
  const panel = `${ordinal(Math.floor(c.x / mural.panelSize) + 1)} panel from the left, ${row} row`;
  const near = nearLandmark(loc);
  if (near) return `${near[0].toUpperCase()}${near.slice(1)}: ${panel}`;
  const side = ['Left side', 'Middle', 'Right side'][Math.min(2, Math.floor((c.x / mural.width) * 3))];
  return `${side} of the mural: ${panel}`;
}

// Where a spot is relative to the nearest landmark, e.g. "just left of the middle window".
// Returns null when no landmark is close enough to be a useful reference.
function nearLandmark(loc) {
  return landmarkClue(loc, landmarks, mural.panelSize);
}

function ordinal(n) {
  const suffix = n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] ?? 'th');
  return `${n}${suffix}`;
}

// A little map of the whole wall: panels, windows, and the object's spot circled.
function drawMiniMap(loc, svg = ui.miniMap) {
  const { width, height, panelSize } = mural;
  const lines = [];
  for (let x = panelSize; x < width; x += panelSize) lines.push(`M${x} 0V${height}`);
  for (let y = panelSize; y < height; y += panelSize) lines.push(`M0 ${y}H${width}`);
  const c = centre(loc);
  const ring = Math.max(loc.w, loc.h, panelSize * 0.35);
  svg.setAttribute('viewBox', `-4 -4 ${width + 8} ${height + 8}`);
  svg.innerHTML = `
    <rect width="${width}" height="${height}" rx="4" class="map-wall"/>
    <path d="${lines.join(' ')}" class="map-panels"/>
    ${landmarks.map((lm) => `<rect x="${lm.x}" y="${lm.y}" width="${lm.w}" height="${lm.h}" class="map-window"/>`).join('')}
    <rect x="${loc.x}" y="${loc.y}" width="${loc.w}" height="${loc.h}" class="map-object"/>
    <circle cx="${c.x}" cy="${c.y}" r="${ring}" class="map-ring"/>`;
}

// ---------- Game flow ----------

function startGame() {
  mode = 'camera';
  document.body.dataset.mode = mode;
  ui.startButton.disabled = true;
  ui.startScreen.hidden = true;
  resetQueue();
  nextRiddle();
  showFoundButton();
  loadModelViewer();
  startedSrc = current?.ar?.mind ?? null;
  sceneEl.systems['mindar-image-system'].start(); // asks for camera permission
}

function resetQueue() {
  foundCount = 0;
  // riddles already solved on this phone wait until the rest are done
  const unsolved = objects.filter((o) => !found.has(o.id));
  queue = shuffle(unsolved.length ? unsolved : [...objects]);

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
  ui.foundModel.replaceChildren();
  ui.foundModel.hidden = true;
  ui.foundModelTip.hidden = true;
  ui.pictureLens.hidden = true;
  ui.magnifier.classList.remove('landing');
  ui.magnifier.classList.toggle('ready', Boolean(visibleTarget));

  current = queue.shift() ?? null;
  if (mode === 'camera') useTargets(current);
  if (!current) {
    ui.riddleCard.hidden = true;
    ui.magnifier.hidden = true;
    ui.doneScreen.hidden = false;
    return;
  }

  prefetchModel(modelUrl(current)); // download the 3D model while the player reads the riddle
  ui.riddleText.textContent = current.riddle;
  setRiddleCollapsed(false); // every new riddle starts open
  ui.tapTip.textContent = mode === 'picture' ? 'Pinch to zoom. Scroll or drag to move. Tap to answer.' : 'Find it on the mural, then tap.';
  ui.hintText.textContent = current.hint ?? '';
  ui.hintText.hidden = true;
  ui.hintMapButton.hidden = true;
  ui.riddleCard.classList.remove('has-position-hint');
  ui.hintButton.textContent = 'Hint';
  ui.hintButton.hidden = false; // even without a written hint, the hint turns on the "which way" arrow
  ui.progress.textContent = `(${Math.min(objects.length, found.size + 1)} of ${objects.length})`;
  ui.riddleCard.hidden = false;
  ui.magnifier.hidden = mode !== 'camera'; // "search here" cue while the riddle is open
}

function showHint() {
  if (!current) return;
  if (!ui.hintMapButton.hidden) {
    ui.hintText.hidden = true;
    ui.hintMapButton.hidden = true;
    ui.riddleCard.classList.remove('has-position-hint');
    ui.hintButton.textContent = 'Hint';
    return;
  }
  hintUsed = true;
  const hint = positionHint(mural, current.location, landmarks);
  if (!hint) return;
  ui.hintText.textContent = `${current.hint ? `${current.hint} ` : ''}${hint.text}`;
  ui.hintText.hidden = false;
  ui.hintMap.setAttribute('viewBox', `0 0 ${mural.width} ${mural.height}`);
  ui.hintMap.setAttribute('aria-label', `Mural overview. ${hint.text} Gold shows the search area.${mode === 'picture' ? ' Blue shows your current view.' : ''}`);
  ui.hintMapImage.setAttribute('href', mural.picture);
  ui.hintMapImage.setAttribute('width', mural.width);
  ui.hintMapImage.setAttribute('height', mural.height);
  setMapRect(ui.hintMapRegion, hint.region);
  ui.hintMapButton.disabled = mode !== 'picture';
  ui.hintMapButton.setAttribute('aria-label', mode === 'picture' ? 'Move the mural to the suggested search area' : 'Suggested search area on the mural');
  ui.hintMapCaption.textContent = mode === 'picture' ? 'Gold: search · Blue: view · Tap to move' : 'Gold: suggested search area';
  ui.hintMapButton.hidden = false;
  ui.hintButton.textContent = 'Hide hint';
  ui.riddleCard.classList.add('has-position-hint');
  updateHintViewport();
  if (visibleTarget && !contains(visibleTarget, current.location)) showDirection(visibleTarget);
}

function setMapRect(element, rect) {
  for (const key of ['x', 'y']) element.setAttribute(key, rect[key]);
  element.setAttribute('width', rect.w);
  element.setAttribute('height', rect.h);
}

function updateHintViewport() {
  if (ui.hintMapButton.hidden) return;
  ui.hintMapViewport.toggleAttribute('hidden', mode !== 'picture');
  if (mode !== 'picture') return;
  const viewport = ui.pictureScroll.getBoundingClientRect();
  const region = visibleMuralRegion(mural, ui.pictureWall.getBoundingClientRect(), {
    left: viewport.left, top: viewport.top, width: ui.pictureScroll.clientWidth, height: ui.pictureScroll.clientHeight,
  });
  ui.hintMapViewport.toggleAttribute('hidden', !region);
  if (region) setMapRect(ui.hintMapViewport, region);
}

function focusHintArea() {
  if (mode !== 'picture' || !current) return;
  const hint = positionHint(mural, current.location, landmarks);
  if (!hint) return;
  const scroll = ui.pictureScroll;
  let wall = ui.pictureWall.getBoundingClientRect();
  const fit = Math.min(scroll.clientWidth / (hint.region.w / mural.width * wall.width / zoom),
    scroll.clientHeight / (hint.region.h / mural.height * wall.height / zoom)) * 0.9;
  setZoom(Math.min(zoom, fit));
  wall = ui.pictureWall.getBoundingClientRect();
  const viewport = scroll.getBoundingClientRect();
  const c = centre(hint.region);
  scroll.scrollTo({
    left: scroll.scrollLeft + wall.left + c.x / mural.width * wall.width - viewport.left - scroll.clientWidth / 2,
    top: scroll.scrollTop + wall.top + c.y / mural.height * wall.height - viewport.top - scroll.clientHeight / 2,
    behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
  });
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
  showCardModel(obj);
  ui.foundCard.hidden = false;
  markFound(obj);
}

// ---------- No-camera mode: tap the object on a picture of the mural ----------
//
// For anyone who can't or won't use the camera, and for testing away from the wall. The picture is
// mural.picture in objects.json, cropped to exactly the painted area, so a tap converts straight to inches.

function startPictureGame() {
  mode = 'picture';
  document.body.dataset.mode = mode;
  ui.startScreen.hidden = true;
  ui.pictureView.hidden = false;
  if (!ui.pictureImg.src) ui.pictureImg.src = mural.picture;
  loadModelViewer();
  resetQueue();
  nextRiddle();
  showFoundButton();
  setZoom(1);
}

function setZoom(z, anchor, previousAnchor = anchor) {
  const scroll = ui.pictureScroll;
  const viewport = scroll.getBoundingClientRect();
  const before = ui.pictureWall.getBoundingClientRect();
  if (!before.width || !before.height) return;
  anchor ??= { x: viewport.left + scroll.clientWidth / 2, y: viewport.top + scroll.clientHeight / 2 };
  previousAnchor ??= anchor;
  const keepX = (previousAnchor.x - before.left) / before.width;
  const keepY = (previousAnchor.y - before.top) / before.height;
  zoom = Math.min(4, Math.max(1, z));
  ui.pictureView.style.setProperty('--zoom', zoom);
  const after = ui.pictureWall.getBoundingClientRect();
  scroll.scrollLeft += after.left + keepX * after.width - anchor.x;
  scroll.scrollTop += after.top + keepY * after.height - anchor.y;
  updateHintViewport();
}

// Where a tap lands on the wall, in inches.
function tapToWall(event) {
  const rect = ui.pictureWall.getBoundingClientRect();
  return {
    x: ((event.clientX - rect.left) / rect.width) * mural.width,
    y: ((event.clientY - rect.top) / rect.height) * mural.height,
  };
}

function onPictureTap(event) {
  if (!current || !ui.foundCard.hidden || cardTimer || performance.now() < pictureTapBlockedUntil) return;
  const p = tapToWall(event);
  const loc = current.location;
  const hit = p.x >= loc.x - TAP_SLACK_IN && p.x <= loc.x + loc.w + TAP_SLACK_IN
    && p.y >= loc.y - TAP_SLACK_IN && p.y <= loc.y + loc.h + TAP_SLACK_IN;
  if (hit) {
    hideDirection();
    showPictureLens(loc);
    const found = current;
    cardTimer = setTimeout(() => showFound(found), 700);
    return;
  }
  wrongScans++;
  placeOnPicture(ui.pictureMiss, { x: p.x, y: p.y, w: 0, h: 0 }, 34 / ui.pictureWall.clientWidth * mural.width);
  ui.pictureMiss.hidden = false;
  ui.pictureMiss.style.animation = 'none';
  void ui.pictureMiss.offsetWidth; // restart the fade
  ui.pictureMiss.style.animation = '';
  showDirection({ x: p.x - 1, y: p.y - 1, w: 2, h: 2 }, 'Nope, not there.');
}

function showPictureLens(loc) {
  const d = Math.max(loc.w, loc.h) * 1.3;
  placeOnPicture(ui.pictureLens, loc, d);
  ui.pictureLens.hidden = false;
  // bring the spot into view if it's off screen
  const c = centre(loc);
  const scroll = ui.pictureScroll;
  const px = (c.x / mural.width) * scroll.scrollWidth;
  if (px < scroll.scrollLeft || px > scroll.scrollLeft + scroll.clientWidth) {
    scroll.scrollTo({ left: px - scroll.clientWidth / 2, behavior: 'smooth' });
  }
}

// Positions a circle marker (diameter d, in inches) on the centre of a box on the wall.
function placeOnPicture(el, loc, d) {
  const c = centre(loc);
  el.style.left = `${(c.x / mural.width) * 100}%`;
  el.style.top = `${(c.y / mural.height) * 100}%`;
  el.style.width = `${(d / mural.width) * 100}%`;
  el.style.height = 'auto';
  el.style.aspectRatio = '1';
}

let modelViewerLoading;
function loadModelViewer() {
  if (!modelViewerLoading) {
    modelViewerLoading = true;
    const script = document.createElement('script');
    script.type = 'module';
    script.src = MODEL_VIEWER_SRC;
    document.head.append(script);
  }
}

// The found card keeps the 3D rendering up for as long as the player wants, and they can spin it with a finger.
async function showCardModel(obj) {
  ui.foundModel.replaceChildren();
  ui.foundModel.hidden = true;
  ui.foundModelTip.hidden = true;
  const viewer = await createViewer(obj, { zoom: false });
  if (!viewer || ui.foundName.textContent !== obj.name) return;
  ui.foundModel.append(viewer);
  ui.foundModel.hidden = false;
  ui.foundModelTip.hidden = false;
}

// An interactive 3D viewer for an object's rendering: drag to spin (and optionally pinch to zoom).
async function createViewer(obj, { zoom }) {
  loadModelViewer();
  const url = modelUrl(obj);
  if (!(await prefetchModel(url))) return null;
  const viewer = document.createElement('model-viewer');
  for (const [k, v] of Object.entries({
    src: url, alt: `3D rendering of the ${obj.name}`, 'auto-rotate': '', 'auto-rotate-delay': '1500',
    'rotation-per-second': '40deg', 'camera-controls': '', 'touch-action': 'pan-y', 'interaction-prompt': 'none',
    'shadow-intensity': '0.7', 'camera-orbit': '20deg 72deg auto', exposure: '1.1',
  })) viewer.setAttribute(k, v);
  if (!zoom) viewer.setAttribute('disable-zoom', '');
  return viewer;
}

function setRiddleCollapsed(collapsed) {
  ui.riddleCard.classList.toggle('collapsed', collapsed);
  const toggle = document.getElementById('riddle-toggle');
  toggle.textContent = collapsed ? 'Show riddle' : 'Hide';
  toggle.setAttribute('aria-expanded', String(!collapsed));
}

// ---------- Found so far ----------

function loadFound() {
  try { return new Set(JSON.parse(localStorage.getItem(FOUND_KEY) || '[]')); } catch { return new Set(); }
}

function saveFound() {
  try { localStorage.setItem(FOUND_KEY, JSON.stringify([...found])); } catch { /* private browsing: keep it for this visit only */ }
}

function markFound(obj) {
  if (found.has(obj.id)) return;
  found.add(obj.id);
  saveFound();
  updateFoundButton();
  ui.foundButton.classList.remove('bump');
  void ui.foundButton.offsetWidth;
  ui.foundButton.classList.add('bump');
}

function showFoundButton() {
  updateFoundButton();
  ui.menuBack.hidden = false;
  ui.foundButton.hidden = false;
}

function updateFoundButton() {
  ui.foundCount.textContent = found.size;
}

function openCollection() {
  showCollectionList();
  ui.collection.hidden = false;
  ui.collection.scrollTop = 0;
}

function showCollectionList() {
  ui.detail.hidden = true;
  ui.detailModel.replaceChildren();
  const list = objects.filter((o) => found.has(o.id));
  ui.collectionEmpty.hidden = list.length > 0;
  ui.collectionList.hidden = false;
  ui.collectionList.replaceChildren(...list.map((obj) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.type = 'button';
    const where = document.createElement('small');
    where.textContent = describeLocation(obj.location).split(':').pop().trim();
    btn.append(obj.name, where);
    btn.addEventListener('click', () => showDetail(obj));
    li.append(btn);
    return li;
  }));
}

async function showDetail(obj) {
  ui.collectionList.hidden = true;
  ui.collectionEmpty.hidden = true;
  ui.detail.hidden = false;
  ui.collection.scrollTop = 0;
  ui.detailName.textContent = obj.name;
  ui.detailStudent.replaceChildren();
  if (obj.student?.name) {
    const name = document.createElement('b');
    name.textContent = obj.student.name;
    ui.detailStudent.append('Art by ', name);
  }
  ui.detailRiddle.textContent = obj.riddle;
  ui.detailWhere.textContent = describeLocation(obj.location);
  drawMiniMap(obj.location, ui.detailMap);
  const url = obj.student?.pageUrl;
  ui.detailLink.hidden = !url;
  if (url) ui.detailLink.href = url;
  ui.detailModel.replaceChildren();
  const viewer = await createViewer(obj, { zoom: true });
  if (viewer && ui.detailName.textContent === obj.name) ui.detailModel.append(viewer);
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

function shuffle(list) {
  for (let i = list.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}
