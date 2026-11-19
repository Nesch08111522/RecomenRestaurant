/* SmartResto · Food Scene (Three.js). Bundled to static/js/auth/food-scene.js with esbuild.
   Real WebGL scene: PerspectiveCamera, PBR GLB, hemisphere + key + rim lights, contact shadow,
   slow rotation, floating, bounded pointer parallax, lazy load, visibility pause, WebP fallback. */
import { Scene, PerspectiveCamera, WebGLRenderer, HemisphereLight, DirectionalLight, SpotLight, Group, Box3, Vector3,
  Mesh, PlaneGeometry, TextureLoader, CircleGeometry, MeshBasicMaterial, CanvasTexture, SRGBColorSpace, ACESFilmicToneMapping, PCFSoftShadowMap, MathUtils, Clock, Color } from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

const reduce = matchMedia('(prefers-reduced-motion: reduce)');
const fine = matchMedia('(pointer: fine)');

function shadowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const ctx = c.getContext('2d'); const g = ctx.createRadialGradient(128, 128, 10, 128, 128, 128);
  g.addColorStop(0, 'rgba(8,24,18,0.55)'); g.addColorStop(1, 'rgba(8,24,18,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, 256, 256);
  const t = new CanvasTexture(c); t.colorSpace = SRGBColorSpace; return t;
}

