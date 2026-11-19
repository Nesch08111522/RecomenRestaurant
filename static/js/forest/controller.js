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
    const place = byId('forest-district'), district = byId('district-select');
    place?.addEventListener('change', () => { district.value = place.value; district.dispatchEvent(new Event('change',{bubbles:true})); });
    district?.addEventListener('change', () => { if (place) place.value = district.value; });
    form.addEventListener('reset', () => { if (place) place.value = ''; });

    const dialog = document.createElement('dialog');
    dialog.className = 'sr-map-dialog';
    dialog.setAttribute('aria-label', 'Restaurantes cercanos y ubicación');
    const closeMap = document.createElement('button');
    closeMap.type = 'button'; closeMap.textContent = 'Cerrar mapa';
    dialog.append(closeMap);
    const choose = document.createElement('button');
    choose.type = 'button'; choose.textContent = 'Elegir ubicación en el mapa';
    const help = document.createElement('p'); help.className = 'sr-map-help'; help.setAttribute('role','status');
    dialog.append(choose, help);
    choose.addEventListener('click', () => {
      help.textContent = 'Toca el mapa para guardar tu ubicación aproximada.';
      const savePoint = (lat, lng) => {
        window.dispatchEvent(new CustomEvent('smartresto:location-picked', {detail:{lat,lng}}));
        help.textContent = 'Ubicación seleccionada.';
      };
      if (window.mapGL) window.mapGL.map.once('click', event => savePoint(event.lngLat.lat,event.lngLat.lng));
      else if (typeof window.map !== 'undefined' && window.map?.once) window.map.once('click', event => savePoint(event.latlng.lat,event.latlng.lng));
      else if (window.getLeafletMap?.()) window.getLeafletMap().once('click', event => savePoint(event.latlng.lat,event.latlng.lng));
      else help.textContent = 'Espera a que termine de cargar el mapa y vuelve a pulsar.';
    });
    panel.before(dialog); dialog.append(panel);
    const fallbackToLeaflet = () => {
      if (window.getLeafletMap?.()) return window.getLeafletMap();
      const modern = window.mapGL;
      try { modern?.map?.remove(); } catch (error) { console.warn('No se pudo cerrar MapLibre antes del mapa alternativo.', error); }
      window.mapGL = null;
      const current = byId('main-map');
      if (current) {
        const clean = current.cloneNode(false);
        clean.id = 'main-map';
        clean.className = 'map-container';
        clean.removeAttribute('style');
        current.replaceWith(clean);
      }
      ['zoomInBtn', 'zoomOutBtn', 'toggle3dBtn'].forEach(id => {
        const button = byId(id);
        if (button) button.replaceWith(button.cloneNode(true));
      });
      if (typeof initMap !== 'function' || typeof L === 'undefined') {
        const status = byId('geo-status');
        if (status) status.textContent = 'No se pudo cargar el mapa. Revisa tu conexión e inténtalo de nuevo.';
        return null;
      }
      try {
        initMap();
        const leaflet = window.getLeafletMap?.();
        if (!leaflet) throw new Error('Leaflet no pudo inicializar el mapa.');
        byId('zoomInBtn')?.addEventListener('click', () => leaflet.zoomIn());
        byId('zoomOutBtn')?.addEventListener('click', () => leaflet.zoomOut());
        const threeD = byId('toggle3dBtn');
        threeD?.remove();
        const status = byId('geo-status');
        if (status && status.textContent.startsWith('No se pudo cargar')) status.textContent = '';
        help.textContent = window._osmTilesState === 'ready' ? 'Calles de OpenStreetMap cargadas.' : 'Descargando calles de OpenStreetMap…';
        requestAnimationFrame(() => leaflet.invalidateSize());
        panel.dataset.mapFallback = 'leaflet';
        return leaflet;
      } catch (error) {
        console.error('Falló el mapa alternativo Leaflet:', error);
        const status = byId('geo-status');
        if (status) status.textContent = 'No se pudo cargar el mapa. Revisa tu conexión e inténtalo de nuevo.';
        return null;
      }
    };
    // Espera a que el diálogo sea visible antes de inicializar/redimensionar el mapa.
    let mapOpenSequence = 0;
    const setMap = visible => {
      panel.hidden = !visible;
      map.setAttribute('aria-pressed', String(visible));
      list.setAttribute('aria-pressed', String(!visible));
      if (!visible) { mapOpenSequence++; dialog.close(); return; }
      if (!dialog.open) dialog.showModal();
      const sequence = ++mapOpenSequence;
      help.textContent = 'Cargando el mapa…';

      // Inicializa después de que el diálogo modal tenga un tamaño visible.
      requestAnimationFrame(() => {
        if (sequence !== mapOpenSequence || !dialog.open || panel.hidden) return;
        window.dispatchEvent(new Event('forest:map-open'));
        if (window.mapGL) {
          const modern = window.mapGL;
          let loadErrors = 0;
          let mapLoaded = modern.map.loaded();
          if (mapLoaded) {
            help.textContent = '';
          } else {
            modern.map.once('load', () => {
              mapLoaded = true;
              if (window.mapGL === modern) help.textContent = '';
            });
          }
          modern.map.on('error', () => { loadErrors += 1; });
          // Cero elementos renderizados puede ser válido; no usarlo como señal de fallo.
          window.setTimeout(() => {
            if (sequence !== mapOpenSequence || !dialog.open || panel.hidden || window.mapGL !== modern || mapLoaded) return;
            if (!modern.map.loaded() || loadErrors >= 5) fallbackToLeaflet();
          }, 10000);
        } else {
          help.textContent = 'Abriendo el mapa de calles…';
          fallbackToLeaflet();
        }

        const resizeMap = () => {
          if (!dialog.open || panel.hidden) return;
          window.mapGL?.map.resize();
          window.getLeafletMap?.()?.invalidateSize({ pan: false });
        };
        requestAnimationFrame(() => {
          resizeMap();
          window.setTimeout(resizeMap, 120);
          window.setTimeout(resizeMap, 350);
          window.setTimeout(resizeMap, 800);
        });
      });
    };
    closeMap.addEventListener('click', () => setMap(false));
    dialog.addEventListener('cancel', event => { event.preventDefault(); setMap(false); });
    dialog.addEventListener('click', event => { if (event.target === dialog) setMap(false); });
    map.addEventListener('click', () => setMap(true));
    list.addEventListener('click', () => setMap(false));
    byId('forest-nearby-map').addEventListener('click', () => setMap(true));
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
