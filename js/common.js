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

// ===== Common: Header & Footer Injection =====

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
      <button class="hamburger" aria-label="メニューを開く">☰</button>
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
    hamburger.textContent = menu.classList.contains('open') ? '✕' : '☰';
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

// Spot-Danger matching: check if spot name or any alias appears in text
function spotNameMatchesText(spot, text) {
  const names = [spot.name, ...(spot.aliases || [])];
  return names.some(n => text.includes(n));
}