export function createFoodScene(host, options = {}) {
  const canvas = host.querySelector('canvas');
  const viewport = host.querySelector('.ax-food-canvas') || host;
  const fallback = host.querySelector('[data-scene-fallback]');
  const state = { renderer: null, current: null, loading: null, pointer: { x: 0, y: 0 }, target: { x: 0, y: 0 }, visible: true, raf: 0, disposed: false };
  const showFallback = (reason) => { host.dataset.sceneState = 'fallback'; host.dataset.sceneReason = reason; if (fallback) fallback.hidden = false; canvas.hidden = true; stop(); };
  let renderer;
  try {
    const gl = canvas.getContext('webgl2', { antialias: true, alpha: true, powerPreference: 'low-power' }) || canvas.getContext('webgl', { antialias: true, alpha: true });
    if (!gl) throw new Error('no-webgl');
    renderer = new WebGLRenderer({ canvas, context: gl, antialias: true, alpha: true });
  } catch (error) { showFallback('webgl'); return { setDish: () => {}, dispose: () => {} }; }
  const lowPower = (navigator.hardwareConcurrency || 4) <= 4 || innerWidth < 768;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, lowPower ? 1.25 : 2));
  renderer.outputColorSpace = SRGBColorSpace; renderer.toneMapping = ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = !lowPower; renderer.shadowMap.type = PCFSoftShadowMap;
  canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); showFallback('context-lost'); });

  const scene = new Scene();
  const camera = new PerspectiveCamera(30, 1, 0.1, 50); camera.position.set(0, 2.1, 5.6); camera.lookAt(0, 0.25, 0);
  scene.add(new HemisphereLight(new Color('#fff6e6'), new Color('#0f2a22'), 1.15));
  const key = new DirectionalLight('#ffe9c9', 2.3); key.position.set(3, 5, 3.5); key.castShadow = !lowPower; key.shadow.mapSize.set(1024, 1024); key.shadow.radius = 6; scene.add(key);
  const rim = new SpotLight('#e8b969', 18, 20, 0.7, 0.8); rim.position.set(-4, 3, -3); scene.add(rim);
  const fill = new DirectionalLight('#dfeee8', 0.55); fill.position.set(-3, 1.5, 4); scene.add(fill);
  const contact = new Mesh(new CircleGeometry(1.9, 48), new MeshBasicMaterial({ map: shadowTexture(), transparent: true, depthWrite: false }));
  contact.rotation.x = -Math.PI / 2; contact.position.y = -0.62; scene.add(contact);
  const pivot = new Group(); scene.add(pivot);
  const loader = new GLTFLoader(); const clock = new Clock();

  function resize() {
    const w = viewport.clientWidth || 1, h = viewport.clientHeight || 1;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    const compact = w < 560; camera.position.set(0, compact ? 1.7 : 2.1, compact ? 6.4 : 5.6); camera.lookAt(0, 0.25, 0);
  }
  const ro = new ResizeObserver(() => { resize(); renderOnce(); }); ro.observe(viewport); resize();

  function fit(object) {
    const box = new Box3().setFromObject(object); const size = box.getSize(new Vector3()); const center = box.getCenter(new Vector3());
    const scale = 2.9 / Math.max(size.x, size.z, 0.001); object.scale.setScalar(scale);
    object.position.set(-center.x * scale, -box.min.y * scale - 0.6, -center.z * scale);
    object.traverse((node) => { if (node.isMesh) { node.castShadow = !lowPower; node.receiveShadow = !lowPower; if (node.material && node.material.map) node.material.map.anisotropy = 4; } });
  }
  function disposeObject(object) { object.traverse((n) => { if (n.isMesh) { n.geometry?.dispose(); const mats = Array.isArray(n.material) ? n.material : [n.material]; mats.forEach((m) => { Object.values(m).forEach((v) => v?.isTexture && v.dispose()); m.dispose(); }); } }); }

  function setDish(item) {
    if (state.disposed || !item || !item.model) return Promise.resolve(false);
    if (fallback) { const img = fallback.matches('img') ? fallback : fallback.querySelector('img'); if (img && item.image) { img.src = item.image; img.alt = item.name || ''; } }
    host.dataset.sceneState = 'loading';
    const token = state.loading = {};
    // A photographic relief, not a reconstruction of unseen sides of the dish.
    if (host.dataset.photoRelief === 'true' && item.model_kind !== 'catalog' && item.image) {
      return new Promise(resolve => new TextureLoader().load(item.image, texture => {
        if (state.loading !== token || state.disposed) { texture.dispose(); return resolve(false); }
        texture.colorSpace = SRGBColorSpace;
        const ratio = texture.image.width / texture.image.height;
        const geometry = new PlaneGeometry(3.25, 3.25 / ratio, 40, 40);
        const positions = geometry.attributes.position;
        for (let i = 0; i < positions.count; i++) {
          const x = positions.getX(i), y = positions.getY(i);
          positions.setZ(i, 0.12 * Math.exp(-(x*x + y*y)));
        }
        geometry.computeVertexNormals();
        const next = new Mesh(geometry, new MeshBasicMaterial({map:texture, transparent:true, toneMapped:false}));
        next.rotation.x = -0.32;
        next.userData.enter = 0;
        if (state.current) { pivot.remove(state.current); disposeObject(state.current); }
        state.current = next; pivot.add(next); state.photo = true;
        host.dataset.sceneState = 'ready'; host.dataset.presentation = 'photo-relief';
        canvas.hidden = false; if (fallback) fallback.hidden = true;
        start(); renderOnce(); resolve(true);
      }, undefined, () => { if (state.loading === token) showFallback('image'); resolve(false); }));
    }
    state.photo = false;
    return new Promise((resolve) => {
      loader.load(item.model, (gltf) => {
        if (state.loading !== token || state.disposed) { disposeObject(gltf.scene); return resolve(false); }
        const next = gltf.scene; fit(next);
        const previous = state.current; state.current = next; next.userData.enter = 0;
        pivot.add(next); if (previous) { previous.userData.leaving = true; setTimeout(() => { pivot.remove(previous); disposeObject(previous); }, 900); }
        host.dataset.sceneState = 'ready'; canvas.hidden = false; if (fallback) fallback.hidden = true;
        start(); renderOnce(); resolve(true);
      }, undefined, () => { if (state.loading === token) showFallback('model'); resolve(false); });
    });
  }

  function animate() {
    state.raf = 0;
    if (state.disposed || !state.visible) return;
    const t = clock.getElapsedTime(); const dt = Math.min(clock.getDelta() || 0.016, 0.05);
    state.pointer.x = MathUtils.lerp(state.pointer.x, state.target.x, 0.06); state.pointer.y = MathUtils.lerp(state.pointer.y, state.target.y, 0.06);
    const motion = reduce.matches ? 0 : 1;
    pivot.rotation.y = (state.photo ? motion * Math.sin(t * 0.35) * 0.1 : motion * t * 0.11) + state.pointer.x * 0.22;
    pivot.rotation.x = -0.08 + state.pointer.y * 0.09 + motion * Math.sin(t * 0.7) * 0.015;
    pivot.position.y = motion * Math.sin(t * 0.9) * 0.045;
    contact.scale.setScalar(1 - pivot.position.y * 0.35);
    for (const child of pivot.children) { child.userData.enter = Math.min(1, (child.userData.enter ?? 1) + dt * 1.6); const k = child.userData.leaving ? 1 - child.userData.enter * 0.0 : child.userData.enter; child.traverse((n) => { if (n.isMesh && n.material) { n.material.transparent = k < 1; n.material.opacity = k; } }); }
    renderer.render(scene, camera);
    if (motion || Math.abs(state.pointer.x - state.target.x) > 0.001) state.raf = requestAnimationFrame(animate);
  }
  function start() { if (!state.raf && state.visible) state.raf = requestAnimationFrame(animate); }
  function stop() { if (state.raf) cancelAnimationFrame(state.raf); state.raf = 0; }
  function renderOnce() { if (state.current) renderer.render(scene, camera); }

  const io = new IntersectionObserver(([entry]) => { state.visible = entry.isIntersecting && !document.hidden; state.visible ? start() : stop(); }, { threshold: 0.05 });
  io.observe(host);
  document.addEventListener('visibilitychange', () => { state.visible = !document.hidden; state.visible ? start() : stop(); });
  const area = options.pointerArea || host;
  let drag = null;
  viewport.style.touchAction = 'pan-y';
  viewport.addEventListener('pointerdown', e => { drag = {x:e.clientX, y:e.clientY}; viewport.setPointerCapture(e.pointerId); });
  viewport.addEventListener('pointermove', e => {
    if (!drag) return;
    state.target.x = MathUtils.clamp((e.clientX - drag.x) / 100, -1.5, 1.5);
    state.target.y = MathUtils.clamp((e.clientY - drag.y) / 150, -1, 1); start();
  });
  const release = () => { drag = null; state.target.x = 0; state.target.y = 0; start(); };
  viewport.addEventListener('pointerup', release);
  viewport.addEventListener('pointercancel', release);
  area.addEventListener('pointermove', (e) => {
    if (drag || !fine.matches || reduce.matches) return;
    const r = area.getBoundingClientRect();
    state.target.x = MathUtils.clamp((e.clientX - r.left) / r.width * 2 - 1, -1, 1); state.target.y = MathUtils.clamp((e.clientY - r.top) / r.height * 2 - 1, -1, 1); start();
  }, { passive: true });
  area.addEventListener('pointerleave', () => { state.target.x = 0; state.target.y = 0; start(); });
  reduce.addEventListener('change', () => { reduce.matches ? renderOnce() : start(); });
  host.dataset.sceneState = 'idle';
  return { setDish, dispose() { state.disposed = true; stop(); ro.disconnect(); io.disconnect(); if (state.current) disposeObject(state.current); renderer.dispose(); } };
}

