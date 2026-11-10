// ===== Top Page: 検索・近い順・絞り込み・一覧 =====
// 2026-11 デザイン刷新（行き先帳）: 絞り込みは「条件で絞り込む」を押すと画面の下から出る。
// 選んでいる条件は一覧の上に出し、「すべて外す」で戻せる。一覧1件の形は common.js の spotRowHTML。

(async function () {
  renderHeader('home');
  renderFooter();

  const spots = await loadJSON('data/spots.json');
  let userLat = null;
  let userLng = null;
  const activePrefs = new Set();
  const activeFilters = new Set();
  let activeSearch = '';

  const $ = id => document.getElementById(id);
  const spotList = $('spotList');
  const spotCount = $('spotCount');
  const btnGps = $('btnGps');
  const gpsLabel = btnGps.querySelector('.gps-label');
  const gpsStatus = $('gpsStatus');
  const prefSection = $('prefSection');
  const filterSection = $('filterSection');
  const searchInput = $('spotSearch');
  const searchClear = $('searchClear');
  const btnFilter = $('btnFilter');
  const filterPanel = $('filterPanel');
  const btnSeeResults = $('btnSeeResults');
  const summary = $('activeSummary');

  document.querySelectorAll('[data-total]').forEach(el => { el.textContent = spots.length; });
  document.querySelectorAll('[data-visited]').forEach(el => { el.textContent = spots.filter(s => s.visited).length; });

  // カタカナ→ひらがな変換
  function kataToHira(str) {
    return str.replace(/[ァ-ヶ]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0x60));
  }
  // 検索用の正規化（カタカナ→ひらがな、記号除去、小文字化）
  function normalizeForSearch(str) {
    return kataToHira(str.toLowerCase()).replace(/[・\-\s　]/g, '');
  }
  // 検索マッチング（name, aliases, addressを対象）
  function matchesSearch(spot, query) {
    const q = normalizeForSearch(query);
    return [spot.name, ...(spot.aliases || []), spot.address].some(f => normalizeForSearch(f).includes(q));
  }

  let searchTimer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      activeSearch = searchInput.value.trim();
      searchClear.hidden = !activeSearch;
      renderSpots();
    }, 200);
  });
  searchClear.addEventListener('click', () => {
    searchInput.value = '';
    activeSearch = '';
    searchClear.hidden = true;
    renderSpots();
    searchInput.focus();
  });

  const has = (s, t) => (s.tags || []).includes(t);
  // 絞り込みの定義（データ駆動・段ごと）
  const FILTER_GROUPS = [
    { label: '駐車場', filters: [
      { id: 'parking-free', label: '無料', test: s => s.parking.available && s.parking.free },
      { id: 'parking-paid', label: '有料', test: s => s.parking.available && !s.parking.free },
      { id: 'parking-none', label: 'なし', test: s => !s.parking.available },
    ]},
    { label: '施設', filters: [
      { id: 'dogrun', label: 'ドッグラン', test: s => s.dogRun.available },
      { id: 'toilet', label: 'トイレ', test: s => s.toilet.available },
    ]},
    { label: '料金', filters: [
      { id: 'admission-free', label: '入場無料', test: s => s.admission.free },
      { id: 'admission-paid', label: '入場有料', test: s => !s.admission.free },
    ]},
    { label: '特徴', filters: [
      { id: 'sakura', label: '桜', test: s => has(s, 'sakura') },
      { id: 'koyo', label: '紅葉', test: s => has(s, 'koyo') },
      { id: 'water', label: '水遊び', test: s => has(s, 'water') },
      { id: 'rain', label: '雨でもOK', test: s => has(s, 'rain') },
      { id: 'stay-ok', label: '宿泊可', test: s => has(s, 'stay-ok') },
      { id: 'stay-only', label: '宿泊専用', test: s => has(s, 'stay-only') },
    ]},
    // 犬のサイズ（2026-09-21）。dogSize は「そのサイズの犬がスポットの目的を果たせるか」。
    // 「ドッグラン」と同時に押している時だけ、ドッグランだけの制限（dogRun.maxSize）も見る。
    { label: '犬のサイズ', filters: [
      { id: 'size-medium', label: '中型犬OK', test: s => dogSizeAllows(s, 'medium') && (!activeFilters.has('dogrun') || dogRunSizeAllows(s, 'medium')) },
      { id: 'size-large', label: '大型犬OK', test: s => dogSizeAllows(s, 'large') && (!activeFilters.has('dogrun') || dogRunSizeAllows(s, 'large')) },
      { id: 'small-dog-only', label: '小型犬のみ', test: s => !dogSizeAllows(s, 'medium') },
    ]},
  ];
  const FILTERS = FILTER_GROUPS.flatMap(g => g.filters);

  function buildFilterButtons() {
    // 府県は一覧の上と絞り込みの画面の両方に置く（どちらで押しても両方の札がそろう・2026-11-10）
    filterSection.innerHTML = `
      <fieldset class="filter-group">
        <legend class="filter-group-label">府県</legend>
        <div class="filter-group-btns">${prefButtonsHTML()}</div>
      </fieldset>` + FILTER_GROUPS.map(g => `
      <fieldset class="filter-group">
        <legend class="filter-group-label">${g.label}</legend>
        <div class="filter-group-btns">
          ${g.filters.map(f => `<button type="button" class="filter-btn" data-filter="${f.id}" aria-pressed="false">${f.label}</button>`).join('')}
        </div>
      </fieldset>`).join('')
      + '<p class="filter-note">同じ段で複数押すと「どれか」に、別の段と組み合わせると「すべて」に当てはまるスポットを出します。</p>';
    filterSection.querySelectorAll('.filter-btn[data-pref]').forEach(btn => {
      btn.addEventListener('click', () => togglePref(btn.dataset.pref));
    });
    filterSection.querySelectorAll('.filter-btn[data-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.filter;
        if (activeFilters.has(id)) activeFilters.delete(id); else activeFilters.add(id);
        btn.setAttribute('aria-pressed', activeFilters.has(id));
        renderSpots();
      });
    });
  }

  // 府県の一覧はデータから作る。「京都府」は最短一致だと「京都」で切れるので都府道を先に並べる
  const PREF_RE = /^(北海道|東京都|京都府|大阪府|.+?県)/;
  function getPrefecture(address) {
    const m = (address || '').match(PREF_RE);
    return m ? m[1] : 'その他';
  }
  const prefList = [...new Set(spots.map(s => getPrefecture(s.address)))].filter(p => p !== 'その他');

  const prefCounts = {};
  spots.forEach(s => { const p = getPrefecture(s.address); prefCounts[p] = (prefCounts[p] || 0) + 1; });
  function prefButtonsHTML() {
    return prefList.filter(p => prefCounts[p]).map(p =>
      `<button type="button" class="filter-btn pref-btn" data-pref="${p}" aria-pressed="${activePrefs.has(p)}">${p.replace(/[府県]$/, '')}<span class="pref-n">${prefCounts[p]}</span></button>`
    ).join('');
  }
  function togglePref(p) {
    if (activePrefs.has(p)) activePrefs.delete(p); else activePrefs.add(p);
    document.querySelectorAll('.filter-btn[data-pref]').forEach(b => {
      if (b.dataset.pref === p) b.setAttribute('aria-pressed', activePrefs.has(p));
    });
    renderSpots();
  }
  function buildPrefButtons() {
    prefSection.innerHTML = prefButtonsHTML();
    prefSection.querySelectorAll('.filter-btn[data-pref]').forEach(btn => {
      btn.addEventListener('click', () => togglePref(btn.dataset.pref));
    });
  }

  function clearAll() {
    activeFilters.clear();
    activePrefs.clear();
    activeSearch = '';
    searchInput.value = '';
    searchClear.hidden = true;
    document.querySelectorAll('.filter-btn').forEach(b => b.setAttribute('aria-pressed', 'false'));
    renderSpots();
  }

  // ===== 絞り込みの画面（下から出る） =====
  // 開く時は下からすっと出し、閉じる時は下へ引っ込めてから隠す（動きは css の sheet-in / sheet-out）
  let lastFocus = null;
  let closeTimer = null;
  const reduceMotion = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  const isOpen = () => !filterPanel.hidden && !filterPanel.classList.contains('is-closing');
  function finishClose() {
    clearTimeout(closeTimer);
    closeTimer = null;
    filterPanel.removeEventListener('animationend', onCloseEnd);
    filterPanel.classList.remove('is-closing');
    filterPanel.hidden = true;
    document.body.classList.remove('sheet-open', 'sheet-closing');
  }
  function onCloseEnd(e) {
    if (e.target === filterPanel) finishClose();
  }
  function openPanel() {
    if (closeTimer) {
      // 閉じている途中で開き直した時は、引っ込める動きを取り消す
      clearTimeout(closeTimer);
      closeTimer = null;
      filterPanel.removeEventListener('animationend', onCloseEnd);
      filterPanel.classList.remove('is-closing');
      document.body.classList.remove('sheet-closing');
    } else {
      lastFocus = document.activeElement;
    }
    filterPanel.hidden = false;
    btnFilter.setAttribute('aria-expanded', 'true');
    document.body.classList.add('sheet-open');
    const first = filterPanel.querySelector('.filter-btn');
    if (first) first.focus();
  }
  function closePanel() {
    if (!isOpen()) return;
    btnFilter.setAttribute('aria-expanded', 'false');
    if (lastFocus) lastFocus.focus();
    if (reduceMotion && reduceMotion.matches) {
      finishClose();
      return;
    }
    filterPanel.classList.add('is-closing');
    document.body.classList.add('sheet-closing');
    filterPanel.addEventListener('animationend', onCloseEnd);
    // 動きの終わりの合図が来ない端末でも必ず隠す
    closeTimer = setTimeout(finishClose, 400);
  }
  btnFilter.addEventListener('click', () => (isOpen() ? closePanel() : openPanel()));
  $('sheetClose').addEventListener('click', closePanel);
  $('sheetBackdrop').addEventListener('click', closePanel);
  btnSeeResults.addEventListener('click', () => {
    closePanel();
    $('listHead').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && isOpen()) closePanel(); });

  // ===== 一覧を描く =====
  function renderSpots() {
    let filtered = [...spots];
    if (activePrefs.size > 0) {
      filtered = filtered.filter(s => activePrefs.has(getPrefecture(s.address)));
    }
    // 同じ段の中は「どれか」（OR）、段どうしは「すべて」（AND）（2026-10-04）
    if (activeFilters.size > 0) {
      const groups = FILTER_GROUPS.map(g => g.filters.filter(f => activeFilters.has(f.id))).filter(fs => fs.length > 0);
      filtered = filtered.filter(s => groups.every(fs => fs.some(f => f.test(s))));
    }
    if (activeSearch) filtered = filtered.filter(s => matchesSearch(s, activeSearch));
    if (userLat !== null && userLng !== null) {
      filtered.forEach(s => { s._distance = calcDistance(userLat, userLng, s.lat, s.lng); });
      filtered.sort((a, b) => a._distance - b._distance);
    }

    // 選んでいる条件
    const chosen = [
      ...(activeSearch ? ['「' + escapeHtml(activeSearch) + '」'] : []),
      ...[...activePrefs].map(p => p.replace(/[府県]$/, '')),
      ...FILTERS.filter(f => activeFilters.has(f.id)).map(f => f.label),
    ];
    const n = activeFilters.size + activePrefs.size;
    btnFilter.querySelector('.btn-filter-n').textContent = n ? String(n) : '';
    btnSeeResults.textContent = `${filtered.length}件を見る`;
    if (chosen.length) {
      summary.innerHTML = `<span class="sum-label">絞り込み中</span><span class="sum-items">${chosen.join('・')}</span><button type="button" class="sum-clear" id="sumClear">すべて外す</button>`;
      $('sumClear').addEventListener('click', clearAll);
    } else {
      summary.innerHTML = '';
    }
    spotCount.innerHTML = `<b>${filtered.length}</b>件${chosen.length ? `（全${spots.length}件中）` : ''}${userLat !== null ? '・近い順' : ''}`;

    // 宿泊専用フィルター時の注意書き
    let stayNote = $('stayNote');
    if (activeFilters.has('stay-only')) {
      if (!stayNote) {
        stayNote = document.createElement('p');
        stayNote.id = 'stayNote';
        stayNote.className = 'stay-note';
        stayNote.textContent = '宿泊専用の施設は、運営者が実際に泊まった場所だけを載せています。';
        spotList.parentNode.insertBefore(stayNote, spotList);
      }
    } else if (stayNote) {
      stayNote.remove();
    }

    if (filtered.length === 0) {
      spotList.innerHTML = `
        <div class="empty-state">
          <img src="images/chihuahua-notfound.png" alt="" class="empty-state-img">
          <p>この条件に合うスポットはありません。条件を1つ外してみてください。</p>
          <button type="button" class="sum-clear" id="emptyClear">条件をすべて外す</button>
        </div>`;
      $('emptyClear').addEventListener('click', clearAll);
      return;
    }
    spotList.innerHTML = filtered.map(s => spotRowHTML(s, { distance: s._distance })).join('');
  }

  // ===== 現在地 =====
  btnGps.addEventListener('click', () => {
    if (!navigator.geolocation) {
      gpsStatus.textContent = 'このブラウザでは現在地を使えません。府県やスポット名で探してください。';
      return;
    }
    btnGps.classList.add('loading');
    btnGps.setAttribute('aria-busy', 'true');
    gpsLabel.textContent = '現在地を取得中';
    gpsStatus.textContent = '';
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userLat = pos.coords.latitude;
        userLng = pos.coords.longitude;
        btnGps.classList.remove('loading');
        btnGps.removeAttribute('aria-busy');
        gpsLabel.textContent = '近い順に並べました';
        renderSpots();
      },
      (err) => {
        btnGps.classList.remove('loading');
        btnGps.removeAttribute('aria-busy');
        gpsLabel.textContent = '現在地から近い順';
        gpsStatus.textContent = err.code === 1
          ? '位置情報の使用が許可されていません。府県やスポット名で探すこともできます。'
          : '現在地を取れませんでした。もう一度押してください。';
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });

  // お気に入り（ハートはリンクの外にある）
  spotList.addEventListener('click', (e) => {
    const favBtn = e.target.closest('.fav-btn');
    if (!favBtn) return;
    e.preventDefault();
    const isNowFav = toggleFavorite(favBtn.dataset.id);
    favBtn.classList.toggle('active', isNowFav);
    favBtn.setAttribute('aria-pressed', isNowFav);
  });

  buildPrefButtons();
  buildFilterButtons();
  renderSpots();
})();
