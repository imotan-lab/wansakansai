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

// Spot-Danger matching: check if spot name or any alias appears in text
function spotNameMatchesText(spot, text) {
  const names = [spot.name, ...(spot.aliases || [])];
  return names.some(n => text.includes(n));
}


/* ===== スクロールで浮き上がる（2026-09-15導入） =====
   今電のサイト（imaden-inc.com）と同じ考え方で、下から少し上がりながら現れる。
   ・対象は下の SELECTOR。JSが後から描くカードも MutationObserver で拾う
   ・一度現れたら監視をやめる（スクロールのたびに明滅しない）
   ・端末が「動きを減らす」設定なら何もしない
   ・IntersectionObserver が無い古い環境でも、何も起きないだけで表示は壊れない */
(function revealInit() {
  /* 対象は「スクロールした先に出てくるもの」だけ。
     ページの主役（スポット詳細の本文など）は入れない。動きが出ない環境で
     本文が見えなくなるため。 */
  var SELECTOR = [
    '.spot-card',          // トップと一覧のカード
    '.danger-card',        // 危険情報
    '.theme-card',         // テーマ別のカード
    '.theme-spot',
    '.blog-card',          // ブログ一覧
    '.nearby-spots'        // スポット詳細の下の「近くのスポット」
  ].join(',');

  if (!('IntersectionObserver' in window)) return;
  try {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  } catch (e) { /* matchMedia が無い環境では動きを入れる */ }

  document.documentElement.classList.add('has-reveal');

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      e.target.classList.add('is-in');
      io.unobserve(e.target);
    });
  }, { rootMargin: '0px 0px -6% 0px', threshold: 0.06 });

  function mark(el, i) {
    if (el.classList.contains('reveal')) return;
    el.classList.add('reveal');
    // 続けて並ぶものは少しずつ遅らせる（最大8つぶんまで）
    if (i) el.style.transitionDelay = (Math.min(i, 8) * 55) + 'ms';
    io.observe(el);
  }

  function scan(root) {
    var list = (root || document).querySelectorAll(SELECTOR);
    for (var i = 0; i < list.length; i++) mark(list[i], i);
    // 描いた直後に画面へ入っているものは、すぐ出す（薄いまま残さない）
    window.requestAnimationFrame(function () { sweep(); });
  }

  scan(document);

  // 一覧は絞り込みのたびに描き直されるので、増えた分を拾う
  var mo = new MutationObserver(function (records) {
    for (var i = 0; i < records.length; i++) {
      var added = records[i].addedNodes;
      for (var j = 0; j < added.length; j++) {
        var n = added[j];
        if (n.nodeType !== 1) continue;
        if (n.matches && n.matches(SELECTOR)) mark(n, j);
        if (n.querySelectorAll) scan(n);
      }
    }
  });
  mo.observe(document.body, { childList: true, subtree: true });

  document.addEventListener('DOMContentLoaded', function () { scan(document); });

  /* スクロールのたびに位置を見て表示する。
     IntersectionObserver が働かない場合でも、内容が薄いまま残らないようにする。 */
  var ticking = false;
  function sweep() {
    ticking = false;
    var h = window.innerHeight || document.documentElement.clientHeight;
    var list = document.querySelectorAll('.reveal:not(.is-in)');
    for (var i = 0; i < list.length; i++) {
      var r = list[i].getBoundingClientRect();
      if (r.top < h * 0.94 && r.bottom > 0) list[i].classList.add('is-in');
    }
  }
  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(sweep);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  onScroll();

  /* 保険: 3秒たってもまだ現れていないもののうち、画面内にあるものは表示する。 */
  window.setTimeout(function () {
    var left = document.querySelectorAll('.reveal:not(.is-in)');
    if (!left.length) return;
    var h = window.innerHeight || document.documentElement.clientHeight;
    for (var i = 0; i < left.length; i++) {
      var r = left[i].getBoundingClientRect();
      if (r.top < h) left[i].classList.add('is-in');
    }
  }, 3000);
})();
