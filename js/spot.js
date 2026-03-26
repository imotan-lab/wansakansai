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
    const spots = await loadJSON('data/spots.json');
    const spot = spots.find(s => s.id === spotId);

    if (!spot) {
      container.innerHTML = '<div class="empty-state"><p>スポットが見つかりませんでした</p></div>';
      return;
    }

    // Update page title
    document.title = `${spot.name} - 犬阪んさい`;
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) metaDesc.content = `${spot.name}（${spot.address}）の犬連れお出かけ情報。駐車場・トイレ・ドッグラン情報など。`;

    // Build info rows
    const visitedBadge = spot.visited ? '<span class="tag tag-visited" style="margin-left:8px;font-size:0.8rem;">実訪問済み</span>' : '';

    const dogSizeText = [];
    if (spot.dogSize.small) dogSizeText.push('小型犬OK');
    if (spot.dogSize.large) dogSizeText.push('大型犬OK');

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
    }

    let admissionText = spot.admission.free ? '無料' : `有料（${spot.admission.fee || ''})`;

    const mapQuery = encodeURIComponent(spot.name + ' ' + spot.address);

    container.innerHTML = `
      <div class="spot-detail">
        <div class="spot-detail-header">
          <h1>${spot.name}${visitedBadge}</h1>
          <p class="address">${spot.address}</p>
        </div>
        <div class="spot-detail-body">
          <iframe
            class="spot-map"
            src="https://maps.google.co.jp/maps?q=${mapQuery}&output=embed&z=15"
            allowfullscreen
            loading="lazy"
            referrerpolicy="no-referrer-when-downgrade"
          ></iframe>

          <table class="detail-table">
            <tr><th>犬のサイズ</th><td>${dogSizeText.join('　') || '情報なし'}</td></tr>
            <tr><th>駐車場</th><td>${parkingText}</td></tr>
            <tr><th>トイレ</th><td>${toiletText}</td></tr>
            <tr><th>ドッグラン</th><td>${dogRunText}</td></tr>
            <tr><th>入場料</th><td>${admissionText}</td></tr>
          </table>

          ${spot.remarks ? `
            <div class="detail-remarks">
              <h3>備考・犬連れでのポイント</h3>
              <p>${spot.remarks}</p>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  } catch (e) {
    container.innerHTML = '<div class="empty-state"><p>データの読み込みに失敗しました</p></div>';
  }
})();
