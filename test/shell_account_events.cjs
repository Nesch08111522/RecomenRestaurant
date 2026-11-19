const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const events = new Map();
class Element {
  constructor(interactive = false) { this.interactive = interactive; this.parentElement = null; }
  closest(selector) { return this.interactive && /a\[href\]|private-account/.test(selector) ? this : null; }
  focus() { document.activeElement = this; }
}
const link = new Element(true), account = new Element(true);
account.setAttribute = () => {};
account.addEventListener = (type, fn) => { account[type] = fn; };
const options = {hidden: true, querySelector: () => link, addEventListener(type, fn) { this[type] = fn; }};
const classes = {add() {}, remove() {}, contains: () => true};
const document = {
  documentElement: {classList: classes}, body: {classList: classes},
  querySelectorAll: () => [], querySelector: selector => selector === '[data-account-toggle]' ? account : null,
  getElementById: () => options,
  scrollingElement: {scrollHeight: 1000, clientHeight: 100, scrollWidth: 100, clientWidth: 100,
    scrollLeft: 0, scrollTop: 0, setPointerCapture() {}, scrollTo() {}},
  addEventListener(type, fn, capture) { if (!events.has(type)) events.set(type, []); events.get(type).push({fn, capture}); }
};
const window = {addEventListener() {}, getSelection: () => ({removeAllRanges() {}})};
const source = process.env.SR_BASELINE
  ? require('node:child_process').execFileSync('git', ['show', 'HEAD:static/js/shell.js'], {encoding: 'utf8'})
  : fs.readFileSync(require.resolve('../static/js/shell.js'), 'utf8');
vm.runInNewContext(source, {
  document, window, Element, queueMicrotask: fn => fn(), localStorage: {getItem: () => null},
  getComputedStyle: () => ({overflowY: 'visible', overflowX: 'visible'})
});
function emit(type, target, extra = {}) {
  const event = {target, detail: 1, pointerType: 'mouse', button: 0, buttons: 1, pointerId: 1,
    clientX: 0, clientY: 0, defaultPrevented: false, stopped: false,
    preventDefault() { this.defaultPrevented = true; }, stopImmediatePropagation() { this.stopped = true; }, ...extra};
  for (const {fn} of [...(events.get(type) || [])].sort((a, b) => Number(b.capture) - Number(a.capture))) {
    fn(event); if (event.stopped) break;
  }
  return event;
}
emit('DOMContentLoaded', link);
let checks = 0;
for (const pointerType of ['mouse', 'touch', 'pen']) {
  for (let destination = 0; destination < 3; destination++) {
    account.click();
    emit('pointerdown', link, {pointerType});
    emit('pointermove', link, {pointerType, clientY: 20});
    options.focusout({relatedTarget: null});
    assert.equal(options.hidden, false);
    emit('pointerup', link, {pointerType});
    const click = emit('click', link);
    assert.equal(click.defaultPrevented, false); assert.equal(click.stopped, false); checks++;
    options.hidden = true;
  }
}
const plain = new Element();
emit('pointerdown', plain); emit('pointermove', plain, {clientY: 30}); emit('pointerup', plain);
assert.equal(emit('click', link).defaultPrevented, false); checks++;
options.hidden = false; options.focusout({relatedTarget: plain}); assert.equal(options.hidden, true); checks++;
console.log(`PASS ${checks} actual shell event scenarios (mouse/touch/pen, null focus target, stale drag, keyboard focus exit)`);