/* Controller: loads selection from the read-only API and rotates between dishes. */
function boot() {
  const host = document.querySelector('[data-food-experience-api]');
  if (!host) return;
  const stage = host.closest('.ax-stage') || host;
  const api = host.dataset.foodExperienceApi; const view = host.dataset.foodView || 'login';
  const title = host.querySelector('[data-dish-name]'), caption = host.querySelector('[data-dish-caption]'), dots = host.querySelector('[data-dish-dots]'), badge = host.querySelector('[data-dish-source]');
  const connection = navigator.connection || {};
  if (connection.saveData) { host.dataset.sceneState = 'fallback'; host.dataset.sceneReason = 'save-data'; return; }
  const sceneApi = createFoodScene(host, { pointerArea: stage });
  let items = [], index = 0, timer = 0;
  const esc = (v) => String(v ?? '');
  function describe(item) {
    if (title) title.textContent = esc(item.name); if (caption) caption.textContent = host.dataset.photoRelief === 'true' && item.model_kind !== 'catalog' ? 'Fotografía con relieve · arrastra para inclinar' : esc(item.caption);
    if (badge) { badge.textContent = item.source === 'catalog' ? (item.model_kind === 'catalog' ? 'Modelo del negocio' : 'Del catálogo') : 'Selección editorial'; badge.hidden = false; }
    if (dots) dots.querySelectorAll('button').forEach((b, i) => { b.setAttribute('aria-pressed', String(i === index)); });
    const link = host.querySelector('[data-dish-link]'); if (link) { link.href = /^\/(?!\/)/.test(item.href || '') ? item.href : '/mercado/'; }
  }
  async function show(i) { index = (i + items.length) % items.length; const item = items[index]; describe(item); await sceneApi.setDish(item); }
  function schedule() { clearInterval(timer); if (items.length > 1 && !reduce.matches) timer = setInterval(() => { if (!document.hidden && host.getBoundingClientRect().bottom > 0 && host.getBoundingClientRect().top < innerHeight) show(index + 1); }, 14000); }
  reduce.addEventListener('change', schedule);
  function render(data) {
    items = Array.isArray(data.items) ? data.items.filter((x) => x && typeof x.model === 'string' && /^\/(?!\/)/.test(x.model)) : [];
    host.dataset.personalized = String(Boolean(data.personalized));
    const note = host.querySelector('[data-dish-note]'); if (note) { note.textContent = data.personalized ? (data.notice || 'Seleccionado según tus gustos y favoritos.') : 'Selección editorial para inspirarte.'; }
    if (dots) { dots.replaceChildren(...items.map((x, i) => { const b = document.createElement('button'); b.type = 'button'; b.setAttribute('aria-label', `Ver ${esc(x.name)}`); b.addEventListener('click', () => { show(i); schedule(); }); return b; })); }
    if (!items.length) { host.dataset.sceneState = 'fallback'; host.dataset.sceneReason = 'empty'; return; }
    show(0); schedule();
  }
  const start = () => fetch(`${api}?view=${encodeURIComponent(view)}`, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
    .then((r) => r.ok ? r.json() : Promise.reject(new Error(String(r.status)))).then(render)
    .catch(() => render({ items: [{ id: 'local', name: host.dataset.fallbackName || 'SmartResto', caption: 'Inspiración gastronómica', model: host.dataset.fallbackModel, image: host.dataset.fallbackImage, source: 'editorial', model_kind: 'reference', href: '/mercado/' }], personalized: false }));
  if ('requestIdleCallback' in window) requestIdleCallback(start, { timeout: 1200 }); else setTimeout(start, 120);
  window.addEventListener('pagehide', () => { clearInterval(timer); sceneApi.dispose(); }, { once: true });
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
