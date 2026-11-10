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
          ${g.filters.map(f => `<button type="button" class="filter-btn" data-filter="${f.id}" aria-pressed="${activeFilters.has(f.id)}">${f.label}</button>`).join('')}
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
  // 動きは css の transition（is-off＝画面の下に隠れた位置）。途中で閉じても開いても、その位置から引き返す。
  // 開いている間は後ろのページを操作できなくし（inert）、Tab も画面の中で回す。
  // 閉じ終わってから、開く前の場所へフォーカスを戻す（2026-11-11 Codex と自分の試験で見つけた抜けを直した）。
  let lastFocus = null;
  let closeTimer = null;
  let focusAfterClose = null;
  const sheetBackdrop = $('sheetBackdrop');
  const reduceMotion = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  const noMotion = () => !!(reduceMotion && reduceMotion.matches);
  const isOpen = () => !filterPanel.hidden && !filterPanel.classList.contains('is-closing');
  filterPanel.classList.add('is-off');

  // 後ろのページ（絞り込みの画面と背景の幕以外）を操作できなくする
  function setBackgroundInert(on) {
    let el = filterPanel;
    while (el && el !== document.body && el.parentElement) {
      Array.from(el.parentElement.children).forEach(sib => {
        if (sib === el || sib === sheetBackdrop || sib.tagName === 'SCRIPT') return;
        if (on) sib.setAttribute('inert', ''); else sib.removeAttribute('inert');
      });
      el = el.parentElement;
    }
  }
  function focusables() {
    return Array.from(filterPanel.querySelectorAll('button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
      .filter(el => !el.disabled && el.offsetParent !== null);
  }
  function finishClose() {
    clearTimeout(closeTimer);
    closeTimer = null;
    filterPanel.removeEventListener('transitionend', onCloseEnd);
    filterPanel.classList.remove('is-closing');
    filterPanel.hidden = true;
    document.body.classList.remove('sheet-open');
    // 後ろを操作できるようにするのは、画面が消えきってから（閉じる途中に Tab で後ろへ出ないように）
    setBackgroundInert(false);
    const target = focusAfterClose || lastFocus;
    focusAfterClose = null;
    if (target && target.focus) target.focus({ preventScroll: true });
  }
  function onCloseEnd(e) {
    if (e.target === filterPanel && e.propertyName === 'transform') finishClose();
  }
  function openPanel() {
    if (closeTimer) {
      // 閉じている途中で開き直した時は、今の位置から引き返す（フォーカスの戻り先は最初に開いた時のまま）
      clearTimeout(closeTimer);
      closeTimer = null;
      filterPanel.removeEventListener('transitionend', onCloseEnd);
      filterPanel.classList.remove('is-closing');
      focusAfterClose = null;
    } else {
      // iPhone の Safari はボタンを押してもフォーカスを移さないので、その時は「条件で絞り込む」へ戻す
      const ae = document.activeElement;
      lastFocus = ae && ae !== document.body && !filterPanel.contains(ae) ? ae : btnFilter;
      filterPanel.classList.add('is-off');
      filterPanel.hidden = false;
      document.body.classList.add('sheet-open');
      void filterPanel.offsetHeight; // 隠れた位置を一度描かせてから動かす
    }
    filterPanel.classList.remove('is-off');
    document.body.classList.add('sheet-shown');
    btnFilter.setAttribute('aria-expanded', 'true');
    setBackgroundInert(true);
    const first = filterPanel.querySelector('.filter-btn');
    if (first) first.focus({ preventScroll: true });
  }
  function closePanel(then) {
    if (!isOpen()) return;
    focusAfterClose = then || null;
    btnFilter.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('sheet-shown');
    if (noMotion()) {
      filterPanel.classList.add('is-off');
      finishClose();
      return;
    }
    filterPanel.classList.add('is-closing', 'is-off');
    filterPanel.addEventListener('transitionend', onCloseEnd);
    // 動きの終わりの合図が来ない端末でも必ず隠す（閉じる動きは0.38秒）
    closeTimer = setTimeout(finishClose, 700);
  }
  btnFilter.addEventListener('click', () => (isOpen() ? closePanel() : openPanel()));
  $('sheetClose').addEventListener('click', () => closePanel());
  sheetBackdrop.addEventListener('click', () => closePanel());
  btnSeeResults.addEventListener('click', () => {
    // 一覧の見出しへ送り、閉じ終わったらフォーカスもそこへ（ボタンへ戻すと画面が上へ引き戻されるため）
    const head = $('listHead');
    closePanel(head);
    head.scrollIntoView({ behavior: noMotion() ? 'auto' : 'smooth', block: 'start' });
  });
  document.addEventListener('keydown', e => {
    if (filterPanel.hidden) return;
    if (e.key === 'Escape') { if (isOpen()) closePanel(); return; }
    if (e.key !== 'Tab') return; // Tab は閉じる途中も画面の中で回す（消えきるまでは後ろへ出さない）
    const items = focusables();
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (!filterPanel.contains(document.activeElement)) {
      e.preventDefault(); first.focus();
    } else if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  });

  // ===== 一覧を描く =====
  function renderSpots() {
    // 条件が変わるたびに、この履歴に状態を残す（ページを離れる時の保存は WebKit では効かないことがあるため）
    saveSoon();
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

  // ===== 詳細から戻った時に、絞り込み・並び・見ていた位置をそのまま出す（2026-11-10・11-11作り直し） =====
  // ブラウザがページを残していればそのまま戻る。読み直す端末のために、このページの履歴の1件ずつに
  // 状態を持たせる（history.state）。履歴の1件ごとなので、別の時に開いたトップの状態が混ざらない。
  // 普通にトップを開いた時（ロゴ・リンク）は新しい履歴なので、何も出し直さない。
  const STATE_KEY = 'wskTop';
  function rowAnchor() {
    // 画面の上端に見えている最初のスポットと、そのずれ。フォントの読み込みで行の高さが変わっても同じ行へ戻すため
    const top = 64;
    const rows = spotList.querySelectorAll('.spot-row');
    for (const r of rows) {
      const rect = r.getBoundingClientRect();
      if (rect.bottom > top) {
        const link = r.querySelector('.row-link');
        return { href: link ? link.getAttribute('href') : '', off: Math.round(rect.top) };
      }
    }
    return null;
  }
  let saveTimer = null;
  function saveState() {
    clearTimeout(saveTimer);
    saveTimer = null;
    try {
      const st = Object.assign({}, history.state || {});
      st[STATE_KEY] = {
        prefs: [...activePrefs], filters: [...activeFilters],
        q: searchInput.value.trim(), // 打ったばかりでまだ一覧に反映していない語も残す
        lat: userLat, lng: userLng,
        y: Math.round(window.scrollY), anchor: rowAnchor(),
      };
      history.replaceState(st, '');
    } catch (_) { /* 保存できない端末では覚えないだけ */ }
  }
  function saveSoon() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveState, 400);
  }
  let restore = null;
  try {
    const saved = history.state && history.state[STATE_KEY];
    if (saved) {
      (saved.prefs || []).forEach(p => { if (prefList.includes(p)) activePrefs.add(p); });
      (saved.filters || []).forEach(id => { if (FILTERS.some(f => f.id === id)) activeFilters.add(id); });
      if (saved.q) {
        activeSearch = String(saved.q);
        searchInput.value = activeSearch;
        searchClear.hidden = false;
      }
      if (typeof saved.lat === 'number' && typeof saved.lng === 'number') {
        userLat = saved.lat;
        userLng = saved.lng;
        gpsLabel.textContent = '近い順に並べました';
      }
      restore = saved;
    }
  } catch (_) { /* 読めなければ最初の状態で出す */ }
  // 位置はこちらで戻すので、ブラウザ任せの位置戻しは止める（順番が前後して一覧の描画前に戻されるため）
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  window.addEventListener('pagehide', saveState);
  window.addEventListener('scroll', saveSoon, { passive: true });
  spotList.addEventListener('click', (e) => { if (e.target.closest('a')) saveState(); });

  function jumpTo(y) {
    // html の scroll-behavior: smooth を一時的に外して、すぐその位置へ
    const html = document.documentElement;
    const prev = html.style.scrollBehavior;
    html.style.scrollBehavior = 'auto';
    window.scrollTo(0, Math.max(0, y));
    html.style.scrollBehavior = prev;
  }
  function restorePosition() {
    if (!restore) return;
    const a = restore.anchor;
    const row = a && a.href ? Array.from(spotList.querySelectorAll('.row-link')).find(l => l.getAttribute('href') === a.href) : null;
    if (row) {
      const r = row.closest('.spot-row').getBoundingClientRect();
      jumpTo(window.scrollY + r.top - a.off);
    } else if (typeof restore.y === 'number') {
      jumpTo(restore.y);
    }
  }

  // ブラウザが残していたページに戻った時: 詳細で押したお気に入りを、一覧のハートに反映し直す
  window.addEventListener('pageshow', (e) => {
    if (!e.persisted) return;
    const favs = getFavorites();
    spotList.querySelectorAll('.fav-btn').forEach(b => {
      const on = favs.has(b.dataset.id);
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on);
    });
  });

  buildPrefButtons();
  buildFilterButtons();
  renderSpots();
  if (restore) {
    restorePosition();
    // 文字の読み込みで行の高さが変わったら、もう一度合わせる（その前に自分で動かし始めていたら触らない）
    let userMoved = false;
    ['touchstart', 'wheel', 'keydown', 'pointerdown'].forEach(ev =>
      window.addEventListener(ev, () => { userMoved = true; }, { once: true, passive: true }));
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(() => { if (!userMoved) restorePosition(); });
    }
  }
})();
