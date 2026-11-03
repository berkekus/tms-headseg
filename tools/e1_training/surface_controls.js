const graph = document.getElementById('e1-surface-plot');
const status = document.getElementById('e1-surface-status');
const checks = Array.from(document.querySelectorAll('[data-surface-index]'));
const ranges = Array.from(document.querySelectorAll('[data-opacity-index]'));
const defaults = {1: 12, 2: 30, 3: 25, 4: 100, 5: 100};

checks.forEach(check => {
  check.disabled = false;
  check.addEventListener('change', () => {
    Plotly.restyle(graph, {visible: check.checked}, [Number(check.dataset.surfaceIndex)]);
  });
});
ranges.forEach(range => {
  range.disabled = false;
  range.addEventListener('input', () => {
    Plotly.restyle(graph, {opacity: Number(range.value) / 100}, [Number(range.dataset.opacityIndex)]);
  });
});
document.querySelectorAll('[data-surface-preset]').forEach(button => {
  button.disabled = false;
  button.addEventListener('click', () => {
    const preset = button.dataset.surfacePreset;
    checks.forEach((check, index) => {
      const label = Number(check.dataset.surfaceLabel);
      let visible = label === 1 || label === 4;
      let opacity = defaults[label];
      if (preset === 'brain') visible = label === 4 || label === 5;
      if (preset === 'head') {visible = label === 1; opacity = 100;}
      if (preset === 'all') {visible = true; if (label === 4) opacity = 60;}
      check.checked = visible;
      ranges[index].value = String(opacity);
      Plotly.restyle(graph, {visible, opacity: opacity / 100}, [index]);
    });
    if (preset === 'reset') {
      Plotly.relayout(graph, {'scene.camera': {up: {x: 0, y: 0, z: 1}, eye: {x: 1.6, y: -1.8, z: 1.1}}});
    }
  });
});
status.textContent = '3B hazır · görünürlük kaydırıcısı: 0 saydam, 100 opak.';
graph.on('plotly_webglcontextlost', () => {
  status.textContent = 'Tarayıcının 3B bağlamı kesildi. Raporu yeniden aç veya 2B kesitleri kullan.';
});
