// A soft, warm room for the 3D renderings to reflect. Without an environment map, three.js gives metal
// almost no light (metals reflect, they barely diffuse), so chrome, brass and steel came out nearly black.
// The room is built in code, so there's nothing extra to download.
const THREE = AFRAME.THREE;

export function addRoomEnvironment(sceneEl) {
  const apply = () => {
    const pmrem = new THREE.PMREMGenerator(sceneEl.renderer);
    sceneEl.object3D.environment = pmrem.fromScene(roomScene(), 0.04).texture;
    pmrem.dispose();
  };
  if (sceneEl.renderer) apply();
  else sceneEl.addEventListener('renderstart', apply, { once: true });
}

// The mural's workshop in miniature: dark wood walls, a warm lamp overhead, a sky window to one side.
function roomScene() {
  const scene = new THREE.Scene();
  const box = new THREE.BoxGeometry(1, 1, 1);
  const room = new THREE.Mesh(box, new THREE.MeshBasicMaterial({ color: 0x3a2212, side: THREE.BackSide }));
  room.scale.set(12, 8, 12);
  scene.add(room);
  const panel = (color, strength, position, scale) => {
    const m = new THREE.Mesh(box, new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(strength) }));
    m.position.set(...position);
    m.scale.set(...scale);
    scene.add(m);
  };
  panel(0xffd9a0, 5, [0, 3.9, 0], [4, 0.1, 4]); // warm lamp overhead
  panel(0xcfe6f2, 2.5, [-5.9, 1, -1], [0.1, 3, 4]); // sky window, left
  panel(0xffe7c4, 1.5, [5.9, 0.5, 2], [0.1, 2, 3]); // warm fill, right
  panel(0xfff3e0, 1.2, [0, 1, 5.9], [5, 3, 0.1]); // behind the viewer
  return scene;
}
