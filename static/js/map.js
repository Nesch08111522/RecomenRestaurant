/**
 * SmartResto - Mapa Leaflet
 * Solo se inicializa si el contenedor existe
 */

let map = null;
let markers = {};

function initMap() {
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
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Verificar si hay coordenadas pendientes
    if (window._pendingCenter) {
        console.log('📍 Centrando mapa en ubicación guardada:', window._pendingCenter);
        map.setView([window._pendingCenter.lat, window._pendingCenter.lng], 15);
        delete window._pendingCenter;
    }

    // Verificar que los datos existen
    if (typeof RESTAURANTS_DATA !== 'undefined' && RESTAURANTS_DATA && RESTAURANTS_DATA.length > 0) {
        updateMarkers(RESTAURANTS_DATA);
    }
}

function updateMarkers(restaurants) {
    if (!map) {
        console.warn('⚠️ Map not initialized');
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
        if (!r.lat || !r.lng) return;
        
        const marker = L.marker([r.lat, r.lng]).addTo(map);
        marker.bindPopup(`
            <div class="map-popup">
                <strong>${r.name}</strong><br>
                Rating: ${r.rating} ⭐<br>
                <a href="/restaurant/${r.id}">Ver detalle</a>
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
        console.warn('⚠️ Mapa no inicializado, guardando coordenadas para después');
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
            background: #3B82F6;
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.3), 0 2px 8px rgba(0,0,0,0.2);
            animation: pulse 1.5s ease-in-out infinite;
        "></div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });
    
    userLocationMarker = L.marker([lat, lng], { icon: userIcon }).addTo(map);
    userLocationMarker.bindPopup('📍 Tu ubicación actual');
    
    // Añadir círculo de precisión
    if (window._userAccuracy) {
        L.circle([lat, lng], {
            radius: window._userAccuracy,
            color: '#3B82F6',
            fillColor: '#3B82F6',
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
        console.warn('⚠️ Mapa no inicializado, guardando coordenadas para después');
        window._pendingCenter = { lat, lng, accuracy };
    }
}