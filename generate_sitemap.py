"""
spots.jsonからsitemap.xmlを自動生成するスクリプト。
スポット追加後に実行してコミット・プッシュすること。
ブログは blog/index.html にカードとして掲載済み（=公開済み）の記事のみ自動収録する。

lastmod（更新日）は「そのページの中身が実際に変わった日」を書く（2026-11-11）。
以前は毎回すべてのページを「今日」にしていたため、Google がこの日付を当てにせず、
どのページを先に見に来るかの手がかりにならなかった（未登録のスポットが100件以上残っていた）。
ページのHTMLから読み込み番号（?v=数字）を除いて指紋を取り、前回と違う時だけ今日の日付にする。
指紋の控えはリポジトリの外（下の LASTMOD_LEDGER）。自動タスクは決まったファイルしか git add しないので、
リポジトリの中に置くと「コミットされていない変更＝前の実行が途中で止まった印」と取り違えられるため。
控えが無くなった時は、今の sitemap.xml に書いてある日付をそのまま引き継ぐ（全部が今日にはならない）。
"""
import hashlib
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

BASE_URL = "https://wansakansai.com"
TODAY = date.today().isoformat()
PROJECT_DIR = Path(__file__).resolve().parent
LASTMOD_LEDGER = Path(r'C:/Users/imao_/Documents/wansakansai/sitemap_lastmod.json')


def page_file(loc):
    """sitemap の URL → リポジトリの中のファイル"""
    rel = loc[len(BASE_URL) + 1:]
    if rel == '' or rel.endswith('/'):
        rel += 'index.html'
    return PROJECT_DIR / rel


def fingerprint(path):
    try:
        html = path.read_text(encoding='utf-8')
    except OSError:
        return ''
    html = re.sub(r'\?v=\d+', '', html)          # 読み込み番号だけの違いは変更に数えない
    html = html.replace('\r\n', '\n')
    return hashlib.sha256(html.encode('utf-8')).hexdigest()[:16]


def previous_dates():
    """今の sitemap.xml に書いてある日付（控えが無い時の引き継ぎ用）"""
    p = PROJECT_DIR / 'sitemap.xml'
    if not p.exists():
        return {}
    xml = p.read_text(encoding='utf-8')
    return dict(re.findall(r'<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', xml))


def load_ledger():
    try:
        with open(LASTMOD_LEDGER, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_ledger(d):
    LASTMOD_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(LASTMOD_LEDGER.parent), suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, LASTMOD_LEDGER)

with open(PROJECT_DIR / 'data' / 'spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

static_pages = [
    {"loc": f"{BASE_URL}/",             "changefreq": "weekly",  "priority": "1.0"},
    {"loc": f"{BASE_URL}/danger.html",  "changefreq": "weekly",  "priority": "0.8"},
    {"loc": f"{BASE_URL}/contact.html", "changefreq": "monthly", "priority": "0.5"},
    {"loc": f"{BASE_URL}/privacy.html", "changefreq": "yearly",  "priority": "0.3"},
    {"loc": f"{BASE_URL}/about.html",   "changefreq": "monthly", "priority": "0.5"},
    {"loc": f"{BASE_URL}/editorial.html", "changefreq": "monthly", "priority": "0.5"},
    # 全スポットの静的一覧（generate_spot_pages.py が生成）。全スポットページへの
    # 静的リンクを持つクロール経路のハブなので優先度を高めに置く
    {"loc": f"{BASE_URL}/spots/index.html", "changefreq": "weekly", "priority": "0.9"},
]

# テーマ別まとめページ（generate_theme_pages.py の THEMES と対応）
theme_slugs = ["dogrun-free", "dogrun", "sakura", "koyo", "water", "rain", "free"]
static_pages.append({"loc": f"{BASE_URL}/themes/index.html", "changefreq": "weekly", "priority": "0.7"})
for slug in theme_slugs:
    static_pages.append({"loc": f"{BASE_URL}/themes/{slug}.html", "changefreq": "weekly", "priority": "0.6"})

# ブログ: blog/index.html とそこからリンクされている公開記事のみ収録
# （未リンク=下書き状態の記事は本番導線が無いため含めない）
blog_count = 0
blog_index = PROJECT_DIR / 'blog' / 'index.html'
if blog_index.exists():
    # ★/blog/index.html ではなく /blog/ を載せること★
    # Googleは2026-09-04時点で /blog/ を登録済みで、index.html は代替ページ扱い。
    # 一度 canonical を index.html 側に合わせて登録済みURLを捨てかけた（9ce2cdc）。
    static_pages.append({"loc": f"{BASE_URL}/blog/", "changefreq": "weekly", "priority": "0.6"})
    html = blog_index.read_text(encoding='utf-8')
    article_slugs = sorted({m for m in re.findall(r'href="([a-z0-9\-]+\.html)"', html) if m != 'index.html'})
    for slug in article_slugs:
        static_pages.append({"loc": f"{BASE_URL}/blog/{slug}", "changefreq": "monthly", "priority": "0.6"})
    blog_count = 1 + len(article_slugs)

ledger = load_ledger()
prev = previous_dates()
first_run = ledger is None
ledger = ledger or {}
changed = []


def lastmod(loc):
    fp = fingerprint(page_file(loc))
    old = ledger.get(loc)
    if old and old.get('fp') == fp:
        return old['date']
    if old is None and first_run and loc in prev:
        d = prev[loc]                  # 控えが無い: 前の sitemap の日付を引き継ぐ
    else:
        d = TODAY                      # 中身が変わった・新しいページ
        changed.append(loc)
    ledger[loc] = {'fp': fp, 'date': d}
    return d


lines = ['<?xml version="1.0" encoding="UTF-8"?>']
lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

for page in static_pages:
    lines.append(f'  <url>')
    lines.append(f'    <loc>{page["loc"]}</loc>')
    lines.append(f'    <lastmod>{lastmod(page["loc"])}</lastmod>')
    lines.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
    lines.append(f'    <priority>{page["priority"]}</priority>')
    lines.append(f'  </url>')

for spot in spots:
    loc = f"{BASE_URL}/spots/{spot['id']}.html"
    lines.append(f'  <url>')
    lines.append(f'    <loc>{loc}</loc>')
    lines.append(f'    <lastmod>{lastmod(loc)}</lastmod>')
    lines.append(f'    <changefreq>monthly</changefreq>')
    lines.append(f'    <priority>0.7</priority>')
    lines.append(f'  </url>')

lines.append('</urlset>')

with open(PROJECT_DIR / 'sitemap.xml', 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')

save_ledger(ledger)
print(f"更新日を今日にしたページ: {len(changed)}件" + (f"（例: {', '.join(c[len(BASE_URL)+1:] for c in changed[:5])}）" if changed else ''))
print(f"sitemap.xml 生成完了: 静的{len(static_pages)}件（うちブログ{blog_count}件）+ スポット{len(spots)}件 = 計{len(static_pages)+len(spots)}件")
