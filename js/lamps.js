// Each lamp gets one freshly randomized outage in every nine-second period.
// Inline artwork lets the page control the bulbs and their beams together.
(() => {
  const PERIOD_MS = 9000;
  const FLICKER_MS = 70;
  const EDGE_MS = 300;
  const MIN_SEPARATION_MS = 250;
  const screen = document.getElementById('start-screen');
  const background = screen.querySelector('.scene-bg');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let artwork;

  fetch('images/workshop.svg?v=window-silhouette-24', { cache: 'no-cache' })
    .then((response) => {
      if (!response.ok) throw new Error('Workshop artwork could not load');
      return response.text();
    })
    .then((source) => {
      const parsed = new DOMParser().parseFromString(source, 'image/svg+xml');
      if (parsed.querySelector('parsererror')) throw new Error('Invalid workshop artwork');
      const svg = document.importNode(parsed.documentElement, true);
      artwork = svg;
      svg.setAttribute('aria-hidden', 'true');
      svg.setAttribute('focusable', 'false');

      // Filtered ancestors can rasterize their animated descendants in WebKit.
      // Keep the existing texture elsewhere, and draw the moving objects as vectors.
      for (const moving of svg.querySelectorAll('.workshop-gear, .workshop-eye-open, .workshop-eye-closed, .teapot-steam, .magnifier-glint, .lamp-light')) {
        for (let parent = moving.parentElement; parent && parent !== svg; parent = parent.parentElement) {
          parent.removeAttribute('filter');
        }
      }

      // Match the existing background's cover sizing and 50% / 40% positioning.
      const fit = () => {
        const { clientWidth: width, clientHeight: height } = background;
        if (!width || !height) return;
        const scale = Math.max(width / 900, height / 1400);
        const artworkWidth = 900 * scale, artworkHeight = 1400 * scale;
        svg.setAttribute('width', artworkWidth);
        svg.setAttribute('height', artworkHeight);
        svg.style.width = `${artworkWidth}px`;
        svg.style.height = `${artworkHeight}px`;
        // Position directly instead of transforming the whole filtered SVG surface.
        svg.style.left = `${(width - artworkWidth) * 0.5}px`;
        svg.style.top = `${(height - artworkHeight) * 0.4}px`;
        // The menu badge shares the painted window's actual center at every cover size.
        screen.style.setProperty('--window-center-y', `${(height - artworkHeight) * 0.4 + 500 * scale}px`);
      };
      background.append(svg);
      fit();
      if (typeof ResizeObserver !== 'undefined') new ResizeObserver(fit).observe(background);
      window.addEventListener('resize', fit);

      const lights = [
        [...svg.querySelectorAll('.lamp-light:not(.lamp-light-right)')],
        [...svg.querySelectorAll('.lamp-light-right')],
      ];
      const timers = new Set();
      const animations = new Set();

      const later = (callback, delay) => {
        const timer = setTimeout(() => {
          timers.delete(timer);
          callback();
        }, delay);
        timers.add(timer);
      };
      const flicker = (parts) => {
        for (const part of parts) {
          const animation = part.animate([{ opacity: 0 }, { opacity: 0 }], { duration: FLICKER_MS });
          animations.add(animation);
          animation.finished.then(
            () => animations.delete(animation),
            () => animations.delete(animation),
          );
        }
      };
      const cycle = () => {
        const range = PERIOD_MS - 2 * EDGE_MS - FLICKER_MS;
        const offsets = [Math.random() * range, Math.random() * range];
        // Avoid accidentally blinking together, without a fixed order or alternating pattern.
        if (Math.abs(offsets[0] - offsets[1]) < MIN_SEPARATION_MS) {
          offsets[1] = (offsets[0] + range / 2) % range;
        }
        lights.forEach((parts, index) => later(() => flicker(parts), EDGE_MS + offsets[index]));
        later(cycle, PERIOD_MS);
      };
      const sync = () => {
        timers.forEach(clearTimeout);
        timers.clear();
        animations.forEach((animation) => animation.cancel());
        animations.clear();
        if (!screen.hidden && !document.hidden && !reducedMotion.matches) cycle();
      };

      new MutationObserver(sync).observe(screen, { attributes: true, attributeFilter: ['hidden'] });
      document.addEventListener('visibilitychange', sync);
      window.addEventListener('pageshow', () => { fit(); sync(); });
      if (reducedMotion.addEventListener) reducedMotion.addEventListener('change', sync);
      else reducedMotion.addListener(sync);
      sync();
    })
    .catch((error) => {
      artwork?.remove(); // Leave the static CSS illustration visible if enhancement fails.
      console.warn('Lamp animation unavailable:', error);
    });
})();
