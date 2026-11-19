(() => {
  const canvases = [...document.querySelectorAll('[data-intelligence-chart]')];
  if (!canvases.length) return;
  const showError = (canvas) => {
    canvas.hidden = true;
    let message = canvas.parentElement.querySelector('[role="status"]');
    if (!message) {
      message = document.createElement('p');
      message.setAttribute('role', 'status');
      canvas.parentElement.append(message);
    }
    message.textContent = 'No se pudo mostrar el grafico. Consulta los valores del informe.';
  };
  if (!window.Chart) { canvases.forEach(showError); return; }
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const charts = [];
  const color = (name) => getComputedStyle(document.documentElement).getPropertyValue(`--theme-${name}`).trim();
  const money = (value) => `S/ ${(Number(value || 0) / 100).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const grid = () => color('border');
  const text = () => color('muted');
  const baseOptions = (tooltip) => ({ responsive: true, maintainAspectRatio: false, animation: reducedMotion.matches ? false : { duration: 260 }, interaction: { intersect: false, mode: 'index' }, plugins: { legend: { labels: { color: text(), usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: tooltip ? { label: tooltip } : {} } }, scales: { x: { grid: { display: false }, ticks: { color: text(), maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } }, y: { beginAtZero: true, grid: { color: grid() }, ticks: { color: text(), precision: 0 } } } });
  const draw = () => {
    charts.splice(0).forEach((chart) => chart.destroy());
    canvases.forEach((canvas) => {
      try {
      const type = canvas.dataset.intelligenceChart;
      const rows = JSON.parse(canvas.dataset.chartSeries || '[]');
      let config;
      if (type === 'forecast') {
        config = { type: 'line', data: { labels: rows.map((row) => row.day), datasets: [{ label: 'Rango histórico', data: rows.map((row) => row.high), borderColor: 'transparent', backgroundColor: color('info-bg'), fill: '+1', pointRadius: 0, tension: .35 }, { label: 'Límite inferior', data: rows.map((row) => row.low), borderColor: 'transparent', backgroundColor: color('surface'), fill: false, pointRadius: 0, tension: .35 }, { label: 'Pedidos estimados', data: rows.map((row) => row.orders), borderColor: color('accent'), backgroundColor: color('accent'), borderWidth: 2.5, pointRadius: 3, tension: .35, fill: false }] }, options: baseOptions((item) => `${item.dataset.label}: ${item.parsed.y} pedidos`) };
      } else {
        const isMoney = canvas.dataset.chartMoney === 'true' || type === 'finance';
        config = { type: type === 'line' ? 'line' : 'bar', data: { labels: rows.map((row) => row[0]), datasets: [{ label: isMoney ? 'Importe' : 'Cantidad', data: rows.map((row) => row[1]), borderColor: color('accent'), backgroundColor: type === 'line' ? color('accent-bg') : color('accent'), borderWidth: 2, borderRadius: 7, tension: .35, fill: type === 'line', pointRadius: type === 'line' ? 2.5 : 0 }] }, options: baseOptions((item) => `${item.dataset.label}: ${isMoney ? money(item.parsed.y) : item.parsed.y}`) };
      }
      charts.push(new Chart(canvas, config));
      } catch (error) { console.error('Intelligence chart failed', error); showError(canvas); }
    });
  };
  draw();
  reducedMotion.addEventListener('change', draw);
  new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
