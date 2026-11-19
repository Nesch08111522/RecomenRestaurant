/* Loaded after Chart.js and before page chart constructors. */
(() => {
  if (!window.Chart) return;
  Chart.register({id:'srTheme', beforeUpdate(chart) {
    const c = window.SRTheme.color;
    chart.options.color = c('text');
    if (chart.options.plugins.legend) chart.options.plugins.legend.labels.color = c('text');
    if (chart.options.plugins.tooltip) Object.assign(chart.options.plugins.tooltip, {backgroundColor:c('elevated'), titleColor:c('text'), bodyColor:c('text'), borderColor:c('border'), borderWidth:1});
    Object.values(chart.options.scales || {}).forEach(scale => {
      if (scale.ticks) scale.ticks.color = c('muted');
      if (scale.grid) scale.grid.color = c('border');
      if (scale.title) scale.title.color = c('text');
    });
    chart.data.datasets.forEach((dataset, index) => {
      const multi = ['pie','doughnut','polarArea'].includes(chart.config.type);
      dataset.backgroundColor = multi ? chart.data.labels.map((_, i) => c('chart-' + (i % 6 + 1))) : c('chart-' + (index % 6 + 1));
      dataset.borderColor = multi ? c('surface') : c('chart-' + (index % 6 + 1));
    });
  }});
  document.addEventListener('themechange', () => Object.values(Chart.instances).forEach(chart => chart.update('none')));
})();
