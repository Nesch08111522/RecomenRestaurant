/**
 * SmartResto - Panel de Administración
 * Paradigma: Imperativo / Orientado a Objetos
 */

// ============================================
// ADMIN CONTROLLER
// ============================================

class AdminController {
    constructor() {
        this.chartInstances = {};
        this.init();
    }

    init() {
        // Gráficos: solo si estamos en el dashboard
        if (document.querySelector('.charts-container')) {
            setTimeout(() => this.loadAnalytics(), 300);
        }

        this.initTable();   // tabla de restaurantes
        this.initModals();  // modal de edición
    }

    // ------------------------------------------------------------
    // Utilidad: fetch que espera JSON y da errores claros
    // (evita "Unexpected token '<'" cuando el servidor devuelve HTML)
    // ------------------------------------------------------------
    async requestJSON(url, method = 'GET', payload = null) {
        const opts = { method, headers: { 'Accept': 'application/json' } };

        // Token CSRF si lo usas (<meta name="csrf-token"> en base.html)
        const csrf = document.querySelector('meta[name="csrf-token"]');
        if (csrf) opts.headers['X-CSRFToken'] = csrf.content;

        if (payload) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(payload);
        }

        const res = await fetch(url, opts);
        const isJson = (res.headers.get('content-type') || '').includes('application/json');

