// ===== Spot Detail Page =====

(async function () {
  renderHeader('home');
  renderFooter();

  const container = document.getElementById('spotDetail');
  const params = new URLSearchParams(window.location.search);
  const spotId = params.get('id');

  if (!spotId) {
    container.innerHTML = '<div class="empty-state"><p>スポットが指定されていません</p></div>';
    return;
  }

  try {
    const [spots, dangers] = await Promise.all([
      loadJSON('data/spots.json'),
      loadJSON('data/dangers.json')
    ]);
    const spot = spots.find(s => s.id === spotId);

    if (!spot) {
      container.innerHTML = '<div class="empty-state"><p>スポットが見つかりませんでした</p></div>';
      return;
    }

    // Update page title & SEO meta
    document.title = `${spot.name} - わんさかんさい`;
    const spotUrl = `https://wansakansai.com/spot.html?id=${spot.id}`;
    const spotDesc = `${spot.name}（${spot.address}）の犬連れお出かけ情報。駐車場・トイレ・ドッグラン情報など。`;
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) metaDesc.content = spotDesc;
    // canonical
    let canonical = document.querySelector('link[rel="canonical"]');
    if (canonical) canonical.href = spotUrl;
    // OGP
    const ogUpdates = { 'og:title': `${spot.name} - わんさかんさい`, 'og:description': spotDesc, 'og:url': spotUrl };
    for (const [prop, val] of Object.entries(ogUpdates)) {
      const el = document.querySelector(`meta[property="${prop}"]`);
      if (el) el.content = val;
    }
    // JSON-LD
    const jsonLd = document.createElement('script');
    jsonLd.type = 'application/ld+json';
    jsonLd.textContent = JSON.stringify({
      '@context': 'https://schema.org', '@type': 'Place',
      name: spot.name, address: { '@type': 'PostalAddress', addressRegion: spot.address },
      geo: { '@type': 'GeoCoordinates', latitude: spot.lat, longitude: spot.lng },
      url: spotUrl
    });
    document.head.appendChild(jsonLd);

    // Build info
    const visitedStamp = spot.visited ? '<img src="images/stamp-visited.png" alt="運営が実際に訪問済み" class="detail-visited-stamp">' : '';

    let parkingText = 'なし';
    if (spot.parking.available) {
      parkingText = spot.parking.free ? 'あり（無料）' : 'あり（有料）';
    }

    let toiletText = 'なし';
    if (spot.toilet.available) {
      toiletText = spot.toilet.western ? 'あり（洋式）' : 'あり（和式）';
    }

    let dogRunText = 'なし';
    if (spot.dogRun.available) {
      dogRunText = spot.dogRun.free ? 'あり（無料）' : 'あり（有料）';
      if (spot.dogRun.detail) dogRunText += ` / ${spot.dogRun.detail}`;
    }

    let admissionText = spot.admission.free ? '無料' : `有料（${spot.admission.fee || ''})`;

    const mapQuery = encodeURIComponent(spot.name + ' ' + spot.address);

    const isFav = isFavorite(spot.id);

    // Build gallery
    const images = spot.images || (spot.imageUrl ? [spot.imageUrl] : []);
    let galleryHtml = '';
    if (images.length > 0) {
      galleryHtml = `
        <div class="spot-gallery">
          <div class="spot-gallery-main">
            <img src="${images[0]}" alt="${spot.name}" class="spot-gallery-img" id="galleryMainImg">
            ${images.length > 1 ? `
              <button class="gallery-nav gallery-prev" id="galleryPrev">&lt;</button>
              <button class="gallery-nav gallery-next" id="galleryNext">&gt;</button>
            ` : ''}
          </div>
          ${images.length > 1 ? `
            <div class="spot-gallery-thumbs">
              ${images.map((img, i) => `<img src="${img}" alt="" class="spot-gallery-thumb${i === 0 ? ' active' : ''}" data-index="${i}">`).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }

    container.className = '';
    container.innerHTML = `
      <div class="spot-detail">
        ${galleryHtml}
        <div class="spot-detail-header">
          ${visitedStamp}
          <h1 class="spot-detail-title">${spot.name}</h1>
        </div>
        <p class="spot-detail-address">${spot.address}</p>
        <button class="detail-fav-btn${isFav ? ' active' : ''}" id="detailFavBtn">
          &#9829; ${isFav ? 'お気に入り済み' : 'お気に入りに追加'}
        </button>

        <iframe
          class="spot-map"
          src="https://maps.google.co.jp/maps?q=${mapQuery}&output=embed&z=15"
          allowfullscreen
          loading="lazy"
          referrerpolicy="no-referrer-when-downgrade"
        ></iframe>

        <div class="detail-info-list">
          <div class="detail-info-item">
            <span class="detail-info-label">駐車場</span>
            <span class="detail-info-value">${parkingText}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-label">トイレ</span>
            <span class="detail-info-value">${toiletText}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-label">ドッグラン</span>
            <span class="detail-info-value">${dogRunText}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-label">入場料</span>
            <span class="detail-info-value">${admissionText}</span>
          </div>
          ${spot.officialUrl ? `
          <div class="detail-info-item">
            <span class="detail-info-label">公式HP</span>
            <span class="detail-info-value"><a href="${spot.officialUrl}" target="_blank" rel="noopener noreferrer">${spot.officialUrl.replace(/^https?:\/\//, '').replace(/\/$/, '')}</a></span>
          </div>` : ''}
        </div>

        ${(spot.tags || []).includes('small-dog-only') ? `
          <div class="detail-warn">小型犬のみ入場可（大型犬は要確認）</div>
        ` : ''}

        ${spot.remarks ? `
          <div class="detail-remarks">
            <h3>備考・犬連れでのポイント</h3>
            <p>${(() => {
              const sentences = spot.remarks.split('。').filter(s => s);
              let html = '';
              let buffer = '';
              for (let i = 0; i < sentences.length; i++) {
                const s = sentences[i] + '。';
                buffer += s;
                if (buffer.length >= 30 || i === sentences.length - 1) {
                  html += buffer + (i < sentences.length - 1 ? '<br>' : '');
                  buffer = '';
                }
              }
              return html;
            })()}</p>
          </div>
        ` : ''}

        <div class="share-buttons">
          <span class="share-label">シェア</span>
          <a href="https://twitter.com/intent/tweet?text=${encodeURIComponent(spot.name + ' - わんさかんさい')}&url=${encodeURIComponent(window.location.href)}" target="_blank" rel="noopener noreferrer" class="share-btn share-x">X</a>
          <a href="https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(window.location.href)}" target="_blank" rel="noopener noreferrer" class="share-btn share-line">LINE</a>
          <a href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(window.location.href)}" target="_blank" rel="noopener noreferrer" class="share-btn share-fb">Facebook</a>
        </div>

        ${(() => {
          const related = dangers.filter(d => {
            const text = d.location + d.description;
            return spotNameMatchesText(spot, text);
          });
          if (related.length === 0) return '';
          related.sort((a, b) => new Date(b.date) - new Date(a.date));
          return `
            <div class="detail-danger-alert">
              <h3>このスポットに関する危険情報</h3>
              ${related.map(d => `
                <div class="detail-danger-item">
                  <span class="danger-card-type">${d.type}</span>
                  <span class="detail-danger-date">${d.date}</span>
                  <p>${d.description}</p>
                </div>
              `).join('')}
            </div>
            <a href="danger.html" class="detail-danger-more">危険情報の一覧を見る</a>
          `;
        })()}
      </div>
    `;
    // Gallery controls
    if (images.length > 1) {
      let currentIndex = 0;
      const mainImg = document.getElementById('galleryMainImg');
      const thumbs = container.querySelectorAll('.spot-gallery-thumb');
      const prevBtn = document.getElementById('galleryPrev');
      const nextBtn = document.getElementById('galleryNext');

      function showImage(index) {
        currentIndex = index;
        mainImg.src = images[index];
        thumbs.forEach((t, i) => t.classList.toggle('active', i === index));
      }

      prevBtn.addEventListener('click', () => showImage((currentIndex - 1 + images.length) % images.length));
      nextBtn.addEventListener('click', () => showImage((currentIndex + 1) % images.length));
      thumbs.forEach(t => t.addEventListener('click', () => showImage(Number(t.dataset.index))));
    }

    // Favorite button
    const favBtn = document.getElementById('detailFavBtn');
    favBtn.addEventListener('click', () => {
      const isNow = toggleFavorite(spot.id);
      favBtn.textContent = `♥ ${isNow ? 'お気に入り済み' : 'お気に入りに追加'}`;
      favBtn.classList.toggle('active', isNow);
    });

    // Nearby spots
    const nearby = spots
      .filter(s => s.id !== spot.id)
      .map(s => ({ ...s, _distance: calcDistance(spot.lat, spot.lng, s.lat, s.lng) }))
      .sort((a, b) => a._distance - b._distance)
      .slice(0, 3);

    if (nearby.length > 0) {
      const nearbyEl = document.createElement('div');
      nearbyEl.className = 'nearby-spots';
      nearbyEl.innerHTML = `
        <h3>近くのスポット</h3>
        ${nearby.map(s => `
          <a href="spot.html?id=${s.id}" class="nearby-spot-card">
            <span class="nearby-spot-name">${s.name}</span>
            <span class="nearby-spot-dist">${formatDistance(s._distance)}</span>
          </a>
        `).join('')}
      `;
      container.querySelector('.spot-detail').appendChild(nearbyEl);
    }

  } catch (e) {
    container.innerHTML = '<div class="empty-state"><p>データの読み込みに失敗しました</p></div>';
  }
})();
