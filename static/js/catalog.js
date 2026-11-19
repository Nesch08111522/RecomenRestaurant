(function () {
  'use strict';

  const app = document.getElementById('catalogApp');
  if (!app) return;
  const state = {
    apiUrl: app.dataset.apiUrl || '',
    restaurantId: app.dataset.restaurantId || '',
    currency: app.dataset.currency || 'S/',
    products: [], drafts: [], categories: [], import: null, recognition: null,
    busy: false, voiceListening: false,
  };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const byId = (id) => document.getElementById(id);
  const text = (value) => String(value ?? '');
  const safe = (value, fallback = '—') => {
    const result = text(value).trim();
    return result || fallback;
  };
  const el = (tag, className, content) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  };
  const icon = (name) => { const node = el('i', `fas fa-${name}`); node.setAttribute('aria-hidden', 'true'); return node; };

  function notice(message, kind = 'info') {
    const box = byId('catalogNotice');
    if (!box) return;
    box.className = `catalog-notice is-${kind}`;
    box.textContent = text(message);
    box.hidden = !message;
    if (message) box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  async function request(url, options = {}) {
    if (!url) throw new Error('Selecciona un restaurante antes de continuar.');
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    let payload = {};
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok) throw new Error(payload.error || payload.message || `No se pudo completar la operación (${response.status}).`);
    return payload;
  }

  function asArray(value) { return Array.isArray(value) ? value : []; }
  function lines(value) { return text(value).split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean); }
  function parseJson(value, label) {
    const raw = text(value).trim();
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) throw new Error(`${label} debe ser una lista JSON.`);
      return parsed;
    } catch (error) { throw new Error(`${label}: ${error.message || 'JSON inválido.'}`); }
  }
  function nullablePrice(value) {
    const raw = text(value).trim();
    if (!raw) return null;
    const number = Number(raw);
    if (!Number.isFinite(number) || number < 0 || !/^\d+(\.\d{1,2})?$/.test(raw)) throw new Error('El precio debe ser un decimal positivo con hasta 2 decimales o quedar vacío.');
    return raw;
  }
  function productTypeLabel(type) { return ({ plato: 'Plato', bebida: 'Bebida', postre: 'Postre' }[type] || safe(type, 'Producto')); }
  function availabilityLabel(value) { return ({ available: 'Disponible', sold_out: 'Agotado', paused: 'Pausado' }[value] || 'Sin estado'); }
  function productId(product) { return product && (product.id ?? product.product_id); }
  function priceLabel(value) {
    if (value === null || value === undefined || text(value).trim() === '') return 'Precio por definir';
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${state.currency} ${numeric.toFixed(2)}` : 'Precio por definir';
  }
  function productArray(product, key) { return asArray(product && product[key]); }

  function seedState() {
    const seed = byId('catalogSeed');
    if (!seed) return;
    try {
      const data = JSON.parse(seed.textContent || '{}');
      state.products = asArray(data.products);
      state.drafts = asArray(data.drafts);
      state.categories = asArray(data.categories);
    } catch (_) { notice('No se pudo leer la carga inicial del catálogo.', 'warning'); }
  }

  function updateMetrics() {
    const available = state.products.filter((item) => (item.availability || (item.is_available === false ? 'sold_out' : 'available')) === 'available').length;
    const confirmed = state.products.filter((item) => item.ingredients_confirmed && item.allergens_confirmed).length;
    const quality = state.products.length ? Math.round((confirmed / state.products.length) * 100) : 0;
    byId('metricPublished').textContent = state.products.length;
    byId('metricDrafts').textContent = state.drafts.length;
    byId('metricAvailable').textContent = available;
    byId('metricQuality').textContent = state.products.length ? `${quality}%` : '—';
    byId('metricPublishedHint').textContent = state.products.length ? 'En este restaurante' : 'Aún sin productos';
    byId('productCount').textContent = state.products.length;
  }

  function renderProducts() {
    const list = byId('productsList');
    const empty = byId('productsEmpty');
    const query = text(byId('productSearch')?.value).toLowerCase().trim();
    const type = byId('productTypeFilter')?.value || 'all';
    list.replaceChildren();
    const filtered = state.products.filter((product) => {
      const matchesQuery = !query || [product.name, product.description, product.category].some((value) => text(value).toLowerCase().includes(query));
      return matchesQuery && (type === 'all' || product.product_type === type);
    });
    empty.hidden = filtered.length > 0;
    filtered.forEach((product) => {
      const availability = product.availability || (product.is_available === false ? 'sold_out' : 'available');
      const card = el('article', 'catalog-product-card');
      card.setAttribute('role', 'listitem');
      card.dataset.availability = availability;
      const top = el('div', 'catalog-product-top');
      const typeNode = el('span', 'catalog-product-type', productTypeLabel(product.product_type));
      const availabilityNode = el('span', `catalog-availability catalog-availability--${availability}`);
      availabilityNode.append(icon(availability === 'available' ? 'circle-check' : availability === 'sold_out' ? 'triangle-exclamation' : 'pause'));
      availabilityNode.append(document.createTextNode(availabilityLabel(availability)));
      top.append(typeNode, availabilityNode);
      card.append(top);
      card.append(el('h3', '', safe(product.name, 'Producto sin nombre')));
      card.append(el('p', 'catalog-product-description', safe(product.description, 'Añade una descripción breve desde el editor.')));
      const meta = el('div', 'catalog-product-meta');
      meta.append(el('span', 'catalog-price', priceLabel(product.price)));
      if (product.category) meta.append(el('span', 'catalog-tag', safe(product.category)));
      if (product.portion) meta.append(el('span', 'catalog-tag', safe(product.portion)));
      card.append(meta);
      const actions = el('div', 'catalog-product-actions');
      const edit = el('button', 'catalog-mini-button', 'Editar'); edit.type = 'button'; edit.dataset.action = 'edit'; edit.dataset.id = text(productId(product)); edit.prepend(icon('pen'));
      const toggle = el('button', 'catalog-mini-button', availability === 'available' ? 'Cambiar estado' : 'Hacer disponible'); toggle.type = 'button'; toggle.dataset.action = 'availability'; toggle.dataset.id = text(productId(product)); toggle.dataset.next = availability === 'available' ? 'paused' : 'available'; toggle.prepend(icon(availability === 'available' ? 'pause' : 'circle-check'));
      actions.append(edit, toggle); card.append(actions); list.append(card);
    });
    updateMetrics();
  }

  function renderDrafts() {
    const list = byId('draftsList');
    const empty = byId('draftsEmpty');
    list.replaceChildren();
    empty.hidden = state.drafts.length > 0;
    state.drafts.forEach((draft) => {
      const card = el('article', 'catalog-draft-card');
      const copy = el('div', 'catalog-draft-copy');
      const product = draft.product || draft;
      copy.append(el('strong', '', safe(product.name, 'Borrador sin nombre')));
      copy.append(el('span', '', `${productTypeLabel(product.product_type)} · ${safe(draft.status, 'pendiente')} · edita antes de confirmar`));
      const actions = el('div', 'catalog-draft-actions');
      const edit = el('button', 'catalog-button catalog-button--soft', 'Editar'); edit.type = 'button'; edit.dataset.action = 'edit-draft'; edit.dataset.id = text(draft.id || product.id); edit.prepend(icon('pen'));
      const confirm = el('button', 'catalog-button catalog-button--primary', 'Publicar'); confirm.type = 'button'; confirm.dataset.action = 'confirm-draft'; confirm.dataset.id = text(draft.id); confirm.prepend(icon('circle-check'));
      actions.append(edit, confirm); card.append(copy, actions); list.append(card);
    });
    updateMetrics();
  }

  function setValue(id, value) { const node = byId(id); if (node) node.value = value ?? ''; }
  function setChecked(id, value) { const node = byId(id); if (node) node.checked = Boolean(value); }
  function fillForm(product = {}, draftId = '') {
    setValue('editingProductId', productId(product) || '');
    setValue('editingDraftId', draftId || '');
    const seasons = productArray(product, 'seasons');
    for (const input of byId('productForm').querySelectorAll('[name="seasons"]')) {
      input.checked = seasons.some(season => text(season).toLowerCase() === input.value.toLowerCase());
    }
    setValue('productName', product.name); setValue('productType', product.product_type || 'plato'); setValue('productCategory', product.category); setValue('productSubcategory', product.subcategory); setValue('productDescription', product.description); setValue('productPrice', product.price); setValue('productPortion', product.portion); setValue('productAvailability', product.availability || (product.is_available === false ? 'sold_out' : 'available')); setValue('productMenuType', product.menu_type || 'carta'); setValue('productMenuDate', product.menu_date); setValue('productMealTime', product.meal_time || 'almuerzo'); setChecked('productPromotional', product.promotional); setValue('productPromoText', product.promo_text); setValue('productIngredients', productArray(product, 'ingredients').join('\n')); setValue('productProbableIngredients', productArray(product, 'probable_ingredients').join('\n')); setValue('productAllergens', product.allergens === null || product.allergens === undefined ? '' : productArray(product, 'allergens').join('\n')); setChecked('ingredientsConfirmed', product.ingredients_confirmed); setChecked('rightsConfirmed', product.rights_confirmed); setChecked('allergensConfirmed', product.allergens_confirmed); setValue('productRecipe', productArray(product, 'recipe').length ? JSON.stringify(product.recipe, null, 2) : ''); setValue('productVariants', productArray(product, 'variants').length ? JSON.stringify(product.variants, null, 2) : ''); setValue('productAddons', productArray(product, 'addons').length ? JSON.stringify(product.addons, null, 2) : ''); setValue('productTags', productArray(product, 'tags').join('\n')); setValue('productImages', productArray(product, 'images').join('\n')); setValue('productVideos', productArray(product, 'videos').join('\n'));
    byId('editorTitle').textContent = productId(product) ? 'Editar producto' : 'Nuevo producto';
    byId('saveProductButton').querySelector('span').textContent = productId(product) ? 'Guardar cambios' : 'Guardar borrador';
    byId('productEditorPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function readForm() {
    const name = text(byId('productName').value).trim();
    if (!name) throw new Error('Escribe un nombre para el producto.');
    const videos = lines(byId('productVideos').value);
    if (videos.some((url) => !/^https:\/\/.*\.(mp4|webm)(\?.*)?$/i.test(url))) throw new Error('Cada video debe ser una URL HTTPS con extensión .mp4 o .webm.');
    const price = nullablePrice(byId('productPrice').value);
    const product = {
      name, product_type: byId('productType').value, category: text(byId('productCategory').value).trim() || ({plato:'Fondo',bebida:'Bebida',postre:'Postre'}[byId('productType').value]), subcategory: text(byId('productSubcategory').value).trim(), description: text(byId('productDescription').value).trim(), price, portion: text(byId('productPortion').value).trim(), ingredients: lines(byId('productIngredients').value), probable_ingredients: lines(byId('productProbableIngredients').value), allergens: byId('allergensConfirmed').checked ? lines(byId('productAllergens').value) : null, allergens_confirmed: byId('allergensConfirmed').checked, ingredients_confirmed: byId('ingredientsConfirmed').checked, recipe: parseJson(byId('productRecipe').value, 'Receta'), variants: parseJson(byId('productVariants').value, 'Variantes'), addons: parseJson(byId('productAddons').value, 'Adicionales'), tags: lines(byId('productTags').value), images: lines(byId('productImages').value), videos, availability: byId('productAvailability').value, promotional: byId('productPromotional').checked, promo_text: text(byId('productPromoText').value).trim(), menu_type: byId('productMenuType').value, menu_date: byId('productMenuDate').value || null, meal_time: byId('productMealTime').value, rights_confirmed: byId('rightsConfirmed').checked,
      seasons: Array.from(byId('productForm').querySelectorAll('[name="seasons"]:checked'), input => input.value),
    };
    return product;
  }

  async function saveProduct(event) {
    event.preventDefault();
    if (state.busy) return;
    try {
      const product = readForm();
      state.busy = true; setButtonBusy(byId('saveProductButton'), true, 'Guardando…');
      const id = text(byId('editingProductId').value).trim();
      const draftId = text(byId('editingDraftId').value).trim();
      const payload = { product }; if (id && !draftId) payload.product_id = Number(id);
      const endpoint = draftId ? `${state.apiUrl}/drafts/${encodeURIComponent(draftId)}` : `${state.apiUrl}/draft`;
      const method = draftId ? 'PUT' : 'POST';
      const result = await request(endpoint, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const draft = result.draft || { id: result.id, product: result.product || product, status: 'pending' };
      state.drafts = [draft, ...state.drafts.filter((item) => text(item.id) !== text(draft.id))];
      renderDrafts(); fillForm(draft.product, draft.id); notice('Borrador guardado. Revisa las confirmaciones antes de publicarlo.', 'success');
    } catch (error) { notice(error.message, 'error'); } finally { state.busy = false; setButtonBusy(byId('saveProductButton'), false, text(byId('editingDraftId').value).trim() ? 'Guardar cambios' : 'Guardar borrador'); }
  }

  function setButtonBusy(button, busy, label) { if (!button) return; button.disabled = busy; if (label) { const span = button.querySelector('span'); if (span) span.textContent = label; } }
  function resetForm() { fillForm({}); byId('productForm').reset(); setValue('productType', 'plato'); setValue('productAvailability', 'available'); setValue('productMenuType', 'carta'); setValue('productMealTime', 'almuerzo'); byId('editorTitle').textContent = 'Nuevo producto'; byId('saveProductButton').querySelector('span').textContent = 'Guardar borrador'; }

  async function loadCatalog() {
    if (!state.apiUrl) { updateMetrics(); renderProducts(); renderDrafts(); return; }
    try {
      const data = await request(state.apiUrl);
      state.products = asArray(data.products); state.drafts = asArray(data.drafts); state.categories = asArray(data.categories);
      updateCategoryOptions(state.categories); renderProducts(); renderDrafts();
    } catch (error) { renderProducts(); renderDrafts(); notice(error.message, 'warning'); }
  }
  function updateCategoryOptions(categories) {
    const select = byId('productCategory'); if (!select || !categories.length) return;
    const current = select.value; select.replaceChildren(); select.append(el('option', '', 'Sin categoría')); categories.forEach((category) => { const option = el('option', '', typeof category === 'object' ? (category.name || category.label || category.value) : category); option.value = typeof category === 'object' ? (category.name || category.value || category.label) : category; select.append(option); }); select.value = current;
  }

  async function updateAvailability(id, next) {
    try { const result = await request(`${state.apiUrl}/products/${encodeURIComponent(id)}/availability`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ availability: next }) }); const updated = result.product || result; const item = state.products.find((product) => text(productId(product)) === text(id)); if (item) { item.availability = updated.availability || next; item.is_available = next === 'available'; } renderProducts(); notice(`Disponibilidad actualizada: ${availabilityLabel(next)}.`, 'success'); } catch (error) { notice(error.message, 'error'); }
  }

  async function confirmDraft(id, button) {
    if (!id || state.busy) return;
    if (button) button.disabled = true;
    if (!window.confirm('Publicar este borrador tras la validación?')) { if (button) button.disabled = false; return; }
    try { state.busy = true; const result = await request(`${state.apiUrl}/drafts/${encodeURIComponent(id)}/confirm`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true }) }); const product = result.product || result.draft?.product; if (product) state.products = [product, ...state.products.filter((item) => text(productId(item)) !== text(productId(product)))]; state.drafts = state.drafts.filter((item) => text(item.id) !== text(id)); renderProducts(); renderDrafts(); notice('Producto publicado tras validar el borrador.', 'success'); } catch (error) { notice(error.message, 'error'); } finally {state.busy = false; if (button) button.disabled = false; }
  }

  async function uploadPhoto(event) { event.preventDefault(); const input = byId('photoInput'); if (!input.files.length || state.busy) { notice('Elige una imagen antes de analizar.', 'warning'); return; } const form = new FormData(); form.append('file', input.files[0]); try { state.busy = true; setButtonBusy(byId('photoButton'), true, 'Analizando…'); const result = await request(`${state.apiUrl}/photo`, { method: 'POST', body: form }); const draft = result.draft; if (draft) { const photoProduct = { ...(draft.product || draft), ingredients: [], probable_ingredients: asArray((draft.product || draft).probable_ingredients || (draft.product || draft).ingredients), allergens: null, ingredients_confirmed: false, allergens_confirmed: false, price: null }; const safeDraft = { ...draft, product: photoProduct }; state.drafts = [safeDraft, ...state.drafts]; renderDrafts(); fillForm(photoProduct, draft.id); } notice(result.notice || 'Foto convertida en borrador. Revisa ingredientes probables y confirma manualmente.', 'success'); } catch (error) { notice(error.message, 'error'); } finally { state.busy = false; setButtonBusy(byId('photoButton'), false, 'Analizar foto'); } }

  function initVoice() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const supportText = byId('voiceSupportText');
    if (!Recognition) { supportText.textContent = 'Este navegador no ofrece SpeechRecognition. Usa la transcripción manual; no se suben archivos de audio al backend.'; byId('voiceButton').disabled = true; return; }
    const recognition = new Recognition(); recognition.lang = 'es-PE'; recognition.interimResults = true; recognition.continuous = false; state.recognition = recognition;
    recognition.onstart = () => { state.voiceListening = true; byId('voiceButton').classList.add('is-listening'); byId('voiceButton').querySelector('i').className = 'fas fa-stop'; byId('voiceButton').lastChild.textContent = ' Detener dictado'; byId('voiceState').textContent = 'Escuchando…'; byId('voiceState').classList.add('is-listening'); notice('El navegador está procesando tu voz. Revisa el resultado antes de usarlo.', 'info'); };
    recognition.onresult = (event) => { const transcript = Array.from(event.results).map((result) => result[0].transcript).join(''); byId('voiceTranscript').value = transcript; };
    recognition.onerror = (event) => { byId('voiceState').textContent = `No se pudo escuchar (${event.error}). Puedes escribirlo manualmente.`; notice('El dictado no pudo completarse; la transcripción manual sigue disponible.', 'warning'); };
    recognition.onend = () => { state.voiceListening = false; byId('voiceButton').classList.remove('is-listening'); byId('voiceButton').querySelector('i').className = 'fas fa-microphone'; byId('voiceButton').lastChild.textContent = ' Iniciar dictado'; byId('voiceState').textContent = 'Listo'; byId('voiceState').classList.remove('is-listening'); };
  }
  function toggleVoice() { if (!state.recognition) return; if (state.voiceListening) state.recognition.stop(); else { notice('Se solicitará permiso de micrófono al navegador. No se envía un archivo de audio.', 'info'); state.recognition.start(); } }
  async function sendVoiceDraft() { const sendButton = byId('voiceSendButton'); const transcript = text(byId('voiceTranscript').value).trim(); if (!transcript || state.busy) { notice('Escribe o dicta una descripción antes de crear el borrador.', 'warning'); return; } try { state.busy = true; setButtonBusy(sendButton, true, 'Procesando...'); const result = await request(`${state.apiUrl}/voice`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ transcript, product: byId('productName').value.trim() ? readForm() : {}, product_id: byId('editingProductId').value ? Number(byId('editingProductId').value) : null }) }); if (result.draft) { state.drafts = [result.draft, ...state.drafts]; renderDrafts(); fillForm(result.draft.product || result.draft, result.draft.id); } notice(result.notice || 'La voz creó un borrador editable. Revisa precio e ingredientes.', 'success'); } catch (error) { notice(error.message, 'error'); } finally { state.busy = false; setButtonBusy(sendButton, false, 'Usar como borrador'); } }

  async function importExcel(event) { event.preventDefault(); const input = byId('excelInput'); if (!input.files.length || state.busy) { notice('Selecciona una plantilla .xlsx.', 'warning'); return; } const form = new FormData(); form.append('file', input.files[0]); try { state.busy = true; setButtonBusy(byId('importButton'), true, 'Preparando…'); const result = await request(`${state.apiUrl}/import-preview`, { method: 'POST', body: form }); state.import = result.import || result; renderImportPreview(state.import); notice('Preview listo. Las filas con errores bloquean la confirmación.', 'success'); } catch (error) { notice(error.message, 'error'); } finally { state.busy = false; setButtonBusy(byId('importButton'), false, 'Crear preview'); } }
  function renderImportPreview(importData) { const panel = byId('importPreviewPanel'); panel.hidden = false; const errors = asArray(importData.errors); const warnings = asArray(importData.warnings); const status = text(importData.status || 'pending'); byId('importPreviewStatus').textContent = status; const summary = byId('importSummary'); summary.replaceChildren(); [['Filas', Array.isArray(importData.rows) ? importData.rows.length : (importData.rows ?? 0)], ['Errores', errors.length], ['Advertencias', warnings.length]].forEach(([label, value]) => { const chip = el('span', 'catalog-summary-chip'); chip.append(el('strong', '', text(value)), document.createTextNode(` ${label}`)); summary.append(chip); }); const body = byId('importIssuesBody'); body.replaceChildren(); asArray(importData.rows).forEach(item => { const row = document.createElement('tr'); [item.sheet,item.row,'Datos validados',JSON.stringify(item.data),'Vista previa'].forEach(value => row.append(el('td','',text(value)))); body.append(row); }); [...errors.map((item) => ({ ...item, level: 'error' })), ...warnings.map((item) => ({ ...item, level: 'warning' }))].forEach((issue) => { const row = document.createElement('tr'); row.className = `is-${issue.level}`; ['sheet', 'row', 'field', 'message', 'level'].forEach((key) => { const cell = document.createElement('td'); cell.textContent = key === 'level' ? (issue.level === 'error' ? 'Error' : 'Advertencia') : safe(issue[key], '—'); row.append(cell); }); body.append(row); }); const canConfirm = status === 'pending' && errors.length === 0; const button = byId('confirmImportButton'); button.disabled = !canConfirm; button.dataset.importId = text(importData.id); if (!canConfirm) notice(status !== 'pending' ? 'La importación no está pendiente y no se puede confirmar.' : 'Corrige los errores de la preview antes de confirmar.', 'warning'); }
  async function confirmImport() { const button = byId('confirmImportButton'); const id = button.dataset.importId; if (!id || button.disabled || state.busy) return; if (!window.confirm('Confirmo que revisé las filas, ingredientes y alérgenos declarados y tengo derechos sobre el contenido. Importar todos estos registros?')) return; try { state.busy = true; setButtonBusy(button, true, 'Confirmando…'); const result = await request(`${state.apiUrl}/imports/${encodeURIComponent(id)}/confirm`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true }) }); byId('importPreviewStatus').textContent = result.import?.status || 'confirmed'; button.disabled = true; notice('Importación confirmada. Actualizando catálogo…', 'success'); await loadCatalog(); } catch (error) { notice(error.message, 'error'); } finally { state.busy = false; setButtonBusy(button, false, 'Confirmar importación'); button.disabled = true; } }

  function handleActions(event) { const button = event.target.closest('button[data-action]'); if (!button) return; const id = button.dataset.id; const product = state.products.find((item) => text(productId(item)) === text(id)); if (button.dataset.action === 'edit' && product) fillForm(product); if (button.dataset.action === 'availability') updateAvailability(id, button.dataset.next); if (button.dataset.action === 'confirm-draft') confirmDraft(id, button); if (button.dataset.action === 'edit-draft') { const draft = state.drafts.find((item) => text(item.id) === text(id)); if (draft) fillForm(draft.product || draft, draft.id); } }

  function initTheme() { const saved = localStorage.getItem('catalog-theme'); const isDark = saved === 'dark'; app.dataset.theme = isDark ? 'dark' : 'light'; const button = byId('themeToggle'); button.setAttribute('aria-pressed', String(isDark)); button.setAttribute('aria-label', isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'); button.replaceChildren(icon(isDark ? 'sun' : 'moon')); button.addEventListener('click', () => { const dark = app.dataset.theme !== 'dark'; app.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('catalog-theme', dark ? 'dark' : 'light'); button.setAttribute('aria-pressed', String(dark)); button.setAttribute('aria-label', dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'); button.replaceChildren(icon(dark ? 'sun' : 'moon')); }); }
  function wire() {
    initTheme(); seedState(); renderProducts(); renderDrafts(); initVoice(); loadCatalog();
    byId('productForm').addEventListener('submit', saveProduct); byId('resetProductButton').addEventListener('click', resetForm); byId('newProductButton').addEventListener('click', () => { resetForm(); byId('productName').focus(); }); byId('productSearch').addEventListener('input', renderProducts); byId('productTypeFilter').addEventListener('change', renderProducts); byId('productsList').addEventListener('click', handleActions); byId('draftsList').addEventListener('click', handleActions); byId('productPromotional').addEventListener('change', (event) => { byId('productPromoText').disabled = !event.target.checked; if (!event.target.checked) byId('productPromoText').value = ''; }); byId('restaurantSelector').addEventListener('change', (event) => { if (event.target.value) window.location.href = `/owner/catalog?restaurant_id=${encodeURIComponent(event.target.value)}`; }); byId('focusImportButton').addEventListener('click', () => byId('importPanel').scrollIntoView({ behavior: 'smooth' })); byId('photoForm').addEventListener('submit', uploadPhoto); byId('voiceButton').addEventListener('click', toggleVoice); byId('voiceSendButton').addEventListener('click', sendVoiceDraft); byId('importForm').addEventListener('submit', importExcel); byId('confirmImportButton').addEventListener('click', confirmImport); byId('closeImportPreview').addEventListener('click', () => { byId('importPreviewPanel').hidden = true; });
  }
  wire();
})();
