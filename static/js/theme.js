/* One preference for the platform, editor and public business sites. */
(() => {
  'use strict';
  const root = document.documentElement;
  const color = name => getComputedStyle(root).getPropertyValue('--theme-' + name).trim();
  function sync() {
    const dark = root.dataset.theme !== 'light';
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.setAttribute('aria-label', 'Tema oscuro');
      button.setAttribute('aria-pressed', String(dark));
      button.title = dark ? 'Usar tema claro' : 'Usar tema oscuro';
      const label = button.querySelector('[data-theme-label]');
      const icon = button.querySelector('[data-theme-icon], .material-icons');
      if (label) label.textContent = button.title;
      if (icon) {
        if (icon.classList.contains('material-icons')) icon.textContent = dark ? 'light_mode' : 'dark_mode';
        else {
          const ns = 'http://www.w3.org/2000/svg';
          const glyph = document.createElementNS(ns, 'svg');
          glyph.setAttribute('viewBox', '0 0 24 24');
          glyph.setAttribute('width', '1em');
          glyph.setAttribute('height', '1em');
          glyph.setAttribute('fill', 'none');
          glyph.setAttribute('stroke', 'currentColor');
          glyph.setAttribute('stroke-width', '1.8');
          glyph.setAttribute('aria-hidden', 'true');
          const path = document.createElementNS(ns, 'path');
          path.setAttribute('d', dark
            ? 'M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0'
            : 'M20 15.5A9 9 0 0 1 8.5 4 9 9 0 1 0 20 15.5Z');
          glyph.appendChild(path);
          icon.replaceChildren(glyph);
        }
      }
    });
  }
  function set(value, persist = true) {
    const theme = value === 'light' ? 'light' : 'dark';
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    if (persist) { try { localStorage.setItem('theme', theme); } catch (_) {} }
    sync();
    document.dispatchEvent(new CustomEvent('themechange', {detail: {theme}}));
  }
  window.SRTheme = {color, set, toggle: () => set(root.dataset.theme === 'light' ? 'dark' : 'light')};
  document.addEventListener('click', event => {
    if (event.target.closest('[data-theme-toggle]')) window.SRTheme.toggle();
  });
  document.addEventListener('DOMContentLoaded', sync);
  window.addEventListener('storage', event => { if (event.key === 'theme' || event.key === null) set(event.newValue, false); });
})();
