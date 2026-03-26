// ===== Top Page: GPS, Filter, Spot List =====

(async function () {
  renderHeader('home');
  renderFooter();

  const spots = await loadJSON('data/spots.json');
  let userLat = null;
  let userLng = null;
  const spotList = document.getElementById('spotList');
  const spotCount = document.getElementById('spotCount');
  const btnGps = document.getElementById('btnGps');
  const gpsStatus = document.getElementById('gpsStatus');
  const sortSelect = document.getElementById('sortSelect');

  // Prefecture order for sorting
  const prefOrder = ['大阪府', '京都府', '兵庫県', '奈良県', '滋賀県', '和歌山県'];

  function getPrefecture(address) {
    for (const pref of prefOrder) {
      if (address.startsWith(pref)) return pref;
    }
    return 'その他';
  }

  // ===== Render spots =====
  function renderSpots() {
    let filtered = [...spots];

    const sortMode = sortSelect.value;

    // Sort by distance if GPS available and sort mode is gps
    if (sortMode === 'gps' && userLat !== null && userLng !== null) {
      filtered.forEach(s => {
        s._distance = calcDistance(userLat, userLng, s.lat, s.lng);
      });
      filtered.sort((a, b) => a._distance - b._distance);
    } else if (sortMode === 'prefecture') {
      filtered.sort((a, b) => {
        const pa = prefOrder.indexOf(getPrefecture(a.address));
        const pb = prefOrder.indexOf(getPrefecture(b.address));
        return (pa === -1 ? 999 : pa) - (pb === -1 ? 999 : pb);
      });
    }

    spotCount.textContent = `${filtered.length} 件のスポット`;

    if (filtered.length === 0) {
      spotList.innerHTML = `
        <div class="empty-state">
          <div class="icon"></div>
          <p>条件に合うスポットが見つかりませんでした</p>
        </div>
      `;
      return;
    }

    spotList.innerHTML = filtered.map(s => {
      const distText = s._distance != null ? `<span class="spot-card-distance">${formatDistance(s._distance)}</span>` : '';
      const tags = [];

      if (s.visited) tags.push('<span class="tag tag-visited">実訪問済み</span>');
      if (s.dogSize.small) tags.push('<span class="tag">小型犬OK</span>');
      if (s.dogSize.large) tags.push('<span class="tag">大型犬OK</span>');
      if (s.parking.available) {
        tags.push(`<span class="tag">P ${s.parking.free ? '無料' : '有料'}</span>`);
      }
      if (s.dogRun.available) tags.push('<span class="tag">ドッグラン</span>');
      if (s.admission.free) tags.push('<span class="tag">入場無料</span>');

      return `
        <a href="spot.html?id=${s.id}" class="spot-card">
          <div class="spot-card-header">
            <span class="spot-card-name">${s.name}</span>
            ${distText}
          </div>
          <p class="spot-card-address">${s.address}</p>
          <div class="spot-card-tags">${tags.join('')}</div>
        </a>
      `;
    }).join('');
  }

  // ===== GPS =====
  btnGps.addEventListener('click', () => {
    if (!navigator.geolocation) {
      gpsStatus.textContent = 'お使いのブラウザではGPS機能を利用できません';
      return;
    }

    btnGps.classList.add('loading');
    btnGps.textContent = '取得中...';
    gpsStatus.textContent = '';

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userLat = pos.coords.latitude;
        userLng = pos.coords.longitude;
        btnGps.classList.remove('loading');
        btnGps.textContent = '現在地を更新';
        gpsStatus.textContent = '現在地を取得しました。近い順に並べ替えました。';
        // Add GPS sort option if not already present
        if (!sortSelect.querySelector('option[value="gps"]')) {
          const opt = document.createElement('option');
          opt.value = 'gps';
          opt.textContent = '現在地から近い順';
          sortSelect.insertBefore(opt, sortSelect.firstChild);
        }
        sortSelect.value = 'gps';
        renderSpots();
      },
      (err) => {
        btnGps.classList.remove('loading');
        btnGps.textContent = '現在地から探す';
        if (err.code === 1) {
          gpsStatus.textContent = '位置情報の使用が許可されていません。ブラウザの設定をご確認ください。';
        } else {
          gpsStatus.textContent = '位置情報の取得に失敗しました。もう一度お試しください。';
        }
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });

  // ===== Sort =====
  sortSelect.addEventListener('change', () => {
    renderSpots();
  });

  // Initial render
  renderSpots();
})();
