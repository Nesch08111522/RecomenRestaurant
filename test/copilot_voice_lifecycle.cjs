const assert = require('node:assert/strict');
const elements = {};
class Element {
  constructor() { this.handlers = {}; this.value = ''; this.checked = true; }
  addEventListener(k, f) { (this.handlers[k] ??= []).push(f); }
  emit(k, e = {}) { for (const f of this.handlers[k] || []) f(e); }
  setAttribute() {}
  querySelectorAll() { return []; }
  querySelector() { return new Element(); }
  insertAdjacentText() {}
  requestSubmit() { this.submitted = (this.submitted || 0) + 1; }
}
for (const id of ['question', 'status', 'conversation', 'message', 'preview', 'new', 'voice', 'voice-stop', 'read', 'audio-stop', 'cancel', 'confirm', 'mode-help']) elements['copilot-' + id] = new Element();
global.document = { getElementById: id => elements[id] || null, querySelectorAll: () => [{ checked: true, value: 'basic', addEventListener() {} }] };
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
global.window = { SpeechRecognition: Recognition, speechSynthesis: synth, addEventListener: (k, f) => { listeners[k] = f; } };
require('../static/js/copilot.js');
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
listeners.pagehide(); flush();
assert.ok(rec.aborts > 0);
assert.equal(rec.starts, 4);
console.log('PASS: continuous restart, indexed interim/final, command removal, automatic submit, permission stop, explicit stop, cleanup');
