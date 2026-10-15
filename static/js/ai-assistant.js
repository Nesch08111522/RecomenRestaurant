(function () {
    'use strict';

    const API_INTERPRET = '/api/ai/interpret';
    const API_CHAT = '/api/ai/chat';

    // Botones rápidos del chat: [texto del botón, mensaje que se envía]
    const QUICK_REPLIES = [
        ['📍 Cerca de mí', '¿Qué restaurantes me quedan cerca?'],
        ['💰 Económico', 'Algo económico'],
        ['❤️ Romántico', 'Un lugar romántico para una cena'],
        ['👨‍👩‍👧 En familia', 'Algo para ir en familia'],
        ['🏷️ Promociones', '¿Qué restaurantes tienen promoción?'],
        ['⭐ Mejor valorados', '¿Cuáles son los mejor valorados?']
    ];

    const getApp = () => window.app;
    const money = () => (typeof MONEDA !== 'undefined' ? MONEDA : 'S/.');

    async function postJSON(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        let data = {};
        try { data = await res.json(); } catch (e) { /* respuesta sin JSON */ }
        if (!res.ok || !data.success) {
            throw new Error(data.error || 'La IA no está disponible ahora. Intenta de nuevo.');
        }
        return data;
    }

    function el(tag, className, text) {
        const n = document.createElement(tag);
        if (className) n.className = className;
        if (text != null) n.textContent = text;
        return n;
    }

    function clearActiveChips() {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    }

    function showList(list) {
        const a = getApp();
        if (!a) return;
        a.state.filteredRestaurants = list;
        a.renderRestaurants();
        a.updateMapMarkers(list);
    }

    // ------------------------------------------------------------ ubicación
    const toNum = (v) => {
        const x = parseFloat(v);
        return Number.isFinite(x) ? x : null;
    };

    function normLoc(loc) {
        if (!loc) return null;
        const lat = toNum(loc.lat ?? loc.latitude);
        const lng = toNum(loc.lng ?? loc.lon ?? loc.longitude);
        return lat != null && lng != null ? { lat, lng } : null;
    }

    function restLatLng(r) {
        let lat = toNum(r.lat ?? r.latitude ?? r.latitud);
        let lng = toNum(r.lng ?? r.lon ?? r.long ?? r.longitude ?? r.longitud);
        if (lat != null && lng != null) return { lat, lng };

        const c = r.coordinates || r.coords || r.location;
        if (Array.isArray(c) && c.length >= 2) {
            const x = toNum(c[0]);
            const y = toNum(c[1]);
            if (x != null && y != null) {
                // En Perú la latitud (≈ -8) tiene menor valor absoluto que la longitud (≈ -79)
                return Math.abs(x) < Math.abs(y) ? { lat: x, lng: y } : { lat: y, lng: x };
            }
        }
        if (c && typeof c === 'object') return normLoc(c);
        return null;
    }

    function distanceKm(a, b) {
        const R = 6371;
        const rad = d => (d * Math.PI) / 180;
        const dLat = rad(b.lat - a.lat);
        const dLng = rad(b.lng - a.lng);
        const h = Math.sin(dLat / 2) ** 2 +
            Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
        return 2 * R * Math.asin(Math.sqrt(h));
    }

    // ------------------------------------------------------------ estilos
    function injectStyles() {
        if (document.getElementById('ai-assistant-styles')) return;
        const s = document.createElement('style');
        s.id = 'ai-assistant-styles';
        s.textContent = `
            .ai-smart { margin: 0 0 18px; }
            .ai-smart-row {
                display: flex; align-items: center; gap: 10px;
                padding: 8px 8px 8px 16px;
                background: #fff; border: 1px solid rgba(17,24,39,.1);
                border-radius: 999px; box-shadow: 0 2px 10px rgba(17,24,39,.06);
            }
            .ai-smart-icon { color: var(--primary, #ff385c); }
            .ai-smart-input {
                flex: 1; min-width: 0; border: none; outline: none;
                background: transparent; font-size: 14px; padding: 8px 0;
            }
            .ai-smart-btn {
                flex-shrink: 0; border: none; cursor: pointer; color: #fff;
                padding: 10px 18px; border-radius: 999px; font-weight: 600; font-size: 14px;
                background: linear-gradient(135deg, var(--primary, #ff385c), #ff6b81);
            }
            .ai-smart-btn:disabled { opacity: .7; cursor: wait; }
            .ai-smart-status {
                margin-top: 10px; padding: 9px 14px; border-radius: 12px;
                background: #fff1f3; color: #4b5563; font-size: 13px;
                display: flex; align-items: center; justify-content: space-between; gap: 10px;
            }
            .ai-smart-status.error { background: #fef2f2; color: #b91c1c; }
            .ai-smart-reset {
                border: none; background: none; cursor: pointer; white-space: nowrap;
                color: var(--primary, #ff385c); font-weight: 600; font-size: 13px;
            }

            .ai-fab {
                position: fixed; right: 20px; bottom: 20px; z-index: 1200;
                width: 58px; height: 58px; border: none; border-radius: 50%; cursor: pointer;
                color: #fff; font-size: 24px;
                background: linear-gradient(135deg, var(--primary, #ff385c), #ff6b81);
                box-shadow: 0 8px 22px rgba(255,56,92,.4);
                transition: transform .2s ease;
            }
            .ai-fab:hover { transform: scale(1.08); }

            .ai-chat {
                position: fixed; right: 20px; bottom: 92px; z-index: 1200;
                width: 360px; max-width: calc(100vw - 40px); height: 520px; max-height: calc(100vh - 120px);
                display: flex; flex-direction: column; overflow: hidden;
                background: #fff; border-radius: 18px;
                box-shadow: 0 18px 50px rgba(17,24,39,.28);
            }
            .ai-chat-head {
                display: flex; align-items: center; justify-content: space-between;
                padding: 14px 16px; color: #fff; font-weight: 700;
                background: linear-gradient(135deg, var(--primary, #ff385c), #ff6b81);
            }
            .ai-chat-close {
                border: none; background: none; color: #fff; font-size: 24px; line-height: 1; cursor: pointer;
            }
            .ai-chat-body {
                flex: 1; overflow-y: auto; padding: 14px;
                display: flex; flex-direction: column; gap: 10px; background: #f9fafb;
            }
            .ai-bubble {
                max-width: 85%; padding: 9px 13px; border-radius: 14px;
                font-size: 13.5px; line-height: 1.45; white-space: pre-wrap; word-wrap: break-word;
            }
            .ai-bubble.bot { align-self: flex-start; background: #fff; color: #374151; border: 1px solid #eceff3; }
            .ai-bubble.user { align-self: flex-end; background: var(--primary, #ff385c); color: #fff; }
            .ai-bubble.ai-typing { opacity: .6; font-style: italic; }
            .ai-recs { display: flex; flex-direction: column; gap: 8px; align-self: stretch; }
            .ai-rec {
                display: flex; flex-direction: column; gap: 2px; padding: 10px 12px;
                background: #fff; border: 1px solid #eceff3; border-left: 3px solid var(--primary, #ff385c);
                border-radius: 10px; text-decoration: none; color: #374151; font-size: 12.5px;
            }
            .ai-rec strong { color: #111827; font-size: 13.5px; }
            .ai-rec-show {
                align-self: flex-start; border: none; cursor: pointer; padding: 6px 12px;
                border-radius: 999px; background: #fff1f3; color: var(--primary, #ff385c);
                font-weight: 600; font-size: 12.5px;
            }

            .ai-quick {
                display: flex; gap: 6px; padding: 8px 10px; overflow-x: auto;
                border-top: 1px solid #eceff3; background: #fff; scrollbar-width: thin;
            }
            .ai-quick-btn {
                flex-shrink: 0; border: 1px solid #f3d4da; background: #fff1f3; cursor: pointer;
                color: var(--primary, #ff385c); font-weight: 600; font-size: 12.5px;
                padding: 6px 12px; border-radius: 999px; white-space: nowrap;
            }
            .ai-quick-btn:hover { background: #ffe3e8; }
            .ai-quick-btn.loc { background: var(--primary, #ff385c); color: #fff; border-color: transparent; }
            .ai-quick-btn.loc.on { background: #16a34a; }
            .ai-quick-btn:disabled { opacity: .6; cursor: wait; }

            .ai-chat-form { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #eceff3; background: #fff; }
            .ai-chat-input {
                flex: 1; min-width: 0; padding: 10px 14px; border: 1px solid #e5e7eb;
                border-radius: 999px; outline: none; font-size: 13.5px;
            }
            .ai-chat-send {
                width: 40px; height: 40px; border: none; border-radius: 50%; cursor: pointer;
                color: #fff; background: var(--primary, #ff385c);
            }
            @media (max-width: 600px) {
                .ai-smart-btn { padding: 10px 12px; }
                .ai-smart-btn span { display: none; }
            }
        `;
        document.head.appendChild(s);
    }

    // ------------------------------------- 1) BÚSQUEDA INTELIGENTE (texto libre)
    function uniqueTags(restaurants) {
        const set = new Set();
        restaurants.forEach(r => (r.tags || []).forEach(t => set.add(String(t).toLowerCase())));
        return [...set].slice(0, 80);
    }

    async function applyFilters(f) {
        const a = getApp();
        let list = [...a.state.restaurants];

        if (f.min_price != null) list = list.filter(r => r.avg_price >= f.min_price);
        if (f.max_price != null) list = list.filter(r => r.avg_price <= f.max_price);
        if (f.category_ids && f.category_ids.length) {
            const ids = f.category_ids.map(String);
            list = list.filter(r => ids.includes(String(r.category_id)));
        }
        if (f.promo_only) list = list.filter(r => r.promo);
        if (f.open_now) list = list.filter(r => a.isRestaurantOpen(r));

        if (f.nearby || f.sort_by === 'distance') {
            const loc = a.state.userLocation || await a.getUserLocation();
            if (loc) list = a.sortByDistance(list, loc);
        }

        const kws = (f.keywords || []).map(k => String(k).toLowerCase());
        const score = r => kws.reduce(
            (s, k) => s + ((r.tags || []).some(t => String(t).toLowerCase() === k) ? 1 : 0), 0);

        list.sort((x, y) => {
            if (f.sort_by === 'price') return x.avg_price - y.avg_price;
            if (f.sort_by === 'distance') return (x.distance_km ?? 999) - (y.distance_km ?? 999);
            if (f.sort_by === 'rating') return y.rating - x.rating;
            return (score(y) - score(x)) || (y.rating - x.rating);
        });

        if (list.length) {
            clearActiveChips();
            showList(list);
        }
        return list.length;
    }

    function buildSmartBar() {
        const col = document.querySelector('.results-column');
        const header = col && col.querySelector('.results-header');
        if (!col || !header) return;

        const wrap = el('div', 'ai-smart');
        const row = el('div', 'ai-smart-row');
        const icon = el('i', 'fas fa-robot ai-smart-icon');
        const input = el('input', 'ai-smart-input');
        input.type = 'text';
        input.maxLength = 300;
        input.placeholder = 'Dile a la IA qué buscas: "algo económico y romántico para esta noche"';
        const btn = el('button', 'ai-smart-btn');
        btn.type = 'button';
        const idleHTML = '<i class="fas fa-magic"></i> <span>Buscar con IA</span>';
        btn.innerHTML = idleHTML;
        const status = el('div', 'ai-smart-status');
        status.style.display = 'none';

        row.append(icon, input, btn);
        wrap.append(row, status);
        col.insertBefore(wrap, header);

        function setStatus(message, isError, withReset) {
            status.textContent = '';
            status.className = 'ai-smart-status' + (isError ? ' error' : '');
            status.appendChild(el('span', null, message));
            if (withReset) {
                const reset = el('button', 'ai-smart-reset', 'Quitar filtro');
                reset.type = 'button';
                reset.addEventListener('click', () => {
                    const a = getApp();
                    showList(a.state.restaurants);
                    clearActiveChips();
                    const all = document.querySelector('.filter-chip[data-filter="all"]');
                    if (all) all.classList.add('active');
                    status.style.display = 'none';
                    input.value = '';
                });
                status.appendChild(reset);
            }
            status.style.display = 'flex';
        }

        async function run() {
            const text = input.value.trim();
            const a = getApp();
            if (!text || !a) return;

            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Pensando...</span>';
            try {
                const cats = (typeof CATEGORIES_DATA !== 'undefined' ? CATEGORIES_DATA : [])
                    .map(c => ({ id: c.id, name: c.name }));
                const data = await postJSON(API_INTERPRET, {
                    text,
                    categories: cats,
                    available_tags: uniqueTags(a.state.restaurants)
                });
                const count = await applyFilters(data.filters);
                if (count > 0) {
                    setStatus(`🤖 ${data.summary || 'Listo'} · ${count} resultado${count === 1 ? '' : 's'}`, false, true);
                } else {
                    setStatus('No encontré restaurantes con eso. Prueba con otras palabras o pregúntale al chat.', true, false);
                }
            } catch (e) {
                setStatus(e.message, true, false);
            } finally {
                btn.disabled = false;
                btn.innerHTML = idleHTML;
            }
        }

        btn.addEventListener('click', run);
        input.addEventListener('keydown', e => { if (e.key === 'Enter') run(); });
    }

    // --------------------------------------------------------- 2) CHAT FLOTANTE
    function buildChat() {
        const fab = el('button', 'ai-fab');
        fab.type = 'button';
        fab.title = 'Asistente IA';
        fab.innerHTML = '<i class="fas fa-comment-dots"></i>';

        const panel = el('div', 'ai-chat');
        panel.style.display = 'none';
        panel.innerHTML =
            '<div class="ai-chat-head"><span><i class="fas fa-robot"></i> Asistente SmartResto</span>' +
            '<button type="button" class="ai-chat-close" aria-label="Cerrar">&times;</button></div>' +
            '<div class="ai-chat-body"></div>' +
            '<div class="ai-quick"></div>' +
            '<div class="ai-chat-form">' +
            '<input type="text" class="ai-chat-input" maxlength="300" placeholder="Ej: ¿dónde como ceviche?">' +
            '<button type="button" class="ai-chat-send" aria-label="Enviar"><i class="fas fa-paper-plane"></i></button>' +
            '</div>';

        document.body.append(fab, panel);

        const body = panel.querySelector('.ai-chat-body');
        const quick = panel.querySelector('.ai-quick');
        const input = panel.querySelector('.ai-chat-input');
        const sendBtn = panel.querySelector('.ai-chat-send');
        const history = [];
        let busy = false;
        let userLoc = null;
        let locBtn = null;

        function addBubble(role, text) {
            const b = el('div', 'ai-bubble ' + role, text);
            body.appendChild(b);
            body.scrollTop = body.scrollHeight;
            return b;
        }

        // ---- ubicación dentro del chat
        function currentLoc() {
            const a = getApp();
            return userLoc || normLoc(a && a.state && a.state.userLocation);
        }

        function markLocationOn() {
            if (!locBtn) return;
            locBtn.classList.add('on');
            locBtn.textContent = '✓ Ubicación activa';
        }

        function requestLocation() {
            return new Promise(resolve => {
                if (!navigator.geolocation) {
                    addBubble('bot', 'Tu navegador no permite obtener la ubicación.');
                    resolve(null);
                    return;
                }
                if (locBtn) locBtn.disabled = true;
                navigator.geolocation.getCurrentPosition(
                    pos => {
                        userLoc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
                        markLocationOn();
                        if (locBtn) locBtn.disabled = false;
                        resolve(userLoc);
                    },
                    () => {
                        if (locBtn) locBtn.disabled = false;
                        addBubble('bot', 'No pude obtener tu ubicación. Permite el acceso en el navegador (icono del candado junto a la dirección) e inténtalo de nuevo.');
                        resolve(null);
                    },
                    { enableHighAccuracy: true, timeout: 8000 }
                );
            });
        }

        function addRecommendations(ids) {
            const a = getApp();
            if (!a) return;
            const found = (ids || [])
                .map(id => a.state.restaurants.find(r => String(r.id) === String(id)))
                .filter(Boolean);
            if (!found.length) return;

            const box = el('div', 'ai-recs');
            found.forEach(r => {
                const link = el('a', 'ai-rec');
                link.href = '/restaurant/' + encodeURIComponent(r.id);
                link.append(
                    el('strong', null, r.name),
                    el('span', null, `${money()}${r.avg_price} · ★ ${r.rating}${r.district ? ' · ' + r.district : ''}`)
                );
                box.appendChild(link);
            });
            const show = el('button', 'ai-rec-show', 'Ver en la lista y el mapa');
            show.type = 'button';
            show.addEventListener('click', () => {
                clearActiveChips();
                showList(found);
            });
            box.appendChild(show);
            body.appendChild(box);
            body.scrollTop = body.scrollHeight;
        }

        function compactRestaurants() {
            const a = getApp();
            const loc = currentLoc();
            return a.state.restaurants.slice(0, 40).map(r => {
                let km = r.distance_km;
                if (loc) {
                    const p = restLatLng(r);
                    if (p) km = Math.round(distanceKm(loc, p) * 10) / 10;
                }
                return {
                    id: r.id,
                    name: r.name,
                    district: r.district,
                    avg_price: r.avg_price,
                    rating: r.rating,
                    tags: r.tags,
                    category_id: r.category_id,
                    promo: r.promo,
                    distance_km: km
                };
            });
        }

        async function send(override) {
            const text = (override != null ? override : input.value).trim();
            if (!text || busy || !getApp()) return;
            busy = true;
            input.value = '';

            addBubble('user', text);
            history.push({ role: 'user', content: text });

            // Si pregunta por cercanía y aún no hay ubicación, se pide aquí mismo
            if (/cerca|cercan|mi casa|mi ubicaci|donde estoy|dónde estoy/i.test(text) && !currentLoc()) {
                addBubble('bot', 'Para decirte qué te queda cerca necesito tu ubicación. Acepta el permiso del navegador 👇');
                await requestLocation();
            }

            const typing = addBubble('bot', 'Pensando…');
            typing.classList.add('ai-typing');

            try {
                const data = await postJSON(API_CHAT, {
                    messages: history.slice(-6),
                    restaurants: compactRestaurants()
                });
                typing.remove();
                addBubble('bot', data.reply);
                history.push({ role: 'assistant', content: data.reply });
                addRecommendations(data.restaurant_ids);
            } catch (e) {
                typing.remove();
                history.pop();
                addBubble('bot', e.message);
            } finally {
                busy = false;
                input.focus();
            }
        }

        // ---- botones rápidos dentro del chat
        locBtn = el('button', 'ai-quick-btn loc', '📍 Usar mi ubicación');
        locBtn.type = 'button';
        locBtn.addEventListener('click', async () => {
            if (busy) return;
            const loc = await requestLocation();
            if (loc) addBubble('bot', '📍 Listo, ya tengo tu ubicación. Ahora pregúntame lo que quieras, por ejemplo: "¿qué me queda cerca?".');
        });
        quick.appendChild(locBtn);

        QUICK_REPLIES.forEach(([label, message]) => {
            const b = el('button', 'ai-quick-btn', label);
            b.type = 'button';
            b.addEventListener('click', () => send(message));
            quick.appendChild(b);
        });

        function toggle(open) {
            panel.style.display = open ? 'flex' : 'none';
            if (open) input.focus();
        }

        fab.addEventListener('click', () => toggle(panel.style.display === 'none'));
        panel.querySelector('.ai-chat-close').addEventListener('click', () => toggle(false));
        sendBtn.addEventListener('click', () => send());
        input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

        addBubble('bot', '¡Hola! Soy el asistente de SmartResto. Usa los botones de abajo o escríbeme, por ejemplo: "¿dónde como ceviche?".');
    }

    // ------------------------------------------------------------------ inicio
    function init() {
        if (!document.getElementById('resultsGrid')) return; // solo en la página de restaurantes
        injectStyles();
        buildSmartBar();
        buildChat();
    }

    window.addEventListener('load', init);
})();