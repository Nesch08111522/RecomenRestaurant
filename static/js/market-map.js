(() => {
  const cards = document.querySelectorAll('[data-ticket]');
  function track(card, stage) {
    fetch('/mercado/interaccion', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ticket:card.dataset.ticket, stage})}).catch(() => {});
  }
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const e of entries) if (e.isIntersecting) { track(e.target,'viewed'); observer.unobserve(e.target); }
    }, {threshold:.3});
    for (const card of cards) {
      observer.observe(card);
      card.querySelector('summary')?.addEventListener('click', () => track(card,'clicked'), {once:true});
    }
  }
  const mapNode = document.getElementById('market-map');
  if (mapNode && window.L) {
    const pins = JSON.parse(document.getElementById('market-pins').textContent);
    const map = L.map(mapNode);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution:'© OpenStreetMap contributors'}).addTo(map);
    const bounds = L.latLngBounds([]);
    for (const pin of pins) {
      const text = document.createElement('span');
      text.textContent = [pin.name, pin.pickup].filter(Boolean).join(' · ');
      L.marker(pin.point).addTo(map).bindPopup(text);
      bounds.extend(pin.point);
      if (pin.radius) {
        const circle = L.circle(pin.point, {radius:pin.radius*1000, color:window.SRTheme.color('info'), fillOpacity:.07}).addTo(map);
        bounds.extend(circle.getBounds());
      }
    }
    if (pins.length) map.fitBounds(bounds, {maxZoom:15, padding:[16,16]});
  }
  const button = document.getElementById('market-near');
  if (button) button.onclick = () => {
    const feedback = document.getElementById('location-feedback');
    if (!navigator.geolocation) { feedback.textContent = 'Puedes buscar por distrito.'; return; }
    navigator.geolocation.getCurrentPosition(async ({coords}) => {
      try {
        const res = await fetch('/api/save-location',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({lat:coords.latitude,lng:coords.longitude})});
        if (!res.ok) throw new Error();
        const url = new URL(location.href);
        url.searchParams.set('near','1');
        location.assign(url);
      } catch { feedback.textContent = 'No se pudo guardar la ubicación.'; }
    }, () => { feedback.textContent = 'Ubicación no disponible. Prueba con el distrito.'; });
  };
})();
