(() => {
 const root = document.querySelector('.bp-page'); if (!root) return;
 root.querySelectorAll('[data-billing]').forEach(button => button.addEventListener('click', () => {
   const annual = button.dataset.billing === 'annual';
   root.querySelectorAll('[data-billing]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
   root.querySelectorAll('[data-price]').forEach(el => el.textContent = 'S/ ' + Number(el.dataset[annual ? 'annual' : 'monthly']).toLocaleString('en-US'));
   root.querySelectorAll('[data-period]').forEach(el => el.textContent = annual ? '/ año' : '/ mes');
   root.querySelectorAll('[data-plan-link]').forEach(link => { const url = new URL(link.href); url.searchParams.set('billing', annual ? 'annual' : 'monthly'); link.href = url.href; });
 }));
 const styles = {
   commercial:['Cocina peruana con carácter','Una mesa. Mil razones para volver.','Recetas que reúnen, ingredientes que inspiran y una experiencia para compartir.','Descubrir la carta','lomo'],
   minimal:['El placer de lo esencial','Pocos ingredientes. Mucha intención.','Una cocina honesta que deja hablar al producto.','Conocer nuestra cocina','dessert'],
   promo:['Un momento para compartir','Hoy se disfruta en compañía.','Dale protagonismo a tus promociones de temporada, con condiciones claras y una presentación irresistible.','Explorar promociones','ceviche'],
   fit:['Frescura en cada elección','Come a tu ritmo. Disfruta a tu manera.','Ingredientes declarados, opciones variadas y una carta que acompaña tus preferencias.','Explorar opciones','signature'],
   immersive:['Una experiencia para los sentidos','Acércate. Tu mesa te espera.','Una presentación envolvente para descubrir los detalles de tu propuesta gastronómica.','Vivir la experiencia','lomo']
 };
 const preview = root.querySelector('.bp-site-preview');
 root.querySelectorAll('[data-preview-style]').forEach(button => button.addEventListener('click', () => {
   const [tag,title,copy,cta,image] = styles[button.dataset.previewStyle]; preview.dataset.style = button.dataset.previewStyle;
   root.querySelectorAll('[data-preview-style]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
   for (const [key,value] of Object.entries({tag,title,copy,cta})) root.querySelector('[data-preview-'+key+']').textContent = value;
   const photo = root.querySelector('[data-preview-image]'); photo.src = '/static/images/auth/'+image+'.webp'; photo.alt = 'Ejemplo gastronómico del estilo '+button.textContent;
 }));
})();
