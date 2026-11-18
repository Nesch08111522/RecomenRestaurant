(() => {
    const root = document.documentElement;
    root.classList.add('sr-compact');
    try {
        const saved = localStorage.getItem('theme');
        root.dataset.theme = ['dark', 'light'].includes(saved) ? saved : 'light';
    } catch { root.dataset.theme = 'light'; }

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
                event.target.closest('input,textarea,select,button,[contenteditable=true],.map-container,.leaflet-container,.maplibregl-map')) return;
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
            if (suppressClick && event.detail) { event.preventDefault(); event.stopImmediatePropagation(); }
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
        const menu = document.getElementById('sr-navigation');
        const trigger = document.querySelector('.sr-menu-button');
        const backdrop = document.querySelector('.sr-backdrop');
        const collapse = document.querySelector('.sr-collapse');
        const wide = matchMedia('(min-width: 1100px)');
        const isDesktopPanel = () => wide.matches && !document.body.classList.contains('sr-discover');
        function drawer(open, restoreFocus = true) {
            root.classList.toggle('sr-drawer-open', open);
            backdrop.hidden = !open;
            updateCollapse();
            trigger.setAttribute('aria-expanded', String(open));
            trigger.setAttribute('aria-label', open ? 'Cerrar navegación' : 'Abrir navegación');
            const areas = document.querySelectorAll('.sr-header, #main-content, .sr-footer, .sr-mobile-nav');
            areas.forEach(area => { area.inert = open; });
            if (open) {
                menu.setAttribute('role', 'dialog');
                menu.setAttribute('aria-modal', 'true');
                collapse.focus();
            } else {
                menu.removeAttribute('role');
                menu.removeAttribute('aria-modal');
                if (restoreFocus) trigger.focus();
            }
        }
        function updateCollapse() {
            const compact = root.classList.contains('sr-compact');
            const label = isDesktopPanel() ? (compact ? 'Expandir menú' : 'Contraer menú') : 'Cerrar menú';
            collapse.setAttribute('aria-controls', 'sr-navigation');
            collapse.setAttribute('aria-expanded', String(isDesktopPanel() ? !compact : root.classList.contains('sr-drawer-open')));
            collapse.title = label;
            collapse.setAttribute('aria-label', label);
            collapse.textContent = isDesktopPanel() ? (compact ? '⇥' : '⇤') : '×';
        }
        trigger.addEventListener('click', () => drawer(true));
        backdrop.addEventListener('click', () => drawer(false));
        collapse.addEventListener('click', () => {
            if (!isDesktopPanel()) return drawer(false);
            root.classList.toggle('sr-compact');
            updateCollapse();
        });
        wide.addEventListener('change', () => { drawer(false, false); updateCollapse(); });
        updateCollapse();
        document.addEventListener('keydown', event => {
            if (!root.classList.contains('sr-drawer-open')) return;
            if (event.key === 'Escape') return drawer(false);
            if (event.key !== 'Tab') return;
            const items = [...menu.querySelectorAll('button, a[href]')];
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
