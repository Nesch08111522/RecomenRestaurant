document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-mailbox]').forEach(box => {
    const items = [...box.querySelectorAll('[data-mail-item]')];
    const details = [...box.querySelectorAll('[data-mail-detail]')];
    const search = box.querySelector('[data-mail-search]');
    const filter = box.querySelector('[data-mail-filter]');
    function select(item) {
      items.forEach(row => row.setAttribute('aria-expanded', String(row === item)));
      details.forEach(detail => { detail.hidden = !item || detail.id !== item.dataset.mailItem; });
    }
    function update() {
      const query = search.value.trim().toLocaleLowerCase('es');
      items.forEach(item => { item.hidden = !item.textContent.toLocaleLowerCase('es').includes(query) || Boolean(filter?.value && filter.value !== item.dataset.state); });
      const visible = items.filter(item => !item.hidden);
      select(visible.find(item => item.getAttribute('aria-expanded') === 'true') || visible[0]);
      box.querySelector('[data-mail-status]').textContent = `${visible.length} resultados`;
    }
    items.forEach(item => item.addEventListener('click', () => select(item)));
    search.addEventListener('input', update);
    filter?.addEventListener('change', update);
    update();
  });
});
