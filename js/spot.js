// ===== Spot Detail Page =====

(async function () {
  renderHeader('home');
  renderFooter();

  const container = document.getElementById('spotDetail');
  // SPOT_ID取得: 静的HTML(spots/{id}.html)では window.WANSAKA_SPOT_ID、
  // 旧URL(spot.html?id=xxx)では URLパラメータ
  const params = new URLSearchParams(window.location.search);
  const spotId = window.WANSAKA_SPOT_ID || params.get('id');

  if (!spotId) {
    container.innerHTML = '<div class="empty-state"><p>スポットが指定されていません</p></div>';
    return;
  }

  try {
    const [spots, dangers] = await Promise.all([
      loadJSON('../data/spots.json').catch(() => loadJSON('data/spots.json')),
      loadJSON('../data/dangers.json').catch(() => loadJSON('data/dangers.json'))
    ]);
    const spot = spots.find(s => s.id === spotId);

    if (!spot) {
      container.innerHTML = '<div class="empty-state"><p>スポットが見つかりませんでした</p></div>';
      return;
    }

    // SEO関連（title/description/canonical/OGP/JSON-LD）は generate_spot_pages.py で
    // 静的HTMLに埋め込み済みのため、JSでの動的更新は不要

    // パス解決は common.js の getBasePath() に統一（/spots/ 配下なら '../'）
    const imgBase = getBasePath();
    const spotLinkBase = imgBase + 'spots/';

    // Build info
    const visitedStamp = spot.visited ? `<img src="${imgBase}images/stamp-visited.png" alt="運営が実際に訪問済み" class="detail-visited-stamp">` : '';

    let parkingText = 'なし';
    if (spot.parking.available) {
      parkingText = spot.parking.free ? 'あり（無料）' : 'あり（有料）';
    }

    let toiletText = 'なし';
    if (spot.toilet.available) {
      // western が null（洋式/和式が未確認）のときは断定せず「あり」とだけ表示する
      if (spot.toilet.western === null || spot.toilet.western === undefined) {
        toiletText = 'あり';
      } else {
        toiletText = spot.toilet.western ? 'あり（洋式）' : 'あり（和式）';
      }
    }

    let dogRunText = 'なし';
    if (spot.dogRun.available) {
      dogRunText = spot.dogRun.free ? 'あり（無料）' : 'あり（有料）';
      if (spot.dogRun.detail) dogRunText += ` / ${escapeHtml(spot.dogRun.detail)}`;
    }

    // 入場自体は無料でも fee に駐車場代・一部有料施設などの補足がある場合は捨てずに表示する。
    // fee が既に「無料」を含む場合はそのまま（「無料（〜は無料（〜））」の二重表記を防ぐ）
    const admissionFee = (spot.admission.fee || '').trim();
    let admissionText;
    if (spot.admission.free) {
      if (!admissionFee) {
        admissionText = '無料';
      } else {
        admissionText = admissionFee.includes('無料')
          ? escapeHtml(admissionFee)
          : `無料（${escapeHtml(admissionFee)}）`;
      }
    } else {
      admissionText = `有料（${escapeHtml(admissionFee)}）`;
    }

    // 公式URLは http(s) のみ許可（javascript: 等のスキーム混入を防ぐ）
    const officialUrlSafe = /^https?:\/\//i.test(spot.officialUrl || '') ? spot.officialUrl : '';

    const mapQuery = encodeURIComponent(spot.name + ' ' + spot.address);

    const isFav = isFavorite(spot.id);

    // Build gallery
    const rawImages = spot.images || (spot.imageUrl ? [spot.imageUrl] : []);
    const images = rawImages.map(img => imgBase + img);
    let galleryHtml = '';
    if (images.length > 0) {
      galleryHtml = `
        <div class="spot-gallery">
          <div class="spot-gallery-main">
            <img src="${images[0]}" alt="${escapeHtml(spot.name)}" class="spot-gallery-img" id="galleryMainImg">
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
          <h1 class="spot-detail-title">${escapeHtml(spot.name)}</h1>
        </div>
        <p class="spot-detail-address">${escapeHtml(spot.address)}</p>
        <button class="detail-fav-btn${isFav ? ' active' : ''}" id="detailFavBtn">
          &#9829; ${isFav ? 'お気に入り済み' : 'お気に入りに追加'}
        </button>

        <iframe
          class="spot-map"
          title="${escapeHtml(spot.name)}の地図"
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
          ${officialUrlSafe ? `
          <div class="detail-info-item">
            <span class="detail-info-label">公式HP</span>
            <span class="detail-info-value"><a href="${escapeHtml(officialUrlSafe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(officialUrlSafe.replace(/^https?:\/\//, '').replace(/\/$/, ''))}</a></span>
          </div>` : ''}
        </div>

        ${(spot.tags || []).includes('small-dog-only') ? `
          <div class="detail-warn">小型犬のみ入場可（大型犬は要確認）</div>
        ` : ''}

        ${spot.remarks ? `
          <div class="detail-remarks">
            <h3>備考・犬連れでのポイント</h3>
            <p>${(() => {
              const sentences = escapeHtml(spot.remarks).split('。').filter(s => s);
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
                  <span class="danger-card-type">${escapeHtml(d.type)}</span>
                  <span class="detail-danger-date">${escapeHtml(d.date)}</span>
                  <p>${escapeHtml(d.description)}</p>
                </div>
              `).join('')}
            </div>
            <a href="${getBasePath()}danger.html" class="detail-danger-more">危険情報の一覧を見る</a>
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
          <a href="${spotLinkBase}${encodeURIComponent(s.id)}.html" class="nearby-spot-card">
            <span class="nearby-spot-name">${escapeHtml(s.name)}</span>
            <span class="nearby-spot-dist">${formatDistance(s._distance)}</span>
          </a>
        `).join('')}
      `;
      container.querySelector('.spot-detail').appendChild(nearbyEl);
    }

    // 楽天 + じゃらん アフィリエイト（ペット可宿）- 最下部に配置
    (() => {
      // スポットの都道府県を判定（app.jsのgetPrefectureと同一ロジック）
      const prefMatch = (spot.address || '').match(/^(北海道|東京都|京都府|大阪府|.+?県)/);
      const prefName = prefMatch ? prefMatch[1] : '';
      // 都道府県 → 楽天トラベルのローマ字エリア（県別ペット可宿ランキングへディープリンク）
      const PREF_ROMAJI = {
        '大阪府': 'osaka', '和歌山県': 'wakayama', '滋賀県': 'shiga',
        '奈良県': 'nara', '兵庫県': 'hyogo', '京都府': 'kyoto',
      };
      const romaji = PREF_ROMAJI[prefName];
      // 県が判定できれば県別ページ、未対応なら全国ペット可トップにフォールバック
      const travelUrl = romaji
        ? `https://travel.rakuten.co.jp/share/batch/rrg_pg/pgenerator/hotel/id235/${romaji}/index.html`
        : 'https://travel.rakuten.co.jp/pet/';
      // 楽天アフィリの「どこでもリンク」形式（既存IDを流用、link_typeはtextのまま＝規約上安全）
      const RAKUTEN_AFFILIATE_ID = '535b3809.5ed3e82b.535b380a.3e77d4ae';
      const rakutenLink = `https://hb.afl.rakuten.co.jp/hgc/${RAKUTEN_AFFILIATE_ID}/?pc=${encodeURIComponent(travelUrl)}&link_type=text`;
      // じゃらんnet（A8.net 経由。ディープリンク可否未確認のため汎用リンクのまま）
      const JALAN_A8MAT = '4B3G6J+9ICAE2+14CS+64JTE';
      const jalanLink = `https://px.a8.net/svt/ejp?a8mat=${JALAN_A8MAT}`;
      const jalanTracker = `https://www13.a8.net/0.gif?a8mat=${JALAN_A8MAT}`;
      // 見出し（県が判定できれば県名入り）
      const headingText = prefName
        ? `${prefName}で愛犬と泊まれる宿を探す`
        : '愛犬と泊まれる宿を探す';

      const affEl = document.createElement('div');
      affEl.className = 'affiliate-stay';
      affEl.innerHTML = `
        <div class="affiliate-stay-head">
          <span class="affiliate-pr-tag">PR</span>
          <span class="affiliate-stay-text">${headingText}</span>
        </div>
        <div class="affiliate-btns">
          <a href="${rakutenLink}" target="_blank" rel="sponsored noopener" class="affiliate-btn affiliate-btn-rakuten" data-aff="rakuten">楽天トラベルで探す</a>
          <a href="${jalanLink}" target="_blank" rel="sponsored nofollow noopener" class="affiliate-btn affiliate-btn-jalan" data-aff="jalan">じゃらんnetで探す</a>
        </div>
        <img border="0" width="1" height="1" src="${jalanTracker}" alt="" style="display:none;">
      `;
      container.querySelector('.spot-detail').appendChild(affEl);

      // GAアウトバウンドクリック計測（common.jsがwindow.gtagを定義済み）
      affEl.querySelectorAll('.affiliate-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          if (typeof window.gtag === 'function') {
            window.gtag('event', 'affiliate_click', {
              network: btn.dataset.aff,
              prefecture: prefName || 'unknown',
              spot_id: spot.id,
            });
          }
        });
      });
    })();

  } catch (e) {
    container.innerHTML = '<div class="empty-state"><p>データの読み込みに失敗しました</p></div>';
  }
})();
