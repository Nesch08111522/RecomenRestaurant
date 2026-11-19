(() => {
  if (window.smartrestoVoice) return;
  const panel = document.getElementById('sr-wake');
  if (!panel) return;
  const toggle = document.getElementById('sr-wake-toggle');
  const enable = document.getElementById('sr-wake-enable');
  const status = document.getElementById('sr-wake-status');
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  const key = 'smartresto:copilot-wake-enabled';
  let preferred = true;
  try { preferred = localStorage.getItem(key) !== 'false'; } catch (_) {}
  let authorized = false, blocked = false, running = false, disposed = false;
  let timer = null, failures = 0, pending = null;
  const owners = new Set();
  const recognition = Speech ? new Speech() : null;
  const say = text => { status.textContent = text; };
  const eligible = () => preferred && authorized && !blocked && !disposed && !document.hidden && !owners.size;
  function stop() {
    clearTimeout(timer); timer = null;
    if (running) { try { recognition.abort(); } catch (_) {} }
  }
  function start() {
    clearTimeout(timer); timer = null;
    if (!recognition || !eligible() || running) return;
    try { running = true; say('Iniciando micrófono…'); recognition.start(); }
    catch (_) { running = false; blocked = true; say('Pulsa Habilitar micro para reintentar.'); }
  }
  function resume() {
    if (eligible() && !running) timer = setTimeout(start, 600);
  }
  // A competing recognizer starts only after the wake recognizer has ended.
  window.smartrestoVoice = {
    acquire(owner, ready) {
      owners.add(owner); pending = ready || null; stop(); say('Activación pausada por dictado o audio.');
      if (!running && pending) { const next = pending; pending = null; next(); }
    },
    release(owner) { owners.delete(owner); resume(); }
  };
  toggle.checked = preferred;
  toggle.addEventListener('change', () => {
    preferred = toggle.checked;
    try { localStorage.setItem(key, String(preferred)); } catch (_) { say('Preferencia no persistida: almacenamiento bloqueado.'); }
    if (!preferred) { stop(); say('Activación por voz desactivada.'); }
    else if (authorized && !blocked) start();
    else say('Preferencia activa. Pulsa Habilitar micro.');
  });
  enable.addEventListener('click', () => {
    if (!preferred) { say('Activa primero el interruptor.'); return; }
    authorized = true; blocked = false; failures = 0; start();
  });
  if (!recognition) {
    enable.disabled = true; say('Voz no disponible en este navegador.');
  } else {
    recognition.lang = 'es-PE'; recognition.continuous = true; recognition.interimResults = false;
    recognition.addEventListener('start', () => {
      if (!eligible()) { stop(); return; }
      say('Escuchando: hola smart copilot.');
    });
    recognition.addEventListener('result', event => {
      if (!eligible()) return;
      failures = 0;
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (!event.results[i].isFinal) continue;
        const text = event.results[i][0].transcript.trim();
        const match = /(?:^|\s)hola\s+(?:smart\s+copilot|smartresto\s+copilot)(?=$|[\s,.!?])/i.exec(text);
        if (!match) continue;
        const transcript = text.slice(match.index + match[0].length).replace(/^[\s,.!?]+/, '').trim();
        window.smartrestoVoice.acquire('handoff', () => {
          if (disposed) return;
          if (document.getElementById('copilot-question')) {
            document.dispatchEvent(new CustomEvent('smartresto:copilot-wake', { detail: { transcript } }));
            window.smartrestoVoice.release('handoff');
          } else {
            const target = new URL(panel.dataset.copilotUrl, window.location.origin);
            target.searchParams.set('voice', '1'); window.location.assign(target.href);
          }
        });
        break;
      }
    });
    recognition.addEventListener('error', event => {
      if (event.error === 'aborted' && !eligible()) return;
      if (['not-allowed', 'service-not-allowed', 'audio-capture'].includes(event.error) || ++failures >= 3) {
        blocked = true; authorized = false; stop(); say('Micrófono detenido. Revisa permisos y pulsa Habilitar micro.');
      }
    });
    recognition.addEventListener('end', () => {
      running = false;
      if (pending) { const next = pending; pending = null; next(); }
      else {
        if (eligible() && ++failures >= 6) { blocked = true; say('Reconexiones detenidas. Pulsa Habilitar micro.'); }
        else { if (eligible()) say('Reconectando micrófono…'); resume(); }
      }
    });
    say(preferred ? 'Preferencia activa. Pulsa Habilitar micro.' : 'Activación por voz desactivada.');
    // A saved preference is not proof of microphone permission.
    try { window.navigator?.permissions?.query({ name: 'microphone' }).then(permission => {
      if (!disposed && permission.state === 'granted') { authorized = true; start(); }
      permission.onchange = () => {
        if (permission.state !== 'granted') { authorized = false; blocked = true; stop(); say('Permiso pendiente. Pulsa Habilitar micro.'); }
      };
    }).catch(() => {}); } catch (_) {}
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) { stop(); say('Escucha pausada: pestaña oculta.'); } else resume(); });
  window.addEventListener('pagehide', () => { disposed = true; pending = null; stop(); });
  window.addEventListener('pageshow', event => { if (event.persisted) { disposed = false; owners.clear(); resume(); } });
})();
