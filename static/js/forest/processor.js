/* Pure presentation processing; no DOM, state or network access. */
(() => {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const number = value => value !== null && value !== '' && Number.isFinite(Number(value)) ? Number(value) : null;
  window.ForestProcessor = Object.freeze({escape, number,
    tags: tags => Array.isArray(tags) ? tags.slice(0, 2) : [],
    image: value => typeof value === 'string' && (/^https?:\/\//i.test(value) || /^\/(?!\/)/.test(value)) ? value : '',
    rating: value => { const n = number(value); return n !== null && n > 0 ? n.toFixed(1) : 'Sin reseñas'; }
  });
})();
