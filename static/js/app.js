class AppController {
    constructor() {
        this.state = {
            restaurants: [],
            filteredRestaurants: [],
            currentView: 'grid',
            favorites: [],
            user: null,
            theme: 'light'
        };

        this.elements = {};
        this.init();
    }

    init() {
        this.injectCardStyles();

        this.elements = {
            resultsGrid: document.getElementById('resultsGrid'),
            resultsCount: document.getElementById('resultsCount'),
            searchForm: document.getElementById('search-form'),
            themeToggle: document.getElementById('themeToggle'),
            locationBtn: document.getElementById('locationBtn'),
            loadMoreBtn: document.getElementById('loadMoreBtn'),
            recommendationBtn: document.getElementById('recommendationBtn'),
            recommendationModal: document.getElementById('recommendationModal'),
            recommendationForm: document.getElementById('recommendationForm'),
            notificationBtn: document.getElementById('notificationsBtn'),
            notificationPanel: document.getElementById('notificationPanel'),
            userMenuBtn: document.getElementById('userMenuBtn'),
            userDropdown: document.getElementById('userDropdown')
        };

        this.loadState();

        this.loadFavorites();

        this.bindEvents();

        this.loadRestaurants();

        this.applyTheme();
    }

    loadState() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            this.state.theme = savedTheme;
        }

        const savedFavorites = localStorage.getItem('favorites');
        if (savedFavorites) {
            this.state.favorites = JSON.parse(savedFavorites);
        }

        const savedLat = localStorage.getItem('userLat');
        const savedLng = localStorage.getItem('userLng');
        if (savedLat && savedLng) {
            this.state.userLocation = {
                lat: parseFloat(savedLat),
                lng: parseFloat(savedLng)
            };
        }
    }

    saveState() {
        localStorage.setItem('theme', this.state.theme);
        localStorage.setItem('favorites', JSON.stringify(this.state.favorites));
    }

    bindEvents() {
        this.elements.themeToggle?.addEventListener('click', () => {
            this.toggleTheme();
        });

        this.elements.searchForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSearch();
        });

        this.elements.locationBtn?.addEventListener('click', () => {
            console.log('🟢 Botón de ubicación clickeado');
            this.getUserLocation();
        });

        this.elements.loadMoreBtn?.addEventListener('click', () => {
            this.loadMoreRestaurants();
        });

        this.elements.recommendationBtn?.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('🔍 Botón de recomendación clickeado');
            this.openRecommendationModal();
        });

        document.querySelector('.close-modal')?.addEventListener('click', () => {
            this.closeRecommendationModal();
        });

        this.elements.recommendationForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.getRecommendations();
        });

        this.elements.notificationBtn?.addEventListener('click', () => {
            this.toggleNotifications();
        });

        this.elements.userMenuBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.elements.userDropdown?.classList.toggle('show');
        });

        document.addEventListener('click', () => {
            this.elements.userDropdown?.classList.remove('show');
        });

        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                this.applyFilter(chip);
            });
        });

        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.changeView(btn.dataset.view);
            });
        });

        const resultsColumn = document.querySelector('.results-column');
        if (resultsColumn) {
            resultsColumn.addEventListener('scroll', () => {
                this.handleScroll();
            });
        }

        const modal = this.elements.recommendationModal;
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeRecommendationModal();
                }
            });
        }
    }

    loadRestaurants() {
        if (typeof RESTAURANTS_DATA !== 'undefined') {
            this.state.restaurants = RESTAURANTS_DATA;
            this.state.filteredRestaurants = RESTAURANTS_DATA;
            this.renderRestaurants();
        }
    }

    renderRestaurants() {
        const grid = this.elements.resultsGrid;
        if (!grid) return;

        if (this.state.filteredRestaurants.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-utensils"></i>
                    <h3>No encontramos restaurantes</h3>
                    <p>Intenta con otros filtros o ubicación</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.state.filteredRestaurants.map(r =>
            this.renderRestaurantCard(r)
        ).join('');

        if (this.elements.resultsCount) {
            this.elements.resultsCount.textContent =
                `${this.state.filteredRestaurants.length} restaurantes encontrados`;
        }
    }

    injectCardStyles() {
        if (document.getElementById('rc-card-styles')) return;

        const style = document.createElement('style');
        style.id = 'rc-card-styles';
        style.textContent = `
            .restaurant-card.rc {
                background: var(--white, #fff);
                border: 1px solid rgba(17, 24, 39, 0.06);
                border-radius: 18px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(17, 24, 39, 0.06);
                transition: transform .25s ease, box-shadow .25s ease;
            }
            .restaurant-card.rc:hover {
                transform: translateY(-5px);
                box-shadow: 0 14px 30px rgba(17, 24, 39, 0.14);
            }

            .restaurant-card.rc .card-image img { transition: transform .5s ease; }
            .restaurant-card.rc:hover .card-image img { transform: scale(1.06); }

            .restaurant-card.rc .card-image::after {
                content: '';
                position: absolute;
                inset: 0;
                background: linear-gradient(180deg, rgba(0,0,0,.30) 0%, rgba(0,0,0,0) 38%);
                pointer-events: none;
                z-index: 1;
            }

            .restaurant-card.rc .rc-badges {
                position: absolute;
                top: 12px;
                left: 12px;
                z-index: 3;
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                max-width: calc(100% - 66px);
                background: none !important;
                padding: 0 !important;
            }
            .restaurant-card.rc .rc-badge {
                position: static !important;
                display: inline-flex !important;
                align-items: center;
                gap: 5px;
                padding: 5px 11px !important;
                border-radius: 999px !important;
                font-size: 12px;
                font-weight: 700;
                line-height: 1.2;
                white-space: nowrap;
                box-shadow: 0 2px 8px rgba(0,0,0,.18);
            }
            .restaurant-card.rc .rc-badge-promo {
                background: linear-gradient(135deg, var(--primary, #ff385c), #ff6b81) !important;
                color: #fff !important;
            }
            .restaurant-card.rc .rc-badge-top {
                background: linear-gradient(135deg, #ffc107, #ff9800) !important;
                color: #3b2a00 !important;
            }

            .restaurant-card.rc .fav-btn {
                position: absolute !important;
                top: 12px !important;
                right: 12px !important;
                z-index: 3;
                width: 38px;
                height: 38px;
                display: flex !important;
                align-items: center;
                justify-content: center;
                padding: 0;
                border: none;
                border-radius: 50% !important;
                background: rgba(255,255,255,.95) !important;
                box-shadow: 0 3px 10px rgba(0,0,0,.22);
                cursor: pointer;
                transition: transform .2s ease, box-shadow .2s ease;
            }
            .restaurant-card.rc .fav-btn i {
                color: #e11d48 !important;
                font-size: 17px;
            }
            .restaurant-card.rc .fav-btn:hover {
                transform: scale(1.12);
                box-shadow: 0 5px 14px rgba(225, 29, 72, .35);
            }

            .restaurant-card.rc .card-content { padding: 18px 18px 16px; }

            .restaurant-card.rc .card-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 10px;
                margin-bottom: 8px;
            }
            .restaurant-card.rc .card-header h3 {
                margin: 0;
                font-size: 17px;
                font-weight: 700;
                line-height: 1.3;
                color: var(--dark, #111827);
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            .restaurant-card.rc .rating {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                flex-shrink: 0;
                padding: 3px 9px;
                border-radius: 999px;
                background: #fff7e0;
                font-size: 13px;
                font-weight: 700;
                color: #7a5800;
            }
            .restaurant-card.rc .rating i { color: #ffb800; font-size: 12px; }

            .restaurant-card.rc .card-location {
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 6px;
                margin-bottom: 12px;
                font-size: 13.5px;
                color: var(--gray, #6b7280);
            }
            .restaurant-card.rc .card-location i { color: var(--primary, #ff385c); }
            .restaurant-card.rc .card-location .distance { font-weight: 600; }

            .restaurant-card.rc .card-price {
                display: flex;
                align-items: baseline;
                gap: 6px;
                margin-bottom: 14px;
            }
            .restaurant-card.rc .card-price .price {
                font-size: 20px;
                font-weight: 800;
                color: var(--dark, #111827);
            }
            .restaurant-card.rc .card-price .price-label {
                font-size: 13px;
                color: var(--gray, #6b7280);
            }

            .restaurant-card.rc .card-tags {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 14px;
            }
            .restaurant-card.rc .card-tags .tag {
                padding: 5px 12px;
                border-radius: 999px;
                background: #f3f4f6;
                font-size: 12px;
                font-weight: 500;
                color: #4b5563;
                text-transform: capitalize;
            }

            .restaurant-card.rc .ia-justification {
                display: flex;
                align-items: flex-start;
                gap: 8px;
                margin-bottom: 14px;
                padding: 10px 12px;
                border-radius: 12px;
                background: #fff1f3;
                border-left: 3px solid var(--primary, #ff385c);
                font-size: 12.5px;
                line-height: 1.45;
                color: #4b5563;
            }
            .restaurant-card.rc .ia-justification i {
                margin-top: 2px;
                color: var(--primary, #ff385c);
            }

            .restaurant-card.rc .card-link {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-top: 4px;
                padding-top: 14px;
                border-top: 1px solid #f0f0f0;
                font-size: 14px;
                font-weight: 600;
                color: var(--primary, #ff385c);
                text-decoration: none;
            }
            .restaurant-card.rc .card-link i { transition: transform .2s ease; }
            .restaurant-card.rc .card-link:hover i { transform: translateX(5px); }
        `;
        document.head.appendChild(style);
    }

    renderRestaurantCard(restaurant) {
        const tags = restaurant.tags?.slice(0, 3).map(t =>
            `<span class="tag">${t}</span>`
        ).join('') || '';

        const justifications = restaurant.justifications && restaurant.justifications.length > 0
            ? `<div class="ia-justification">
                <i class="fas fa-robot"></i>
                <span>${restaurant.justifications[0]}</span>
               </div>`
            : '';

        const promo = restaurant.promo
            ? `<div class="rc-badge rc-badge-promo"><i class="fas fa-tag"></i> Promoción</div>`
            : '';

        const topRated = restaurant.rating >= 4.5
            ? `<div class="rc-badge rc-badge-top"><i class="fas fa-star"></i> Top</div>`
            : '';

        const isFavorite = this.state.favorites.includes(restaurant.id) ? 'fas' : 'far';

        const currency = typeof MONEDA !== 'undefined' ? MONEDA : 'S/.';

        const distance = restaurant.distance_km
            ? `<span class="dot">•</span>
               <span class="distance">${Number(restaurant.distance_km).toFixed(1)} km</span>`
            : '';

        return `
            <div class="restaurant-card rc" 
                 data-id="${restaurant.id}" 
                 data-lat="${restaurant.lat}" 
                 data-lng="${restaurant.lng}"
                 onmouseenter="highlightMarker(${restaurant.id})" 
                 onmouseleave="resetMarker(${restaurant.id})">
                
                <div class="card-image">
                    <img src="${restaurant.image}" alt="${restaurant.name}" loading="lazy">
                    
                    <div class="rc-badges">
                        ${promo}
                        ${topRated}
                    </div>
                    
                    <button class="fav-btn" onclick="toggleFavorite(${restaurant.id}, event)" title="Agregar a favoritos">
                        <i class="${isFavorite} fa-heart"></i>
                    </button>
                </div>
                
                <div class="card-content">
                    <div class="card-header">
                        <h3>${restaurant.name}</h3>
                        <div class="rating">
                            <i class="fas fa-star"></i>
                            <span>${restaurant.rating}</span>
                        </div>
                    </div>
                    
                    <div class="card-location">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${restaurant.district}</span>
                        ${distance}
                    </div>
                    
                    <div class="card-price">
                        <span class="price">${currency}${restaurant.avg_price}</span>
                        <span class="price-label">por persona</span>
                    </div>
                    
                    <div class="card-tags">${tags}</div>
                    
                    ${justifications}
                    
                    <a href="/restaurant/${restaurant.id}" class="card-link">
                        <span>Ver detalles</span> <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
            </div>
        `;
    }

    async handleSearch() {
        const formData = new FormData(this.elements.searchForm);
        const filters = {
            district: formData.get('district'),
            category: formData.get('category'),
            max_price: formData.get('max_price'),
            search_query: formData.get('q')
        };

        if (this.state.userLocation) {
            filters.lat = this.state.userLocation.lat;
            filters.lng = this.state.userLocation.lng;
        }

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(filters)
            });

            const data = await response.json();

            if (data.results) {
                this.state.filteredRestaurants = data.results;
                this.renderRestaurants();
                this.updateMapMarkers(data.results);
            }
        } catch (error) {
            console.error('Error en búsqueda:', error);
        }
    }

    applyFilter(chip) {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');

        const filter = chip.dataset.filter;
        const category = chip.dataset.category;

        let filtered = [...this.state.restaurants];

        if (filter === 'open') {
            filtered = filtered.filter(r => this.isRestaurantOpen(r));
        } else if (filter === 'promo') {
            filtered = filtered.filter(r => r.promo);
        } else if (filter === 'top-rated') {
            filtered = filtered.sort((a, b) => b.rating - a.rating);
        } else if (filter === 'nearby') {
            if (this.state.userLocation) {
                filtered = this.sortByDistance(filtered, this.state.userLocation);
                this.state.filteredRestaurants = filtered;
                this.renderRestaurants();
                this.updateMapMarkers(filtered);
            } else {
                this.getUserLocation().then(coords => {
                    if (coords) {
                        filtered = this.sortByDistance(filtered, coords);
                        this.state.filteredRestaurants = filtered;
                        this.renderRestaurants();
                        this.updateMapMarkers(filtered);
                    }
                });
            }
            return;
        } else if (filter === 'price-low') {
            filtered = filtered.filter(r => r.avg_price < 30);
        } else if (filter === 'price-mid') {
            filtered = filtered.filter(r => r.avg_price >= 30 && r.avg_price < 50);
        } else if (filter === 'price-high') {
            filtered = filtered.filter(r => r.avg_price >= 50);
        } else if (category) {
            filtered = filtered.filter(r => r.category_id == category);
        }

        this.state.filteredRestaurants = filtered;
        this.renderRestaurants();
        this.updateMapMarkers(filtered);
    }

    sortByDistance(restaurants, coords) {
        return [...restaurants].sort((a, b) => {
            if (!a.lat || !a.lng) return 1;
            if (!b.lat || !b.lng) return -1;
            const distA = this.calculateDistance(coords.lat, coords.lng, a.lat, a.lng);
            const distB = this.calculateDistance(coords.lat, coords.lng, b.lat, b.lng);
            // Agregar distancia al objeto para mostrarla
            a.distance_km = distA;
            b.distance_km = distB;
            return distA - distB;
        });
    }

    isRestaurantOpen(restaurant) {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const currentTime = `${hours}:${minutes}`;
        return currentTime >= restaurant.open_time && currentTime <= restaurant.close_time;
    }

    async loadFavorites() {
        try {
            const response = await fetch('/auth/api/favorites');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.favorites) {
                    this.state.favorites = data.favorites.map(f => f.restaurant_id);
                    this.saveState();
                    console.log('✅ Favoritos cargados desde servidor:', this.state.favorites);
                }
            } else {
                console.warn('⚠️ Error cargando favoritos, usando caché local');
            }
        } catch (error) {
            console.error('❌ Error cargando favoritos:', error);
        }
    }

    async toggleFavorite(restaurantId, event) {
        if (event) event.stopPropagation();

        // Verificar si el usuario está autenticado
        const isLoggedIn = document.querySelector('.user-dropdown') !== null;
        if (!isLoggedIn) {
            alert('Debes iniciar sesión para guardar favoritos');
            window.location.href = '/auth/login';
            return;
        }

        try {
            const response = await fetch('/auth/api/favorites/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ restaurant_id: restaurantId })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Error al procesar la solicitud');
            }

            if (data.favorites) {
                this.state.favorites = data.favorites;
            } else {
                if (data.favorited) {
                    if (!this.state.favorites.includes(restaurantId)) {
                        this.state.favorites.push(restaurantId);
                    }
                } else {
                    this.state.favorites = this.state.favorites.filter(id => id !== restaurantId);
                }
            }

            this.saveState();
            this.renderRestaurants();

            if (window.location.pathname === '/auth/favorites') {
                window.location.reload();
            }

        } catch (error) {
            console.error('❌ Error al toggle favorito:', error);
            alert(error.message || 'Error al guardar favorito. Por favor intenta de nuevo.');
        }
    }

    toggleTheme() {
        this.state.theme = this.state.theme === 'light' ? 'dark' : 'light';
        this.applyTheme();
        this.saveState();
    }

    applyTheme() {
        const isDark = this.state.theme === 'dark';
        document.documentElement.style.setProperty('--bg-primary', isDark ? '#1A1A1A' : '#F7F7F7');
        document.documentElement.style.setProperty('--bg-secondary', isDark ? '#2A2A2A' : '#FFFFFF');
        document.documentElement.style.setProperty('--text-primary', isDark ? '#FFFFFF' : '#1A1A1A');
        document.documentElement.style.setProperty('--text-secondary', isDark ? '#A0A0A0' : '#717171');

        // ✅ Verificar que el elemento existe antes de modificarlo
        if (this.elements.themeToggle) {
            this.elements.themeToggle.innerHTML = isDark
                ? '<i class="fas fa-sun"></i>'
                : '<i class="fas fa-moon"></i>';
        }
    }

    openRecommendationModal() {
        const modal = this.elements.recommendationModal;
        if (modal) {
            modal.style.display = 'flex';
            modal.classList.add('show');
            console.log('✅ Modal de recomendación abierto');
        } else {
            console.error('❌ Modal no encontrado');
        }
    }

    closeRecommendationModal() {
        const modal = this.elements.recommendationModal;
        if (modal) {
            modal.style.display = 'none';
            modal.classList.remove('show');
            console.log('✅ Modal de recomendación cerrado');
        }
    }

    async getRecommendations() {
        const form = this.elements.recommendationForm;
        if (!form) return;

        const formData = new FormData(form);

        const data = {
            location: formData.get('location') || '',
            budget: parseFloat(formData.get('budget')) || 0,
            food_preference: parseInt(formData.get('food_preference')) || 0,
            visit_time: formData.get('visit_time') || '',
            restrictions: formData.getAll('restrictions'),
            goal: formData.get('goal') || ''
        };

        if (this.state.userLocation) {
            data.lat = this.state.userLocation.lat;
            data.lng = this.state.userLocation.lng;
        }

        console.log('📤 Enviando recomendación:', data);

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            console.log('📥 Resultado:', result);

            if (result.results && result.results.length > 0) {
                this.state.filteredRestaurants = result.results;
                this.renderRestaurants();
                this.updateMapMarkers(result.results);
                this.closeRecommendationModal();
                alert(`¡Encontramos ${result.results.length} restaurantes recomendados!`);
            } else {
                alert('No encontramos restaurantes que coincidan con tus preferencias.');
            }
        } catch (error) {
            console.error('❌ Error en recomendación:', error);
            alert('Error al obtener recomendaciones. Por favor intenta de nuevo.');
        }
    }


    async getUserLocation() {
        console.log('🟢 Intentando obtener ubicación...');

        // Verificar si la página es segura
        const isSecure = window.location.protocol === 'https:' ||
            window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1';

        if (!isSecure) {
            console.warn('⚠️ La página no es segura. Usa http://localhost:5000');
            this.showLocationError('⚠️ Usa http://localhost:5000 en lugar de una IP para geolocalización');
            return null;
        }

        if (!navigator.geolocation) {
            console.error('❌ Geolocalización no soportada');
            this.showLocationError('Tu navegador no soporta geolocalización');
            return null;
        }

        if (navigator.permissions && navigator.permissions.query) {
            try {
                const permissionStatus = await navigator.permissions.query({ name: 'geolocation' });
                console.log('📌 Estado del permiso:', permissionStatus.state);

                if (permissionStatus.state === 'denied') {
                    this.showLocationError(
                        '❌ Permiso de ubicación denegado.\n\n' +
                        'Para habilitarlo:\n' +
                        '1. Haz clic en el candado 🔒 en la barra de direcciones\n' +
                        '2. Busca "Ubicación" y selecciona "Permitir"\n' +
                        '3. Recarga la página e intenta de nuevo'
                    );
                    return null;
                }

                if (permissionStatus.state === 'prompt') {
                    console.log('📌 El navegador pedirá permiso...');
                    this.showLocationInfo('📍 El navegador te pedirá permiso para acceder a tu ubicación. Haz clic en "Permitir".');
                }
            } catch (e) {
                console.warn('No se pudo verificar el permiso:', e);
            }
        }

        return new Promise((resolve) => {
            const options = {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 60000
            };

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const coords = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    };

                    console.log('📍 Ubicación obtenida:', coords);

                    this.state.userLocation = coords;
                    this.centerMap(coords.lat, coords.lng);
                    this.saveUserLocation(coords);
                    this.showLocationSuccess(coords);
                    this.filterNearbyRestaurants(coords);

                    resolve(coords);
                },
                (error) => {
                    console.error('❌ Error de geolocalización:', error);

                    let userMessage = '';

                    switch (error.code) {
                        case error.PERMISSION_DENIED:
                            userMessage =
                                '❌ Permiso de ubicación denegado.\n\n' +
                                'Para habilitarlo:\n' +
                                '1. Haz clic en el candado 🔒 en la barra de direcciones\n' +
                                '2. Busca "Ubicación" y selecciona "Permitir"\n' +
                                '3. Recarga la página e intenta de nuevo\n\n' +
                                'Si ya lo hiciste, cierra y vuelve a abrir el navegador.';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            userMessage = '❌ No se pudo obtener tu ubicación. Verifica que el GPS esté activo.';
                            break;
                        case error.TIMEOUT:
                            userMessage = '❌ Tiempo de espera agotado. Intenta de nuevo.';
                            break;
                        default:
                            userMessage = `❌ Error: ${error.message}`;
                    }

                    this.showLocationError(userMessage);
                    resolve(null);
                },
                options
            );
        });
    }

    showLocationInfo(message) {
        console.log('ℹ️ ' + message);

        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #3B82F6;
            color: white;
            padding: 16px 24px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 9999;
            font-size: 14px;
            max-width: 90%;
            text-align: center;
            animation: slideUp 0.3s ease;
            white-space: pre-line;
        `;
        toast.innerHTML = `
            <i class="fas fa-info-circle" style="margin-right: 10px; font-size: 20px;"></i>
            ${message.replace(/\n/g, '<br>')}
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    }

    showLocationSuccess(coords) {
        const message = `📍 Ubicación detectada!\nLat: ${coords.lat.toFixed(6)}\nLng: ${coords.lng.toFixed(6)}`;
        console.log('✅ ' + message);

        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #10B981;
            color: white;
            padding: 16px 24px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 9999;
            font-size: 14px;
            max-width: 90%;
            text-align: center;
            animation: slideUp 0.3s ease;
            white-space: pre-line;
        `;
        toast.innerHTML = `
            <i class="fas fa-check-circle" style="margin-right: 10px; font-size: 20px;"></i>
            Ubicación detectada correctamente
            <br><small style="opacity: 0.8;">${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}</small>
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    }

    showLocationError(message) {
        console.error('❌ ' + message);

        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #EF4444;
            color: white;
            padding: 16px 24px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 9999;
            font-size: 14px;
            max-width: 90%;
            text-align: center;
            animation: slideUp 0.3s ease;
            white-space: pre-line;
            max-height: 80vh;
            overflow-y: auto;
        `;
        toast.innerHTML = `
            <i class="fas fa-exclamation-circle" style="margin-right: 10px; font-size: 20px;"></i>
            ${message.replace(/\n/g, '<br>')}
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 10000);
    }

    saveUserLocation(coords) {
        try {
            localStorage.setItem('userLat', coords.lat);
            localStorage.setItem('userLng', coords.lng);
            console.log('💾 Ubicación guardada en localStorage');
        } catch (e) {
            console.error('Error guardando en localStorage:', e);
        }

        try {
            fetch('/api/save-location', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    lat: coords.lat,
                    lng: coords.lng
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('💾 Ubicación guardada en el servidor');
                    }
                })
                .catch(err => console.error('Error guardando ubicación en servidor:', err));
        } catch (e) {
            console.error('Error en fetch:', e);
        }
    }

    filterNearbyRestaurants(coords) {
        const radius = 10;
        const filtered = this.state.restaurants.filter(r => {
            if (!r.lat || !r.lng) return false;
            const dist = this.calculateDistance(coords.lat, coords.lng, r.lat, r.lng);
            r.distance_km = dist;
            return dist <= radius;
        });

        if (filtered.length > 0) {
            this.state.filteredRestaurants = filtered;
            this.renderRestaurants();
            this.updateMapMarkers(filtered);
            console.log(`📍 ${filtered.length} restaurantes encontrados dentro de ${radius} km`);
        } else {
            console.log(`📍 No se encontraron restaurantes dentro de ${radius} km`);
            const withDistance = this.state.restaurants.map(r => {
                if (r.lat && r.lng) {
                    r.distance_km = this.calculateDistance(coords.lat, coords.lng, r.lat, r.lng);
                }
                return r;
            });
            this.state.filteredRestaurants = withDistance;
            this.renderRestaurants();
            this.updateMapMarkers(withDistance);
        }
    }


    updateMapMarkers(restaurants) {
        if (typeof window.updateMarkers === 'function') {
            window.updateMarkers(restaurants);
        }
    }

    centerMap(lat, lng) {
        console.log(`🗺️ Centrando mapa en: ${lat}, ${lng}`);
        if (typeof window.centerMap === 'function') {
            window.centerMap(lat, lng);
        } else {
            console.warn('⚠️ Función centerMap no disponible');
        }
    }

    toggleNotifications() {
        const panel = this.elements.notificationPanel;
        if (panel) {
            const isVisible = panel.style.display === 'block';
            panel.style.display = isVisible ? 'none' : 'block';
            if (!isVisible) {
                this.loadNotifications();
            }
        }
    }

    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications');
            if (!response.ok) {
                throw new Error('Error al cargar notificaciones');
            }

            const data = await response.json();
            const list = document.getElementById('notificationList');
            const badge = document.getElementById('notificationBadge');

            if (list) {
                if (data.notifications && data.notifications.length > 0) {
                    if (badge) {
                        badge.textContent = data.unread_count || 0;
                        badge.style.display = data.unread_count > 0 ? 'flex' : 'none';
                    }

                    list.innerHTML = data.notifications.map(n => `
                        <div class="notification-item ${n.read ? 'read' : 'unread'}" 
                             data-id="${n.id}"
                             onclick="markNotificationRead(${n.id})">
                            <div class="notification-icon ${n.type}">
                                <i class="fas fa-${n.type === 'promo' ? 'tag' : n.type === 'favorite' ? 'heart' : 'bell'}"></i>
                            </div>
                            <div class="notification-content">
                                <div class="notification-title">${n.title}</div>
                                <div class="notification-message">${n.message}</div>
                                <div class="notification-time">${new Date(n.timestamp).toLocaleDateString()}</div>
                            </div>
                            ${!n.read ? '<div class="notification-dot"></div>' : ''}
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = `
                        <div class="notification-empty">
                            <i class="fas fa-bell"></i>
                            No hay notificaciones
                        </div>
                    `;
                    if (badge) {
                        badge.style.display = 'none';
                    }
                }
            }
        } catch (error) {
            console.error('Error cargando notificaciones:', error);
            const list = document.getElementById('notificationList');
            if (list) {
                list.innerHTML = `
                    <div class="notification-empty" style="color: #dc2626;">
                        <i class="fas fa-exclamation-circle"></i>
                        Error al cargar notificaciones
                    </div>
                `;
            }
        }
    }

    calculateDistance(lat1, lng1, lat2, lng2) {
        if (!lat1 || !lng1 || !lat2 || !lng2) return 999;
        const R = 6371;
        const dLat = this.toRad(lat2 - lat1);
        const dLng = this.toRad(lng2 - lng1);
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    toRad(deg) {
        return deg * (Math.PI / 180);
    }

    loadMoreRestaurants() {
        console.log('Cargar más restaurantes');
    }

    handleScroll() {
    }

    changeView(view) {
        const grid = this.elements.resultsGrid;
        if (!grid) return;

        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });

        if (view === 'list') {
            grid.classList.add('list-view');
        } else {
            grid.classList.remove('list-view');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new AppController();
});

// ✅ Funciones globales para usar en los templates
window.toggleFavorite = function (restaurantId, event) {
    if (event) event.stopPropagation();
    if (window.app) {
        window.app.toggleFavorite(restaurantId, event);
    }
};

window.highlightMarker = function (restaurantId) {
    if (typeof window.highlightMarkerOnMap === 'function') {
        window.highlightMarkerOnMap(restaurantId);
    }
};

window.resetMarker = function (restaurantId) {
    if (typeof window.resetMarkerOnMap === 'function') {
        window.resetMarkerOnMap(restaurantId);
    }
};

window.toggleNotifications = function () {
    if (window.app) {
        window.app.toggleNotifications();
    } else {
        console.error('❌ App no inicializada');
    }
};

window.markNotificationRead = async function (id) {
    try {
        const response = await fetch(`/api/notifications/${id}/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Error al marcar como leída');
        }

        if (window.app) {
            await window.app.loadNotifications();
            const badge = document.getElementById('notificationBadge');
            if (badge) {
                const current = parseInt(badge.textContent) || 0;
                badge.textContent = Math.max(0, current - 1);
                if (parseInt(badge.textContent) === 0) {
                    badge.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.error('Error marcando notificación como leída:', error);
    }
};

window.markAllNotificationsRead = async function () {
    try {
        const response = await fetch('/api/notifications/read-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Error al marcar todas como leídas');
        }

        if (window.app) {
            await window.app.loadNotifications();
            const badge = document.getElementById('notificationBadge');
            if (badge) {
                badge.textContent = '0';
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error marcando todas las notificaciones como leídas:', error);
    }
};

window.openRecommendationModal = function () {
    if (window.app) {
        window.app.openRecommendationModal();
    } else {
        console.error('❌ App no inicializada');
    }
};

// Función global para cerrar el modal
window.closeRecommendationModal = function () {
    if (window.app) {
        window.app.closeRecommendationModal();
    }
};

// Función global para el botón de ubicación
window.handleLocationClick = function () {
    console.log('🟢 Botón de ubicación clickeado desde HTML');
    if (window.app) {
        window.app.getUserLocation();
    } else {
        console.error('❌ App no inicializada');
        alert('Error: La aplicación no está lista');
    }
};