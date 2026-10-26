// The 3D rendering that pops out of the wall when an object is found, spinning like a turntable.
// Shared by the game (js/app.js) and the model preview page (tools/preview-model.html).
// What models need to look like: docs/3d-models.md

const THREE = AFRAME.THREE;
export const SPIN_MS = 6000; // one full turn

// Where an object's model lives: models/<id>.glb, unless objects.json gives popout.model.
export const modelUrl = (obj, base = '') => base + (obj.popout?.model || `models/${obj.id}.glb`);

// Starts downloading a model (so it's ready by the time the object is found) and remembers whether it exists.
const available = new Map();
export function prefetchModel(url) {
  if (!available.has(url)) available.set(url, fetch(url).then((r) => r.ok).catch(() => false));
  return available.get(url);
}

// Builds: outer entity (for rise/grow animations) > spinner (turns forever) > model (auto-fitted).
// size: the model's largest side, in scene units. rotation: fixes a model exported facing the wrong way.
export function createSpinningModel(url, { size, rotation = '0 0 0', spinMs = SPIN_MS }) {
  const outer = document.createElement('a-entity');
  const spinner = document.createElement('a-entity');
  spinner.setAttribute('animation__spin', {
    property: 'rotation', from: '0 0 0', to: '0 360 0', dur: spinMs, loop: true, easing: 'linear',
  });
  const model = document.createElement('a-entity');
  model.setAttribute('gltf-model', url);
  model.setAttribute('rotation', rotation);
  model.addEventListener('model-loaded', () => fitModel(model, size));
  model.addEventListener('model-error', () => console.warn(`Could not load 3D model ${url}`));
  spinner.appendChild(model);
  outer.appendChild(spinner);
  return outer;
}

// Models can be exported at any size and position: scale this one so its largest side is `size`,
// and centre it so it spins around its own middle.
function fitModel(el, size) {
  const mesh = el.getObject3D('mesh');
  const parent = mesh.parent;
  parent.remove(mesh); // measure the model on its own, ignoring where it sits in the scene
  mesh.position.set(0, 0, 0);
  mesh.scale.set(1, 1, 1);
  mesh.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(mesh);
  parent.add(mesh);

  const dims = box.getSize(new THREE.Vector3());
  const s = size / Math.max(dims.x, dims.y, dims.z, 1e-6);
  mesh.scale.setScalar(s);
  mesh.position.copy(box.getCenter(new THREE.Vector3())).multiplyScalar(-s);
}
