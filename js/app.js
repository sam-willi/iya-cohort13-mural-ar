// I Spy AR game for the IYA Cohort 13 mural.
//
// Flow: show a riddle -> player points the camera at the mural -> when MindAR recognises
// the object that answers the riddle, it pops out in AR and we link to the student's page.
//
// All content (riddles, student names, links, pop-out art) lives in data/objects.json,
// so most changes never need to touch this file.

const OBJECTS_URL = 'data/objects.json';
const TOAST_COOLDOWN_MS = 3000;

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
};

let objects = [];      // everything in objects.json
let queue = [];        // riddles still to play, in order
let current = null;    // the object the current riddle is about
let foundCount = 0;
const popouts = new Map(); // object id -> pop-out entity

init().catch((err) => {
  console.error(err);
  ui.startButton.textContent = 'Something went wrong';
  showToast('Could not load the game. Please refresh the page.');
});

async function init() {
  objects = await loadObjects();
  await sceneLoaded();
  await Promise.all(objects.map(addTarget));

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

async function loadObjects() {
  const res = await fetch(OBJECTS_URL);
  if (!res.ok) throw new Error(`Failed to load ${OBJECTS_URL}: ${res.status}`);
  const data = await res.json();
  return data.objects;
}

function sceneLoaded() {
  return new Promise((resolve) => {
    if (sceneEl.hasLoaded) resolve();
    else sceneEl.addEventListener('loaded', resolve, { once: true });
  });
}

// ---------- AR targets ----------

// Each mural object gets an anchor that MindAR moves to wherever it sees that image.
// Anchors must be added before arSystem.start() is called.
async function addTarget(obj) {
  const anchor = document.createElement('a-entity');
  anchor.setAttribute('mindar-image-target', `targetIndex: ${obj.targetIndex}`);

  const isModel = Boolean(obj.popout?.model);
  const popout = isModel ? createModelPopout(obj) : await createImagePopout(obj);
  popout.setAttribute('visible', false);
  addPopAnimation(popout, isModel ? (obj.popout.modelScale ?? 0.2) : 1);
  anchor.appendChild(popout);
  popouts.set(obj.id, popout);

  anchor.addEventListener('targetFound', () => onTargetFound(obj));
  anchor.addEventListener('targetLost', () => hidePopout(obj.id));
  sceneEl.appendChild(anchor);
}

// A flat cut-out of the artwork. MindAR treats the target as 1 unit wide,
// so a plane of width 1 lines up exactly with the object on the mural.
async function createImagePopout(obj) {
  const img = await loadImage(obj.popout.image);
  const plane = document.createElement('a-plane');
  plane.setAttribute('width', 1);
  plane.setAttribute('height', img.naturalHeight / img.naturalWidth);
  plane.setAttribute('material', {
    src: obj.popout.image,
    transparent: true,
    alphaTest: 0.01,
    side: 'double',
    shader: 'flat',
  });
  return plane;
}

// A 3D model (.glb). Its "up" should match the mural's up; z points out of the wall.
function createModelPopout(obj) {
  const model = document.createElement('a-gltf-model');
  const s = obj.popout.modelScale ?? 0.2;
  model.setAttribute('src', obj.popout.model);
  model.setAttribute('scale', `${s} ${s} ${s}`);
  return model;
}

// "Pop out" of the wall: jump forward and grow, then gently sway.
function addPopAnimation(el, s) {
  el.setAttribute('animation__rise', {
    property: 'position', from: '0 0 0', to: '0 0 0.35',
    dur: 900, easing: 'easeOutElastic', startEvents: 'pop',
  });
  el.setAttribute('animation__grow', {
    property: 'scale', from: `${s * 0.6} ${s * 0.6} ${s * 0.6}`, to: `${s * 1.15} ${s * 1.15} ${s * 1.15}`,
    dur: 900, easing: 'easeOutElastic', startEvents: 'pop',
  });
  el.setAttribute('animation__sway', {
    property: 'rotation', from: '0 -10 0', to: '0 10 0',
    dur: 1600, dir: 'alternate', loop: true, easing: 'easeInOutSine', startEvents: 'pop',
  });
}

function onTargetFound(obj) {
  if (!current) return;
  if (obj.id !== current.id) {
    showToast("Good eye, but that's not the one. Keep looking!");
    return;
  }
  const popout = popouts.get(obj.id);
  popout.setAttribute('visible', true);
  popout.emit('pop');
  if (ui.foundCard.hidden) showFound(obj);
}

function hidePopout(id) {
  popouts.get(id)?.setAttribute('visible', false);
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
  if (current && !ui.foundCard.hidden) foundCount++;
  if (current) hidePopout(current.id);
  ui.foundCard.hidden = true;

  current = queue.shift() ?? null;
  if (!current) {
    ui.riddleCard.hidden = true;
    ui.doneScreen.hidden = false;
    return;
  }

  ui.riddleText.textContent = current.riddle;
  ui.hintText.textContent = current.hint ?? '';
  ui.hintText.hidden = true;
  ui.hintButton.hidden = !current.hint;
  ui.progress.textContent = `(${foundCount + 1} of ${objects.length})`;
  ui.riddleCard.hidden = false;
}

function showHint() {
  ui.hintText.hidden = false;
  ui.hintButton.hidden = true;
}

function skipRiddle() {
  queue.push(current); // try it again at the end
  current = null;
  nextRiddle();
}

function showFound(obj) {
  ui.riddleCard.hidden = true;
  ui.foundName.textContent = obj.name;
  ui.foundStudent.textContent = obj.student?.name ? `Created by ${obj.student.name}` : '';
  const url = obj.student?.pageUrl;
  ui.studentLink.hidden = !url;
  if (url) ui.studentLink.href = url;
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
