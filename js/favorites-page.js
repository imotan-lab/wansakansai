// ===== Favorites Page =====

(async function () {
  renderHeader('favorites');
  renderFooter();

  const container = document.getElementById('spotList');
  const countEl = document.getElementById('spotCount');
  const favIds = getFavorites();

  if (favIds.size === 0) {
    countEl.textContent = '';
    container.innerHTML = `
      <div class="empty-state">
        <img src="images/chihuahua-notfound.png" alt="" class="empty-state-img">
        <p>まだお気に入りはありません</p>
        <p style="margin-top:8px;font-size:0.85rem;"><a href="index.html">スポット一覧</a>でハートを押して追加しましょう</p>
      </div>
    `;
    return;
  }

  const spots = await loadJSON('data/spots.json');
  const favSpots = spots.filter(s => favIds.has(s.id));

  countEl.textContent = `${favSpots.length} 件`;

  function renderFavList() {
    const current = getFavorites();
    const list = spots.filter(s => current.has(s.id));

    if (list.length === 0) {
      countEl.textContent = '';
      container.innerHTML = `
        <div class="empty-state">
          <img src="images/chihuahua-notfound.png" alt="" class="empty-state-img">
          <p>お気に入りが空になりました</p>
          <p style="margin-top:8px;font-size:0.85rem;"><a href="index.html">スポット一覧に戻る</a></p>
        </div>
      `;
      return;
    }

    countEl.textContent = `${list.length} 件`;

    container.innerHTML = list.map(s => {
      const visitedStamp = s.visited ? '<img src="images/stamp-visited.png" alt="運営が実際に訪問済み" class="visited-stamp">' : '';
      const tags = [];
      if (s.parking.available) {
        tags.push(`<span class="tag">P ${s.parking.free ? '無料' : '有料'}</span>`);
      }
      if (s.dogRun.available) {
        let drText = 'ドッグラン';
        if (s.dogRun.separated) drText += '(エリア分離)';
        tags.push(`<span class="tag">${drText}</span>`);
      }
      if (s.admission.free) tags.push('<span class="tag">入場無料</span>');

      return `
        <a href="spot.html?id=${s.id}" class="spot-card">
          ${visitedStamp}
          <div class="spot-card-header">
            <span class="spot-card-name">${s.name}</span>
            <div class="spot-card-right">
              <button class="fav-btn active" data-id="${s.id}" aria-label="お気に入りを解除">&#9829;</button>
            </div>
          </div>
          <p class="spot-card-address">${s.address}</p>
          <div class="spot-card-tags">${tags.join('')}</div>
        </a>
      `;
    }).join('');
  }

  renderFavList();

  // ハートを押すとリストから除去
  container.addEventListener('click', (e) => {
    const favBtn = e.target.closest('.fav-btn');
    if (!favBtn) return;
    e.preventDefault();
    toggleFavorite(favBtn.dataset.id);
    renderFavList();
  });
})();
