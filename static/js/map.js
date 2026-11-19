/**
 * SmartResto - Mapa Leaflet
 * Solo se inicializa si el contenedor existe
 */

let map = null;
let markers = {};
window.getLeafletMap = () => map;

// Inicializa el mapa solo cuando su contenedor está visible y tiene dimensiones.
function initMap() {
    if (document.body.classList.contains('sr-discover') && document.getElementById('forest-map-panel')?.hidden) return;
    // Verificar que el contenedor existe
    const mapContainer = document.getElementById('main-map');
    if (!mapContainer) {
        console.warn('⚠️ Map container not found - skipping map initialization');
        return;
    }
    
    // Verificar que las coordenadas existen
    let center = [-8.1118, -79.0287];
    if (typeof INITIAL_COORDS !== 'undefined' && INITIAL_COORDS) {
        center = INITIAL_COORDS;
    }
    
    // Si ya existe un mapa, destruirlo primero
    if (map) {
        map.remove();
        map = null;
    }
    
    map = L.map('main-map').setView(center, 13);
    
    window._osmTilesState = 'loading';
    let loadedOsmTiles = 0;
    let failedOsmTiles = 0;
    const mapNotice = () => document.querySelector('.sr-map-dialog .sr-map-help');
    const osmTiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    osmTiles.on('tileload', () => {
        loadedOsmTiles += 1;
        window._osmTilesState = 'ready';
        const notice = mapNotice();
        if (notice && /Descargando calles|Mapa gratuito|OpenStreetMap no entregó/.test(notice.textContent)) {
            notice.textContent = 'Calles de OpenStreetMap cargadas.';
        }
    });
    osmTiles.on('tileerror', event => {
        failedOsmTiles += 1;
        console.error('OpenStreetMap no pudo descargar una tesela:', event.tile?.src);
        if (loadedOsmTiles === 0 && failedOsmTiles >= 2) {
            window._osmTilesState = 'error';
            const notice = mapNotice();
            if (notice) notice.textContent = 'El mapa inició, pero OpenStreetMap no entregó las calles. Revisa la conexión, el firewall o un bloqueador.';
        }
    });
    osmTiles.addTo(map);

    // Verificar si hay coordenadas pendientes
    if (window._pendingCenter) {
        console.log('📍 Centrando mapa en ubicación guardada:', window._pendingCenter);
        map.setView([window._pendingCenter.lat, window._pendingCenter.lng], 15);
        delete window._pendingCenter;
    }

    // Verificar que los datos existen
    const restaurantsToRender = window._pendingRestaurants || RESTAURANTS_DATA;
    if (Array.isArray(restaurantsToRender) && restaurantsToRender.length > 0) {
        updateMarkers(restaurantsToRender);
    }
    delete window._pendingRestaurants;
}

function updateMarkers(restaurants) {
    if (!map && window.mapGL) {
        const visibleIds = Array.isArray(restaurants)
            ? restaurants.map(restaurant => restaurant.id).filter(id => id != null)
            : null;
        window.mapGL.setVisible(visibleIds);
        return;
    }
    if (!map) {
        window._pendingRestaurants = restaurants;
        return;
    }
    
    // Limpiar marcadores existentes
    Object.values(markers).forEach(m => {
        try {
            map.removeLayer(m);
        } catch (e) {
            // Ignorar si el marcador ya fue removido
        }
    });
    markers = {};

    if (!restaurants || restaurants.length === 0) {
        return;
    }

    restaurants.forEach(r => {
        if (r.lat == null || r.lng == null || !Number.isSafeInteger(Number(r.id))) return;
        
        const marker = L.marker([r.lat, r.lng]).addTo(map);
        marker.bindPopup(`
            <div class="map-popup">
                <strong>${window.escapeDisplayText(r.name)}</strong><br>
                Rating: ${window.escapeDisplayText(r.rating)} ⭐<br>
                <a href="/restaurant/${Number(r.id)}">Ver detalle</a>
            </div>
        `);
        markers[r.id] = marker;
    });
}

function highlightMarker(id) {
    if (markers[id]) {
        markers[id].openPopup();
    }
}

function resetMarker(id) {
    // Opcional: cerrar popup después de un tiempo
    if (markers[id]) {
        setTimeout(() => {
            try {
                markers[id].closePopup();
            } catch (e) {
                // Ignorar
            }
        }, 2000);
    }
}

function centerMap(lat, lng) {
    console.log(`🗺️ Centrando mapa en: ${lat}, ${lng}`);
    if (map) {
        map.setView([lat, lng], 15);
        console.log('✅ Mapa centrado correctamente');
    } else {
        // La ubicación queda en cola y se aplica al abrir el mapa.
        // Guardar para usar cuando el mapa esté listo
        window._pendingCenter = { lat, lng };
    }
}

// Solo inicializar si estamos en la página correcta
document.addEventListener('DOMContentLoaded', () => {
    // Verificar si estamos en una página que tiene mapa
    if (document.getElementById('main-map')) {
        initMap();
    }
});

// Exportar funciones globales
window.updateMarkers = updateMarkers;
window.centerMap = centerMap;
window.highlightMarkerOnMap = highlightMarker;
window.resetMarkerOnMap = resetMarker;

let userLocationMarker = null;

function addUserLocationMarker(lat, lng) {
    // Eliminar marcador anterior si existe
    if (userLocationMarker) {
        map.removeLayer(userLocationMarker);
        userLocationMarker = null;
    }
    
    // Crear icono personalizado para la ubicación del usuario
    const userIcon = L.divIcon({
        className: 'user-location-marker',
        html: `<div style="
            width: 20px;
            height: 20px;
            background: var(--theme-info-bg);
            border-radius: 50%;
            border: 3px solid var(--theme-border);
            box-shadow: 0 0 0 4px var(--theme-shadow), 0 2px 8px var(--theme-shadow);
            animation: pulse 1.5s ease-in-out infinite;
        "></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });
    
    userLocationMarker = L.marker([lat, lng], { icon: userIcon }).addTo(map);
    userLocationMarker.bindPopup('<i class="fas fa-map-marker-alt" aria-hidden="true"></i> Tu ubicación actual');
    
    // Añadir círculo de precisión
    if (window._userAccuracy) {
        L.circle([lat, lng], {
            radius: window._userAccuracy,
            color: window.SRTheme.color('info'),
            fillColor: window.SRTheme.color('info'),
            fillOpacity: 0.1,
            weight: 1
        }).addTo(map);
    }
    
    // Centrar el mapa en la ubicación
    map.setView([lat, lng], 15);
}

// Modificar centerMap para usar el marcador
function centerMap(lat, lng, accuracy) {
    console.log(`🗺️ Centrando mapa en: ${lat}, ${lng}`);
    if (map) {
        addUserLocationMarker(lat, lng);
        if (accuracy) {
            window._userAccuracy = accuracy;
        }
        console.log('✅ Mapa centrado con marcador de ubicación');
    } else {
        // La ubicación queda en cola y se aplica al abrir el mapa.
        window._pendingCenter = { lat, lng, accuracy };
    }
}
