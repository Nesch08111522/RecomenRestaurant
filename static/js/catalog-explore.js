(() => {
    const form = document.getElementById('catalog-search');
    if (!form) return;
    const status = document.getElementById('catalog-status');
    const results = document.getElementById('catalog-results');
    let origin = {};
    const selected = new Set();
    const products = new Set();
    const declaration = value => Array.isArray(value) ? value.join(', ') || 'Ninguno declarado' : 'Sin declarar';
    async function showProduct(id) {
        const data = await api(`/api/catalog/products/${id}`);
        const row = data.product;
        const panel = document.getElementById('catalog-product-card');
        panel.replaceChildren(); panel.hidden = false;
        text(panel, 'h2', row.name);
        text(panel, 'p', row.description || 'Sin descripcion');
        text(panel, 'p', `S/ ${row.price ?? 'Sin precio'} | ${row.availability || (row.is_available ? 'Disponible' : 'Disponibilidad desconocida')}`);
        text(panel, 'p', `Ingredientes: ${declaration(row.ingredients)} | Confirmados: ${row.ingredients_confirmed === true ? 'si' : 'no'}`);
        text(panel, 'p', `Alergenos: ${declaration(row.allergens)} | Confirmados: ${row.allergens_confirmed === true ? 'si' : 'no'}`);
        const link = text(panel, 'a', 'Ver negocio'); link.href = data.business_url;
        const close = text(panel, 'button', 'Cerrar ficha'); close.onclick = () => { panel.hidden = true; };
        panel.scrollIntoView({block:'nearest'});
    }
    const text = (parent, tag, value) => {
        const node = document.createElement(tag); node.textContent = value; parent.append(node); return node;
    };
    async function api(url, body) {
        const token = document.querySelector('meta[name="csrf-token"]')?.content;
        const response = await fetch(url, body ? {method:'POST', headers:{'Content-Type':'application/json', 'X-CSRFToken':token || ''}, body:JSON.stringify(body)} : {});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'No se pudo consultar el catalogo');
        return data;
    }
    function render(rows) {
        results.replaceChildren(); selected.clear(); products.clear(); document.getElementById('catalog-comparison').replaceChildren(); status.textContent = `${rows.length} negocios encontrados`;
        for (const row of rows) {
            const card = document.createElement('article'); card.style.padding = '16px'; results.append(card);
            const check = document.createElement('input'); check.type = 'checkbox'; check.setAttribute('aria-label', `Comparar ${row.name}`);
            check.onchange = () => { if(check.checked) selected.add(row.id); else selected.delete(row.id); }; card.append(check);
            text(card, 'h2', row.name); text(card, 'p', `${row.district || ''} | S/ ${row.avg_price ?? 'Sin precio'} | ${row.rating ?? 'Sin puntuacion'}`);
            const link = text(card, 'a', 'Ver negocio y carta'); link.href = `/restaurant/${row.id}`;
            for (const product of row.matching_dishes || []) {
                const item = document.createElement('div'); card.append(item);
                const label = document.createElement('label'); item.append(label);
                const choice = document.createElement('input'); choice.type='checkbox'; label.append(choice);
                text(label, 'span', ` Comparar ${product.name} | S/ ${product.price ?? 'Sin precio'}`);
                choice.onchange = () => {
                    if(choice.checked && products.size >= 4) { choice.checked=false; status.textContent='Maximo cuatro productos'; return; }
                    if(choice.checked) products.add(product.id); else products.delete(product.id);
                };
                const detail = text(item, 'button', 'Ver ficha producto');
                detail.onclick = () => showProduct(product.id).catch(error => { status.textContent=error.message; });
            }
            const favorite = text(card, 'button', 'Guardar / quitar favorito');
            favorite.onclick = async () => { try {
                const data = await api('/auth/api/favorites/toggle', {restaurant_id:row.id});
                favorite.textContent = data.favorited ? 'Guardado en favoritos' : 'Guardar favorito';
            } catch(error) { status.textContent=error.message; } };
            const map = text(card, 'button', 'Recojo, cobertura y ruta');
            map.onclick = async () => { try {
                const data = await api(`/api/catalog/${row.id}/map?${new URLSearchParams(origin)}`);
                const info = text(card, 'p', `${data.pickup || 'Sin punto de recojo declarado'} | Zonas: ${data.zones.join(', ') || 'Sin cobertura declarada'} | Radio: ${data.radius_km} km | Distancia en linea recta: ${data.distance_km ?? 'desconocida'}`);
                if (data.point && window.L) {
                    const container = document.createElement('div'); container.style.height='260px'; card.append(container);
                    const geo = L.map(container).setView(data.point, 14);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution:'OpenStreetMap contributors'}).addTo(geo);
                    L.marker(data.point).addTo(geo).bindPopup(document.createTextNode(data.pickup || row.name));
                    if(data.radius_km > 0) L.circle(data.point, {radius:data.radius_km * 1000}).addTo(geo);
                    if(origin.lat != null) L.marker([origin.lat, origin.lng]).addTo(geo);
                }
                if(data.route_url) { const route = text(info, 'a', ' Abrir ruta OSM'); route.href=data.route_url; route.target='_blank'; route.rel='noopener'; }
            } catch(error) { status.textContent=error.message; } };
        }
    }
    document.getElementById('catalog-location').onclick = () => {
        if (!navigator.geolocation) { status.textContent='Ubicacion no disponible'; return; }
        navigator.geolocation.getCurrentPosition(p => { origin={lat:p.coords.latitude,lng:p.coords.longitude}; status.textContent='Ubicacion lista para filtrar'; }, () => { status.textContent='No se pudo obtener ubicacion'; });
    };
    form.onsubmit = async event => { event.preventDefault(); const filters={...origin};
        for(const input of form.elements) if(input.name && input.value && (input.type !== 'checkbox' || input.checked)) filters[input.name]=input.type==='checkbox' ? true : input.value;
        try { render(await api('/api/search',filters)); } catch(error) { status.textContent=error.message; }
    };
    document.getElementById('catalog-ai').onclick = async () => { try {
        const data=await api('/api/ai/interpret',{text:document.getElementById('catalog-natural').value,...origin}); render(data.results); status.textContent += ` | ${data.summary}`;
    } catch(error) { status.textContent=error.message; } };
    document.getElementById('catalog-compare-products').onclick = async () => { try {
        const data = await api(`/api/catalog/compare?kind=product&ids=${[...products].join(',')}`);
        const panel = document.getElementById('catalog-comparison'); panel.replaceChildren();
        text(panel, 'h2', 'Comparacion de productos');
        for(const row of data.results) {
            const item = document.createElement('article'); panel.append(item);
            text(item, 'h3', row.name);
            text(item, 'p', `S/ ${row.price ?? 'Sin precio'} | ${row.availability || 'Sin estado declarado'}`);
            text(item, 'p', `Ingredientes: ${declaration(row.ingredients)} | Alergenos: ${declaration(row.allergens)}`);
            const detail = text(item, 'button', 'Ver ficha producto');
            detail.onclick = () => showProduct(row.id).catch(error => { status.textContent=error.message; });
        }
    } catch(error) { status.textContent=error.message; } };
    document.getElementById('catalog-compare').onclick = async () => { try {
        const data=await api(`/api/catalog/compare?ids=${[...selected].join(',')}`);
        const panel=document.getElementById('catalog-comparison'); panel.replaceChildren();
        for(const row of data.results) text(panel,'p',`${row.name}: S/ ${row.avg_price ?? '?'} | ${row.rating ?? '?'} | ${row.district || ''} | ${(row.market_channels || []).join(', ')}`);
    } catch(error) { status.textContent=error.message; } };
})();
