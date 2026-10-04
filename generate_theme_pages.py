"""テーマ別まとめページ（themes/）の一覧を、HTMLに直接書き込む（2026-10-04）。

それまでは js/theme-page.js がスポットの一覧を後から描いていたため、Googleが読む最初のHTMLには
導入文しか無く、Search Console で過去16か月の表示回数が0だった（ブログは同じ3か月で66回）。
一覧・件数・テーマ一覧の件数をここで生HTMLに書き込み、検索の入口になれるようにする。

- テーマの定義（どのスポットを載せるか）はここの THEMES が唯一の正本。JS側には持たない
- 各テーマページの <!-- THEME_LIST_START --> 〜 <!-- THEME_LIST_END --> の間と、
  件数の <p class="theme-count"> を書き換える。導入文・選び方のポイント・meta は手書きのまま触らない
- themes/index.html は <!-- THEME_GRID_START --> 〜 <!-- THEME_GRID_END --> の間を書き換える
- generate_spot_pages.py の最後から呼ばれるので、スポットを直せば自動で追従する。単独でも動く:
    python generate_theme_pages.py
"""
import html
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
THEMES_DIR = PROJECT_DIR / "themes"
SPOTS_JSON = PROJECT_DIR / "data" / "spots.json"


def _tags(s):
    return s.get("tags") or []


def _dog_run(s):
    return s.get("dogRun") or {}


THEMES = [
    {"slug": "dogrun-free", "navTitle": "無料ドッグラン", "lead": "入場・利用とも無料でドッグランが使える公園。",
     "filter": lambda s: bool(_dog_run(s).get("available") and _dog_run(s).get("free"))},
    {"slug": "dogrun", "navTitle": "ドッグランがある公園", "lead": "無料・有料を問わず、ドッグランを備えた公園すべて。",
     "filter": lambda s: bool(_dog_run(s).get("available"))},
    {"slug": "sakura", "navTitle": "桜・お花見", "lead": "愛犬と桜を楽しめる、関西のお花見スポット。",
     "filter": lambda s: "sakura" in _tags(s)},
    {"slug": "koyo", "navTitle": "紅葉", "lead": "秋に犬と訪れたい、関西の紅葉スポット。",
     "filter": lambda s: "koyo" in _tags(s)},
    {"slug": "water", "navTitle": "水遊び・川遊び", "lead": "夏に愛犬と水辺で遊べる川・海沿いのスポット。",
     "filter": lambda s: "water" in _tags(s)},
    {"slug": "rain", "navTitle": "雨でもOK", "lead": "屋根付き・屋内で、雨の日も楽しめるスポット。",
     "filter": lambda s: "rain" in _tags(s)},
    {"slug": "free", "navTitle": "完全無料で行ける", "lead": "入場料も駐車場も無料。お財布にやさしいお出かけ先。",
     "filter": lambda s: bool((s.get("admission") or {}).get("free")
                              and (s.get("parking") or {}).get("available")
                              and (s.get("parking") or {}).get("free"))},
]

PREF_RE = re.compile(r"^(北海道|東京都|京都府|大阪府|.+?県)")


def prefecture(address):
    m = PREF_RE.match(address or "")
    return m.group(1) if m else "その他"


def excerpt(remarks, limit=80):
    """備考の最初の一文（長ければ切る）。一覧に中身を持たせるため"""
    text = (remarks or "").strip()
    if not text:
        return ""
    first = text.split("。")[0] + "。"
    if len(first) > limit:
        first = first[:limit - 1] + "…"
    return first


