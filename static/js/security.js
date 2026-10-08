/* Seguridad transversal de formularios y APIs same-origin. */
(function () {
  'use strict';

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
    const url = typeof input === 'string' ? input : input.url;
    const sameOrigin = !/^https?:\/\//i.test(url) || url.startsWith(window.location.origin);

    if (sameOrigin && isMutating(method)) {
      const headers = new Headers(options.headers || {});
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
      if (!isMutating(method) || form.querySelector('input[name="csrf_token"]')) return;
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'csrf_token';
      input.value = csrfToken;
      form.appendChild(input);
    });
  });
})();
