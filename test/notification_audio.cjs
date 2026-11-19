const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/notification-feed.js', 'utf8');
const storage = new Map();
let sounds = 0, closes = 0, disconnects = 0, pending = Promise.resolve();
const locks = {request: (_key, callback) => { pending = pending.then(callback); return pending; }};
function tab() {
  const events = {}, listeners = {}, nodes = [];
  const badge = {textContent: '', hidden: true};
  const script = {dataset: {user: '1', role: 'business_owner', feed: '/feed'}};
  const make = () => { const n = {setAttribute() {}, after() {}, addEventListener: (name, cb) => { n[name] = cb; }}; nodes.push(n); return n; };
  let rows = [{id: 10, read: false, type: 'order'}];
  const Audio = class {
    state = 'running'; currentTime = 0; destination = {};
    resume() { this.state = 'running'; return Promise.resolve(); }
    suspend() { this.state = 'suspended'; return Promise.resolve(); }
    close() { closes++; return Promise.resolve(); }
    createGain() { return {gain: {setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {}}, connect() {}, disconnect() { disconnects++; }}; }
    createOscillator() { return {frequency: {setValueAtTime() {}}, connect() {}, disconnect() { disconnects++; }, start() { sounds++; }, stop() { this.onended(); }}; }
  };
  const window = {AudioContext: Audio, addEventListener: (name, fn) => { events[name] = fn; }, dispatchEvent() {}};
  const document = {currentScript: script, hidden: false, createElement: make,
    querySelector: () => ({append() {}}), querySelectorAll: () => [badge],
    addEventListener: (name, fn) => { listeners[name] = fn; }};
  const sandbox = {window, document, navigator: {locks}, localStorage: {
    getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value)},
    AbortController, CustomEvent: class {}, setTimeout: cb => { sandbox.next = cb; return 1; }, clearTimeout() {},
    fetch: async () => ({ok: true, status: 200, json: async () => ({notifications: rows, unread_count: rows.length})})};
  vm.runInNewContext(source, sandbox);
  return {sandbox, events, listeners, nodes, badge, document, setRows: value => { rows = value; }};
}
const flush = async () => { for (let i = 0; i < 10; i++) await Promise.resolve(); };
(async () => {
  const a = tab(), b = tab();
  await flush(); assert.equal(sounds, 0, 'history must be silent');
  await a.nodes[0].click(); await b.nodes[0].click();
  a.setRows([{id: 11, read: false, type: 'order'}]);
  b.setRows([{id: 11, read: false, type: 'order'}]);
  await Promise.all([a.sandbox.next(), b.sandbox.next()]); await pending;
  assert.equal(sounds, 1, 'same id across tabs must sound once');
  await a.sandbox.next(); assert.equal(sounds, 1);
  assert.equal(disconnects, 2, 'audio nodes must disconnect');
  await a.nodes[0].click();
  a.setRows([{id: 12, read: false}]); await a.sandbox.next();
  assert.equal(sounds, 1, 'mute must suppress audio');
  a.events.pagehide(); b.events.pagehide(); assert.equal(closes, 2);
  assert.equal(a.badge.textContent, '1');
  console.log('PASS: silent history, gesture, mute, cross-tab id dedup, audio cleanup, pagehide');
})().catch(error => { console.error(error); process.exitCode = 1; });
