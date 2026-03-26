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

  // ===== Render spots =====
  function renderSpots() {
    let filtered = [...spots];

    // Sort by distance if GPS available
    if (userLat !== null && userLng !== null) {
      filtered.forEach(s => {
        s._distance = calcDistance(userLat, userLng, s.lat, s.lng);
      });
      filtered.sort((a, b) => a._distance - b._distance);
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
      const categoryLabel = s.category === 'park' ? '公園' : '散歩スポット';
      const tags = [];

      if (s.visited) tags.push('<span class="tag tag-visited">実訪問済み</span>');
      tags.push(`<span class="tag tag-category">${categoryLabel}</span>`);
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

  // Initial render
  renderSpots();
})();
