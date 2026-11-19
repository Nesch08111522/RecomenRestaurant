/* Presentation only: never intercept navigation, forms or history. */
(() => {
    if (!document.body.classList.contains('sr-admin-precision')) return;
    document.querySelectorAll('#main-content table').forEach(table => {
      let container = table.closest('.table-container,.cat-table-wrap,.mgr-table,.table-responsive,.admin-scroll');
      if (!container) {
        container = document.createElement('div');
        container.className = 'admin-scroll';
        table.before(container);
        container.append(table);
      }
      container.tabIndex = 0;
      container.setAttribute('role', 'region');
      container.setAttribute('aria-label', table.caption?.textContent.trim() || 'Tabla de datos, desplazamiento horizontal');
    });
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    if (window.Chart) {
      Chart.register({
        id: 'adminPrecision',
        beforeUpdate(chart) {
          if (reduced.matches) chart.options.animation = false;
          chart.canvas.setAttribute('role', 'img');
          if (!chart.canvas.hasAttribute('aria-label')) {
            chart.canvas.setAttribute('aria-label', chart.canvas.closest('section,.chart-card')?.querySelector('h2,h3')?.textContent || 'Gráfico de registros');
          }
        },
        afterUpdate(chart) {
          if (!chart.canvas.closest('.chart-card')) return;
          const panel = chart.canvas.closest('.chart-card');
          let values = panel.querySelector('.admin-chart-values');
          if (!values) {
            values = document.createElement('details');
            values.className = 'admin-chart-values';
            const summary = document.createElement('summary');
            summary.textContent = 'Consultar valores registrados';
            values.append(summary);
            panel.append(values);
          }
          values.querySelector('dl')?.remove();
          const list = document.createElement('dl');
          chart.data.datasets.forEach(dataset => dataset.data.forEach((value, index) => {
            const term = document.createElement('dt');
            const description = document.createElement('dd');
            term.textContent = chart.data.labels?.[index] ?? dataset.label ?? 'Registro';
            description.textContent = typeof value === 'object' ? `Precio: ${value.x}; calificación: ${value.y}` : String(value);
            list.append(term, description);
          }));
          values.append(list);
          let empty = chart.canvas.parentElement.querySelector('.admin-chart-empty');
          const hasData = chart.data.datasets.some(dataset => dataset.data.some(value => typeof value === 'object' || Number(value) !== 0));
          chart.canvas.hidden = !hasData;
          if (!hasData && !empty) {
            empty = document.createElement('p');
            empty.className = 'admin-chart-empty';
            empty.textContent = 'Sin registros disponibles para este gráfico.';
            chart.canvas.before(empty);
          }
          if (hasData) empty?.remove();
        }
      });
      reduced.addEventListener('change', () => Object.values(Chart.instances).forEach(chart => chart.update('none')));
    }
})();
