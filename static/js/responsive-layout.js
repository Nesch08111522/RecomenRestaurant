/* Add internal horizontal scrolling around data tables where markup has no wrapper. */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('table').forEach((table) => {
    if (table.closest('.table-responsive, .table-container, .table-wrapper')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'table-responsive';
    wrapper.setAttribute('tabindex', '0');
    wrapper.setAttribute('role', 'region');
    wrapper.setAttribute('aria-label', 'Tabla desplazable horizontalmente');
    table.parentNode.insertBefore(wrapper, table);
    wrapper.appendChild(table);
  });
});
