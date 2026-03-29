// ===== Common: Header & Footer Injection =====

function getBasePath() {
  return '';
}

function renderHeader(activePage) {
  const base = getBasePath();
  const nav = [
    { href: `${base}index.html`, label: 'スポット検索', id: 'home' },
    { href: `${base}danger.html`, label: '危険情報', id: 'danger' },
    { href: `${base}contact.html`, label: 'お問い合わせ', id: 'contact' },
  ];

  const header = document.createElement('header');
  header.className = 'site-header';
  header.innerHTML = `
    <div class="header-inner">
      <a href="${base}index.html" class="site-logo">
        <img src="${base}images/logo-chihuahua.png" alt="" class="logo-icon">
        <span>
          犬阪んさい
          <span class="logo-sub">わんさかんさい</span>
        </span>
      </a>
      <nav>
        <ul class="nav-menu">
          ${nav.map(n => `<li><a href="${n.href}" class="${activePage === n.id ? 'active' : ''}">${n.label}</a></li>`).join('')}
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
      <a href="${base}index.html">スポット検索</a>
      <a href="${base}danger.html">危険情報</a>
      <a href="${base}privacy.html">プライバシーポリシー</a>
      <a href="${base}contact.html">お問い合わせ</a>
    </div>
    <p>&copy; 2026 犬阪んさい All rights reserved.</p>
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

// Spot-Danger matching: check if a spot name appears in text
// Also tries shorter name without common prefixes like "道の駅"
function spotNameMatchesText(spotName, text) {
  if (text.includes(spotName)) return true;
  const prefixes = ['道の駅 ', '道の駅　', '大阪府民の森 ', '大阪府民の森　'];
  for (const p of prefixes) {
    if (spotName.startsWith(p)) {
      const short = spotName.slice(p.length);
      if (short.length >= 3 && text.includes(short)) return true;
    }
  }
  // Extract parenthesized parts from spot name as aliases
  const paren = spotName.match(/[（(](.+?)[）)]/);
  if (paren && paren[1].length >= 3 && text.includes(paren[1])) return true;
  // Reverse check: split text by separators and see if any segment is part of the spot name
  // e.g. "くろまろの郷" in text matches "奥河内くろまろの郷" in spot name
  const segments = text.split(/[・、，,（）()／/\s]+/);
  for (const seg of segments) {
    if (seg.length >= 4 && spotName.includes(seg)) return true;
  }
  return false;
}
