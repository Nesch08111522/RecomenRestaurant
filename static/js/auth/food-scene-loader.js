(() => {
  const loader = document.currentScript;
  const moduleUrl = loader?.dataset.sceneModule;
  const host = document.querySelector('.ax-food-host[data-food-experience-api]');
  if (!host || !moduleUrl) return;

  const desktop = window.matchMedia('(min-width: 901px)');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection || {};
  const slowNetwork = /(?:slow-)?2g/i.test(connection.effectiveType || '');
  const allowed = () => desktop.matches && !reducedMotion.matches && !connection.saveData && !slowNetwork;

  if (!allowed()) {
    host.dataset.sceneState = 'fallback';
    host.dataset.sceneReason = reducedMotion.matches ? 'reduced-motion' : !desktop.matches ? 'compact-layout' : 'slow-network';
    return;
  }

  let started = false;
  const loadScene = () => {
    if (started || !allowed() || document.hidden) return;
    started = true;
    const module = document.createElement('script');
    module.type = 'module';
    module.src = moduleUrl;
    module.onerror = () => {
      host.dataset.sceneState = 'fallback';
      host.dataset.sceneReason = 'module-load';
    };
    document.body.append(module);
  };

  const scheduleWhenIdle = () => {
    if (!allowed()) return;
    if (document.hidden) {
      document.addEventListener('visibilitychange', scheduleWhenIdle, { once: true });
      return;
    }
    window.setTimeout(() => {
      if ('requestIdleCallback' in window) window.requestIdleCallback(loadScene, { timeout: 2400 });
      else window.setTimeout(loadScene, 900);
    }, 500);
  };

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        observer.disconnect();
        scheduleWhenIdle();
      }
    }, { rootMargin: '40px' });
    observer.observe(host);
  } else {
    scheduleWhenIdle();
  }
})();
