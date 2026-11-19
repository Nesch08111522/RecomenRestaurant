(() => {
  'use strict';
  const script = document.currentScript || document.querySelector('script[data-feed]');
  if (!script || window.srNotificationFeed) return;
  window.srNotificationFeed = true;
  const prefix = `sr-notifications:${script.dataset.user}:`;
  const button = document.createElement('button');
  button.type = 'button';
  button.title = 'Actualizacion periodica, no tiempo real estricto';
  const controls = document.getElementById('sr-audio-controls');
  if (!controls) { window.srNotificationFeed = false; return; }
  controls.append(button);
  const status = document.createElement('span');
  status.setAttribute('role', 'status');
  button.after(status);
  let context, timer, controller, stopped = false, initialized = false, enabled = false;
  let high = 0;
  const seen = new Set();
  const get = key => { try { return localStorage.getItem(prefix + key); } catch { return null; } };
  const set = (key, value) => { try { localStorage.setItem(prefix + key, value); return true; } catch { return false; } };
  let muted = get('muted') !== 'false';
  function label() {
    button.textContent = muted ? 'Activar sonidos' : enabled ? 'Silenciar sonidos' : 'Habilitar audio';
    button.setAttribute('aria-pressed', String(!muted && enabled));
  }
  label();
  button.addEventListener('click', async () => {
    if (enabled && !muted) {
      muted = true;
      set('muted', 'true');
      await context?.suspend();
    } else {
      try {
        const Audio = window.AudioContext || window.webkitAudioContext;
        if (!Audio) throw new Error('Audio unavailable');
        context ||= new Audio();
        await context.resume();
        enabled = context.state === 'running';
        muted = !enabled;
        set('muted', String(muted));
        status.textContent = enabled ? '' : 'Audio bloqueado por el navegador';
      } catch { status.textContent = 'Audio no disponible'; }
    }
    label();
  });
  window.addEventListener('storage', event => {
    if (event.key === prefix + 'muted') {
      muted = event.newValue !== 'false';
      if (muted) context?.suspend();
      label();
    }
  });
  function tone(n) {
    if (muted || !enabled || context?.state !== 'running') return;
    const type = n.type || 'info';
    const frequency = {order: 660, promotion: 440, subscription: 880, message: 550,
      warning: 330, success: 740, commercial: 980, reservation: 500, review: 790, info: 600}[type] || 600;
    const roleOffset = {admin: 0, business_owner: 80, user: -80}[script.dataset.role] || 0;
    const oscillator = context.createOscillator(), gain = context.createGain();
    oscillator.type = script.dataset.role === 'admin' ? 'triangle' : 'sine';
    oscillator.frequency.setValueAtTime(frequency + roleOffset, context.currentTime);
    gain.gain.setValueAtTime(0, context.currentTime);
    gain.gain.linearRampToValueAtTime(.08, context.currentTime + .015);
    gain.gain.exponentialRampToValueAtTime(.001, context.currentTime + .22);
    oscillator.connect(gain); gain.connect(context.destination);
    oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
    oscillator.start(); oscillator.stop(context.currentTime + .24);
  }
  async function claim(n) {
    // Web Locks makes the shared watermark atomic across tabs. Without it,
    // sound is disabled rather than promising unsafe cross-tab deduplication.
    if (!navigator.locks || document.hidden || muted || !enabled) return;
    await navigator.locks.request(prefix + 'audio', () => {
      const previous = Number(get('played') || 0);
      if (n.id <= previous || stopped) return;
      if (set('played', String(n.id))) tone(n);
    });
  }
  async function refresh() {
    if (stopped || document.hidden) return;
    controller = new AbortController();
    try {
      const response = await fetch(script.dataset.feed, {cache: 'no-store', signal: controller.signal});
      if (response.status === 401 || response.status === 403) { cleanup(); return; }
      if (!response.ok) throw new Error('Feed unavailable');
      const data = await response.json();
      if (stopped) return;
      const rows = data.notifications || [];
      document.querySelectorAll('[data-count="notificaciones"], #notificationBadge').forEach(node => {
        node.textContent = String(data.unread_count);
        node.hidden = data.unread_count === 0;
      });
      const newest = Math.max(high, ...rows.map(n => Number(n.id)));
      if (initialized) {
        for (const n of [...rows].sort((a, b) => a.id - b.id)) {
          if (n.id > high && !seen.has(n.id) && !n.read && !n.archived && !n.deleted) await claim(n);
        }
        if (newest > high) {
          status.textContent = 'Hay nuevas notificaciones en la bandeja';
          window.dispatchEvent(new CustomEvent('sr:notifications', {detail: data}));
        }
      }
      rows.forEach(n => seen.add(n.id));
      if (seen.size > 1000) seen.clear();
      high = newest;
      initialized = true;
    } catch (error) {
      if (error.name !== 'AbortError') status.textContent = 'Notificaciones sin conexion; reintentando';
    } finally {
      controller = null;
      if (!stopped) timer = setTimeout(refresh, 10000);
    }
  }
  function cleanup() {
    stopped = true;
    clearTimeout(timer);
    controller?.abort();
    context?.close();
  }
  window.addEventListener('pagehide', cleanup);
  window.addEventListener('pageshow', event => {
    if (event.persisted) {
      stopped = false; enabled = false; context = null; initialized = false;
      label(); refresh();
    }
  });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && !stopped && !controller) { clearTimeout(timer); refresh(); }
  });
  refresh();
})();
