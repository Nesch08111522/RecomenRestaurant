(() => {
  'use strict';

  const page = document.querySelector('[data-recommendations]');
  if (!page) return;

  async function post(url, payload, keepalive = false) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive,
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || 'No se pudo guardar el cambio.');
    return result;
  }

  function updateCount(list, change) {
    const count = list.querySelector('[data-rec-count]');
    const countLabel = list.querySelector('[data-rec-count-label]');
    const visible = Number(count.textContent) + change;
    count.textContent = String(visible);
    countLabel.textContent = visible === 1 ? countLabel.dataset.singular : countLabel.dataset.plural;
  }

  function showPhotoFallback(photo) {
    photo.hidden = true;
    photo.parentElement.querySelector('.rec-photo-fallback').hidden = false;
    photo.parentElement.querySelector('.rec-photo-caption').hidden = false;
  }

  for (const photo of page.querySelectorAll('[data-rec-photo]')) {
    photo.addEventListener('error', () => showPhotoFallback(photo), { once: true });
    if (photo.complete && !photo.naturalWidth) showPhotoFallback(photo);
  }

  function recordView(event) {
    if (!(event.target instanceof Element) || (event.type === 'auxclick' && event.button !== 1)) return;
    const token = event.target.closest('[data-rec-view]')?.closest('[data-token]')?.dataset.token;
    if (token) post(page.dataset.interactionUrl, { token, action: 'view' }, true).catch(() => {});
  }

  page.addEventListener('click', recordView);
  page.addEventListener('auxclick', recordView);

  const cards = new Map();
  for (const card of page.querySelectorAll('[data-rec-card][data-token]')) {
    const entry = {
      card,
      list: card.closest('[data-rec-list]'),
      like: card.querySelector('[data-rec-like]'),
      dismiss: card.querySelector('[data-rec-dismiss]'),
      undo: card.querySelector('[data-rec-undo]'),
      body: card.querySelector('.rec-card-main'),
      dismissed: card.querySelector('[data-rec-dismissed]'),
    };
    const key = card.dataset.recKey;
    if (!cards.has(key)) cards.set(key, []);
    cards.get(key).push(entry);
    entry.like.addEventListener('click', () => saveFeedback(entry, entry.like.getAttribute('aria-pressed') === 'true' ? 'undo' : 'like', entry.like));
    entry.dismiss?.addEventListener('click', () => saveFeedback(entry, 'dismiss', entry.dismiss));
    entry.undo?.addEventListener('click', () => saveFeedback(entry, 'undo', entry.undo));
  }

  function setCardPending(entries, pending) {
    for (const entry of entries) {
      if (pending) entry.card.setAttribute('aria-busy', 'true');
      else entry.card.removeAttribute('aria-busy');
      for (const control of [entry.like, entry.dismiss, entry.undo]) {
        if (control) control.disabled = pending;
      }
    }
  }

  async function saveFeedback(entry, action, button) {
    if (entry.card.getAttribute('aria-busy') === 'true') return;
    const duplicates = cards.get(entry.card.dataset.recKey);
    const status = entry.list.querySelector('[data-rec-feedback]');
    let focus = button;
    setCardPending(duplicates, true);
    status.textContent = '';
    try {
      const result = await post(page.dataset.interactionUrl, { token: entry.card.dataset.token, action });
      const hidden = result.state === 'dismissed';
      for (const duplicate of duplicates) {
        duplicate.like.setAttribute('aria-pressed', String(result.liked));
        if (!duplicate.dismissed) continue;
        if (duplicate.body.hidden !== hidden) updateCount(duplicate.list, hidden ? -1 : 1);
        duplicate.body.hidden = hidden;
        duplicate.dismissed.hidden = !hidden;
      }
      if (hidden) focus = entry.undo;
      else if (button === entry.undo) focus = entry.dismiss;
      else status.textContent = result.liked ? 'Preferencia guardada.' : 'Preferencia retirada.';
    } catch (error) {
      status.textContent = error.message || 'No se pudo guardar el cambio.';
    } finally {
      setCardPending(duplicates, false);
      focus.focus({ preventScroll: true });
    }
  }

  const searchForm = page.querySelector('[data-rec-search-form]');
  const queryField = searchForm.querySelector('input[name="q"]');
  const originalQuery = queryField.value.trim();
  const searchStatus = page.querySelector('[data-rec-search-status]');
  let searchPending = false;
  searchForm.addEventListener('submit', async event => {
    if (searchPending) {
      event.preventDefault();
      return;
    }
    const query = queryField.value.trim();
    const focusedFilter = searchForm.contains(document.activeElement) &&
      document.activeElement.matches('input:not([name="q"]), select');
    const explicitSearch = event.submitter?.hasAttribute('data-rec-search-submit') && !focusedFilter;
    const isSearch = query && (query !== originalQuery || explicitSearch);
    const history = window.smartRestoSearchHistory;
    if (!isSearch || !history) return;

    event.preventDefault();
    searchPending = true;
    searchStatus.textContent = 'Guardando búsqueda…';
    const buttons = Array.from(searchForm.querySelectorAll('button[type="submit"]'));
    buttons.forEach(button => { button.disabled = true; });
    try {
      await history.record(query);
    } finally {
      HTMLFormElement.prototype.submit.call(searchForm);
    }
  });

  const locate = page.querySelector('[data-rec-location]');
  const clear = page.querySelector('[data-rec-location-clear]');
  const weather = page.querySelector('[data-rec-weather]');
  const geoStatus = page.querySelector('[data-rec-geo-status]');
  const weatherWasEnabled = weather.checked;

  function setLocationPending(pending) {
    locate.disabled = pending;
    weather.disabled = pending;
    if (clear) clear.disabled = pending;
  }

  async function saveLocation(payload) {
    setLocationPending(true);
    try {
      await post(page.dataset.locationUrl, payload);
      window.location.reload();
    } catch (error) {
      weather.checked = weatherWasEnabled;
      geoStatus.textContent = error.message || 'No se pudo actualizar tu ubicación.';
      setLocationPending(false);
    }
  }

  locate.addEventListener('click', () => {
    if (!navigator.geolocation) {
      geoStatus.textContent = 'El navegador no tiene acceso a la ubicación en esta página.';
      return;
    }
    setLocationPending(true);
    geoStatus.textContent = 'Solicitando tu ubicación…';
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      saveLocation({ lat: coords.latitude, lng: coords.longitude, weather: weather.checked });
    }, error => {
      geoStatus.textContent = error.code === 1 ? 'Puedes permitir la ubicación en el navegador e intentarlo de nuevo.' : 'No pudimos obtener tu ubicación. Inténtalo de nuevo.';
      setLocationPending(false);
    }, { maximumAge: 300000, timeout: 12000 });
  });

  clear?.addEventListener('click', () => saveLocation({ clear: true }));
  weather.addEventListener('change', () => {
    if (page.dataset.locationEnabled === 'true') saveLocation({ weather: weather.checked });
  });
})();
