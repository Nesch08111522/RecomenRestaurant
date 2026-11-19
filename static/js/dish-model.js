(() => {
 const button=document.getElementById('load-dish-model');if(!button)return;
 const status=document.getElementById('model-status'),controls=document.getElementById('immersive-controls');let viewer;
 async function track(event){try{await fetch(button.dataset.event,{method:'POST',body:new URLSearchParams({event})});}catch{}}
 button.addEventListener('click',async()=>{
  button.disabled=true;status.textContent='Cargando visor…';
  try{
   const [metadataResponse]=await Promise.all([fetch(button.dataset.metadata,{headers:{Accept:'application/json'}}),import('/static/vendor/model-viewer/model-viewer-4.1.0.min.js')]);
   if(!metadataResponse.ok)throw Error('metadata');const meta=await metadataResponse.json();
   viewer=document.createElement('model-viewer');viewer.setAttribute('src',button.dataset.src);viewer.setAttribute('camera-controls','');viewer.setAttribute('touch-action','pan-y');viewer.setAttribute('loading','lazy');viewer.setAttribute('shadow-intensity','.7');viewer.setAttribute('alt','Modelo del plato aportado por el negocio');viewer.style.cssText='width:100%;height:400px;max-height:65vh;touch-action:pan-y';
   viewer.addEventListener('load',()=>{
    controls.hidden=false;status.textContent='Arrastra para girar 360°. Amplía con la rueda o dos dedos.';track('model');
    const text=document.getElementById('model-measurements');
    text.textContent=meta.width_cm?`Medidas declaradas: ${meta.width_cm} × ${meta.height_cm} × ${meta.depth_cm} cm. ${meta.portion_g?'Porción: '+meta.portion_g+' g.':''}`:'Sin dimensiones declaradas: representación visual sin escala garantizada.';
    if(meta.scale_verified){const dimensions=viewer.getDimensions(),ratios=[meta.width_cm/(dimensions.x*100),meta.height_cm/(dimensions.y*100),meta.depth_cm/(dimensions.z*100)];const factor=ratios[0];if(ratios.every(x=>Number.isFinite(x)&&Math.abs(x/factor-1)<.15)){viewer.setAttribute('scale',`${factor} ${factor} ${factor}`);viewer.setAttribute('ar','');viewer.setAttribute('ar-scale','fixed');viewer.setAttribute('ar-modes','webxr scene-viewer quick-look');text.textContent+=' Escala revisada; AR disponible en dispositivos compatibles.';}else text.textContent+=' Las proporciones no coinciden: se desactiva AR a escala.';}
   });
   viewer.addEventListener('error',()=>{status.textContent='El modelo no pudo cargarse. Consulta la fotografía y los ingredientes.';button.disabled=false;controls.hidden=true;});
   viewer.addEventListener('ar-status',e=>{if(e.detail.status==='session-started')track('ar');if(e.detail.status==='failed')status.textContent='La realidad aumentada no está disponible en este dispositivo.';});
   document.getElementById('dish-model').replaceChildren(viewer);
  }catch{status.textContent='No se pudo cargar el visor. Puedes consultar la fotografía.';button.disabled=false;}
 });
 controls.querySelectorAll('[data-camera]').forEach(b=>b.addEventListener('click',()=>viewer?.setAttribute('camera-orbit',b.dataset.camera)));
 document.getElementById('model-rotate').addEventListener('click',e=>{const active=e.currentTarget.getAttribute('aria-pressed')!=='true';e.currentTarget.setAttribute('aria-pressed',String(active));viewer?.toggleAttribute('auto-rotate',active);});
 document.getElementById('model-compare').addEventListener('click',e=>{const photo=document.getElementById('model-reference');if(!photo){status.textContent='El negocio aún no publicó una fotografía de referencia.';return;}photo.hidden=!photo.hidden;e.currentTarget.setAttribute('aria-pressed',String(!photo.hidden));photo.parentElement.classList.toggle('is-comparing',!photo.hidden);});
})();
