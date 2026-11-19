(() => {
    const root = document.documentElement;
    try {
        if (localStorage.getItem('sr-sidebar-state') === 'expanded') root.classList.remove('sr-compact');
        else root.classList.add('sr-compact');
    } catch {
        root.classList.add('sr-compact');
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.setAttribute('aria-pressed', String(chip.classList.contains('active')));
        });
        document.querySelectorAll('.sr-filter-form').forEach(form => {
            const fields = [...form.querySelectorAll('.sr-filter-fields input, .sr-filter-fields select')];
            const count = form.querySelector('[data-filter-count]');
            if (!count) return;
            function updateFilterCount() {
                const active = fields.filter(field => field.type === 'checkbox' ? field.checked : field.value.trim() !== '').length;
                count.textContent = active ? ` (${active})` : '';
            }
            form.addEventListener('input', updateFilterCount);
            form.addEventListener('change', updateFilterCount);
            updateFilterCount();
        });

        // Touch, wheel and keyboard keep their native scrolling behaviour.
        let drag;
        let suppressClick = false;
        document.addEventListener('pointerdown', event => {
            suppressClick = false;
            if (!(event.target instanceof Element) || event.pointerType !== 'mouse' || event.button !== 0 || event.shiftKey ||
                event.target.closest('a[href],input,textarea,select,button,summary,[role=button],[role=link],[contenteditable=true],.private-account,.map-container,.leaflet-container,.maplibregl-map')) return;
            const candidates = [];
            for (let el = event.target; el && el !== document.documentElement; el = el.parentElement) {
                const css = getComputedStyle(el);
                if (/auto|scroll/.test(css.overflowY) && el.scrollHeight > el.clientHeight ||
                    /auto|scroll/.test(css.overflowX) && el.scrollWidth > el.clientWidth) candidates.push(el);
            }
            candidates.push(document.scrollingElement);
            drag = {id:event.pointerId, x:event.clientX, y:event.clientY, candidates};
        });
        document.addEventListener('pointermove', event => {
            if (!drag || drag.id !== event.pointerId || !event.buttons) return;
            const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
            if (!drag.target) {
                if (Math.max(Math.abs(dx), Math.abs(dy)) < 7) return;
                const horizontal = Math.abs(dx) > Math.abs(dy);
                drag.target = drag.candidates.find(el => horizontal ? el.scrollWidth > el.clientWidth : el.scrollHeight > el.clientHeight);
                if (!drag.target) return;
                drag.left = drag.target.scrollLeft;
                drag.top = drag.target.scrollTop;
                root.classList.add('sr-dragging');
                window.getSelection()?.removeAllRanges();
                drag.target.setPointerCapture(event.pointerId);
            }
            event.preventDefault();
            drag.target.scrollTo(drag.left - dx, drag.top - dy);
        });
        function endDrag() {
            suppressClick = Boolean(drag?.target);
            root.classList.remove('sr-dragging');
            drag = null;
        }
        document.addEventListener('pointerup', endDrag);
        document.addEventListener('pointercancel', endDrag);
        window.addEventListener('blur', endDrag);
        document.addEventListener('click', event => {
            if (suppressClick && event.detail && event.target instanceof Element &&
                !event.target.closest('a[href],button,input,select,textarea,summary,[role=button],[role=link]')) {
                event.preventDefault(); event.stopImmediatePropagation();
            }
            suppressClick = false;
        }, true);

        const counters = document.querySelector('[data-counts-url]');
        if (counters) {
            async function refresh() {
                if (document.hidden) return;
                try {
                    const response = await fetch(counters.dataset.countsUrl, {cache:'no-store'});
                    if (!response.ok) return;
                    const counts = await response.json();
                    counters.querySelectorAll('[data-count]').forEach(node => {
                        if (node.dataset.count === 'notificaciones' && window.srNotificationFeed) return;
                        const count = counts[node.dataset.count] || 0;
                        node.textContent = String(count);
                        node.hidden = count === 0;
                    });
                } catch { /* The inbox and notifications remain available on navigation. */ }
            }
            refresh();
            const timer = setInterval(refresh, 30000);
            document.addEventListener('visibilitychange', refresh);
            window.addEventListener('pagehide', () => clearInterval(timer), {once:true});
        }

        const account = document.querySelector('[data-account-toggle]');
        const options = document.getElementById('private-account-menu');
        function accountOpen(value, restore = false) {
            if (!options || !account) return;
            options.hidden = !value;
            account.setAttribute('aria-expanded', String(value));
            if (value) options.querySelector('a')?.focus();
            else if (restore) account.focus();
        }
        account?.addEventListener('click', () => accountOpen(options.hidden));
        document.addEventListener('click', event => {
            if (!event.target.closest('.private-account')) accountOpen(false);
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && options && !options.hidden) {
                event.preventDefault(); event.stopImmediatePropagation(); accountOpen(false, true);
            }
        }, true);
        options?.addEventListener('focusout', event => {
            // A null target occurs on touch/blur before the anchor's native click.
            if (event.relatedTarget instanceof Element && !event.relatedTarget.closest('.private-account')) accountOpen(false);
        });
        document.querySelector('.sr-menu-button')?.addEventListener('click', () => accountOpen(false), true);
        window.addEventListener('pagehide', () => accountOpen(false));

        // Private navigation owns its drawer lifecycle and compact rail.
        if (document.body.classList.contains('sr-private')) return;

        // ===== MENÚ / DRAWER =====
        const menu = document.getElementById('sr-navigation');
        const trigger = document.querySelector('.sr-menu-button');
        const backdrop = document.querySelector('.sr-backdrop');
        const collapse = document.querySelector('.sr-collapse');

        // Si la página no tiene menú (login sin header, etc.) no seguimos.
        if (!menu || !trigger || !backdrop) {
            return;
        }

        const wide = matchMedia('(min-width: 1100px)');
        const isDesktopPanel = () => wide.matches && menu.classList.contains('sr-sidebar');

        function updateCollapse() {
            if (!collapse) return;
            const compact = root.classList.contains('sr-compact') && !root.classList.contains('sr-nav-preview');
            const label = isDesktopPanel() ? (root.classList.contains('sr-compact') ? (compact ? 'Expandir menú' : 'Fijar menú abierto') : 'Contraer menú') : 'Cerrar menú';
            collapse.setAttribute('aria-controls', 'sr-navigation');
            collapse.setAttribute('aria-expanded', String(isDesktopPanel() ? !compact : root.classList.contains('sr-drawer-open')));
            collapse.title = label;
            collapse.setAttribute('aria-label', label);
            collapse.textContent = isDesktopPanel() ? (compact ? '⇥' : '⇤') : '×';
        }

        function drawer(open, restoreFocus = true) {
            root.classList.toggle('sr-drawer-open', open);
            backdrop.hidden = !open;
            updateCollapse();
            trigger.setAttribute('aria-expanded', String(open));
            trigger.setAttribute('aria-label', open ? 'Cerrar navegación' : 'Abrir navegación');

            // NO inertizar .sr-header: contiene el propio botón hamburguesa.
            const areas = document.querySelectorAll('#main-content, .sr-footer, .sr-mobile-nav');
            areas.forEach(area => { area.inert = open; });

            if (open) {
                menu.setAttribute('role', 'dialog');
                menu.setAttribute('aria-modal', 'true');
                (collapse || menu).focus();
            } else {
                menu.removeAttribute('role');
                menu.removeAttribute('aria-modal');
                if (restoreFocus) trigger.focus();
            }
        }

        // ── FIX CLAVE: toggle real en lugar de abrir siempre ──
        trigger.addEventListener('click', () => {
            const isOpen = root.classList.contains('sr-drawer-open');
            drawer(!isOpen);
        });
        backdrop.addEventListener('click', () => drawer(false));

        if (collapse) {
            collapse.addEventListener('click', () => {
                if (!isDesktopPanel()) return drawer(false);
                root.classList.toggle('sr-compact');
                try { localStorage.setItem('sr-sidebar-state', root.classList.contains('sr-compact') ? 'collapsed' : 'expanded'); } catch { /* The current view still works without storage. */ }
                updateCollapse();
            });
        }

        document.addEventListener('keydown', event => {
            if (!(event.ctrlKey || event.metaKey) || event.altKey || event.key.toLowerCase() !== 'b') return;
            event.preventDefault();
            if (!isDesktopPanel()) return drawer(!root.classList.contains('sr-drawer-open'));
            root.classList.toggle('sr-compact');
            try { localStorage.setItem('sr-sidebar-state', root.classList.contains('sr-compact') ? 'collapsed' : 'expanded'); } catch { /* The current view still works without storage. */ }
            updatePreview();
        });

        // Preview overlays the compact rail without shifting the page layout.
        let pointerInside = false;
        function updatePreview() {
            const keyboardInside = Boolean(menu.querySelector(':focus-visible'));
            root.classList.toggle('sr-nav-preview', isDesktopPanel() && (pointerInside || keyboardInside));
            updateCollapse();
        }
        menu.addEventListener('pointerenter', event => {
            if (event.pointerType !== 'mouse') return;
            pointerInside = true;
            updatePreview();
        });
        menu.addEventListener('pointerleave', () => {
            pointerInside = false;
            updatePreview();
        });
        menu.addEventListener('focusin', updatePreview);
        menu.addEventListener('focusout', () => requestAnimationFrame(updatePreview));
        wide.addEventListener('change', () => {
            pointerInside = false;
            drawer(false, false);
            updatePreview();
        });

        // ── FIX CLAVE: el drawer SIEMPRE arranca cerrado ──
        drawer(false, false);
        updateCollapse();

        document.addEventListener('keydown', event => {
            if (!root.classList.contains('sr-drawer-open')) return;
            if (event.key === 'Escape') return drawer(false);
            if (event.key !== 'Tab') return;
            const items = [...menu.querySelectorAll('button, a[href], summary')].filter(item => item.getClientRects().length);
            if (!items.length) return;
            if (event.shiftKey && document.activeElement === items[0]) { event.preventDefault(); items.at(-1).focus(); }
            if (!event.shiftKey && document.activeElement === items.at(-1)) { event.preventDefault(); items[0].focus(); }
        });

        const toggle = document.querySelector('#recommendationBtn');
        const modal = document.querySelector('#recommendationModal');
        if (toggle && modal && !document.body.classList.contains('sr-discover')) {
            toggle.addEventListener('click', () => requestAnimationFrame(() => modal.querySelector('textarea')?.focus()));
            document.addEventListener('keydown', event => {
                if (event.key === 'Escape' && modal.style.display === 'flex') {
                    modal.querySelector('.close-modal')?.click();
                    toggle.focus();
                }
            });
        }
    });
})();
