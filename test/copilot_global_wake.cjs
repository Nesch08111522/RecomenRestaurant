const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(require.resolve('../static/js/copilot-wake.js'), 'utf8');
function harness(saved = null, supported = true, copilot = false) {
  const timers = new Map(), events = {}, windowEvents = {}, elements = {};
  let serial = 0;
  class Element {
    constructor() { this.handlers = {}; this.dataset = { copilotUrl: '/copilot' }; }
    addEventListener(k, f) { this.handlers[k] = f; }
    emit(k) { this.handlers[k](); }
  }
  for (const id of ['sr-wake', 'sr-wake-toggle', 'sr-wake-enable', 'sr-wake-status']) elements[id] = new Element();
  if (copilot) elements['copilot-question'] = new Element();
  let rec;
  class Recognition {
    constructor() { rec = this; this.handlers = {}; this.starts = 0; this.aborts = 0; }
    addEventListener(k, f) { this.handlers[k] = f; }
    start() { this.starts++; }
    abort() { this.aborts++; }
    emit(k, e = {}) { this.handlers[k](e); }
  }
  const document = { hidden: false, getElementById: id => elements[id], addEventListener: (k, f) => { events[k] = f; }, dispatchEvent: e => { document.lastEvent = e; } };
  const window = { SpeechRecognition: supported ? Recognition : null, location: { origin: 'https://test.local', assign: url => { window.destination = url; } }, addEventListener: (k, f) => { windowEvents[k] = f; } };
  const localStorage = { getItem: () => saved, setItem: (k, value) => { saved = value; } };
  const context = vm.createContext({ window, document, localStorage, URL, CustomEvent: class { constructor(type, args) { this.type = type; this.detail = args.detail; } }, setTimeout: f => { timers.set(++serial, f); return serial; }, clearTimeout: id => timers.delete(id) });
  vm.runInContext(source, context);
  const flush = () => { const work = [...timers.values()]; timers.clear(); work.forEach(f => f()); };
  const wake = text => { const r = [{ transcript: text }]; r.isFinal = true; rec.emit('result', { resultIndex: 0, results: [r] }); };
  return { elements, window, document, rec, timers, events, windowEvents, flush, wake, saved: () => saved, context };
}
let h = harness();
assert.equal(h.elements['sr-wake-toggle'].checked, true);
assert.equal(h.rec.starts, 0, 'preference does not grant permission');
h.elements['sr-wake-enable'].emit('click'); h.rec.emit('start');
assert.equal(h.rec.starts, 1);
h.rec.emit('end'); h.flush(); assert.equal(h.rec.starts, 2);
h.wake('hola smart copilot abre pedidos');
assert.equal(h.window.destination, undefined, 'wait for microphone release');
h.rec.emit('end'); assert.equal(h.window.destination, 'https://test.local/copilot?voice=1');
h = harness(null, true, true); h.elements['sr-wake-enable'].emit('click');
h.wake('hola SmartResto Copilot consulta'); h.rec.emit('end');
assert.equal(h.document.lastEvent.type, 'smartresto:copilot-wake');
assert.equal(h.document.lastEvent.detail.transcript, 'consulta');
h = harness(); h.elements['sr-wake-enable'].emit('click');
h.wake('hola smart copiloto'); assert.equal(h.rec.aborts, 0);
let ready = false; h.window.smartrestoVoice.acquire('dictation', () => { ready = true; });
assert.equal(ready, false); h.rec.emit('end'); assert.equal(ready, true);
h.flush(); assert.equal(h.rec.starts, 1);
h.window.smartrestoVoice.acquire('tts'); h.window.smartrestoVoice.release('dictation'); h.flush(); assert.equal(h.rec.starts, 1);
h.window.smartrestoVoice.release('tts'); h.flush(); assert.equal(h.rec.starts, 2);
h.rec.emit('error', { error: 'not-allowed' }); h.rec.emit('end'); h.flush(); assert.equal(h.rec.starts, 2);
h.elements['sr-wake-enable'].emit('click'); assert.equal(h.rec.starts, 3);
h.document.hidden = true; h.events.visibilitychange(); h.rec.emit('end'); h.flush(); assert.equal(h.rec.starts, 3);
h.document.hidden = false; h.events.visibilitychange(); h.flush(); assert.equal(h.rec.starts, 4);
h.elements['sr-wake-toggle'].checked = false; h.elements['sr-wake-toggle'].emit('change');
assert.equal(h.saved(), 'false'); h.rec.emit('end'); h.flush(); assert.equal(h.rec.starts, 4);
h.elements['sr-wake-toggle'].checked = true; h.elements['sr-wake-toggle'].emit('change');
h.windowEvents.pagehide(); h.rec.emit('end'); h.flush(); assert.equal(h.rec.starts, 5);
vm.runInContext(source, h.context); assert.equal(h.rec.starts, 5, 'duplicate script is inert');
h = harness(); h.elements['sr-wake-enable'].emit('click');
for (let i = 0; i < 10; i++) { h.rec.emit('end'); h.flush(); }
assert.equal(h.rec.starts, 6, 'empty restart cycles are bounded');
h = harness('false'); assert.equal(h.elements['sr-wake-toggle'].checked, false);
h = harness(null, false); assert.equal(h.elements['sr-wake-enable'].disabled, true);
console.log('PASS global wake: default, permission gesture, persistence, phrases, navigation/event, exclusive dictation/TTS, denial, visibility, cleanup, duplicate guard, unsupported');
