/* Business sites: editor API + public-site interactions. security.js wraps same-origin mutating fetches with CSRF. */
(function () {
  'use strict';

  const qs = (root, selector) => root ? root.querySelector(selector) : null;
  const qsa = (root, selector) => root ? Array.from(root.querySelectorAll(selector)) : [];
  const text = (value) => String(value == null ? '' : value);
  const lines = (value) => text(value).split(/\r?\n/).map(item => item.trim()).filter(Boolean);
  const safeJson = async (response) => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || payload.message || 'No se pudo completar la operación.');
    return payload;
  };
  const notify = (message, type) => {
    if (typeof window.showOwnerToast === 'function') window.showOwnerToast(message, type || 'info');
    else {
      let notice = document.getElementById('bs-inline-notice');
      if (!notice) { notice = document.createElement('div'); notice.id = 'bs-inline-notice'; notice.setAttribute('role','status'); notice.setAttribute('aria-live','polite'); const root = document.querySelector('[data-bs-editor]'); if (root) root.prepend(notice); }
      notice.textContent = message; notice.className = 'bs-inline-notice' + (type === 'error' ? ' is-error' : '');
    }
  };



  function initPublic() {
    const toggle = qs(document, '[data-public-menu]');
    const links = qs(document, '#bs-public-links');
    if (!toggle || !links) return;
    toggle.addEventListener('click', () => {
      const open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    qsa(links, 'a').forEach(link => link.addEventListener('click', () => {
      links.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    }));
  }

  function initEditor(root) {
    const apiUrl = root.dataset.apiUrl;
    const restaurantId = root.dataset.restaurantId;
    if (!apiUrl || !restaurantId) return;
    const form = qs(root, '[data-site-form]');
    const saveButton = qs(root, '[data-save]');
    const saveNote = qs(root, '[data-save-note]');
    const statusPill = qs(root, '[data-site-status]');
    const statusLabel = qs(root, '[data-status-label]');
    let proposal = null;

    const getField = (key) => qs(form, `[data-field="${key}"]`);
    const collectDraft = () => {
      const draft = {};
      qsa(form, '[data-field]').forEach(field => {
        const key = field.dataset.field;
        if (field.type === 'radio') { if (field.checked) draft[key] = field.value; return; }
        if (field.type === 'checkbox') draft[key] = field.checked;
        else if (field.dataset.list === 'lines') draft[key] = lines(field.value);
        else if (field.dataset.list === 'ids') draft[key] = text(field.value).split(',').map(item => item.trim()).filter(Boolean).map(Number).filter(item => Number.isInteger(item) && item > 0);
        else draft[key] = field.value.trim();
      });
      draft.social = {};
      qsa(form, '[data-social]').forEach(field => {
        if (field.value.trim()) draft.social[field.dataset.social] = field.value.trim();
      });
      return draft;
    };
    const setField = (key, value) => {
      const field = getField(key);
      if (!field || value === undefined || value === null) return;
      if (field.type === 'radio') qsa(form, `[data-field="${key}"]`).forEach(option => { option.checked = option.value === text(value); });
      else if (field.type === 'checkbox') field.checked = Boolean(value);
      else if (field.dataset.list === 'lines' && Array.isArray(value)) field.value = value.join('\n');
      else if (field.dataset.list === 'ids' && Array.isArray(value)) field.value = value.join(', ');
      else field.value = text(value);
    };
    const applyProposal = (draft) => {
      Object.keys(draft || {}).forEach(key => {
        if (key === 'social' && draft.social && typeof draft.social === 'object') {
          Object.entries(draft.social).forEach(([network, value]) => {
            const field = qs(form, `[data-social="${network}"]`);
            if (field) field.value = text(value);
          });
        } else setField(key, draft[key]);
      });
      syncPreview();
    };
    const setBusy = (busy, label) => {
      if (!saveButton) return;
      saveButton.disabled = busy;
      saveButton.querySelector('.material-icons').textContent = busy ? 'hourglass_top' : 'save';
      saveButton.lastChild.textContent = ` ${label || 'Guardar borrador'}`;
    };
    const setStatus = (live) => {
      if (!statusPill || !statusLabel) return;
      statusPill.classList.toggle('is-live', Boolean(live));
      statusLabel.textContent = live ? 'Publicado' : 'Borrador';
    };
    const syncPreview = () => {
      const draft = collectDraft();
      const card = qs(root, '[data-preview-window]');
      if (card) {
        card.dataset.heroStyle = draft.hero_style || 'commercial';
        card.style.setProperty('--preview-primary', draft.primary_color || window.SRTheme.color('brand-primary'));
        card.style.setProperty('--preview-secondary', draft.secondary_color || window.SRTheme.color('brand-secondary'));
      }
      const setText = (selector, value, fallback) => { const node = qs(root, selector); if (node) node.textContent = value || fallback; };
      setText('[data-preview-name]', draft.name, 'Tu restaurante');
      setText('[data-preview-heading]', draft.name, 'Tu restaurante');
      setText('[data-preview-tagline]', draft.tagline, 'Una mesa para recordar');
      setText('[data-preview-description]', draft.description, 'Tu historia aparece aquí.');
      setText('[data-preview-template]', text(draft.template || 'atelier').replace(/^./, char => char.toUpperCase()), 'Atelier');
      setText('[data-preview-specialties]', draft.specialties[0], 'Cocina con intención');
      const logo = qs(root, '[data-preview-logo]');
      if (logo) {
        logo.replaceChildren();
        if (draft.logo && /^(https:\/\/|\/portal-media\/\d+$|\/static\/)/.test(draft.logo)) {
          const image = document.createElement('img'); image.src = draft.logo; image.alt = ''; logo.append(image);
        } else {
          const ns = 'http://www.w3.org/2000/svg';
          const glyph = document.createElementNS(ns, 'svg');
          glyph.setAttribute('viewBox', '0 0 24 24');
          glyph.setAttribute('width', '1em');
          glyph.setAttribute('height', '1em');
          glyph.setAttribute('fill', 'none');
          glyph.setAttribute('stroke', 'currentColor');
          glyph.setAttribute('stroke-width', '1.8');
          glyph.setAttribute('aria-hidden', 'true');
          const path = document.createElementNS(ns, 'path');
          path.setAttribute('d', 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z');
          glyph.appendChild(path);
          logo.appendChild(glyph);
        }
      }
      const publish = qs(root, '[data-publish]');
      if (publish) publish.disabled = !draft.rights_confirmed;
    };
    const save = async () => {
      const draft = collectDraft();
      setBusy(true, 'Guardando…');
      try {
        const payload = await safeJson(await fetch(apiUrl, { method: 'PUT', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(draft) }));
        setBusy(false);
        if (saveNote) saveNote.textContent = 'Guardado hace un momento.';
        notify(payload.message || 'Borrador guardado.', 'success');
        if (payload.site) applyProposal(payload.site);
        return true;
      } catch (error) {
        setBusy(false);
        if (saveNote) saveNote.textContent = 'No se pudo guardar.';
        notify(error.message, 'error');
        return false;
      }
    };
    const postAction = async (path, message, live) => {
      try {
        const payload = await safeJson(await fetch(path, { method: 'POST', headers: { Accept: 'application/json' } }));
        setStatus(live);
        notify(payload.message || message, live ? 'success' : 'info');
      } catch (error) { notify(error.message, 'error'); }
    };

    qsa(form, 'input,textarea,select').forEach(field => field.addEventListener('input', syncPreview));
    qsa(form, '[data-hero-selector] input[type="radio"]').forEach(field => field.addEventListener('change', syncPreview));
    qsa(root, '[data-color-picker]').forEach(picker => picker.addEventListener('input', () => { setField(picker.dataset.colorPicker, picker.value); syncPreview(); }));

    const picker = qs(root, '[data-restaurant-picker]');
    if (picker) picker.addEventListener('change', () => { if (picker.value) window.location.assign(`/owner/sites?restaurant_id=${encodeURIComponent(picker.value)}`); });
    form.addEventListener('submit', event => { event.preventDefault(); save(); });
    const publish = qs(root, '[data-publish]');
    const unpublish = qs(root, '[data-unpublish]');
    if (publish) publish.addEventListener('click', async () => { if (!collectDraft().rights_confirmed) return notify('Confirma primero los derechos sobre tus assets.', 'warning'); if (await save()) await postAction(`${apiUrl}/publish`, 'Sitio publicado.', true); });
    if (unpublish) unpublish.addEventListener('click', () => postAction(`${apiUrl}/unpublish`, 'Sitio retirado.', false));
    const logoButton = qs(root, '[data-logo-upload]');
    const logoInput = qs(root, '[data-logo-input]');
    const logoStatus = qs(root, '[data-logo-status]');
    if (logoButton && logoInput) logoButton.addEventListener('click', async () => {
      const file = logoInput.files && logoInput.files[0];
      if (!file) return notify('Selecciona un archivo de logo primero.', 'warning');
      const data = new FormData(); data.append('file', file);
      logoButton.disabled = true;
      try {
        const payload = await safeJson(await fetch(`${apiUrl}/logo`, { method: 'POST', body: data }));
        setField('logo', payload.logo || payload.logo_url || '');
        if (Array.isArray(payload.palette)) {
          if (payload.palette[0]) setField('primary_color', payload.palette[0]);
          if (payload.palette[1]) setField('secondary_color', payload.palette[1]);
        } else if (payload.palette && payload.palette.primary) {
          setField('primary_color', payload.palette.primary);
          if (payload.palette.secondary) setField('secondary_color', payload.palette.secondary);
        }
        syncPreview();
        if (logoStatus) logoStatus.textContent = 'Logo cargado. Revisa la paleta antes de guardar.';
        notify('Logo cargado y paleta sugerida.', 'success');
      } catch (error) { if (logoStatus) logoStatus.textContent = error.message; notify(error.message, 'error'); }
      finally { logoButton.disabled = false; }
    });
    const aiBrief = qs(root, '[data-ai-brief]');
    const aiButton = qs(root, '[data-ai-propose]');
    const aiResult = qs(root, '[data-ai-result]');
    const aiFields = qs(root, '[data-ai-fields]');
    const aiModel = qs(root, '[data-ai-model]');
    const aiApply = qs(root, '[data-ai-apply]');
    if (aiButton) aiButton.addEventListener('click', async () => {
      const brief = text(aiBrief && aiBrief.value).trim();
      if (!brief) return notify('Describe primero la dirección que imaginas.', 'warning');
      aiButton.disabled = true;
      try {
        const payload = await safeJson(await fetch(`${apiUrl}/ai`, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ brief, draft: collectDraft() }) }));
        proposal = payload.proposal || payload.fields || payload;
        if (aiResult) aiResult.hidden = false;
        if (aiModel) aiModel.textContent = payload.model ? `Modelo · ${payload.model}` : 'Sin guardar';
        if (aiFields) {
          aiFields.innerHTML = '';
          Object.entries(proposal || {}).filter(([key]) => key !== 'social').slice(0, 8).forEach(([key, value]) => {
            const dt = document.createElement('dt'); dt.textContent = key.replaceAll('_', ' ');
            const dd = document.createElement('dd'); dd.textContent = Array.isArray(value) ? value.join(' · ') : text(value);
            aiFields.append(dt, dd);
          });
        }
        notify('Propuesta lista. Nada se guardará hasta que la apliques y guardes.', 'success');
      } catch (error) { notify(error.message, 'error'); }
      finally { aiButton.disabled = false; }
    });
    if (aiApply) aiApply.addEventListener('click', () => { if (!proposal) return; applyProposal(proposal); notify('Propuesta aplicada al formulario. Guarda para conservarla.', 'info'); });

    syncPreview();
  }

  document.addEventListener('DOMContentLoaded', () => {
    initPublic();
    const editor = qs(document, '[data-bs-editor]');
    if (editor) initEditor(editor);
  });
})();
