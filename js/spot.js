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

    // Update page title
    document.title = `${spot.name} - 犬阪んさい`;
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) metaDesc.content = `${spot.name}（${spot.address}）の犬連れお出かけ情報。駐車場・トイレ・ドッグラン情報など。`;

    // Build info
    const visitedStamp = spot.visited ? '<img src="images/stamp-visited.png" alt="訪問済み" class="detail-visited-stamp">' : '';

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

    container.className = '';
    container.innerHTML = `
      <div class="spot-detail">
        ${visitedStamp}
        <h1 class="spot-detail-title">${spot.name}</h1>
        <p class="spot-detail-address">${spot.address}</p>

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

        ${spot.remarks ? `
          <div class="detail-remarks">
            <h3>備考・犬連れでのポイント</h3>
            <p>${spot.remarks}</p>
          </div>
        ` : ''}

        <div class="share-buttons">
          <span class="share-label">シェア</span>
          <a href="https://twitter.com/intent/tweet?text=${encodeURIComponent(spot.name + ' - 犬阪んさい')}&url=${encodeURIComponent(window.location.href)}" target="_blank" rel="noopener noreferrer" class="share-btn share-x">X</a>
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
  } catch (e) {
    container.innerHTML = '<div class="empty-state"><p>データの読み込みに失敗しました</p></div>';
  }
})();
