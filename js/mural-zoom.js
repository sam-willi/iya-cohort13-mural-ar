// Handle zoom only inside the mural viewport. The page keeps normal browser zoom elsewhere.
export function setupMuralZoom({ viewport, getZoom, setZoom, onGesture }) {
  let pinch = null;
  let gesture = null;
  const listeners = [];
  const listen = (type, handler) => {
    viewport.addEventListener(type, handler, { passive: false });
    listeners.push([type, handler]);
  };
  const anchorFor = (event) => {
    const rect = viewport.getBoundingClientRect();
    return Number.isFinite(event.clientX) && Number.isFinite(event.clientY)
      && event.clientX >= rect.left && event.clientX <= rect.right
      && event.clientY >= rect.top && event.clientY <= rect.bottom
      ? { x: event.clientX, y: event.clientY }
      : { x: rect.left + viewport.clientWidth / 2, y: rect.top + viewport.clientHeight / 2 };
  };
  const touchPosition = (touches) => ({
    distance: Math.max(1, Math.hypot(touches[0].clientX - touches[1].clientX, touches[0].clientY - touches[1].clientY)),
    center: { x: (touches[0].clientX + touches[1].clientX) / 2, y: (touches[0].clientY + touches[1].clientY) / 2 },
  });

  listen('wheel', (event) => {
    // Ordinary scrolling pans in both directions. Trackpad pinch arrives as Ctrl+wheel.
    if (!event.ctrlKey && !event.metaKey) return;
    if (!event.deltaY) return;
    event.preventDefault();
    if (gesture || pinch) return;
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? viewport.clientHeight : 1;
    const delta = Math.max(-160, Math.min(160, event.deltaY * unit));
    const sensitivity = event.ctrlKey ? 0.008 : 0.002;
    setZoom(getZoom() * Math.exp(-delta * sensitivity), anchorFor(event));
  });

  const startPinch = (event) => {
    if (event.touches.length < 2) return;
    event.preventDefault();
    const { distance, center } = touchPosition(event.touches);
    pinch = { distance, zoom: getZoom(), center };
    onGesture();
  };
  listen('touchstart', startPinch);
  listen('touchmove', (event) => {
    if (event.touches.length < 2) return; // Keep native one-finger panning and momentum.
    if (!pinch) { startPinch(event); return; }
    event.preventDefault();
    const { distance, center } = touchPosition(event.touches);
    setZoom(pinch.zoom * distance / pinch.distance, center, pinch.center);
    pinch.center = center;
    onGesture();
  });
  listen('touchend', (event) => {
    if (!pinch) return;
    onGesture(); // Ignore the synthetic tap browsers can send after a pinch.
    pinch = null;
    if (event.touches.length >= 2) startPinch(event);
  });
  listen('touchcancel', () => {
    if (pinch) onGesture();
    pinch = null;
    gesture = null;
  });

  // Safari exposes trackpad pinch as gesture events instead of Ctrl+wheel.
  listen('gesturestart', (event) => {
    event.preventDefault();
    gesture = { zoom: getZoom(), center: anchorFor(event) };
    onGesture();
  });
  listen('gesturechange', (event) => {
    if (!gesture) return;
    event.preventDefault();
    if (pinch) return; // Touch events already handle a phone pinch.
    const center = anchorFor(event);
    setZoom(gesture.zoom * event.scale, center, gesture.center);
    gesture.center = center;
    onGesture();
  });
  listen('gestureend', (event) => {
    if (!gesture) return;
    event.preventDefault();
    gesture = null;
    onGesture();
  });

  return () => {
    listeners.forEach(([type, handler]) => viewport.removeEventListener(type, handler));
    pinch = null;
    gesture = null;
  };
}
