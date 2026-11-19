(() => {
  document.addEventListener('DOMContentLoaded', () => {
    if (!document.body.classList.contains('sr-private')) return;
    const root = document.documentElement;
    const menu = document.getElementById('sr-navigation');
    const trigger = document.querySelector('.sr-menu-button');
    if (!menu || !trigger) return;
    const close = menu.querySelector('.sr-collapse');
    const backdrop = document.querySelector('.sr-backdrop');
    const wide = matchMedia('(min-width:1100px)');
    const account = document.querySelector('[data-account-toggle]');
    const options = document.getElementById('private-account-menu');
    let open = false;
    const areas = [...document.querySelectorAll('#main-content,.sr-header,.sr-footer,.sr-mobile-nav')];
    const previous = new Map();
    function accountOpen(value, restore = false) {
      if (!options || !account) return;
      options.hidden = !value;
      account.setAttribute('aria-expanded', String(value));
      if (value) options.querySelector('a').focus();
      else if (restore) account.focus();
    }
    function drawer(value, restore = true) {
      open = value && !wide.matches;
      root.classList.toggle('sr-drawer-open', open);
      root.classList.remove('sr-nav-preview');
      backdrop.hidden = !open;
      menu.inert = !wide.matches && !open;
      trigger.setAttribute('aria-expanded', String(wide.matches ? !root.classList.contains('sr-compact') : open));
      const expanded = wide.matches && !root.classList.contains('sr-compact');
      const label = wide.matches ? (expanded ? 'Contraer menu' : 'Expandir menu') : 'Cerrar navegacion';
      close.setAttribute('aria-label', label);
      close.setAttribute('aria-expanded', String(wide.matches ? expanded : open));
      close.title = label;
      trigger.setAttribute('aria-label', open ? 'Cerrar navegacion' : 'Abrir navegacion');
      if (open) {
        accountOpen(false);
        menu.setAttribute('role', 'dialog');
        menu.setAttribute('aria-modal', 'true');
        areas.forEach(area => { if (!previous.has(area)) previous.set(area, area.inert); area.inert = true; });
        close.focus();
      } else {
        menu.removeAttribute('role');
        menu.removeAttribute('aria-modal');
        previous.forEach((value, area) => { area.inert = value; });
        previous.clear();
        if (restore) trigger.focus();
      }
    }
    function toggle() {
      if (!wide.matches) return drawer(!open);
      root.classList.toggle('sr-compact');
      try { localStorage.setItem('sr-sidebar-state', root.classList.contains('sr-compact') ? 'collapsed' : 'expanded'); } catch (_) {}
      drawer(false, false);
    }
    [trigger, close, backdrop].forEach(button => button.addEventListener('click', event => {
      event.preventDefault(); event.stopImmediatePropagation();
      if (button === backdrop || (button === close && !wide.matches)) drawer(false);
      else toggle();
    }, true));
    menu.addEventListener('click', event => { if (open && event.target.closest('a')) drawer(false, false); });
    document.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'b') { event.preventDefault(); event.stopImmediatePropagation(); toggle(); }
      if (!open) return;
      if (event.key === 'Escape') { event.stopImmediatePropagation(); drawer(false); }
      if (event.key !== 'Tab') return;
      const items = [...menu.querySelectorAll('a,button,summary')].filter(node => node.getClientRects().length);
      const first = items[0], last = items.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }, true);
    wide.addEventListener('change', () => drawer(false, false));
    window.addEventListener('pagehide', () => { drawer(false, false); accountOpen(false); });
    window.addEventListener('pageshow', () => drawer(false, false));
    drawer(false, false);
  });
})();
