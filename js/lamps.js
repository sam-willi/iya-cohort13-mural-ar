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

  fetch('images/workshop.svg?v=glint-brighter-11')
    .then((response) => {
      if (!response.ok) throw new Error('Workshop artwork could not load');
      return response.text();
    })
    .then((source) => {
      const parsed = new DOMParser().parseFromString(source, 'image/svg+xml');
      if (parsed.querySelector('parsererror')) throw new Error('Invalid workshop artwork');
      const svg = document.importNode(parsed.documentElement, true);
      svg.setAttribute('aria-hidden', 'true');
      svg.setAttribute('focusable', 'false');

      // Match the existing background's cover sizing and 50% / 40% positioning.
      const fit = () => {
        const scale = Math.max(background.clientWidth / 900, background.clientHeight / 1400);
        svg.style.width = `${900 * scale}px`;
        svg.style.height = `${1400 * scale}px`;
      };
      background.append(svg);
      fit();
      background.classList.add('is-inline');
      new ResizeObserver(fit).observe(background);

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
      reducedMotion.addEventListener('change', sync);
      sync();
    })
    .catch((error) => console.warn('Lamp animation unavailable:', error));
})();
