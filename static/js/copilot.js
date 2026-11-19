(() => {
  const form = document.getElementById('copilot-question');
  if (!form) return;
  const status = document.getElementById('copilot-status');
  const conversation = document.getElementById('copilot-conversation');
  const input = document.getElementById('copilot-message');
  const preview = document.getElementById('copilot-preview');
  const reset = document.getElementById('copilot-new');
  const modes = [...document.querySelectorAll('[name="copilot-mode"]')];
  let history = [], proposal = null, busy = false;
  const mode = () => modes.find(r => r.checked).value;
  const show = text => { status.textContent = text; };
  function lock(value) {
    busy = value;
    input.readOnly = value;
    form.setAttribute('aria-busy', String(value));
    form.querySelectorAll('button').forEach(b => { b.disabled = value; });
    modes.forEach(r => { r.disabled = value; });
    reset.disabled = value;
    const draft = document.getElementById('copilot-proposal');
    if (draft) draft.querySelector('button').disabled = value;
  }
  async function post(url, data) {
    const response = await fetch(url, { method: 'POST', headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
    }, body: JSON.stringify(data) });
    let result;
    try { result = await response.json(); } catch (_) { throw Error('La sesión o el servidor no respondió correctamente. Recarga la página.'); }
    if (!response.ok || !result.success) throw Error(result.error || 'No se completó la operación.');
    return result;
  }
  let attachments = [], loadingImages = false;
  const imageList = document.getElementById('copilot-images');
  const filesInput = document.getElementById('copilot-files');
  const drop = document.getElementById('copilot-drop');
  const dialog = document.getElementById('copilot-image-dialog');
  function renderImages() {
    imageList.replaceChildren();
    attachments.forEach((image, index) => {
      const item = document.createElement('div');
      const open = document.createElement('button'); open.type = 'button'; open.setAttribute('aria-label', 'Ampliar ' + image.name);
      const img = document.createElement('img'); img.src = image.data; img.alt = image.name; open.append(img);
      open.addEventListener('click', () => { dialog.querySelector('img').src = image.data; dialog.showModal(); });
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Quitar';
      remove.setAttribute('aria-label', 'Quitar ' + image.name);
      remove.disabled = busy;
      remove.addEventListener('click', () => { attachments.splice(index, 1); renderImages(); });
      item.append(open, remove); imageList.append(item);
    });
  }
  async function addImages(files) {
    if (busy || loadingImages) return;
    loadingImages = true;
    try {
      for (const file of files) {
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 2 * 1024 * 1024 || attachments.length >= 3 || attachments.reduce((n, a) => n + a.size, 0) + file.size > 4 * 1024 * 1024) {
          show('Solo 3 imágenes PNG, JPG o WebP; 2 MB cada una y 4 MB en total.'); continue;
        }
        const data = await new Promise((resolve, reject) => {
          const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(Error('No se pudo leer la imagen.')); reader.readAsDataURL(file);
        });
        if (!disposed) attachments.push({ data, name: file.name || 'Imagen pegada', size: file.size });
      }
      renderImages();
    } catch (error) { show(error.message); } finally { loadingImages = false; filesInput.value = ''; }
  }
  document.getElementById('copilot-attach')?.addEventListener('click', () => filesInput.click());
  filesInput?.addEventListener('change', () => addImages([...filesInput.files]));
  document.getElementById('copilot-image-close')?.addEventListener('click', () => dialog.close());
  input.addEventListener('paste', e => {
    const files = [...(e.clipboardData?.items || [])].filter(item => item.kind === 'file').map(item => item.getAsFile()).filter(Boolean);
    if (files.length) { e.preventDefault(); addImages(files); }
  });
  drop?.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragging'); });
  drop?.addEventListener('dragleave', () => drop.classList.remove('dragging'));
  drop?.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('dragging'); addImages([...e.dataTransfer.files]); });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!busy && !loadingImages) form.requestSubmit(); }
  });
  async function progressive(p, text) {
    p.setAttribute('aria-busy', 'true');
    for (let end = 0; end < text.length && !disposed; end += 32) {
      p.textContent = text.slice(0, end + 32);
      conversation.scrollTop = conversation.scrollHeight;
      await new Promise(resolve => setTimeout(resolve, 16));
    }
    p.textContent = text; p.setAttribute('aria-busy', 'false');
  }
  function turn(role, text, links = []) {
    const article = document.createElement('article');
    article.className = 'copilot-turn ' + role;
    const label = document.createElement('strong'); label.textContent = role === 'user' ? 'Tú' : 'SmartResto Copilot';
    const p = document.createElement('p'); p.textContent = text;
    article.append(label, p);
    const nav = document.createElement('nav');
    const labels = { recommendations: 'Recomendaciones', orders: 'Pedidos', catalog: 'Carta y productos', reports: 'Informes', websites: 'Sitios del negocio', review: 'Revisión', offers: 'Ofertas', rewards: 'Recompensas' };
    for (const link of links) {
      if (!link || typeof link.url !== 'string' || !link.url.startsWith('/') || link.url.startsWith('//')) continue;
      const target = new URL(link.url, location.origin);
      if (target.origin !== location.origin) continue;
      const a = document.createElement('a'); a.href = target.pathname + target.search + target.hash;
      a.textContent = labels[link.label] || link.label || 'Abrir módulo'; nav.append(a);
    }
    if (nav.childElementCount) article.append(nav);
    conversation.hidden = false; conversation.append(article);
    conversation.scrollTop = conversation.scrollHeight; reset.hidden = false;
    if (role === 'assistant' && synth) {
      const controls = document.createElement('div'); controls.className = 'copilot-response-audio';
      const avatar = document.createElement('span'); avatar.className = 'copilot-avatar'; avatar.textContent = '▂ ▅ ▃ ▆ ▂'; avatar.setAttribute('aria-hidden', 'true');
      const listen = document.createElement('button'); listen.type = 'button'; listen.textContent = 'Escuchar';
      const pause = document.createElement('button'); pause.type = 'button'; pause.textContent = 'Pausar';
      const stop = document.createElement('button'); stop.type = 'button'; stop.textContent = 'Detener';
      listen.addEventListener('click', () => readReply(text, () => {}, true, avatar));
      pause.addEventListener('click', () => {
        if (activeAvatar !== avatar || !speaking) return;
        if (synth.paused) { synth.resume(); avatar.classList.add('speaking'); pause.textContent = 'Pausar'; }
        else { synth.pause(); avatar.classList.remove('speaking'); pause.textContent = 'Continuar'; }
      });
      stop.addEventListener('click', () => { if (activeAvatar === avatar) stopAudio(); pause.textContent = 'Pausar'; });
      controls.append(avatar, listen, pause, stop); article.append(controls);
    }
    return p;
  }
  function cancel() { proposal = null; preview.hidden = true; }
  async function prepare(payload) {
    cancel();
    proposal = await post('/api/copilot/actions', { ...payload, mode: mode() });
    preview.querySelector('p').textContent = Object.entries(proposal.preview).map(([key, value]) => `${key}: ${value}`).join('\n');
    preview.hidden = false;
    show('Propuesta preparada. Revisa sus datos; todavía no se ha aplicado.');
  }
  modes.forEach(r => r.addEventListener('change', () => {
    cancel();
    document.getElementById('copilot-mode-help').textContent = mode() === 'full'
      ? 'Acceso completo: propone los cambios compatibles con tu rol y pide confirmación. No todas las operaciones están integradas; las demás se abren en su módulo.'
      : 'Básico: consultar y navegar, sin modificar datos.';
    const manual = document.getElementById('copilot-manual'); if (manual) manual.hidden = mode() !== 'full';
  }));
  form.addEventListener('submit', async e => {
    e.preventDefault(); if (busy) return;
    if (loadingImages) return;
    const message = input.value.trim() || (attachments.length ? 'Describe estas imágenes con el contexto autorizado.' : ''); if (!message) return;
    stopListening(false, conversational);
    stopAudio();
    lock(true); show('Consultando información autorizada…'); cancel();
    const pending = [...history, { role: 'user', content: message }].slice(-19);
    while (pending.length > 1 && pending.reduce((n, m) => n + m.content.length, 0) > 16000) pending.splice(0, 2);
    try {
      const result = await post('/api/copilot/chat', { messages: pending, mode: mode(), images: attachments.map(image => image.data) });
      turn('user', message);
      attachments = []; renderImages();
      const replyNode = turn('assistant', result.reply, result.links || []);
      replyNode.textContent = '';
      await progressive(replyNode, result.reply);
      history = [...pending, { role: 'assistant', content: result.reply }]; input.value = '';
      show('Respuesta recibida.');
      if (result.action && mode() === 'full') await prepare(result.action);
      const navigate = result.navigate;
      let destination = null;
      if (navigate?.verified === true && typeof navigate.url === 'string' && /^\/(?!\/)/.test(navigate.url) && !/[\\\s]/.test(navigate.url)) {
        const target = new URL(navigate.url, location.origin);
        if (target.origin === location.origin && target.pathname === navigate.url && (result.links || []).some(link => link.url === navigate.url)) destination = target.pathname;
      }
      readReply(result.reply, () => { if (destination && !disposed) location.assign(destination); });
    } catch (error) { show(error.message); } finally { lock(false); resumeConversation(); }
  });
  document.getElementById('copilot-proposal')?.addEventListener('submit', async e => {
    e.preventDefault(); if (busy || mode() !== 'full') return;
    lock(true);
    try { const data = new FormData(e.target); await prepare({ action: 'restaurant_promo', rid: Number(data.get('rid')), text: data.get('text') }); }
    catch (error) { show(error.message); } finally { lock(false); }
  });
  document.getElementById('copilot-cancel').addEventListener('click', cancel);
  document.getElementById('copilot-confirm').addEventListener('click', async e => {
    if (!proposal || busy || mode() !== 'full') return;
    lock(true); e.target.disabled = true;
    try {
      const result = await post('/api/copilot/actions/' + proposal.id + '/confirm', { mode: mode(), confirm: true, token: proposal.token });
      turn('assistant', result.message); show(result.message); cancel();
    } catch (error) { show(error.message); } finally { lock(false); e.target.disabled = false; }
  });
  reset.addEventListener('click', () => { if (busy) return; history = []; conversation.replaceChildren(); conversation.hidden = true; reset.hidden = true; cancel(); show('Nueva conversación.'); input.focus(); });
  const voice = document.getElementById('copilot-voice');
  const voiceStop = document.getElementById('copilot-voice-stop');
  const read = document.getElementById('copilot-read');
  const audioStop = document.getElementById('copilot-audio-stop');
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const synth = window.speechSynthesis;
  let recognition = null, listening = false, running = false, disposed = false;
  const readingKey = 'smartresto:copilot-auto-voice';
  let reading = true;
  try { reading = localStorage.getItem(readingKey) !== 'false'; } catch (_) {}
  let base = '', segments = [], timer = null, speaking = false, audioDone = null;
  let silenceTimer = null, lastActivity = 0, hasSpeech = false, conversational = false;
  let blocked = false, voiceGeneration = 0, restartFailures = 0;
  function clearSilence() { clearTimeout(silenceTimer); silenceTimer = null; }
  function activity() {
    if (!listening || speaking || busy || disposed) return;
    hasSpeech = true; lastActivity = performance.now(); clearSilence();
    silenceTimer = setTimeout(finishSilence, 2000);
  }
  function finishSilence() {
    silenceTimer = null;
    if (!listening || speaking || busy || disposed || !hasSpeech) return;
    const remaining = 2000 - (performance.now() - lastActivity);
    if (remaining > 0) { silenceTimer = setTimeout(finishSilence, remaining); return; }
    if (!input.value.trim() || loadingImages) return;
    stopListening(true, true);
  }
  function resumeConversation() {
    clearTimeout(timer);
    if (!conversational || blocked || disposed || speaking || busy || listening || document.hidden) return;
    timer = setTimeout(() => {
      if (!conversational || blocked || disposed || speaking || busy || document.hidden) return;
      if (running) { resumeConversation(); return; }
      base = ''; segments = []; hasSpeech = false; listening = true;
      voiceUI(); startRecognition(); meter();
    }, 300);
  }
  let stream = null, context = null, analyser = null, frame = null, micGeneration = 0, activeAvatar = null;
  const wave = document.getElementById('copilot-wave');
  const partial = document.getElementById('copilot-partial');
  function releaseMic() {
    micGeneration++;
    if (frame !== null) window.cancelAnimationFrame(frame);
    frame = null;
    stream?.getTracks().forEach(track => track.stop()); stream = null;
    if (context) context.close().catch(() => {});
    context = null; analyser = null;
    if (wave) wave.getContext('2d')?.clearRect(0, 0, wave.width, wave.height);
  }
  async function meter() {
    if (!window.navigator?.mediaDevices?.getUserMedia) return;
    const generation = ++micGeneration;
    try {
      const acquired = await window.navigator.mediaDevices.getUserMedia({ audio: true });
      if (!listening || disposed || generation !== micGeneration) { acquired.getTracks().forEach(track => track.stop()); return; }
      stream = acquired;
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      context = new AudioContext(); await context.resume();
      if (!listening || disposed || generation !== micGeneration || !context) return;
      analyser = context.createAnalyser(); analyser.fftSize = 256;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      const draw = () => {
        if (!listening || disposed || !analyser) return;
        analyser.getByteTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0) / samples.length);
        if (rms >= 0.025) activity();
        const paint = wave?.getContext('2d');
        if (paint) {
          paint.clearRect(0, 0, wave.width, wave.height);
          paint.strokeStyle = getComputedStyle(voice).color; paint.lineWidth = 2; paint.beginPath();
          const pulse = 2 + Math.sin(performance.now() / 400) * 1.5;
          samples.forEach((value, index) => {
            const x = index * wave.width / samples.length;
            const y = wave.height / 2 + (value - 128) / 128 * wave.height / 2 + Math.sin(index / 5) * pulse;
            if (!index) paint.moveTo(x, y); else paint.lineTo(x, y);
          }); paint.stroke();
        }
        frame = window.requestAnimationFrame(draw);
      }; draw();
    } catch (_) { if (generation === micGeneration) { stopListening(false); show('Autoriza el micrófono en un contexto seguro para dictar.'); } }
  }
  // Results are indexed within each recognition session, not appended per event.
  const transcript = () => [base, ...segments.map(s => s.text)].filter(Boolean).join(' ').trim();
  const command = /\b(?:terminar|finalizar|acabar)\s+(?:la\s+)?conversaci[oó]n\b/ig;
  function voiceUI() {
    voice.setAttribute('aria-pressed', String(listening));
    voice.textContent = listening ? 'Escuchando' : 'Voz';
    voiceStop.disabled = !listening;
  }
  function startRecognition() {
    clearTimeout(timer);
    if (!listening || disposed || busy || speaking || running) return;
    segments = [];
    const begin = () => {
      if (!listening || disposed || busy || speaking || running || blocked) return;
      try { running = true; recognition.start(); }
      catch (_) { running = false; blocked = true; stopListening(false); show('No se pudo iniciar el micrófono. Puedes volver a activarlo.'); }
    };
    if (window.smartrestoVoice) window.smartrestoVoice.acquire('copilot-dictation', begin);
    else begin();
  }
  function stopListening(send, preserveConversation = false) {
    if (!preserveConversation) conversational = false;
    listening = false; voiceGeneration++; clearTimeout(timer); clearSilence(); releaseMic(); voiceUI();
    base = ''; segments = []; hasSpeech = false;
    if (partial) partial.textContent = '';
    if (recognition && running) { try { recognition.abort(); } catch (_) {} }
    else window.smartrestoVoice?.release('copilot-dictation');
    if (send && input.value.trim() && !busy && !disposed) form.requestSubmit();
  }
  function stopAudio() {
    const done = audioDone; audioDone = null;
    speaking = false;
    window.smartrestoVoice?.release('copilot-audio');
    activeAvatar?.classList.remove('speaking'); activeAvatar = null;
    if (synth) synth.cancel();
    audioStop.disabled = true;
    // Cancelling audio must not execute a pending navigation.
    void done;
    resumeConversation();
  }
  function readReply(text, done, force = false, avatar = null) {
    if ((!reading && !force) || !synth || disposed) { done(); return; }
    stopAudio(); stopListening(false, conversational);
    speaking = true; clearTimeout(timer);
    const generation = voiceGeneration;
    activeAvatar = avatar || conversation.lastElementChild?.querySelector('.copilot-avatar');
    if (recognition && running) recognition.abort();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-PE';
    const voices = synth.getVoices().filter(v => /^es(?:-|$)/i.test(v.lang));
    utterance.voice = voices.find(v => v.lang === 'es-PE') || voices.find(v => v.lang === 'es-ES') || voices.find(v => v.default) || voices[0] || null;
    utterance.lang = utterance.voice?.lang || 'es-ES';
    utterance.onstart = () => { if (audioDone === done) activeAvatar?.classList.add('speaking'); };
    utterance.onboundary = () => { if (audioDone === done) activeAvatar?.classList.toggle('boundary'); };
    audioDone = done; audioStop.disabled = false;
    utterance.onend = () => { if (audioDone === done) { stopAudio(); if (!disposed) done(); } };
    utterance.onerror = () => { if (audioDone === done) { stopAudio(); show('Audio no disponible. La respuesta sigue visible.'); } };
    const speak = () => { if (speaking && !disposed && generation === voiceGeneration) synth.speak(utterance); };
    if (window.smartrestoVoice) window.smartrestoVoice.acquire('copilot-audio', speak);
    else speak();
  }
  read.disabled = !synth;
  read.setAttribute('aria-pressed', String(reading));
  read.textContent = reading ? 'Desactivar lectura' : 'Activar lectura';
  read.addEventListener('click', () => {
    reading = !reading;
    try { localStorage.setItem(readingKey, String(reading)); } catch (_) {}
    read.setAttribute('aria-pressed', String(reading));
    read.textContent = reading ? 'Desactivar lectura' : 'Activar lectura';
    if (!reading) stopAudio();
  });
  audioStop.addEventListener('click', stopAudio);
  voiceStop.addEventListener('click', () => stopListening(true));
  reset.addEventListener('click', () => { stopListening(false); stopAudio(); base = ''; segments = []; input.value = ''; });
  if (!SpeechRecognition) {
    voice.hidden = true; voiceStop.hidden = true;
    voice.insertAdjacentText('afterend', 'Voz no disponible en este navegador.');
  } else {
    recognition = new SpeechRecognition();
    recognition.lang = 'es-PE'; recognition.continuous = true; recognition.interimResults = true;
    recognition.addEventListener('result', e => {
      if (!listening || speaking || disposed) return;
      for (let i = e.resultIndex; i < e.results.length; i++) {
        segments[i] = { text: e.results[i][0].transcript.trim(), final: e.results[i].isFinal };
      }
      const text = transcript();
      command.lastIndex = 0;
      const match = command.exec(text);
      input.value = (match ? text.slice(0, match.index) : text).trim().slice(0, 2000);
      if (partial) partial.textContent = match ? '' : segments.filter(s => !s.final).map(s => s.text).join(' ');
      restartFailures = 0;
      if (match) stopListening(true);
      else {
        if (segments.some(s => s.text)) activity();
        show('Escuchando. Se enviará tras 2 segundos de silencio.');
      }
    });
    recognition.addEventListener('end', () => {
      running = false;
      if (!listening) window.smartrestoVoice?.release('copilot-dictation');
      // Keep the displayed turn across browser recognition restarts, never across sends.
      if (listening) base = transcript();
      segments = [];
      if (listening && !disposed && !speaking) {
        if (++restartFailures >= 6) { blocked = true; stopListening(false); }
        else timer = setTimeout(startRecognition, 300);
      }
    });
    recognition.addEventListener('error', e => {
      if (e.error === 'no-speech' || (e.error === 'aborted' && (!listening || speaking))) return;
      blocked = true; stopListening(false);
      show(['not-allowed', 'service-not-allowed'].includes(e.error)
        ? 'Autoriza el micrófono para volver a activar la voz.'
        : 'La voz se detuvo por un error. Puedes activarla de nuevo o escribir.');
    });
    voice.addEventListener('click', () => {
      if (busy) return;
      if (listening) { stopListening(true); return; }
      stopAudio(); blocked = false; restartFailures = 0; conversational = true;
      base = input.value.trim(); segments = []; hasSpeech = false; listening = true;
      voiceUI(); startRecognition(); meter();
      if (base) activity();
    });
  }
  document.addEventListener?.('smartresto:copilot-wake', e => {
    if (disposed || busy || !recognition || listening) return;
    const text = e.detail?.transcript;
    if (typeof text === 'string' && text.trim()) input.value = text.trim().slice(0, 2000);
    voice.click();
  });
  if (new URLSearchParams(window.location?.search || '').get('voice') === '1' && recognition) voice.click();
  reset.addEventListener('click', () => { attachments = []; renderImages(); if (partial) partial.textContent = ''; });
  window.addEventListener('pagehide', () => {
    disposed = true; stopListening(false); audioDone = null; stopAudio();
    if (recognition) recognition.abort();
  });
})();
