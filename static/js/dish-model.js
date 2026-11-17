(() => {
 const button=document.getElementById('load-dish-model');
 if(!button) return;
 const status=document.getElementById('model-status');
 async function track(event){try{await fetch(button.dataset.event,{method:'POST',body:new URLSearchParams({event})});}catch{}}
 button.addEventListener('click',async()=>{
  button.disabled=true;status.textContent='Cargando visor…';
  try {
   await import('https://cdn.jsdelivr.net/npm/@google/model-viewer@4.1.0/dist/model-viewer.min.js');
   const viewer=document.createElement('model-viewer');
   viewer.setAttribute('src',button.dataset.src);viewer.setAttribute('camera-controls','');
   viewer.setAttribute('ar','');viewer.setAttribute('ar-modes','webxr scene-viewer quick-look');
   viewer.setAttribute('ar-scale','fixed');viewer.setAttribute('alt','Modelo del plato aportado por el negocio');
   viewer.style.cssText='width:100%;height:400px;max-height:70vh;touch-action:pan-y';
   viewer.addEventListener('load',()=>{status.textContent='Gira el plato y amplía los detalles.';track('model');});
   viewer.addEventListener('error',()=>{status.textContent='El modelo no pudo cargarse. Puedes consultar la fotografía y los ingredientes.';button.disabled=false;});
   viewer.addEventListener('ar-status',e=>{if(e.detail.status==='session-started')track('ar');if(e.detail.status==='failed')status.textContent='La realidad aumentada no está disponible en este dispositivo.';});
   document.getElementById('dish-model').replaceChildren(viewer);
  }catch{status.textContent='No se pudo cargar el visor. Puedes consultar la fotografía.';button.disabled=false;}
 });
})();