def card_html(s):
    esc = html.escape
    dr = _dog_run(s)
    tags = []
    p = s.get("parking") or {}
    if p.get("available"):
        tags.append('<span class="tag">P {}</span>'.format("無料" if p.get("free") else "有料"))
    if dr.get("available"):
        t = "ドッグラン"
        if dr.get("separated"):
            t += "(エリア分離)"
        if dr.get("free"):
            t += "・無料"
        tags.append('<span class="tag">{}</span>'.format(t))
    if (s.get("admission") or {}).get("free"):
        tags.append('<span class="tag">入場無料</span>')
    stamp = ('<img src="../images/stamp-visited.png" alt="運営が実際に訪問済み" class="visited-stamp">'
             if s.get("visited") else "")
    ex = excerpt(s.get("remarks"))
    ex_html = '\n          <p class="spot-card-excerpt">{}</p>'.format(esc(ex)) if ex else ""
    return (
        '        <a href="../spots/{id}.html" class="spot-card">\n'
        '          {stamp}\n'
        '          <div class="spot-card-header">\n'
        '            <span class="spot-card-name">{name}</span>\n'
        '          </div>\n'
        '          <p class="spot-card-address">{addr}</p>{ex}\n'
        '          <div class="spot-card-tags">{tags}</div>\n'
        '        </a>'
    ).format(id=esc(s["id"]), stamp=stamp, name=esc(s["name"]), addr=esc(s.get("address", "")),
             ex=ex_html, tags="".join(tags))


def list_html(matched):
    if not matched:
        return '<p class="theme-empty">現在、該当するスポットはありません。</p>'
    groups = {}
    for s in matched:
        groups.setdefault(prefecture(s.get("address")), []).append(s)
    order = sorted(groups, key=lambda k: -len(groups[k]))
    out = []
    for pref in order:
        items = sorted(groups[pref], key=lambda s: (not s.get("visited"), s["name"]))
        out.append(
            '<section class="theme-group">\n'
            '      <h2 class="theme-group-title">{}（{}）</h2>\n'
            '      <div class="spot-list">\n{}\n      </div>\n'
            '    </section>'.format(html.escape(re.sub(r"[府県]$", "", pref)), len(items),
                                    "\n".join(card_html(s) for s in items)))
    return "\n    ".join(out)


def replace_between(text, start, end, new, path):
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        raise SystemExit(f"★{path.name} に {start} 〜 {end} が無い。手で置いてから流すこと")
    return text[:i + len(start)] + "\n    " + new + "\n    " + text[j:]


def build(spots):
    done = []
    for t in THEMES:
        path = THEMES_DIR / f"{t['slug']}.html"
        text = path.read_text(encoding="utf-8")
        matched = [s for s in spots if t["filter"](s)]
        text = replace_between(text, "<!-- THEME_LIST_START -->", "<!-- THEME_LIST_END -->", list_html(matched), path)
        text, n = re.subn(r'<p class="theme-count"[^>]*>.*?</p>',
                          '<p class="theme-count">該当 {} 件</p>'.format(len(matched)), text, count=1)
        if n != 1:
            raise SystemExit(f"★{path.name} に件数の <p class=\"theme-count\"> が無い")
        path.write_text(text, encoding="utf-8", newline="\n")
        done.append((t["slug"], len(matched)))
    idx = THEMES_DIR / "index.html"
    text = idx.read_text(encoding="utf-8")
    cards = "\n    ".join(
        '<a href="{slug}.html" class="theme-card">'
        '<div class="theme-card-title">{title}</div>'
        '<div class="theme-card-count">{n}件</div>'
        '<div class="theme-card-lead">{lead}</div></a>'.format(
            slug=t["slug"], title=html.escape(t["navTitle"]), n=n, lead=html.escape(t["lead"]))
        for t, (_, n) in zip(THEMES, done))
    text = replace_between(text, "<!-- THEME_GRID_START -->", "<!-- THEME_GRID_END -->", cards, idx)
    idx.write_text(text, encoding="utf-8", newline="\n")
    print("themes/ 生成完了: " + "、".join(f"{slug} {n}件" for slug, n in done))


def main():
    spots = json.loads(SPOTS_JSON.read_text(encoding="utf-8"))
    spots = spots if isinstance(spots, list) else spots["spots"]
    # generate_spot_pages.py と同じく、犬が入れないスポット（dogSize すべて false）は載せない
    spots = [s for s in spots if not all((s.get("dogSize") or {}).get(k) is False for k in ("small", "medium", "large"))]
    build(spots)


if __name__ == "__main__":
    main()
