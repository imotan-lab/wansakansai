"""
spots.jsonからsitemap.xmlを自動生成するスクリプト。
スポット追加後に実行してコミット・プッシュすること。
"""
import json
from datetime import date

BASE_URL = "https://wansakansai.com"
TODAY = date.today().isoformat()

with open('data/spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

static_pages = [
    {"loc": f"{BASE_URL}/",             "changefreq": "weekly",  "priority": "1.0"},
    {"loc": f"{BASE_URL}/danger.html",  "changefreq": "weekly",  "priority": "0.8"},
    {"loc": f"{BASE_URL}/contact.html", "changefreq": "monthly", "priority": "0.5"},
    {"loc": f"{BASE_URL}/privacy.html", "changefreq": "yearly",  "priority": "0.3"},
    {"loc": f"{BASE_URL}/about.html",   "changefreq": "monthly", "priority": "0.5"},
]

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
    loc = f"{BASE_URL}/spot.html?id={spot['id']}"
    lines.append(f'  <url>')
    lines.append(f'    <loc>{loc}</loc>')
    lines.append(f'    <lastmod>{TODAY}</lastmod>')
    lines.append(f'    <changefreq>monthly</changefreq>')
    lines.append(f'    <priority>0.7</priority>')
    lines.append(f'  </url>')

lines.append('</urlset>')

with open('sitemap.xml', 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')

print(f"sitemap.xml 生成完了: 静的{len(static_pages)}件 + スポット{len(spots)}件 = 計{len(static_pages)+len(spots)}件")
