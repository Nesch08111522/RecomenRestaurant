/**
 * SmartResto - Panel de Administración
 * Paradigma: Imperativo / Orientado a Objetos
 */

// ============================================
// ADMIN CONTROLLER
// ============================================

class AdminController {
    constructor() {
        this.charts = {};
        this.chartInstances = {};
        this.init();
    }
    
    init() {
        // Inicializar gráficos si estamos en el dashboard
        if (document.querySelector('.charts-container')) {
            // Esperar a que el DOM esté completamente cargado
            setTimeout(() => {
                this.loadAnalytics();
            }, 300);
        }
        
        // Inicializar tabla de gestión
        this.initTable();
        
        // Inicializar modales de edición
        this.initModals();
    }
    
    /**
     * Destruye TODOS los gráficos existentes de manera segura
     */
    destroyAllCharts() {
        // Método 1: Usar el objeto chartInstances
        Object.keys(this.chartInstances).forEach(key => {
            if (this.chartInstances[key]) {
                try {
                    this.chartInstances[key].destroy();
                    console.log(`✅ Gráfico ${key} destruido`);
                } catch (e) {
                    console.warn(`⚠️ Error destruyendo gráfico ${key}:`, e);
                }
                delete this.chartInstances[key];
            }
        });
        
        // Método 2: Buscar todos los canvas con gráficos de Chart.js
        document.querySelectorAll('canvas').forEach(canvas => {
            try {
                // Verificar si el canvas tiene un gráfico asociado
                if (canvas.chart) {
                    canvas.chart.destroy();
                    console.log(`✅ Canvas ${canvas.id} limpiado`);
                }
            } catch (e) {
                // Ignorar si no se puede destruir
            }
        });
        
        // Limpiar el objeto charts
        this.charts = {};
    }
    
    async loadAnalytics() {
        try {
            // ✅ Destruir gráficos existentes ANTES de cargar nuevos datos
            this.destroyAllCharts();
            
            const response = await fetch('/admin/api/analytics');
            
            // Verificar que la respuesta sea exitosa
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('📊 Datos recibidos para gráficos:', data);
            
            // Verificar que los datos existen
            if (!data || !data.prices || !data.ratings) {
                console.warn('⚠️ Datos insuficientes para crear gráficos');
                return;
            }
            
            // Crear gráficos con un pequeño delay
            setTimeout(() => {
                this.createCharts(data);
            }, 100);
            
        } catch (error) {
            console.error('❌ Error cargando analytics:', error);
            this.showError('Error al cargar los datos de gráficos: ' + error.message);
        }
    }
    
