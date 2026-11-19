(() => {
 const motion = matchMedia('(prefers-reduced-motion: reduce)');
 document.querySelectorAll('[data-editorial-slides]').forEach(host => {
   let items; try { items = JSON.parse(host.dataset.editorialSlides); } catch { return; }
   items = items.filter(x => typeof x === 'string' && x.startsWith('/static/images/'));
   const photo = host.querySelector('img'), pause = host.querySelector('[data-slide-pause]');
   let index = 0, paused = motion.matches, visible = false;
   const update = () => { pause.textContent = paused ? 'Reanudar' : 'Pausar'; pause.setAttribute('aria-pressed', String(paused)); };
   const next = () => { if (!items.length) return; index=(index+1)%items.length; photo.src=items[index]; };
   host.querySelector('[data-slide-next]').addEventListener('click',next);
   pause.addEventListener('click',()=>{paused=!paused;update();});
   const observer=new IntersectionObserver(([entry])=>{visible=entry.isIntersecting;}); observer.observe(host);
   const timer=setInterval(()=>{if(visible&&!paused&&!document.hidden&&!host.matches(':focus-within,:hover'))next();},9000);
   motion.addEventListener('change',()=>{paused=motion.matches;update();});update();
   window.addEventListener('pagehide',()=>{clearInterval(timer);observer.disconnect();},{once:true});
 });
})();
