/* Add internal horizontal scrolling around data tables where markup has no wrapper. */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('table').forEach((table) => {
    let wrapper = table.closest('.table-responsive, .table-container, .table-wrapper, .mgr-table');
    if (!wrapper) {
      wrapper = document.createElement('div');
      wrapper.className = 'table-responsive';
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    }
    if (!wrapper.hasAttribute('tabindex')) wrapper.setAttribute('tabindex', '0');
    if (!wrapper.hasAttribute('role')) wrapper.setAttribute('role', 'region');
    if (!wrapper.hasAttribute('aria-label') && !wrapper.hasAttribute('aria-labelledby')) {
      wrapper.setAttribute('aria-label', table.caption?.textContent.trim() || table.getAttribute('aria-label') || 'Tabla desplazable horizontalmente');
    }
  });
});
