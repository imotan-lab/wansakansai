// ===== Theme Landing Page (reusable) =====
// 各テーマページは本ファイルの前に js/themes-data.js を読み込み、
//   window.THEME_SLUG = '<slug>';  // themes-data.js の THEMES に対応
// を定義しておく。フィルタは themes-data.js 側で一元管理する。
// （旧式の window.THEME_CONFIG.filter も後方互換で受け付ける）
// ページ側に #themeSpotList（一覧描画先）と #themeCount（件数表示・任意）を置くこと。

(async function () {
  const cfg = window.THEME_CONFIG || {};
  renderHeader(cfg.activeNav || 'themes');
  renderFooter();

  const base = getBasePath(); // themes/ 配下からは '../'
  const listEl = document.getElementById('themeSpotList');
  const countEl = document.getElementById('themeCount');

  let filter = cfg.filter;
  if (typeof filter !== 'function' && window.THEME_SLUG && typeof window.getThemeBySlug === 'function') {
    const t = window.getThemeBySlug(window.THEME_SLUG);
    if (t) filter = t.filter;
  }
  if (!listEl || typeof filter !== 'function') return;

  let spots;
  try {
    spots = await loadJSON(base + 'data/spots.json');
  } catch (e) {
    listEl.innerHTML = '<p class="theme-empty">スポット情報の読み込みに失敗しました。時間をおいて再度お試しください。</p>';
    return;
  }

  const matched = spots.filter(filter);
  if (countEl) countEl.textContent = `該当 ${matched.length} 件`;

  if (matched.length === 0) {
    listEl.innerHTML = '<p class="theme-empty">現在、該当するスポットはありません。</p>';
    return;
  }

  // 都道府県の抽出（app.js と同じ規則で統一）
  function getPrefecture(address) {
    const m = (address || '').match(/^(.+?[都道府県])/);
    return m ? m[1] : 'その他';
  }

  // 府県ごとにグループ化（件数の多い順）
  const groups = {};
  matched.forEach(s => {
    const p = getPrefecture(s.address);
    (groups[p] = groups[p] || []).push(s);
  });
  const prefOrder = Object.keys(groups).sort((a, b) => groups[b].length - groups[a].length);

  function cardHTML(s) {
    const dr = s.dogRun || {};
    const visitedStamp = s.visited
      ? `<img src="${base}images/stamp-visited.png" alt="運営が実際に訪問済み" class="visited-stamp">`
      : '';
    const tags = [];
    if (s.parking && s.parking.available) {
      tags.push(`<span class="tag">P ${s.parking.free ? '無料' : '有料'}</span>`);
    }
    if (dr.available) {
      let t = 'ドッグラン';
      if (dr.separated) t += '(エリア分離)';
      if (dr.free) t += '・無料';
      tags.push(`<span class="tag">${t}</span>`);
    }
    if (s.admission && s.admission.free) tags.push('<span class="tag">入場無料</span>');

    return `
      <a href="${base}spots/${encodeURIComponent(s.id)}.html" class="spot-card">
        ${visitedStamp}
        <div class="spot-card-header">
          <span class="spot-card-name">${escapeHtml(s.name)}</span>
        </div>
        <p class="spot-card-address">${escapeHtml(s.address)}</p>
        <div class="spot-card-tags">${tags.join('')}</div>
      </a>`;
  }

  listEl.innerHTML = prefOrder.map(p => {
    const items = groups[p].slice().sort((a, b) => {
      if (!!a.visited !== !!b.visited) return a.visited ? -1 : 1; // 訪問済みを先頭に
      return a.name.localeCompare(b.name, 'ja');
    });
    return `
      <section class="theme-group">
        <h2 class="theme-group-title">${escapeHtml(p.replace(/[府県]$/, ''))}（${items.length}）</h2>
        <div class="spot-list">${items.map(cardHTML).join('')}</div>
      </section>`;
  }).join('');
})();
