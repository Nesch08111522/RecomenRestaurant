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
      if (icon) icon.textContent = icon.classList.contains('material-icons') ? (dark ? 'light_mode' : 'dark_mode') : (dark ? '☀' : '☾');
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
