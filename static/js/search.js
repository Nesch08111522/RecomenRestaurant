/**
 * SmartResto - Búsqueda y Filtros en Tiempo Real
 * Paradigma: Funcional / Reactivo
 */

// ============================================
// CONFIGURACIÓN
// ============================================

const SEARCH_CONFIG = {
    debounceDelay: 300,
    maxResults: 20,
    minQueryLength: 2
};

// ============================================
// DEBOUNCE (Función pura)
// ============================================

function debounce(fn, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
}

// ============================================
// FILTROS FUNCIONALES
// ============================================

const FilterFunctions = {
    byText: (restaurants, query) => {
        if (!query || query.length < SEARCH_CONFIG.minQueryLength) {
            return restaurants;
        }
        const q = query.toLowerCase();
        return restaurants.filter(r => 
            r.name.toLowerCase().includes(q) ||
            r.description?.toLowerCase().includes(q) ||
            r.tags?.some(tag => tag.toLowerCase().includes(q)) ||
            r.district?.toLowerCase().includes(q)
        );
    },
    
    byCategory: (restaurants, categoryId) => {
        if (!categoryId) return restaurants;
        return restaurants.filter(r => r.category_id == categoryId);
    },
    
    byDistrict: (restaurants, district) => {
        if (!district) return restaurants;
        return restaurants.filter(r => r.district === district);
    },
    
    byPrice: (restaurants, maxPrice) => {
        if (!maxPrice || maxPrice <= 0) return restaurants;
        return restaurants.filter(r => r.avg_price <= maxPrice);
    }
};

// ============================================
// BÚSQUEDA EN TIEMPO REAL - CORREGIDA
// ============================================

class RealTimeSearch {
    constructor() {
        this.searchForm = document.getElementById('search-form');
        this.resultsGrid = document.getElementById('resultsGrid');
        this.resultsCount = document.getElementById('resultsCount');
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        if (this.searchForm) {
            this.searchForm.addEventListener('input', () => this.controller?.abort());
            // ✅ Evento submit del formulario
            this.searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.performSearch();
            });
            
