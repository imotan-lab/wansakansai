// ===== テーマ定義（まとめページ共通レジストリ） =====
// まとめ一覧（themes/index.html）と各テーマページ（theme-page.js）が共有する。
// 1テーマ = { slug, navTitle(一覧カードの見出し), lead(一覧カードの一言), filter(該当判定) }
// フィルタはここが唯一の定義。各ページ・一覧で重複定義しないこと。
const THEMES = [
  {
    slug: 'dogrun-free',
    navTitle: '無料ドッグラン',
    lead: '入場・利用とも無料でドッグランが使える公園。',
    filter: (s) => s.dogRun && s.dogRun.available && s.dogRun.free,
  },
  {
    slug: 'dogrun',
    navTitle: 'ドッグランがある公園',
    lead: '無料・有料を問わず、ドッグランを備えた公園すべて。',
    filter: (s) => s.dogRun && s.dogRun.available,
  },
  {
    slug: 'sakura',
    navTitle: '桜・お花見',
    lead: '愛犬と桜を楽しめる、関西のお花見スポット。',
    filter: (s) => (s.tags || []).includes('sakura'),
  },
  {
    slug: 'koyo',
    navTitle: '紅葉',
    lead: '秋に犬と訪れたい、関西の紅葉スポット。',
    filter: (s) => (s.tags || []).includes('koyo'),
  },
  {
    slug: 'water',
    navTitle: '水遊び・川遊び',
    lead: '夏に愛犬と水辺で遊べる川・海沿いのスポット。',
    filter: (s) => (s.tags || []).includes('water'),
  },
  {
    slug: 'rain',
    navTitle: '雨でもOK',
    lead: '屋根付き・屋内で、雨の日も楽しめるスポット。',
    filter: (s) => (s.tags || []).includes('rain'),
  },
  {
    slug: 'free',
    navTitle: '完全無料で行ける',
    lead: '入場料も駐車場も無料。お財布にやさしいお出かけ先。',
    filter: (s) => s.admission && s.admission.free && s.parking && s.parking.available && s.parking.free,
  },
];

window.THEMES = THEMES;
function getThemeBySlug(slug) {
  return (window.THEMES || []).find((t) => t.slug === slug) || null;
}
window.getThemeBySlug = getThemeBySlug;
