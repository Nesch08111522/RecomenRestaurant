(() => {
  'use strict';

  const url = document.currentScript?.dataset.historyUrl;
  if (!url) return;

  const clean = value => typeof value === 'string' ? value.trim().replace(/\s+/g, ' ') : '';

  async function record(value) {
    const query = Array.from(clean(value)).slice(0, 140).join('');
    if (!query) return false;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, submission_id: window.crypto?.randomUUID?.() }),
        keepalive: true,
        signal: controller.signal,
      });
      return response.ok;
    } catch {
      return false;
    } finally {
      clearTimeout(timeout);
    }
  }

  window.smartRestoSearchHistory = { record };

  document.addEventListener('submit', event => {
    if (!(event.target instanceof HTMLFormElement)) return;
    const field = event.target.querySelector('[data-search-history]');
    if (!field || field.disabled) return;
    if (field.hasAttribute('data-search-history-changes-only') &&
        !event.submitter?.hasAttribute('data-search-submit') &&
        clean(field.value).toLowerCase() === clean(field.defaultValue).toLowerCase()) return;
    void record(field.value);
  }, true);
})();
