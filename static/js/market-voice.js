(() => {
  const input = document.getElementById('dictation');
  if (!input) return;
  const message = document.getElementById('voice-status');
  const form = document.getElementById('offer-form');
  const microphone = document.getElementById('microphone');
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Speech) {
    microphone.disabled = true;
    message.textContent = 'Tu navegador permite preparar el borrador escribiendo la instrucción.';
  }
  microphone.addEventListener('click', () => {
    if (!Speech || microphone.disabled) return;
    microphone.disabled = true;
    const speech = new Speech();
    speech.onend = () => { microphone.disabled = false; window.smartrestoVoice?.release('market'); };
    speech.lang = 'es-PE';
    speech.onresult = e => { input.value = e.results[0][0].transcript; message.textContent = 'Revisa el dictado antes de usarlo.'; };
    speech.onerror = () => { message.textContent = 'No se recibió el audio. Puedes escribir la instrucción.'; };
    const begin = () => { try { speech.start(); } catch (_) { microphone.disabled = false; window.smartrestoVoice?.release('market'); } };
    if (window.smartrestoVoice) window.smartrestoVoice.acquire('market', begin);
    else begin();
  });
  const numbers = ['cero','uno','dos','tres','cuatro','cinco','seis','siete','ocho','nueve','diez','once','doce','trece','catorce','quince','dieciseis','diecisiete','dieciocho','diecinueve','veinte'];
  document.getElementById('parse-voice').addEventListener('click', () => {
    let text = input.value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    text = text.replace(/\b[a-z]+\b/g, word => numbers.includes(word) ? String(numbers.indexOf(word)) : word);
    const match = text.match(/(\d+)\s+porciones?\s+de\s+(.+?)\s+(?:para\s+)?(hoy|manana)\s+(?:a|por)\s+(\d+(?:[.,]\d+)?)\s*soles/);
    if (!match) { message.textContent = 'Ejemplo: agrega doce porciones de pollo para mañana a dieciséis soles.'; return; }
    const date = new Date();
    if (match[3] === 'manana') date.setTime(date.getTime() + 86400000);
    const day = new Intl.DateTimeFormat('sv-SE', {timeZone:'America/Lima',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);
    const f = form.elements;
    f.dish.value = ''; f.name.value = match[2]; f.stock.value = match[1]; f.price.value = match[4].replace(',','.'); f.day.value = day;
    document.getElementById('offer-editor').open = true;
    message.textContent = 'Borrador preparado. Revisa ingredientes, fecha y precio antes de confirmar.';
    f.name.focus();
  });
})();
