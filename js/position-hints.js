const center = (r) => ({ x: r.x + r.w / 2, y: r.y + r.h / 2 });
const valid = (r) => r && ['x', 'y', 'w', 'h'].every((k) => Number.isFinite(r[k])) && r.w > 0 && r.h > 0;

// Use the same full-wall coordinates as answer detection. No screen coordinates or guessed landmarks.
export function landmarkClue(location, landmarks, panelSize) {
  const c = center(location);
  const candidates = landmarks.filter(valid).map((landmark) => ({
    landmark,
    dx: c.x < landmark.x ? c.x - landmark.x : Math.max(0, c.x - landmark.x - landmark.w),
    dy: c.y < landmark.y ? c.y - landmark.y : Math.max(0, c.y - landmark.y - landmark.h),
  }));
  candidates.sort((a, b) => Math.hypot(a.dx, a.dy) - Math.hypot(b.dx, b.dy));
  const nearest = candidates[0];
  if (!nearest || Math.hypot(nearest.dx, nearest.dy) > panelSize * 1.5) return null;
  const { landmark: lm, dx, dy } = nearest;
  const inside = location.x >= lm.x && location.y >= lm.y
    && location.x + location.w <= lm.x + lm.w && location.y + location.h <= lm.y + lm.h;
  if (inside) return `inside ${lm.name}`;
  const overlaps = location.x < lm.x + lm.w && location.x + location.w > lm.x
    && location.y < lm.y + lm.h && location.y + location.h > lm.y;
  if (overlaps) {
    const lc = center(lm);
    const rx = (c.x - lc.x) / lm.w;
    const ry = (c.y - lc.y) / lm.h;
    if (Math.max(Math.abs(rx), Math.abs(ry)) < 0.1) return `near ${lm.name}`;
    const edge = Math.abs(rx) > Math.abs(ry) ? (rx < 0 ? 'left' : 'right') : (ry < 0 ? 'top' : 'bottom');
    return `near the ${edge} edge of ${lm.name}`;
  }
  const directions = [];
  if (dy) directions.push(dy < 0 ? 'above' : 'below');
  if (dx) directions.push(dx < 0 ? 'to the left of' : 'to the right of');
  if (!directions.length) return `near ${lm.name}`;
  return `${Math.hypot(dx, dy) < panelSize / 2 ? 'just ' : ''}${directions.join(' and ')} ${lm.name}`;
}

export function positionHint(mural, location, landmarks = []) {
  if (!valid(location) || !(mural.width > 0 && mural.height > 0 && mural.panelSize > 0)
    || location.x < 0 || location.y < 0 || location.x + location.w > mural.width || location.y + location.h > mural.height) return null;
  const c = center(location);
  const p = mural.panelSize;
  // Highlight a broad panel-aligned area containing the entire object, never an exact answer pin.
  let x0 = Math.max(0, Math.min(Math.floor(location.x / p) * p, Math.round((c.x - p) / p) * p));
  const x1 = Math.min(mural.width, Math.max(x0 + 2 * p, Math.ceil((location.x + location.w) / p) * p));
  x0 = Math.min(x0, Math.max(0, x1 - 2 * p));
  const y0 = Math.floor(location.y / p) * p;
  const y1 = Math.min(mural.height, Math.ceil((location.y + location.h) / p) * p);
  const col = Math.min(2, Math.floor(c.x / mural.width * 3));
  const row = Math.min(2, Math.floor(c.y / mural.height * 3));
  const label = [
    ['Upper-left area', 'Upper-middle area', 'Upper-right area'],
    ['Middle-left area', 'Middle area', 'Middle-right area'],
    ['Lower-left area', 'Lower-middle area', 'Lower-right area'],
  ][row][col];
  const landmark = landmarkClue(location, landmarks, p);
  return { region: { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }, label, landmark,
    text: `${label}.${landmark ? ` Look ${landmark}.` : ' Search the highlighted area.'}` };
}

// Convert the actual visible image crop back to full-wall coordinates at any zoom/pan.
export function visibleMuralRegion(mural, wall, viewport) {
  if (!(wall.width > 0 && wall.height > 0)) return null;
  const left = Math.max(wall.left, viewport.left);
  const top = Math.max(wall.top, viewport.top);
  const right = Math.min(wall.left + wall.width, viewport.left + viewport.width);
  const bottom = Math.min(wall.top + wall.height, viewport.top + viewport.height);
  if (right <= left || bottom <= top) return null;
  return {
    x: (left - wall.left) / wall.width * mural.width,
    y: (top - wall.top) / wall.height * mural.height,
    w: (right - left) / wall.width * mural.width,
    h: (bottom - top) / wall.height * mural.height,
  };
}
