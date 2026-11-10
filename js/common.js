// ===== Google Analytics =====
(function() {
  const GA_ID = 'G-NPGCWSCZGB';
  const s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', GA_ID);
})();

// ===== HTML escape helper =====
// データ（spots.json / dangers.json 等）を innerHTML に挿入する箇所で使用しXSSを防ぐ。
function escapeHtml(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

// OGP/Twitterタグは各HTMLの <head> に静的記述済みのため、JSでの動的注入は廃止した。
// （旧実装は旧GitHub Pagesドメインの og:image を全ページに二重出力していた）

// ===== アフィリエイトリンクのクリック計測 =====
// スポット詳細（js/spot.js が動的生成）とブログ記事（静的HTML）の両方を1か所で見る。
// 個別バインドだと二重計測や付け忘れが起きるため document への委譲にまとめている。
// ★計測はここだけで行うこと。他のファイルで addEventListener しないこと★
document.addEventListener('click', function (e) {
  const btn = e.target && e.target.closest ? e.target.closest('.affiliate-btn[data-aff]') : null;
  if (!btn || typeof window.gtag !== 'function') return;
  window.gtag('event', 'affiliate_click', {
    network: btn.dataset.aff,
    prefecture: btn.dataset.affPref || 'unknown',
    page: btn.dataset.affPage || 'unknown',
  });
});

// ===== Common: Header & Footer Injection =====

// ---- 犬のサイズ（2026-09-21）----
// dogSize.{small,medium,large} は「そのサイズの犬がそのスポットの目的を果たせるか」。
// false のものだけ「入れない」。項目が無ければ入れる扱い（記載が無ければ両方trueの決まり）。
// ドッグランだけの制限は dogRun.maxSize（small|medium|large）に分けて持つ。
// 同じ判定が generate_spot_pages.py にもある。片方だけ直さないこと。
function dogSizeAllows(spot, size) {
  const ds = spot.dogSize || {};
  return ds[size] !== false;
}
function dogRunSizeAllows(spot, size) {
  const dr = spot.dogRun || {};
  if (!dr.available || !dr.maxSize) return true;
  const order = { small: 1, medium: 2, large: 3 };
  return (order[size] || 3) <= (order[dr.maxSize] || 3);
}
function dogSizeWarnings(spot) {
  const out = [];
  // すべて false ＝ 犬が入れない施設。掲載ルール上は載せないが、データに入ってしまった時に
  // 「小型犬のみ入場可」と出してはいけない（2026-09-28 小目津公園で本番に出た）。generate_spot_pages.py と揃える
  if (!dogSizeAllows(spot, 'small') && !dogSizeAllows(spot, 'medium') && !dogSizeAllows(spot, 'large')) {
    out.push('犬は入れません（全サイズ不可）');
    return out;
  }
  if (!dogSizeAllows(spot, 'medium')) out.push('小型犬のみ入場可（中型犬・大型犬は不可）');
  else if (!dogSizeAllows(spot, 'large')) out.push('中型犬まで入場可（大型犬は不可）');
  const dr = spot.dogRun || {};
  const max = dr.available ? dr.maxSize : null;
  if (max === 'small') out.push('ドッグランは小型犬のみ（施設自体は全サイズ可）');
  else if (max === 'medium') out.push('ドッグランは中型犬まで（大型犬は不可）');
  return out;
}

function getBasePath() {
  // サブディレクトリ（blog/, spots/, themes/）内にいる場合は親ディレクトリを基準にする
  const path = window.location.pathname;
  if (path.includes('/blog/') || path.includes('/spots/') || path.includes('/themes/')) return '../';
  return '';
}

// サブディレクトリ内からアクセスする場合、SITE_NAVのhrefを調整する
function resolveNavHref(href, base) {
  if (base === '../') {
    const path = window.location.pathname;
    // blog内からは「ブログ一覧」リンクが同じblog内なのでblog/プレフィックスを外す
    if (path.includes('/blog/') && href.startsWith('blog/')) {
      return href.replace('blog/', '');
    }
    // spots内からも同様
    if (path.includes('/spots/') && href.startsWith('spots/')) {
      return href.replace('spots/', '');
    }
    // themes内からも同様（まとめ一覧リンクは同じthemes内なのでthemes/プレフィックスを外す）
    if (path.includes('/themes/') && href.startsWith('themes/')) {
      return href.replace('themes/', '');
    }
  }
  return base + href;
}

// Site navigation definition (single source of truth)
// ヘッダーは主要ページのみ。トップ（ロゴから遷移）・テーマ別・危険情報は
// トップページ上部に導線を置いたため footerOnly でフッターのみ掲載（内部リンクは維持）。
const SITE_NAV = [
  { href: 'index.html', label: 'トップ', id: 'home', footerOnly: true },
  { href: 'themes/index.html', label: 'テーマ別で探す', id: 'themes', footerOnly: true },
  { href: 'danger.html', label: '危険情報', id: 'danger', footerOnly: true },
  { href: 'favorites.html', label: 'お気に入り', id: 'favorites' },
  { href: 'blog/index.html', label: 'ブログ', id: 'blog' },
  { href: 'about.html', label: 'このサイトについて', id: 'about' },
  { href: 'editorial.html', label: '掲載情報について', id: 'editorial', footerOnly: true },
  { href: 'privacy.html', label: 'プライバシーポリシー', id: 'privacy', footerOnly: true },
  { href: 'contact.html', label: 'お問い合わせ', id: 'contact' },
];

function renderHeader(activePage) {
  const base = getBasePath();
  const headerNav = SITE_NAV.filter(n => !n.footerOnly);

  const header = document.createElement('header');
  header.className = 'site-header';
  header.innerHTML = `
    <div class="header-inner">
      <a href="${base}index.html" class="site-logo">
        <img src="${base}images/logo-chihuahua.png" alt="" class="logo-icon">
        <span>わんさかんさい</span>
      </a>
      <nav>
        <ul class="nav-menu">
          ${headerNav.map(n => `<li><a href="${resolveNavHref(n.href, base)}" class="${activePage === n.id ? 'active' : ''}">${n.label}</a></li>`).join('')}
        </ul>
      </nav>
      <button class="hamburger" aria-label="メニューを開く" aria-expanded="false">${MENU_ICON_OPEN}</button>
    </div>
  `;

  document.body.prepend(header);

  // 本文へスキップ（キーボード操作のアクセシビリティ）
  const mainEl = document.querySelector('.main-content');
  if (mainEl && !mainEl.id) mainEl.id = 'main';
  if (mainEl && !document.querySelector('.skip-link')) {
    const skip = document.createElement('a');
    skip.href = '#main';
    skip.className = 'skip-link';
    skip.textContent = '本文へスキップ';
    document.body.prepend(skip);
  }

  // Hamburger toggle
  const hamburger = header.querySelector('.hamburger');
  const menu = header.querySelector('.nav-menu');
  hamburger.addEventListener('click', () => {
    menu.classList.toggle('open');
    const isOpen = menu.classList.contains('open');
    hamburger.innerHTML = isOpen ? MENU_ICON_CLOSE : MENU_ICON_OPEN;
    hamburger.setAttribute('aria-expanded', isOpen);
    hamburger.setAttribute('aria-label', isOpen ? 'メニューを閉じる' : 'メニューを開く');
  });
}

function renderFooter() {
  const base = getBasePath();
  // ★生HTMLに静的フッターがあればそれを使う（新規作成しない）★
  // フッターをJSでしか描いていなかったため、about/contact/privacy/blogへの
  // 内部リンクがレンダリング前HTMLに1本も残らず、Googleが一度もクロールしない
  // 状態になっていた（2026-09-02にSearch Consoleで確認）。
  // 各ページの </body> 直前に同じ内容の静的フッターを置き、ここでは中身を描き直す。
  const existing = document.querySelector('footer.site-footer');
  const footer = existing || document.createElement('footer');
  footer.className = 'site-footer';
  footer.innerHTML = `
    <div class="footer-nav">
      ${SITE_NAV.map(n => `<a href="${resolveNavHref(n.href, base)}">${n.label}</a>`).join('')}
    </div>
    <div class="footer-social">
      <a href="https://x.com/wansakansai" target="_blank" rel="noopener noreferrer" aria-label="Xでフォロー" class="social-x">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
        </svg>
        <span>@wansakansai</span>
      </a>
    </div>
    <p class="footer-affiliate-note">当サイトはアフィリエイト広告（楽天・じゃらんnet・Amazonなど）を利用しています。</p>
    <p>&copy; 2026 わんさかんさい All rights reserved.</p>
  `;
  if (!existing) document.body.appendChild(footer);
}

// Distance calculation (Haversine formula)
function calcDistance(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLng / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function formatDistance(km) {
  if (km < 1) return `${Math.round(km * 1000)}m`;
  return `${km.toFixed(1)}km`;
}

// Load JSON
async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}`);
  return res.json();
}

// ===== Favorites (localStorage) =====
function getFavorites() {
  try {
    return new Set(JSON.parse(localStorage.getItem('wansakan_favorites') || '[]'));
  } catch {
    return new Set();
  }
}

function toggleFavorite(spotId) {
  const favs = getFavorites();
  if (favs.has(spotId)) {
    favs.delete(spotId);
  } else {
    favs.add(spotId);
  }
  localStorage.setItem('wansakan_favorites', JSON.stringify([...favs]));
  return favs.has(spotId);
}

function isFavorite(spotId) {
  return getFavorites().has(spotId);
}

// Spot-Danger matching: 危険情報の本文に、スポットの名前・別名が出てくるか
// ★2026-10-06に「長い名前を優先」へ変更★ 単純な部分一致だと、京丹後の「かぶとやまこうえん」と
// 書かれた危険情報に、西宮の甲山森林公園（別名「かぶとやま」）まで結び付いた（別名の包含は全体で25組）。
// 別のスポットのもっと長い名前の一部としてしか出てこない名前は、一致に数えない。
function spotsMatchingText(allSpots, text) {
  const hits = allSpots
    .map(s => ({ s, names: [s.name, ...(s.aliases || [])].filter(n => n && text.includes(n)) }))
    .filter(h => h.names.length);
  return hits
    .filter(h => h.names.some(n => !hits.some(o => o !== h && o.names.some(m => m.length > n.length && m.includes(n)))))
    .map(h => h.s);
}

function spotNameMatchesText(spot, text, allSpots) {
  if (!allSpots) return [spot.name, ...(spot.aliases || [])].some(n => n && text.includes(n));
  return spotsMatchingText(allSpots, text).some(s => s.id === spot.id);
}

/* ===== 一覧1件の作り（2026-11 デザイン刷新「行き先帳」） =====
   名前 → 府県・市区町村（と距離）→ 駐車場・入場・ドッグランを同じ位置に → 注意と特徴 → 訪問済なら判子と訪問メモ。
   リンクは名前に付け、行全体を押せるようにする（::after）。ハートはリンクの外に置く（リンクの中にボタンを入れない）。
   generate_theme_pages.py の card_html も同じ形を書くので、片方だけ直さないこと。 */
const MENU_ICON_OPEN = '<svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M3 6h16M3 11h16M3 16h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
const MENU_ICON_CLOSE = '<svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M5 5l12 12M17 5L5 17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
const HEART_ICON = '<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-9.2-9A5 5 0 0 1 12 6.2 5 5 0 0 1 21.2 11C19 15.6 12 20 12 20z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>';

const SPOT_PREF_RE = /^(北海道|東京都|京都府|大阪府|.+?県)/;

// 住所から「大阪・堺市西区」の形を作る（府県は府・県を外す。市は政令市なら区まで、郡なら町村まで）
function spotPlace(address) {
  const a = address || '';
  const pm = a.match(SPOT_PREF_RE);
  const pref = pm ? pm[1].replace(/[府県]$/, '') : '';
  const rest = pm ? a.slice(pm[1].length) : a;
  let city = '';
  const m = rest.match(/^(.+?[市郡])(.+?[区町村])?/);
  if (m) {
    city = m[1];
    if (m[2] && (m[1].endsWith('郡') || /区$/.test(m[2]))) city += m[2];
  } else {
    const m2 = rest.match(/^(.+?[町村])/);
    city = m2 ? m2[1] : '';
  }
  return pref && city ? pref + '・' + city : (pref || city);
}

function spotRowHTML(s, opts) {
  const o = opts || {};
  const base = o.base || '';
  const has = t => (s.tags || []).includes(t);
  const parking = s.parking && s.parking.available ? (s.parking.free ? '無料' : '有料') : 'なし';
  const admission = s.admission && s.admission.free ? '無料' : '有料';
  const dr = s.dogRun || {};
  const dogrun = dr.available ? (dr.separated ? 'あり（大小別）' : 'あり') : 'なし';
  const warns = [];
  if (!dogSizeAllows(s, 'medium')) warns.push('小型犬のみ');
  else if (!dogSizeAllows(s, 'large')) warns.push('中型犬まで');
  if (dr.available && dr.maxSize === 'small') warns.push('ランは小型犬のみ');
  else if (dr.available && dr.maxSize === 'medium') warns.push('ランは中型犬まで');
  if (has('stay-only')) warns.push('宿泊専用');
  const feats = [];
  if (has('sakura')) feats.push('桜');
  if (has('koyo')) feats.push('紅葉');
  if (has('water')) feats.push('水遊び');
  if (has('rain')) feats.push('雨でもOK');
  if (has('stay-ok')) feats.push('宿泊可');
  const more = warns.length || feats.length
    ? `<p class="row-more">${warns.map(w => `<span class="row-warn">${w}</span>`).join('')}${feats.map(f => `<span class="row-feat">${f}</span>`).join('')}</p>` : '';
  const dist = o.distance != null ? `<span class="row-dist">${formatDistance(o.distance)}</span>` : '';
  const fav = o.fav === false ? '' :
    `<button type="button" class="fav-btn${isFavorite(s.id) ? ' active' : ''}" data-id="${escapeHtml(s.id)}" aria-pressed="${isFavorite(s.id)}" aria-label="${escapeHtml(s.name)}をお気に入りに入れる">${HEART_ICON}</button>`;
  const v = Array.isArray(s.visit) ? s.visit[0] : s.visit;
  const memo = v && v.note ? `<span class="row-memo">${escapeHtml(v.note)}</span>` : '';
  const visited = s.visited
    ? `<p class="row-visit"><img src="${base}images/stamp-visited.png" alt="" class="row-stamp" width="34" height="34">運営者が訪問${memo}</p>` : '';
  const excerpt = o.excerpt ? `<p class="row-excerpt">${escapeHtml(o.excerpt)}</p>` : '';
  return `<article class="spot-row${s.visited ? ' is-visited' : ''}${has('stay-only') ? ' is-stay' : ''}">
  <div class="row-head"><h2 class="row-name"><a href="${base}spots/${encodeURIComponent(s.id)}.html" class="row-link">${escapeHtml(s.name)}</a></h2>${fav}</div>
  <p class="row-where">${escapeHtml(spotPlace(s.address))}${dist}</p>
  <p class="row-facts">駐車場 <b>${parking}</b>　入場 <b>${admission}</b>　ドッグラン <b>${dogrun}</b></p>
  ${more}${excerpt}${visited}
</article>`;
}

// ===== 戻るリンク（スポット詳細の左上）=====
// 一覧（トップ・テーマ別・お気に入り・府県別一覧）から同じタブで来た時は、履歴をさかのぼって一覧へ戻す。
// 絞り込み・並び・見ていた位置がそのまま残るため。詳細から「近くのスポット」で詳細へ移っていても、最初の一覧まで戻す。
// 何件さかのぼれば一覧かは、この詳細を初めて開いた時に決めて、この履歴の1件に持たせる（history.state）。
// 一覧から来たと確かめられない時（検索・X・ブックマーク・新しいタブ）は、リンクどおりトップへ進む。
// 2026-11-11 作り直し: 前の作りは「前のページが一覧か」を毎回 referrer で見ていたので、新しいタブで開いた後に
// 戻れなくなる・詳細から詳細へ移ると一覧の状態を失う、という抜けがあった（Codex の見直しで分かった）。
(function () {
  const back = document.querySelector('a.back-link');
  if (!back) return;
  const KEY = 'wskBack';          // この詳細の履歴に持たせる「何件さかのぼれば一覧か」（0＝リンクどおり）
  const HOP = 'wsk_spot_hop';     // 詳細から詳細へ移る時の受け渡し（このタブの中だけ）
  const here = () => location.href.split('#')[0];
  const isList = (u) => u.origin === location.origin &&
    (/\/(index\.html)?$/.test(u.pathname) || /\/themes\/[^/]*$/.test(u.pathname) || /\/favorites\.html$/.test(u.pathname));
  let depth = 0;
  try {
    const st = history.state || {};
    if (typeof st[KEY] === 'number') {
      depth = st[KEY];
    } else {
      let ref = null;
      try { ref = new URL(document.referrer); } catch (_) { ref = null; }
      if (ref && history.length > 1) {
        if (isList(ref)) {
          depth = 1;
        } else {
          let hop = null;
          try { hop = JSON.parse(sessionStorage.getItem(HOP) || 'null'); } catch (_) { hop = null; }
          if (hop && hop.href === document.referrer && hop.depth > 0 && hop.depth < 50) depth = hop.depth + 1;
        }
      }
      history.replaceState(Object.assign({}, st, { [KEY]: depth }), '');
    }
  } catch (_) {
    depth = 0;
  }
  // ページの中のリンク（「本文へスキップ」など # で始まるもの）は履歴を1件増やす。
  // 増えた履歴には印が無いので、ここで「一覧までの件数」を1つ足して持たせる。履歴を戻って元の印のある所へ来たら、その値に戻す
  window.addEventListener('hashchange', () => {
    try {
      const st = history.state || {};
      if (typeof st[KEY] === 'number') {
        depth = st[KEY];
      } else {
        depth = depth > 0 ? depth + 1 : 0;
        history.replaceState(Object.assign({}, st, { [KEY]: depth }), '');
      }
    } catch (_) { /* 覚えられなければそのまま */ }
  });
  const remember = () => {
    try { sessionStorage.setItem(HOP, JSON.stringify({ href: here(), depth })); } catch (_) { /* 覚えられなければリンクどおり */ }
  };
  window.addEventListener('pagehide', remember);
  document.addEventListener('click', (e) => { if (e.target.closest && e.target.closest('a[href]')) remember(); });
  back.addEventListener('click', (e) => {
    if (!depth || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    history.go(-depth);
  });
})();
