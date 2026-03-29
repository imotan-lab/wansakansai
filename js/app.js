// ===== Top Page: GPS, Prefecture Filter, Spot List =====

(async function () {
  renderHeader('home');
  renderFooter();

  const spots = await loadJSON('data/spots.json');
  let userLat = null;
  let userLng = null;
  let activePref = null; // null = all

  const spotList = document.getElementById('spotList');
  const spotCount = document.getElementById('spotCount');
  const btnGps = document.getElementById('btnGps');
  const gpsStatus = document.getElementById('gpsStatus');
  const prefSection = document.getElementById('prefSection');

  // Extract prefecture list from spot data
  function getPrefecture(address) {
    const m = address.match(/^(.+?[都道府県])/);
    return m ? m[1] : 'その他';
  }

  const prefList = [...new Set(spots.map(s => getPrefecture(s.address)))].filter(p => p !== 'その他');

  // Build prefecture buttons from actual data
  function buildPrefButtons() {
    const prefCounts = {};
    spots.forEach(s => {
      const pref = getPrefecture(s.address);
      prefCounts[pref] = (prefCounts[pref] || 0) + 1;
    });

    // "すべて" button
    let html = `<button class="pref-btn active" data-pref="">すべて(${spots.length})</button>`;
    prefList.forEach(pref => {
      if (prefCounts[pref]) {
        const shortName = pref.replace(/[府県]$/, '');
        html += `<button class="pref-btn" data-pref="${pref}">${shortName}(${prefCounts[pref]})</button>`;
      }
    });

    prefSection.innerHTML = html;

    // Add click events
    prefSection.querySelectorAll('.pref-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        prefSection.querySelectorAll('.pref-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activePref = btn.dataset.pref || null;
        renderSpots();
      });
    });
  }

  // ===== Render spots =====
  function renderSpots() {
    let filtered = [...spots];

    // Filter by prefecture
    if (activePref) {
      filtered = filtered.filter(s => getPrefecture(s.address) === activePref);
    }

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
          <img src="images/chihuahua-notfound.png" alt="" class="empty-state-img">
          <p>この地域のスポットはまだありません</p>
        </div>
      `;
      return;
    }

    spotList.innerHTML = filtered.map(s => {
      const distText = s._distance != null ? `<span class="spot-card-distance">${formatDistance(s._distance)}</span>` : '';
      const visitedStamp = s.visited ? '<img src="images/stamp-visited.png" alt="訪問済み" class="visited-stamp">' : '';
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

  // Build buttons & initial render
  buildPrefButtons();
  renderSpots();
})();
