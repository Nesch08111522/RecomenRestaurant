(() => {
  const status = document.getElementById('commercialStatus');
  async function send(path, data, button) {
    if (button) button.disabled = true;
    status.textContent = 'Consultando...';
    try {
      const response = await fetch('/admin/api/radar-comercial/' + path, {
        method: 'POST', credentials: 'same-origin', headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
        }, body: JSON.stringify(data)
      });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || 'Operacion no completada');
      window.location.reload();
    } catch (error) { status.textContent = error.message; }
    finally { if (button) button.disabled = false; }
  }
  document.getElementById('commercialSearch').addEventListener('submit', event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    send('discover', data, event.submitter);
  });
  document.querySelectorAll('.commercialState').forEach(form => form.addEventListener('submit', event => {
    event.preventDefault();
    send(form.dataset.id + '/state', Object.fromEntries(new FormData(form)), event.submitter);
  }));
  document.querySelectorAll('button[data-action]').forEach(button => button.addEventListener('click', () => {
    const data = {};
    if (button.dataset.action === 'convert') {
      if (!window.confirm('Crear empresa en borrador. No afilia, no asigna propietario ni activa suscripcion. Revisar evidencia y titularidad por separado.')) return;
      data.notes = window.prompt('Evidencia revisada y motivo:');
      if (!data.notes) return;
      data.confirm = true;
    }
    send(button.dataset.id + '/' + button.dataset.action, data, button);
  }));
  document.getElementById('commercialFilter').addEventListener('change', event => {
    document.querySelectorAll('article[data-state]').forEach(card => {
      card.hidden = Boolean(event.target.value && card.dataset.state !== event.target.value);
    });
  });
})();