        if (!res.ok || !isJson) {
            let msg;
            if (isJson) {
                msg = (await res.json().catch(() => ({}))).error || `Error ${res.status}`;
            } else if (res.redirected || res.status === 401 || res.status === 403) {
                msg = 'Sesión expirada o sin permisos';
            } else {
                msg = `El servidor devolvió HTML (status ${res.status}) en ${url}`;
            }
            throw new Error(msg);
        }
        return res.json();
    }

    // ============================================
    // GRÁFICOS
    // ============================================

    destroyAllCharts() {
        // Instancias guardadas por nosotros
        Object.keys(this.chartInstances).forEach(key => {
            try {
                this.chartInstances[key].destroy();
            } catch (e) {
                console.warn(`⚠️ Error destruyendo gráfico ${key}:`, e);
            }
            delete this.chartInstances[key];
        });

        // Cualquier otro gráfico de Chart.js que siga en un canvas
        if (typeof Chart !== 'undefined' && Chart.getChart) {
            document.querySelectorAll('canvas').forEach(canvas => {
                const old = Chart.getChart(canvas);
                if (old) old.destroy();
            });
        }
    }

    async loadAnalytics() {
        try {
            this.destroyAllCharts();

            const data = await this.requestJSON('/admin/api/analytics');

            if (!data || !data.prices || !data.ratings) {
                console.warn('⚠️ Datos insuficientes para crear gráficos');
                return;
            }

            setTimeout(() => this.createCharts(data), 100);
        } catch (error) {
            console.error('❌ Error cargando analytics:', error);
            this.showError('Error al cargar los datos de gráficos: ' + error.message);
        }
    }

    showError(message) {
        const container = document.querySelector('.charts-container');
        if (!container) return;

        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            grid-column: 1 / -1;
            padding: 20px;
            background: #fee2e2;
            border-radius: 8px;
            color: #991b1b;
            text-align: center;
            border: 1px solid #fca5a5;
        `;

        const icon = document.createElement('i');
        icon.className = 'fas fa-exclamation-triangle';
        icon.style.fontSize = '20px';

        const p = document.createElement('p');
        p.style.marginTop = '8px';
        p.textContent = message; // textContent: evita inyectar HTML

        errorDiv.append(icon, p);
        container.prepend(errorDiv);
    }

    /** Crea (o recrea) un gráfico en el canvas indicado */
    makeChart(key, canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        try {
            const old = Chart.getChart ? Chart.getChart(canvas) : null;
            if (old) old.destroy();
            this.chartInstances[key] = new Chart(canvas, config);
        } catch (error) {
            console.error(`❌ Error creando gráfico ${key}:`, error);
        }
    }

    createCharts(data) {
        const css = getComputedStyle(document.documentElement);
        const primaryColor = css.getPropertyValue('--primary').trim() || '#FF385C';
        const secondaryColor = css.getPropertyValue('--secondary').trim() || '#008489';

        const palette = ['#FF385C', '#008489', '#FFB800', '#00A699', '#FF5A5F',
                         '#767676', '#4A90D9', '#27AE60', '#E74C3C', '#8E44AD'];

        const legendBottom = {
            position: 'bottom',
            labels: { padding: 12, usePointStyle: true, pointStyle: 'circle' }
        };

        // 1. Precio promedio
        if (data.prices && data.prices.length > 0) {
            this.makeChart('price', 'priceChart', {
                type: 'bar',
                data: {
                    labels: data.prices.map((_, i) => `Rest ${i + 1}`),
                    datasets: [{
                        label: 'Precio Promedio (S/.)',
                        data: data.prices,
                        backgroundColor: primaryColor,
                        borderColor: primaryColor + 'dd',
                        borderWidth: 1,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { callback: (value) => 'S/.' + value }
                        }
                    }
                }
            });
        } else {
            console.warn('⚠️ No hay datos de precios para el gráfico');
        }

        // 2. Rating
        if (data.ratings && data.ratings.length > 0) {
            this.makeChart('rating', 'ratingChart', {
                type: 'line',
                data: {
                    labels: data.ratings.map((_, i) => `Rest ${i + 1}`),
                    datasets: [{
                        label: 'Rating',
                        data: data.ratings,
                        borderColor: secondaryColor,
                        backgroundColor: secondaryColor + '33',
                        fill: true,
                        tension: 0.1,
                        pointBackgroundColor: secondaryColor,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, max: 5, ticks: { stepSize: 0.5 } } }
                }
            });
        } else {
            console.warn('⚠️ No hay datos de ratings para el gráfico');
        }

        // 3. Categorías (dona) y 4. Distritos (pastel)
        const circular = [
            { key: 'categories', canvasId: 'categoryChart', type: 'doughnut', source: data.categories },
            { key: 'districts',  canvasId: 'districtChart', type: 'pie',      source: data.districts }
        ];

        circular.forEach(({ key, canvasId, type, source }) => {
            if (!source || Object.keys(source).length === 0) {
                console.warn(`⚠️ No hay datos de ${key} para el gráfico`);
                return;
            }
            const labels = Object.keys(source);
            this.makeChart(key, canvasId, {
                type,
                data: {
                    labels,
                    datasets: [{
                        data: Object.values(source),
                        backgroundColor: palette.slice(0, labels.length),
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: legendBottom }
                }
            });
        });
    }

    // ============================================
    // TABLA DE RESTAURANTES
    // ============================================

    initTable() {
        // Se excluye la tabla de usuarios (.users-table): tiene su propio modal
        const scope = '.admin-table:not(.users-table) ';

        const tableSearch = document.getElementById('tableSearch');
        if (tableSearch) {
            tableSearch.addEventListener('input', (e) => this.filterTable(e.target.value));
        }

        const tableFilter = document.getElementById('tableFilter');
        if (tableFilter) {
            tableFilter.addEventListener('change', (e) => this.filterTableByStatus(e.target.value));
        }

        document.querySelectorAll(scope + '.edit-btn').forEach(btn => {
            btn.addEventListener('click', () => this.editRestaurant(btn.dataset.id));
        });

        document.querySelectorAll(scope + '.delete-btn').forEach(btn => {
            btn.addEventListener('click', () => this.deleteRestaurant(btn.dataset.id));
        });

        document.querySelectorAll(scope + '.promo-btn').forEach(btn => {
            btn.addEventListener('click', () => this.addPromotion(btn.dataset.id));
        });
    }

    filterTable(query) {
        const rows = document.querySelectorAll('.admin-table:not(.users-table) tbody tr');
        const q = query.toLowerCase();

        rows.forEach(row => {
            row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
        });
    }

    filterTableByStatus(status) {
        const rows = document.querySelectorAll('.admin-table:not(.users-table) tbody tr');

        rows.forEach(row => {
            if (!status) {
                row.style.display = '';
                return;
            }

            const statusBadge = row.querySelector('.status-badge');
            if (statusBadge) {
                const isActive = statusBadge.classList.contains('status-open');
                const show = (status === 'active' && isActive) ||
                             (status === 'inactive' && !isActive);
                row.style.display = show ? '' : 'none';
            }
        });
    }

    // ============================================
    // MODAL DE EDICIÓN
    // ============================================

    initModals() {
        const editModal = document.getElementById('editModal');
        const closeModal = document.querySelector('.close-modal');
        const form = document.getElementById('editForm');

        // Cerrar con la X, clic afuera o Esc
        if (closeModal && editModal) {
            closeModal.addEventListener('click', () => { editModal.style.display = 'none'; });
        }
        window.addEventListener('click', (e) => {
            if (editModal && e.target === editModal) editModal.style.display = 'none';
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && editModal) editModal.style.display = 'none';
        });

        // Guardar al enviar el formulario
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveRestaurant(form);
            });
        }
    }

    // Carga los datos del restaurante en el modal (ruta ADMIN, devuelve JSON)
    async editRestaurant(id) {
        try {
            const data = await this.requestJSON(`/admin/restaurant/${id}`);

            const form = document.getElementById('editForm');
            if (!form) return;

            form.dataset.id = id;
            form.querySelector('input[name="name"]').value = data.name ?? '';
            form.querySelector('input[name="avg_price"]').value = data.avg_price ?? '';
            form.querySelector('input[name="rating"]').value = data.rating ?? '';
            form.querySelector('textarea[name="description"]').value = data.description ?? '';

            document.getElementById('editModal').style.display = 'block';
        } catch (error) {
            console.error('Error cargando restaurante para editar:', error);
            alert(error.message);
        }
    }

    // Valida y guarda los cambios
    async saveRestaurant(form) {
        const id = form.dataset.id;
        if (!id) return;

        const payload = {
            name: form.querySelector('input[name="name"]').value.trim(),
            avg_price: parseFloat(form.querySelector('input[name="avg_price"]').value),
            rating: parseFloat(form.querySelector('input[name="rating"]').value),
            description: form.querySelector('textarea[name="description"]').value.trim()
        };

        if (!payload.name) { alert('El nombre es obligatorio'); return; }
        if (Number.isNaN(payload.avg_price) || payload.avg_price < 0) { alert('Precio inválido'); return; }
        if (Number.isNaN(payload.rating) || payload.rating < 0 || payload.rating > 5) {
            alert('El rating debe estar entre 0 y 5');
            return;
        }

        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;

        try {
            await this.requestJSON(`/admin/restaurant/${id}`, 'PUT', payload);
            location.reload();
        } catch (error) {
            console.error('Error guardando restaurante:', error);
            alert(error.message);
            if (submitBtn) submitBtn.disabled = false;
        }
    }

    // ============================================
    // ELIMINAR / PROMOCIÓN
    // ============================================

    async deleteRestaurant(id) {
        if (!confirm('¿Estás seguro de eliminar este restaurante?')) return;

        try {
            await this.requestJSON(`/admin/restaurant/${id}`, 'DELETE');
            location.reload();
        } catch (error) {
            console.error('Error eliminando restaurante:', error);
            alert(error.message);
        }
    }

    async addPromotion(id) {
        const promoText = prompt('Ingresa la promoción para este restaurante:');
        if (promoText === null) return;

        try {
            await this.requestJSON(`/admin/restaurant/${id}`, 'PUT', { promo: promoText.trim() });
            location.reload();
        } catch (error) {
            console.error('Error agregando promoción:', error);
            alert(error.message);
        }
    }
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    window.admin = new AdminController();
});