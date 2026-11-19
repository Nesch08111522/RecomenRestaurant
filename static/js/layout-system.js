/* Progressive, reduced-motion-safe reveal for shared layout components. */
(function () {
  'use strict';
  const targets = document.querySelectorAll('[data-layout-reveal]');
  if (!targets.length || !('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.documentElement.classList.add('layout-observe');
  const observer = new IntersectionObserver((entries, current) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      current.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -32px 0px', threshold: 0.08 });
  targets.forEach(target => observer.observe(target));
})();