            // ✅ Búsqueda en tiempo real con debounce
            const searchInput = this.searchForm.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.addEventListener('input', debounce((e) => {
                    this.performSearch();
                }, SEARCH_CONFIG.debounceDelay));
            }
            
            // ✅ Cambios en selects
            const selects = this.searchForm.querySelectorAll('select');
            selects.forEach(select => {
                select.addEventListener('change', () => {
                    this.performSearch();
                });
            });
            
            // ✅ Cambios en input de precio
            const priceInput = this.searchForm.querySelector('input[name="max_price"]');
            if (priceInput) {
                priceInput.addEventListener('input', debounce(() => {
                    this.performSearch();
                }, SEARCH_CONFIG.debounceDelay));
            }
        }
    }
    
    async performSearch() {
        this.controller?.abort();
        const controller = new AbortController();
        this.controller = controller;
        
        // Obtener valores del formulario
        const formData = new FormData(this.searchForm);
        
        // ✅ Usar los IDs correctos del header
        const district = document.getElementById('district-select')?.value || '';
        const category = document.getElementById('category-select')?.value || '';
        const maxPrice = document.querySelector('input[name="max_price"]')?.value || '';
        const query = formData.get('q') || '';
        
        const filters = {
            district: district,
            category_id: category ? parseInt(category) : null,
            max_price: maxPrice ? parseFloat(maxPrice) : null,
            search_query: query,
            lat: typeof INITIAL_COORDS !== 'undefined' ? INITIAL_COORDS[0] : -8.1118,
            lng: typeof INITIAL_COORDS !== 'undefined' ? INITIAL_COORDS[1] : -79.0287
        };
        
        console.log('🔍 Buscando con filtros:', filters);
        
        this.showLoading();
        
        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(filters)
            });
            
            if (!response.ok) throw new Error("search");
            const data = await response.json();
            if (controller.signal.aborted) return;
            console.log('📥 Resultados:', data);
            
            const results = Array.isArray(data) ? data : (Array.isArray(data.results) ? data.results : []);
            this.updateResults(results);
            this.updateMapMarkers(results);
        } catch (error) {
            if (controller.signal.aborted) return;
            console.error('❌ Error en la búsqueda:', error);
            this.showError('Error al realizar la búsqueda. Por favor intenta de nuevo.');
        } finally {
            if (this.controller === controller) this.hideLoading();
        }
    }
    
    updateResults(results) {
        const grid = this.resultsGrid;
        if (!grid) return;
        
        if (this.resultsCount) {
            this.resultsCount.textContent = `${results.length} restaurantes encontrados`;
        }
        
        if (results.length === 0) {
            document.getElementById('restaurant-pagination')?.remove();
            grid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-utensils" style="font-size: 48px; color: var(--gray);"></i>
                    <h3 style="margin-top: 16px;">No encontramos restaurantes</h3>
                    <p style="color: var(--gray);">Intenta con otros filtros o ubicación</p>
                </div>
            `;
            return;
        }
        
        // ✅ Usar la misma función de renderizado que app.js
        if (window.app) {
            window.app.state.filteredRestaurants = results;
            window.app.renderRestaurants();
        } else {
            // Fallback: renderizado manual
            grid.innerHTML = results.map(r => this.createRestaurantCard(r)).join('');
        }
    }
    
    createRestaurantCard(r) {
        if (!Number.isSafeInteger(Number(r.id))) return "";
        const esc = window.escapeDisplayText;
        const tags = r.tags?.slice(0, 3).map(t => `<span class="tag">${esc(t)}</span>`).join('') || '';
        const promo = r.promo ? `<div class="promo-badge"><i class="fas fa-tag"></i> Promoción</div>` : '';
        const topRated = r.rating >= 4.5 ? `<div class="top-rated-badge"><i class="fas fa-star"></i> Top</div>` : '';
        const justification = r.justifications && r.justifications.length > 0 
            ? `<div class="ia-justification"><i class="fas fa-robot"></i><span>${esc(r.justifications[0])}</span></div>`
            : '';
        const distance = r.distance_km ? r.distance_km.toFixed(1) : '?';
        const currency = typeof MONEDA !== 'undefined' ? MONEDA : 'S/.';
        
        return `
            <div class="restaurant-card" 
                 data-id="${Number(r.id)}"
                 data-lat="${esc(r.lat)}"
                 data-lng="${esc(r.lng)}"
                 onmouseenter="highlightMarker(${Number(r.id)})"
                 onmouseleave="resetMarker(${Number(r.id)})">
                
                <div class="card-image">
                    ${r.image ? `<img src="${esc(r.image)}" alt="${esc(r.name)}" loading="lazy">` : ""}
                    ${promo}
                    ${topRated}
                    <button class="fav-btn" onclick="toggleFavorite(${Number(r.id)}, event)">
                        <i class="far fa-heart"></i>
                    </button>
                </div>
                
                <div class="card-content">
                    <div class="card-header">
                        <h3>${esc(r.name)}</h3>
                        <div class="rating">
                            <i class="fas fa-star"></i>
                            <span>${esc(r.rating)}</span>
                        </div>
                    </div>
                    
                    <div class="card-location">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${esc(r.district)}</span>
                        <span class="dot">•</span>
                        <span class="distance">${distance} km</span>
                    </div>
                    
                    <div class="card-price">
                        <span class="price">${currency}${esc(r.avg_price)}</span>
                        <span class="price-label">por persona</span>
                    </div>
                    
                    <div class="card-tags">${tags}</div>
                    
                    ${justification}
                    
                    <a href="/restaurant/${Number(r.id)}" class="card-link">
                        Ver detalles <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
            </div>
        `;
    }
    
    updateMapMarkers(restaurants) {
        if (typeof window.updateMarkers === 'function') {
            window.updateMarkers(restaurants);
        }
    }
    
    showLoading() {
        this.isLoading = true;
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) {
            spinner.style.display = 'block';
        }
    }
    
    hideLoading() {
        this.isLoading = false;
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) {
            spinner.style.display = 'none';
        }
    }
    
    showError(message) {
        const grid = this.resultsGrid;
        if (grid) {
            grid.innerHTML = `
                <div class="empty-state" style="border: 1px solid #fca5a5; background: #fee2e2;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #991b1b;"></i>
                    <h3 style="margin-top: 16px; color: #991b1b;">Error</h3>
                    <p style="color: #991b1b;">${message}</p>
                </div>
            `;
        }
    }
}

// ============================================
// FILTRO POR CATEGORÍA (DESDE CHIPS)
// ============================================

async function filterByCategory(catId, event) {
    // Remover clase active de todos los chips
    document.querySelectorAll('.filter-chip.category-chip').forEach(c => c.classList.remove('active'));
    
    // Agregar clase active al chip clickeado
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
    
    const select = document.getElementById('category-select');
    if (select) select.value = catId || '';
    if (window.search?.searchForm) await window.search.performSearch();
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar búsqueda en tiempo real
    window.search = new RealTimeSearch();
    
    // ✅ Eventos para los chips de categoría
    document.querySelectorAll('.filter-chip.category-chip').forEach(chip => {
        chip.addEventListener('click', function(e) {
            const catId = this.dataset.category;
            filterByCategory(catId, e);
        });
    });
    
    // ✅ Evento para el chip "Todos"
    document.querySelectorAll('.filter-chip[data-filter="all"]').forEach(chip => {
        chip.addEventListener('click', function() {
            // Remover active de todos los chips de categoría
            document.querySelectorAll('.filter-chip.category-chip').forEach(c => c.classList.remove('active'));
            // Ejecutar búsqueda sin filtro de categoría
            filterByCategory(null, null);
        });
    });
});

// Funciones globales
window.filterByCategory = filterByCategory;
window.performSearch = function() {
    if (window.search) {
        window.search.performSearch();
    }
};