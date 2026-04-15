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

// ===== OGP Meta Tags =====
(function() {
  const BASE_URL = 'https://imotan-lab.github.io/wansakansai/';
  const siteName = 'わんさかんさい';
  const ogImage = BASE_URL + 'images/ogp.png';
  const title = document.title;
  const desc = document.querySelector('meta[name="description"]');
  const description = desc ? desc.content : '';
  const url = window.location.href;

  const tags = {
    'og:type': 'website',
    'og:site_name': siteName,
    'og:title': title,
    'og:description': description,
    'og:url': url,
    'og:image': ogImage,
    'og:locale': 'ja_JP',
    'twitter:card': 'summary',
    'twitter:title': title,
    'twitter:description': description,
    'twitter:image': ogImage,
  };

  Object.entries(tags).forEach(([key, value]) => {
    const meta = document.createElement('meta');
    meta.setAttribute(key.startsWith('twitter:') ? 'name' : 'property', key);
    meta.content = value;
    document.head.appendChild(meta);
  });
})();

// ===== Common: Header & Footer Injection =====

function getBasePath() {
  // サブディレクトリ（blog/等）内にいる場合は親ディレクトリを基準にする
  const path = window.location.pathname;
  if (path.includes('/blog/')) return '../';
  return '';
}

// ブログ内からアクセスする場合、SITE_NAVのhrefを調整する
function resolveNavHref(href, base) {
  // blog/index.html のようなサブディレクトリへのリンクは、blog内からは index.html になる
  if (base === '../' && href.startsWith('blog/')) {
    return href.replace('blog/', '');
  }
  return base + href;
}

// Site navigation definition (single source of truth)
const SITE_NAV = [
  { href: 'index.html', label: 'スポット検索', id: 'home' },
  { href: 'favorites.html', label: 'お気に入り', id: 'favorites' },
  { href: 'danger.html', label: '危険情報', id: 'danger' },
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
  const footer = document.createElement('footer');
  footer.className = 'site-footer';
  footer.innerHTML = `
    <div class="footer-nav">
      ${SITE_NAV.map(n => `<a href="${resolveNavHref(n.href, base)}">${n.label}</a>`).join('')}
    </div>
    <p>&copy; 2026 わんさかんさい All rights reserved.</p>
  `;
  document.body.appendChild(footer);
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
