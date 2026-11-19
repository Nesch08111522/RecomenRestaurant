(() => {
  const page = document.querySelector('.copilot-page');
  if (!page) return;
  const conversation = document.getElementById('copilot-conversation');
  const welcome = document.getElementById('copilot-welcome');
  const scroll = page.querySelector('.copilot-chat-scroll');
  const expand = document.getElementById('copilot-expand');
  const workspace = document.getElementById('copilot-workspace-details');
  const notice = document.getElementById('copilot-layout-status');
  let previousOpen = workspace.open;
  let previousFocus = null;
  let wasFullscreen = false;
  let expanded = false;
  const syncConversation = () => {
    const active = conversation.childElementCount > 0;
    page.classList.toggle('has-conversation', active);
    welcome.hidden = active;
    // Follow replies only while the reader is already near the bottom.
    if (scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight < 160) {
      scroll.scrollTop = scroll.scrollHeight;
    }
  };
  const observer = new MutationObserver(syncConversation);
  observer.observe(conversation, { childList: true, subtree: true, characterData: true });
  syncConversation();
  if (matchMedia('(max-width: 900px)').matches) workspace.open = false;

  async function restore() {
    if (!expanded) return;
    expanded = false;
    page.classList.remove('is-expanded');
    document.body.classList.remove('copilot-layout-expanded');
    expand.setAttribute('aria-pressed', 'false');
    expand.textContent = 'Ampliar espacio';
    workspace.open = previousOpen;
    notice.textContent = '';
    if (document.fullscreenElement === page) {
      try { await document.exitFullscreen(); } catch (_) { /* Layout still restores. */ }
    }
    previousFocus?.focus({ preventScroll: true });
  }
  expand.addEventListener('click', async () => {
    if (expanded) { await restore(); return; }
    expanded = true;
    previousOpen = workspace.open;
    previousFocus = document.activeElement;
    workspace.open = false;
    page.classList.add('is-expanded');
    document.body.classList.add('copilot-layout-expanded');
    expand.setAttribute('aria-pressed', 'true');
    expand.textContent = 'Restaurar espacio';
    notice.textContent = 'Espacio ampliado. Escape o Restaurar espacio para volver.';
    if (page.requestFullscreen && document.fullscreenEnabled && !document.fullscreenElement) {
      try {
        await page.requestFullscreen();
        if (!expanded && document.fullscreenElement === page) await document.exitFullscreen();
      } catch (_) {
        if (expanded) notice.textContent = 'Pantalla completa no disponible. Espacio ampliado dentro de la app; Escape para volver.';
      }
    } else {
      notice.textContent = 'Espacio ampliado dentro de la app. Escape o Restaurar espacio para volver.';
    }
  });
  document.addEventListener('fullscreenchange', () => {
    if (document.fullscreenElement === page) wasFullscreen = true;
    else if (wasFullscreen) { wasFullscreen = false; void restore(); }
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !expanded) return;
    // Let an attachment dialog consume Escape before leaving expanded mode.
    if (page.querySelector('dialog[open]')) return;
    event.preventDefault();
    void restore();
  });
  window.addEventListener('pagehide', () => observer.disconnect(), { once: true });
})();
