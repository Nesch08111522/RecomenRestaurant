/* UI rendering only. Data transformations and opening rules are separate. */
(() => {
  'use strict';
  window.ForestUI = Object.freeze({
    renderRestaurantCard(r, favorites = [], currency = 'S/') {
      const id = Number(r.id);
      if (!Number.isSafeInteger(id) || id <= 0) return '';
      const p = window.ForestProcessor, e = p.escape;
      const image = p.image(r.image);
      const favorite = favorites.some(value => String(value) === String(id));
      const state = window.ForestRules.openingState(r);
      const reviews = p.number(r.review_count ?? r.reviews_count ?? r.num_reviews);
      const price = p.number(r.avg_price);
      return `<article class="restaurant-card rc forest-card" data-id="${id}" data-lat="${e(r.lat)}" data-lng="${e(r.lng)}">
        <div class="card-image">${image ? `<img src="${e(image)}" alt="${e(r.name)}" loading="lazy" width="640" height="480">` : `<div class="forest-photo-missing"><i class="fas fa-utensils" aria-hidden="true"></i><span>Conoce ${e(r.name)}</span></div>`}
          ${r.promo ? '<span class="forest-promo-badge"><i class="fas fa-tag" aria-hidden="true"></i> Promoción</span>' : ''}
          <button type="button" class="fav-btn" onclick="toggleFavorite(${id}, event)" aria-label="${favorite ? 'Quitar' : 'Guardar'} ${e(r.name)} ${favorite ? 'de' : 'en'} favoritos" aria-pressed="${favorite}"><i class="${favorite ? 'fas' : 'far'} fa-heart" aria-hidden="true"></i></button>
        </div><div class="card-content"><h3>${e(r.name)}</h3>
        <div class="card-location"><i class="fas fa-location-dot" aria-hidden="true"></i><span>${e(r.district || 'Ubicación por confirmar')}</span>${p.number(r.distance_km) !== null ? `<small> · ${Number(r.distance_km).toFixed(1)} km</small>` : ''}</div>
        <div class="forest-card-meta"><span class="rating"><i class="fas fa-star" aria-hidden="true"></i> ${p.rating(r.rating)}${reviews > 0 ? `<small> (${reviews} reseñas)</small>` : ''}</span>${state ? `<span class="forest-status ${state.className}">${state.label}</span>` : '<span class="forest-hours">Consultar horario</span>'}</div>
        <p class="card-price"><strong>${price !== null ? e(currency) + ' ' + price.toFixed(0) : 'Consultar precio'}</strong>${price !== null ? ' por persona' : ''}</p>
        <div class="forest-card-bottom"><div class="card-tags">${p.tags(r.tags).map(tag => `<span class="tag">${e(tag)}</span>`).join('')}</div><a href="/restaurant/${id}" class="card-link">Ver restaurante <span aria-hidden="true">→</span></a></div></div></article>`;
    }
  });
})();
