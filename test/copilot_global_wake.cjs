const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(require.resolve('../static/js/copilot-wake.js'), 'utf8');
function harness(saved = null, supported = true, copilot = false, anonymous = false) {
  const timers = new Map(), events = {}, windowEvents = {}, elements = {};
  let serial = 0;
  class Element {
    constructor() { this.handlers = {}; this.dataset = { copilotUrl: '/copilot' }; }
    addEventListener(k, f) { this.handlers[k] = f; }
    emit(k) { this.handlers[k](); }
  }
  for (const id of ['sr-wake', 'sr-wake-toggle', 'sr-wake-enable', 'sr-wake-status']) elements[id] = new Element();
  if (anonymous) delete elements['sr-wake'];
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
let h = harness('true', true, false, true);
assert.equal(h.rec, undefined, 'anonymous page creates no recognizer');
assert.equal(h.window.smartrestoVoice, undefined, 'anonymous page installs no voice runtime');
assert.equal(h.timers.size, 0);
h = harness();
assert.equal(h.elements['sr-wake-toggle'].checked, true);
assert.equal(h.rec.starts, 0, 'preference does not grant permission');
h.elements['sr-wake-enable'].emit('click'); h.rec.emit('start');
assert.equal(h.rec.starts, 1);
h.rec.emit('end'); h.flush(); assert.equal(h.rec.starts, 2);
h.wake('hola smart copilot abre pedidos');
assert.equal(h.window.destination, undefined, 'wait for microphone release');
h.rec.emit('end'); assert.equal(h.window.destination, 'https://test.local/copilot?voice=1&voice_intent=abre+pedidos');
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
h = harness(); h.elements['sr-wake-enable'].emit('click');
let firstReady = 0, secondReady = 0;
h.window.smartrestoVoice.acquire('first', () => firstReady++);
h.window.smartrestoVoice.acquire('second', () => secondReady++);
h.rec.emit('end');
assert.equal(firstReady, 1, 'second acquisition must not overwrite pending callback');
assert.equal(secondReady, 1);
for (const phrase of ['HOLA, SMART COPILOT', 'hola Smart Resto Copilot', 'hola copilot']) {
  h = harness(); h.elements['sr-wake-enable'].emit('click');
  const interim = [{ transcript: phrase }]; interim.isFinal = false;
  h.rec.emit('result', { resultIndex: 0, results: [interim] });
  assert.equal(h.rec.aborts, 0, 'interim alone cannot navigate');
  h.wake(phrase); h.rec.emit('end');
  assert.equal(h.window.destination, 'https://test.local/copilot?voice=1');
}
const shell = fs.readFileSync(require.resolve('../static/js/shell.js'), 'utf8');
const accountSource = shell.slice(shell.indexOf("        const account = document.querySelector('[data-account-toggle]');"), shell.indexOf('        // Private navigation owns'));
const handlers = {}, lifecycle = {};
let focused;
const container = {};
const link = { focus() { focused = link; } };
const account = { addEventListener(k, f) { handlers['account:' + k] = f; }, setAttribute(k, v) { this[k] = v; }, focus() { focused = account; } };
const options = { hidden: true, querySelector() { return link; }, addEventListener(k, f) { handlers['options:' + k] = f; } };
const doc = { activeElement: { closest() { return null; } }, querySelector(s) { return s === '[data-account-toggle]' ? account : null; }, getElementById() { return options; }, addEventListener(k, f) { handlers[k] = f; } };
vm.runInNewContext(accountSource, { document: doc, window: { addEventListener(k, f) { lifecycle[k] = f; } }, Element: class {} , queueMicrotask: f => f() });
handlers['account:click']();
assert.equal(options.hidden, false); assert.equal(focused, link); assert.equal(account['aria-expanded'], 'true');
let prevented = false;
handlers.keydown({ key: 'Escape', preventDefault() { prevented = true; }, stopImmediatePropagation() {} });
assert.equal(prevented, true); assert.equal(options.hidden, true); assert.equal(focused, account);
handlers['account:click'](); handlers.click({ target: { closest() { return container; } } }); assert.equal(options.hidden, false);
handlers.click({ target: { closest() { return null; } } }); assert.equal(options.hidden, true);
handlers['account:click'](); handlers['options:focusout']({relatedTarget: null}); assert.equal(options.hidden, false);
handlers['account:click'](); lifecycle.pagehide(); assert.equal(options.hidden, true);
console.log('PASS shared account dropdown: first-link focus, Escape restore, inside/outside click, focusout, pagehide');
console.log('PASS global wake: default, permission gesture, persistence, phrases, navigation/event, exclusive dictation/TTS, denial, visibility, cleanup, duplicate guard, unsupported');