    showError(message) {
        const container = document.querySelector('.charts-container');
        if (container) {
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
            errorDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle" style="font-size: 20px;"></i>
                <p style="margin-top: 8px;">${message}</p>
            `;
            container.prepend(errorDiv);
        }
    }
    
    createCharts(data) {
        // Obtener colores del CSS
        const primaryColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--primary').trim() || '#FF385C';
        const secondaryColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--secondary').trim() || '#008489';
        
        // 1. Gráfico de distribución por precio
        const priceCtx = document.getElementById('priceChart');
        if (priceCtx && data.prices && data.prices.length > 0) {
            try {
                // Asegurar que el canvas está limpio
                if (priceCtx.chart) {
                    priceCtx.chart.destroy();
                }
                
                this.chartInstances.price = new Chart(priceCtx, {
                    type: 'bar',
                    data: {
                        labels: data.prices.map((_, i) => `Rest ${i+1}`),
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
                        plugins: {
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) {
                                        return 'S/.' + value;
                                    }
                                }
                            }
                        }
                    }
                });
                console.log('✅ Gráfico de precios creado');
            } catch (error) {
                console.error('❌ Error creando gráfico de precios:', error);
            }
        } else {
            console.warn('⚠️ No hay datos de precios para el gráfico');
        }
        
        // 2. Gráfico de rating
        const ratingCtx = document.getElementById('ratingChart');
        if (ratingCtx && data.ratings && data.ratings.length > 0) {
            try {
                if (ratingCtx.chart) {
                    ratingCtx.chart.destroy();
                }
                
                this.chartInstances.rating = new Chart(ratingCtx, {
                    type: 'line',
                    data: {
                        labels: data.ratings.map((_, i) => `Rest ${i+1}`),
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
                        plugins: {
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 5,
                                ticks: {
                                    stepSize: 0.5
                                }
                            }
                        }
                    }
                });
                console.log('✅ Gráfico de ratings creado');
            } catch (error) {
                console.error('❌ Error creando gráfico de ratings:', error);
            }
        } else {
            console.warn('⚠️ No hay datos de ratings para el gráfico');
        }
        
        // 3. Gráfico de categorías
        const catCtx = document.getElementById('categoryChart');
        if (catCtx && data.categories && Object.keys(data.categories).length > 0) {
            try {
                if (catCtx.chart) {
                    catCtx.chart.destroy();
                }
                
                const labels = Object.keys(data.categories);
                const values = Object.values(data.categories);
                const colors = ['#FF385C', '#008489', '#FFB800', '#00A699', '#FF5A5F', '#767676', '#4A90D9', '#27AE60', '#E74C3C', '#8E44AD'];
                
                this.chartInstances.categories = new Chart(catCtx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors.slice(0, labels.length),
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 12,
                                    usePointStyle: true,
                                    pointStyle: 'circle'
                                }
                            }
                        }
                    }
                });
                console.log('✅ Gráfico de categorías creado');
            } catch (error) {
                console.error('❌ Error creando gráfico de categorías:', error);
            }
        } else {
            console.warn('⚠️ No hay datos de categorías para el gráfico');
        }
        
        // 4. Gráfico de distritos
        const distCtx = document.getElementById('districtChart');
        if (distCtx && data.districts && Object.keys(data.districts).length > 0) {
            try {
                if (distCtx.chart) {
                    distCtx.chart.destroy();
                }
                
                const labels = Object.keys(data.districts);
                const values = Object.values(data.districts);
                const colors = ['#FF385C', '#008489', '#FFB800', '#00A699', '#FF5A5F', '#767676', '#4A90D9', '#27AE60'];
                
                this.chartInstances.districts = new Chart(distCtx, {
                    type: 'pie',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors.slice(0, labels.length),
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 12,
                                    usePointStyle: true,
                                    pointStyle: 'circle'
                                }
                            }
                        }
                    }
                });
                console.log('✅ Gráfico de distritos creado');
            } catch (error) {
                console.error('❌ Error creando gráfico de distritos:', error);
            }
        } else {
            console.warn('⚠️ No hay datos de distritos para el gráfico');
        }
    }
    
    initTable() {
        // Búsqueda en tabla
        const tableSearch = document.getElementById('tableSearch');
        if (tableSearch) {
            tableSearch.addEventListener('input', (e) => {
                this.filterTable(e.target.value);
            });
        }
        
        // Filtros de tabla
        const tableFilter = document.getElementById('tableFilter');
        if (tableFilter) {
            tableFilter.addEventListener('change', (e) => {
                this.filterTableByStatus(e.target.value);
            });
        }
        
        // Acciones de edición
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.editRestaurant(btn.dataset.id);
            });
        });
        
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.deleteRestaurant(btn.dataset.id);
            });
        });
        
        document.querySelectorAll('.promo-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.addPromotion(btn.dataset.id);
            });
        });
    }
    
    filterTable(query) {
        const rows = document.querySelectorAll('.admin-table tbody tr');
        const q = query.toLowerCase();
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(q) ? '' : 'none';
        });
    }
    
    filterTableByStatus(status) {
        const rows = document.querySelectorAll('.admin-table tbody tr');
        
        rows.forEach(row => {
            if (!status) {
                row.style.display = '';
                return;
            }
            
            const statusBadge = row.querySelector('.status-badge');
            if (statusBadge) {
                const isActive = statusBadge.classList.contains('status-open');
                row.style.display = (status === 'active' && isActive) || 
                                   (status === 'inactive' && !isActive) ? '' : 'none';
            }
        });
    }
    
    initModals() {
        const editModal = document.getElementById('editModal');
        const closeModal = document.querySelector('.close-modal');
        
        if (closeModal) {
            closeModal.addEventListener('click', () => {
                editModal.style.display = 'none';
            });
        }
        
        window.addEventListener('click', (e) => {
            if (e.target === editModal) {
                editModal.style.display = 'none';
            }
        });
    }
    
    async editRestaurant(id) {
        try {
            const response = await fetch(`/restaurant/${id}`);
            const data = await response.json();
            
            const form = document.getElementById('editForm');
            if (form) {
                form.dataset.id = id;
                form.querySelector('input[name="name"]').value = data.name;
                form.querySelector('input[name="avg_price"]').value = data.avg_price;
                form.querySelector('input[name="rating"]').value = data.rating;
                form.querySelector('textarea[name="description"]').value = data.description;
                
                document.getElementById('editModal').style.display = 'block';
            }
        } catch (error) {
            console.error('Error cargando restaurante para editar:', error);
        }
    }
    
    async deleteRestaurant(id) {
        if (!confirm('¿Estás seguro de eliminar este restaurante?')) return;
        
        try {
            const response = await fetch(`/admin/restaurant/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                location.reload();
            } else {
                alert('Error al eliminar el restaurante');
            }
        } catch (error) {
            console.error('Error eliminando restaurante:', error);
        }
    }
    
    async addPromotion(id) {
        const promoText = prompt('Ingresa la promoción para este restaurante:');
        if (promoText === null) return;
        
        try {
            const response = await fetch(`/admin/restaurant/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ promo: promoText })
            });
            
            if (response.ok) {
                location.reload();
            } else {
                alert('Error al agregar promoción');
            }
        } catch (error) {
            console.error('Error agregando promoción:', error);
        }
    }
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    window.admin = new AdminController();
});