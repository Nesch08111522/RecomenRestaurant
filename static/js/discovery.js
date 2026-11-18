/* Radar SmartResto. Los contenidos externos se insertan exclusivamente como texto. */
(function () {
  'use strict';
  const status = document.getElementById('radarStatus');
  function message(text, error) { if (!status) return; status.hidden = false; status.classList.toggle('error', !!error); status.textContent = text; }
  async function api(path, data, method = 'POST') {
    const response = await fetch(path, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || 'La operación no se completó.');
    return result;
  }
  async function busy(button, action) {
    button.disabled = true; button.setAttribute('aria-busy','true');
    try { await action(); } catch(error) { message(error.message, true); }
    finally { button.disabled = false; button.removeAttribute('aria-busy'); }
  }
  const root = document.getElementById('radarApp');
  let decision = null;
  if (root) {
    const cards = Array.from(root.querySelectorAll('.radar-candidate'));
    const search = document.getElementById('radarSearch'), filter = document.getElementById('radarFilter');
    function applyFilters() { let count = 0; cards.forEach(card => { card.hidden = !!((filter.value && card.dataset.state !== filter.value) || !card.dataset.search.includes(search.value.toLowerCase())); if (!card.hidden) count++; }); document.getElementById('radarNoMatches').hidden = count > 0 || !cards.length; }
    search.addEventListener('input', applyFilters); filter.addEventListener('change', applyFilters);
    root.addEventListener('click', event => {
      const button = event.target.closest('button[data-action]'); if (!button) return;
      if (button.dataset.action === 'scan') busy(button, async () => { message('Consultando una fuente autorizada. No cierres esta ventana mientras se procesa.'); const result = await api('/admin/api/discovery/runs', {source:button.dataset.source}); message(`Corrida completada: ${result.run.created} fichas nuevas. Actualizando bandeja.`); location.reload(); });
      if (button.dataset.action === 'pause') busy(button, async () => { await api(`/admin/api/discovery/sources/${button.dataset.id}`, {enabled:button.dataset.enabled === 'true'}, 'PATCH'); location.reload(); });
      if (['review','claim-review'].includes(button.dataset.action)) { decision = {id:button.dataset.id, action:button.dataset.decision, claim:button.dataset.action === 'claim-review'}; document.getElementById('radarNotes').value = ''; document.getElementById('radarDecisionTitle').textContent = button.textContent; document.getElementById('radarDecision').showModal(); }
      if (button.dataset.action === 'invite') busy(button, async () => { const result = await api(`/admin/api/discovery/candidates/${button.dataset.id}/invite`, {}); document.getElementById('radarInviteLink').value = location.origin + result.invitation.path; document.getElementById('radarInvitation').showModal(); });
    });
    document.getElementById('radarConfirm').addEventListener('click', event => busy(event.target, async () => { if (!decision) return; const notes = document.getElementById('radarNotes').value.trim(); if (notes.length < 12) throw new Error('Describe la evidencia y el motivo con al menos 12 caracteres.'); const path = decision.claim ? `/admin/api/discovery/claims/${decision.id}/review` : `/admin/api/discovery/candidates/${decision.id}/review`; await api(path, {action:decision.action, notes}); document.getElementById('radarDecision').close(); location.reload(); }));
    document.getElementById('radarCopy').addEventListener('click', event => busy(event.target, async () => { const field = document.getElementById('radarInviteLink'); try { await navigator.clipboard.writeText(field.value); message('Enlace copiado. La invitación aún no se ha enviado al empresario.'); } catch (_) { field.select(); message('Selecciona y copia el enlace. No se envió ningún mensaje externo.'); } }));
    document.getElementById('radarSourceForm').addEventListener('submit', event => { event.preventDefault(); const form = event.target, data = Object.fromEntries(new FormData(form)); data.use_ai = form.elements.use_ai.checked; data.refresh_days = Number(data.refresh_days); busy(form.querySelector('button'), async () => { await api('/admin/api/discovery/sources', data); location.reload(); }); });
    if (window.L && document.getElementById('radarMap')) {
      const map = L.map('radarMap', {scrollWheelZoom:false}).setView([-8.1118,-79.0287],13);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19, attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
      let candidates = []; try { candidates = JSON.parse(document.getElementById('radarData').textContent); } catch (_) { message('No se pudieron leer las fichas del mapa.',true); }
      candidates.forEach(row => { const data = row.data; if (!Number.isFinite(data.lat) || !Number.isFinite(data.lng)) return; const icon = L.divIcon({className:'',html:'<div class="radar-marker'+(row.status==='duplicate'?' radar-marker-duplicate':'')+'"></div>',iconSize:[22,22]}); const label = document.createElement('div'); const title = document.createElement('strong'); title.textContent = data.name || 'Nombre pendiente'; const detail = document.createElement('p'); detail.textContent = 'Ficha provisional · '+(data.address || 'Dirección pendiente'); label.append(title,detail); L.marker([data.lat,data.lng],{icon}).bindPopup(label).addTo(map); });
    }
  }
  let claimToken = '';
  const preview = document.getElementById('claimPreview');
  if (preview) {
    claimToken = new URLSearchParams(location.hash.slice(1)).get('token') || '';
    if (claimToken) api('/api/discovery/invitations/preview', {token:claimToken}).then(result => { preview.replaceChildren(); const title = document.createElement('h2'); title.textContent = result.business.name || 'Ficha provisional'; const address = document.createElement('p'); address.textContent = result.business.address || 'Dirección pendiente'; preview.append(title,address); }).catch(error => { message(error.message,true); });
    const form = document.getElementById('radarClaimForm');
    if (form) form.addEventListener('submit', event => { event.preventDefault(); busy(form.querySelector('button'), async () => { if (!claimToken) throw new Error('Abre una invitación válida del negocio.'); const result = await api('/api/discovery/claims', {token:claimToken,proof:form.elements.proof.value}); message(result.status+'. La solicitud no transfiere automáticamente propiedad.'); form.hidden = true; history.replaceState(null,'',location.pathname); claimToken = ''; }); });
  }
  const google = document.getElementById('radarGoogleForm');
  if (google) google.addEventListener('submit', event => { event.preventDefault(); busy(google.querySelector('button'), async () => { const box = document.getElementById('googleResults'); box.replaceChildren(); message('Consultando Google Places. Los resultados no se guardarán.'); const result = await api('/admin/api/discovery/google', {q:google.elements.q.value}); result.places.forEach(place => { const card = document.createElement('article'); card.className = 'radar-source'; const name = document.createElement('h2'); name.textContent = place.displayName?.text || 'Lugar sin nombre'; const address = document.createElement('p'); address.textContent = place.formattedAddress || ''; card.append(name,address); if (place.googleMapsUri?.startsWith('https://')) { const link = document.createElement('a'); link.href = place.googleMapsUri; link.textContent = 'Ver en Google Maps'; link.target = '_blank'; link.rel = 'noopener noreferrer'; card.append(link); } (place.attributions || []).forEach(item => { const credit = document.createElement('p'); credit.textContent = item.provider || ''; card.append(credit); }); box.append(card); }); message(`${result.places.length} resultados efímeros. No fueron importados a SmartResto.`); }); });
})();

(function () {
  const root = document.getElementById('radarApp');
  if (!root) return;
  root.querySelectorAll('.radar-candidate[data-state="duplicate"]').forEach(card => {
    const reference = card.querySelector('button[data-id]');
    if (!reference) return;
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'radar-secondary';
    button.dataset.action = 'review'; button.dataset.id = reference.dataset.id;
    button.dataset.decision = 'mark_distinct'; button.textContent = 'Son negocios o sucursales distintos';
    card.querySelector('.radar-candidate-actions').append(button);
  });
})();
