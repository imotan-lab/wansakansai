// ===== テーマ一覧（hub）描画 =====
// js/themes-data.js（window.THEMES）と #themeGrid を前提とする。
(async function () {
  renderHeader('themes');
  renderFooter();

  const base = getBasePath();
  const grid = document.getElementById('themeGrid');
  if (!grid || !window.THEMES) return;

  let spots;
  try {
    spots = await loadJSON(base + 'data/spots.json');
  } catch (e) {
    grid.innerHTML = '<p class="theme-empty">スポット情報の読み込みに失敗しました。時間をおいて再度お試しください。</p>';
    return;
  }

  grid.innerHTML = window.THEMES.map((t) => {
    const n = spots.filter(t.filter).length;
    return `
      <a href="${t.slug}.html" class="theme-card">
        <div class="theme-card-title">${t.navTitle}</div>
        <div class="theme-card-count">${n}件</div>
        <div class="theme-card-lead">${t.lead}</div>
      </a>`;
  }).join('');
})();
