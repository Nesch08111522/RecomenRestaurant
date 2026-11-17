/* Seguridad transversal de formularios y APIs same-origin. */
(function () {
  'use strict';

  window.escapeDisplayText = function (value) {
    const entities = {'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'};
    return String(value ?? '').replace(/[&<>"']/g, ch => entities[ch]);
  };

  function token() {
    const element = document.querySelector('meta[name="csrf-token"]');
    return element ? element.getAttribute('content') : '';
  }

  function isMutating(method) {
    return ['POST', 'PUT', 'PATCH', 'DELETE'].includes((method || 'GET').toUpperCase());
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const options = init ? { ...init } : {};
    const method = (options.method || (input && input.method) || 'GET').toUpperCase();
    const url = input instanceof Request ? input.url : String(input);
    const sameOrigin = new URL(url, document.baseURI).origin === window.location.origin;

    if (sameOrigin && isMutating(method)) {
      const headers = new Headers(options.headers || (input instanceof Request ? input.headers : undefined));
      const csrfToken = token();
      if (csrfToken) headers.set('X-CSRFToken', csrfToken);
      options.headers = headers;
    }
    return nativeFetch(input, options);
  };

  document.addEventListener('DOMContentLoaded', function () {
    const csrfToken = token();
    if (!csrfToken) return;
    document.querySelectorAll('form').forEach(function (form) {
      const method = (form.getAttribute('method') || 'GET').toUpperCase();
      if (new URL(form.action, document.baseURI).origin !== window.location.origin) return;
      if (!isMutating(method) || form.querySelector('input[name="csrf_token"]')) return;
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'csrf_token';
      input.value = csrfToken;
      form.appendChild(input);
    });
  });
})();
