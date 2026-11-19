(() => {
  const banner = document.getElementById('location-consent');
  if (!banner) return;
  const status = banner.querySelector('[data-location-status]');
  const read = () => { try { return localStorage.getItem('sr-location-consent'); } catch { return null; } };
  const save = value => { try { localStorage.setItem('sr-location-consent', value); } catch {} };
  async function persist(lat, lng) {
    const response = await fetch('/api/save-location', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({lat,lng,context_consent:true})});
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error('No se pudo guardar la ubicación. Vuelve a intentarlo.');
    if (window.app) {
      window.app.state.userLocation = {lat,lng};
      window.app.centerMap(lat,lng);
      window.app.filterNearbyRestaurants({lat,lng});
    }
    window.mapGL?.showPosition(lat,lng);
    save('accepted'); banner.hidden = true;
    const output = document.getElementById('geo-status');
    if (output) output.textContent = result.weather ? `Ubicación guardada. Sensación térmica: ${Math.round(result.weather.apparent_temperature)} °C (Open-Meteo).` : 'Ubicación guardada. No hay datos de clima disponibles por ahora.';
  }
  window.addEventListener('smartresto:location-picked', async event => {
    try { await persist(event.detail.lat,event.detail.lng); }
    catch(error) { document.querySelector('dialog[open]')?.close(); banner.hidden=false; status.textContent=error.message; }
  });
  let request;
  async function locate(automatic = false) {
    if (request) return request;
    request = (async () => {
      const buttons = [banner.querySelector('[data-location-accept]'), document.getElementById('locationBtn')].filter(Boolean);
      const output = document.getElementById('geo-status');
      const report = message => { status.textContent = message; if (output) output.textContent = message; };
      buttons.forEach(button => { button.disabled = true; });
      report('Solicitando ubicación al navegador…');
      try {
        if (!isSecureContext || !navigator.geolocation) throw new Error('La ubicación requiere HTTPS o localhost.');
        const position = await new Promise((yes, no) => navigator.geolocation.getCurrentPosition(yes, no, {timeout:20000, maximumAge:60000, enableHighAccuracy:false}));
        await persist(position.coords.latitude, position.coords.longitude);
      } catch (error) {
        if (automatic === true) return;
        banner.hidden = false;
        report(error.code === 1 ? 'El navegador denegó el permiso. Permite Ubicación junto a la dirección o elige un punto en el mapa.' : error.code === 3 ? 'Se agotó el tiempo de espera. Intenta nuevamente.' : error.code === 2 ? 'El dispositivo no pudo obtener tu ubicación. Puedes elegir un punto en el mapa.' : error.message || 'Ubicación no disponible. Intenta nuevamente.');
      } finally { buttons.forEach(button => { button.disabled = false; }); request = null; }
    })();
    return request;
  }
  banner.hidden = location.pathname !== '/' || read() !== null;
  banner.querySelector('[data-location-accept]').addEventListener('click', locate);
  banner.querySelector('[data-location-decline]').addEventListener('click', () => { save('declined'); banner.hidden = true; });

  document.addEventListener('click', event => {
    if (!event.target.closest('#locationBtn, #context-location, #market-near')) return;
    event.preventDefault(); event.stopImmediatePropagation();
    locate();
  }, true);
  if (location.pathname === '/' && read() === 'accepted') navigator.permissions?.query({name:'geolocation'}).then(permission => { if (permission.state === 'granted') locate(true); }).catch(() => {});
})();
