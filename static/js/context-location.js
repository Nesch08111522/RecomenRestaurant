(() => {
 const button=document.getElementById('context-location');
 const status=document.getElementById('context-location-status');
 button?.addEventListener('click',()=>{
  if(!navigator.geolocation){status.textContent='Tu navegador no admite ubicación.';return;}
  button.disabled=true;status.textContent='Buscando ubicación…';
  navigator.geolocation.getCurrentPosition(async ({coords})=>{
   try {
    const response=await fetch('/api/save-location',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:coords.latitude,lng:coords.longitude})});
    if(!response.ok) throw new Error();
    location.reload();
   }catch{status.textContent='No se pudo guardar la ubicación. Intenta nuevamente.';button.disabled=false;}
  },()=>{status.textContent='Activa el permiso de ubicación o filtra por distrito.';button.disabled=false;},{timeout:20000,maximumAge:60000});
 });
})();
