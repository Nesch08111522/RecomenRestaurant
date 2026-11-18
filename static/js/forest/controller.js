/* Imperative coordination/events; all presentation and rules live in siblings. */
(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    if (!document.body.classList.contains('sr-discover')) return;
    const byId = id => document.getElementById(id);
    const themeButton = byId('themeToggle');
    const themeParent = themeButton.parentElement, themeNext = themeButton.nextSibling;
    const narrowHeader = matchMedia('(max-width: 380px)');
    const placeTheme = () => {
      themeButton.classList.toggle('forest-drawer-theme', narrowHeader.matches);
      if (narrowHeader.matches) byId('sr-navigation').appendChild(themeButton);
      else themeParent.insertBefore(themeButton, themeNext?.parentNode === themeParent ? themeNext : null);
    };
    narrowHeader.addEventListener('change', placeTheme);
    placeTheme();
    const panel = byId('forest-map-panel'), list = byId('forest-list'), map = byId('forest-map');
    const filters = byId('forest-filters'), toggle = document.querySelector('.forest-filter-toggle');
    const form = byId('search-form');
    const setMap = visible => {
      panel.hidden = !visible;
      document.querySelector('.forest-results-layout').classList.toggle('forest-with-map', visible);
      for (const [button, active] of [[list, !visible], [map, visible]]) {
        button.setAttribute('aria-pressed', String(active));
        button.classList.toggle('active', active);
      }
      if (visible) {
        window.dispatchEvent(new Event('forest:map-open'));
        if (typeof maplibregl === 'undefined' && typeof initMap === 'function' && typeof L !== 'undefined' && !window.mapGL) {
          if (!panel.querySelector('.leaflet-pane')) initMap();
        }
        requestAnimationFrame(() => { window.mapGL?.map.resize(); if (typeof window.map !== 'undefined') window.map?.invalidateSize?.(); window.dispatchEvent(new Event('resize')); });
      }
    };
    map.addEventListener('click', () => setMap(true));
    list.addEventListener('click', () => setMap(false));
    byId('forest-nearby-map').addEventListener('click', () => { setMap(true); panel.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block:'center'}); });
    toggle.addEventListener('click', () => { filters.open = !filters.open; if (filters.open) filters.scrollIntoView({block:'center'}); });
    filters.addEventListener('toggle', () => toggle.setAttribute('aria-expanded', String(filters.open)));
    const reset = () => {
      form.reset();
      document.querySelectorAll('.filter-chip').forEach(chip => { const active = chip.dataset.filter === 'all'; chip.classList.toggle('active', active); chip.setAttribute('aria-pressed', String(active)); });
      if (window.app) { window.app.state.filteredRestaurants = [...window.app.state.restaurants]; window.app.renderRestaurants(); window.app.updateMapMarkers(window.app.state.filteredRestaurants); }
    };
    byId('forest-all').addEventListener('click', reset);
    form.addEventListener('reset', () => {
      window.search?.controller?.abort();
      setTimeout(() => {
        document.querySelectorAll('.filter-chip').forEach(chip => { const active = chip.dataset.filter === 'all'; chip.classList.toggle('active', active); chip.setAttribute('aria-pressed', String(active)); });
        if(window.app) { window.app.state.filteredRestaurants = [...window.app.state.restaurants]; window.app.renderRestaurants(); }
      }, 0);
    });
    const modal = byId('recommendationModal');
    let returnFocus = null;
    const rememberFocus = button => { returnFocus = button; setTimeout(() => byId('aiRecText').focus(), 0); };
    byId('recommendationBtn').addEventListener('click', () => { const text = byId('forest-query').value.trim(); if(text) byId('aiRecText').value = text; rememberFocus(byId('recommendationBtn')); });
    byId('forest-craving-form').addEventListener('submit', event => {
      event.preventDefault();
      byId('aiRecText').value = byId('forest-craving').value.trim();
      window.app?.openRecommendationModal();
      rememberFocus(byId('forest-recommend'));
    });
    const close = () => { window.app?.closeRecommendationModal(); returnFocus?.focus(); };
    modal.querySelector('.close-modal').addEventListener('click', close);
    modal.addEventListener('click', event => { if(event.target === modal) close(); });
    document.addEventListener('keydown', event => {
      if (!modal.classList.contains('show')) return;
      if(event.key === 'Escape') { event.preventDefault(); close(); }
      if(event.key === 'Tab') {
        const controls = Array.from(modal.querySelectorAll('button, textarea, a[href], input')).filter(el => el.offsetParent !== null && !el.disabled);
        const first = controls[0], last = controls[controls.length-1];
        if(event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if(!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    document.querySelector('#resultsGrid')?.addEventListener('error', event => {
      if(event.target.matches('img')) { event.target.hidden = true; event.target.parentElement.classList.add('forest-image-unavailable'); }
    }, true);
  });
})();
