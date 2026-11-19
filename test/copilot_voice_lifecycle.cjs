const assert = require('node:assert/strict');
const elements = {};
class Element {
  constructor() { this.handlers = {}; this.value = ''; this.checked = true; this.dataset = { username: 'Nancy real' }; this.classList = { add() {}, remove() {}, toggle() {} }; }
  append(...children) { this.lastElementChild = children.at(-1); }
  replaceChildren() {}
  addEventListener(k, f) { (this.handlers[k] ??= []).push(f); }
  emit(k, e = {}) { for (const f of this.handlers[k] || []) f(e); }
  setAttribute() {}
  click() { this.emit('click'); }
  querySelectorAll() { return []; }
  querySelector() { return new Element(); }
  insertAdjacentText() {}
  requestSubmit() { this.submitted = (this.submitted || 0) + 1; }
}
for (const id of ['question', 'status', 'conversation', 'message', 'preview', 'new', 'voice', 'voice-stop', 'read', 'audio-stop', 'cancel', 'confirm', 'mode-help']) elements['copilot-' + id] = new Element();
const documentEvents = {};
global.document = { createElement: () => new Element(), addEventListener: (k, f) => { documentEvents[k] = f; }, getElementById: id => elements[id] || null, querySelectorAll: () => [{ checked: true, value: 'basic', addEventListener() {} }] };
const listeners = {}, timers = new Map();
let serial = 0;
global.setTimeout = f => { timers.set(++serial, f); return serial; };
global.clearTimeout = id => timers.delete(id);
function flush() { const pending = [...timers.values()]; timers.clear(); pending.forEach(f => f()); }
class Recognition {
  constructor() { global.rec = this; this.handlers = {}; this.starts = 0; }
  addEventListener(k, f) { this.handlers[k] = f; }
  start() { this.starts++; }
  stop() { this.stops = (this.stops || 0) + 1; }
  abort() { this.aborts = (this.aborts || 0) + 1; }
}
const synth = { cancel() {}, getVoices: () => [{ lang: 'es-PE' }], speak(u) { this.utterance = u; } };
global.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; } };
let now = 0;
global.performance = { now: () => now };
const storage = new Map();
global.localStorage = { getItem: k => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v) };
const owners = new Set();
let frame, amplitude = 128, tracksStopped = 0;
global.window = {
  SpeechRecognition: Recognition, speechSynthesis: synth,
  smartrestoVoice: { acquire(owner, ready) { owners.add(owner); ready?.(); }, release(owner) { owners.delete(owner); } },
  navigator: { mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop() { tracksStopped++; } }] }) } },
  AudioContext: class {
    resume() { return Promise.resolve(); }
    close() { return Promise.resolve(); }
    createAnalyser() { return { fftSize: 256, getByteTimeDomainData(samples) { samples.fill(amplitude); } }; }
    createMediaStreamSource() { return { connect() {} }; }
  },
  requestAnimationFrame(f) { frame = f; return 1; }, cancelAnimationFrame() { frame = null; },
  addEventListener: (k, f) => { listeners[k] = f; }
};
const source = require('node:fs').readFileSync(require.resolve('../static/js/copilot.js'), 'utf8');
require('node:vm').runInThisContext(source.replace(/\}\)\(\);\s*$/, 'globalThis.voiceTest = { readReply }; })();'));
const el = id => elements['copilot-' + id];
const result = (text, final) => { const r = [{ transcript: text }]; r.isFinal = final; return r; };
el('voice').emit('click');
assert.equal(rec.continuous, true);
assert.equal(rec.interimResults, true);
rec.handlers.result({ resultIndex: 0, results: [result('hola', false)] });
rec.handlers.result({ resultIndex: 0, results: [result('hola mundo', true)] });
assert.equal(el('message').value, 'hola mundo');
rec.handlers.end(); flush();
assert.equal(rec.starts, 2);
rec.handlers.result({ resultIndex: 0, results: [result('terminar conversacion', true)] });
assert.equal(el('message').value, 'hola mundo');
assert.equal(el('question').submitted, 1);
rec.handlers.end();
el('voice').emit('click');
rec.handlers.error({ error: 'not-allowed' });
rec.handlers.end(); flush();
assert.equal(rec.starts, 3);
el('voice').emit('click');
rec.handlers.result({ resultIndex: 0, results: [result('otra consulta', false)] });
el('voice-stop').emit('click');
assert.equal(el('question').submitted, 2);
rec.handlers.end();
el('message').value = '';
el('voice').emit('click');
assert.equal(owners.has('copilot-dictation'), true);
(async () => {
  await Promise.resolve(); await Promise.resolve();
  now = 1000; amplitude = 140; frame();
  rec.handlers.result({ resultIndex: 0, results: [result('nuevo turno', false)] });
  now = 2999; flush();
  assert.equal(el('question').submitted, 2, 'not before 2000ms');
  amplitude = 140; frame();
  now = 4000; flush();
  assert.equal(el('question').submitted, 2, 'real amplitude postpones submission');
  amplitude = 128; frame();
  now = 4999; flush();
  assert.equal(el('question').submitted, 3, 'interim transcript sends after silence');
  rec.handlers.result({ resultIndex: 0, results: [result('audio antiguo', true)] });
  rec.handlers.end(); flush();
  assert.equal(el('message').value, 'nuevo turno', 'late result cannot rewrite sent turn');
  el('message').value = ''; now = 6000; flush();
  now = 9000; flush();
  assert.equal(el('question').submitted, 3, 'empty resumed session never sends old buffer');
  let completed = false;
  voiceTest.readReply('respuesta hablada', () => { completed = true; });
  assert.equal(synth.utterance.text, 'respuesta hablada', 'default speaks without opt-in');
  assert.equal(owners.has('copilot-audio'), true);
  rec.handlers.result({ resultIndex: 0, results: [result('eco del TTS', true)] });
  assert.equal(el('message').value, '', 'TTS is not input');
  rec.handlers.end();
  synth.utterance.onend(); flush();
  assert.equal(completed, true);
  assert.equal(owners.has('copilot-audio'), false);
  assert.equal(owners.has('copilot-dictation'), true, 'conversation resumes after reply');
  el('read').emit('click');
  assert.equal(storage.get('smartresto:copilot-auto-voice'), 'false', 'default reading is enabled and opt-out persists');
  synth.utterance = null;
  voiceTest.readReply('solo texto', () => {});
  assert.equal(synth.utterance, null, 'explicit false suppresses automatic TTS');
  el('read').emit('click');
  el('message').value = '';
  documentEvents['smartresto:copilot-wake']({ detail: { transcript: 'abre pedidos' } });
  assert.match(synth.utterance.text, /^(Buenos días|Buenas tardes|Buenas noches), Nancy real\. ¿Qué desea hacer hoy\?$/);
  const greetingUtterance = synth.utterance;
  const startsBeforeGreeting = rec.starts;
  rec.handlers.result({ resultIndex: 0, results: [result('eco saludo', true)] });
  assert.equal(el('message').value, 'abre pedidos');
  assert.equal(rec.starts, startsBeforeGreeting, 'micro waits for greeting end');
  documentEvents['smartresto:copilot-wake']({ detail: {} });
  assert.equal(synth.utterance, greetingUtterance, 'in-flight greeting not duplicated');
  rec.handlers.end(); greetingUtterance.onend();
  assert.equal(rec.starts, startsBeforeGreeting + 1);
  assert.equal(el('message').value, 'abre pedidos', 'wake intent survives greeting');
  listeners.pagehide(); flush();
  assert.ok(rec.aborts > 0);
  assert.ok(tracksStopped > 0);
  assert.equal(timers.size, 0);
  console.log('PASS: indexed transcripts, command, permission stop, explicit send, 2000ms silence, RMS activity, stale/empty protection, preference, global ownership, cleanup');
})().catch(error => { console.error(error); process.exitCode = 1; });
