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

  countEl.innerHTML = `<b>${favSpots.length}</b>件`;

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

    countEl.innerHTML = `<b>${list.length}</b>件`;

    // 一覧1件の形はトップと同じ（common.js の spotRowHTML）
    container.innerHTML = list.map(s => spotRowHTML(s)).join('');
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
