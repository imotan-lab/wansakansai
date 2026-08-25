"""
spots.jsonからsitemap.xmlを自動生成するスクリプト。
スポット追加後に実行してコミット・プッシュすること。
ブログは blog/index.html にカードとして掲載済み（=公開済み）の記事のみ自動収録する。
"""
import json
import re
from datetime import date
from pathlib import Path

BASE_URL = "https://wansakansai.com"
TODAY = date.today().isoformat()
PROJECT_DIR = Path(__file__).resolve().parent

with open(PROJECT_DIR / 'data' / 'spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

static_pages = [
    {"loc": f"{BASE_URL}/",             "changefreq": "weekly",  "priority": "1.0"},
    {"loc": f"{BASE_URL}/danger.html",  "changefreq": "weekly",  "priority": "0.8"},
    {"loc": f"{BASE_URL}/contact.html", "changefreq": "monthly", "priority": "0.5"},
    {"loc": f"{BASE_URL}/privacy.html", "changefreq": "yearly",  "priority": "0.3"},
    {"loc": f"{BASE_URL}/about.html",   "changefreq": "monthly", "priority": "0.5"},
    # 全スポットの静的一覧（generate_spot_pages.py が生成）。全スポットページへの
    # 静的リンクを持つクロール経路のハブなので優先度を高めに置く
    {"loc": f"{BASE_URL}/spots/index.html", "changefreq": "weekly", "priority": "0.9"},
]

# テーマ別まとめページ（js/themes-data.js の THEMES と対応）
theme_slugs = ["dogrun-free", "dogrun", "sakura", "koyo", "water", "rain", "free"]
static_pages.append({"loc": f"{BASE_URL}/themes/index.html", "changefreq": "weekly", "priority": "0.7"})
for slug in theme_slugs:
    static_pages.append({"loc": f"{BASE_URL}/themes/{slug}.html", "changefreq": "weekly", "priority": "0.6"})

# ブログ: blog/index.html とそこからリンクされている公開記事のみ収録
# （未リンク=下書き状態の記事は本番導線が無いため含めない）
blog_count = 0
blog_index = PROJECT_DIR / 'blog' / 'index.html'
if blog_index.exists():
    static_pages.append({"loc": f"{BASE_URL}/blog/index.html", "changefreq": "weekly", "priority": "0.6"})
    html = blog_index.read_text(encoding='utf-8')
    article_slugs = sorted({m for m in re.findall(r'href="([a-z0-9\-]+\.html)"', html) if m != 'index.html'})
    for slug in article_slugs:
        static_pages.append({"loc": f"{BASE_URL}/blog/{slug}", "changefreq": "monthly", "priority": "0.6"})
    blog_count = 1 + len(article_slugs)

lines = ['<?xml version="1.0" encoding="UTF-8"?>']
lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

for page in static_pages:
    lines.append(f'  <url>')
    lines.append(f'    <loc>{page["loc"]}</loc>')
    lines.append(f'    <lastmod>{TODAY}</lastmod>')
    lines.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
    lines.append(f'    <priority>{page["priority"]}</priority>')
    lines.append(f'  </url>')

for spot in spots:
    loc = f"{BASE_URL}/spots/{spot['id']}.html"
    lines.append(f'  <url>')
    lines.append(f'    <loc>{loc}</loc>')
    lines.append(f'    <lastmod>{TODAY}</lastmod>')
    lines.append(f'    <changefreq>monthly</changefreq>')
    lines.append(f'    <priority>0.7</priority>')
    lines.append(f'  </url>')

lines.append('</urlset>')

with open(PROJECT_DIR / 'sitemap.xml', 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')

print(f"sitemap.xml 生成完了: 静的{len(static_pages)}件（うちブログ{blog_count}件）+ スポット{len(spots)}件 = 計{len(static_pages)+len(spots)}件")
