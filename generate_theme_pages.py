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


def place(address):
    """住所から「大阪・堺市西区」の形を作る（js/common.js の spotPlace と同じ決まり）"""
    a = address or ""
    m = PREF_RE.match(a)
    pref = re.sub(r"[府県]$", "", m.group(1)) if m else ""
    rest = a[len(m.group(1)):] if m else a
    city = ""
    m2 = re.match(r"^(.+?[市郡])(.+?[区町村])?", rest)
    if m2:
        city = m2.group(1)
        if m2.group(2) and (m2.group(1).endswith("郡") or m2.group(2).endswith("区")):
            city += m2.group(2)
    else:
        m3 = re.match(r"^(.+?[町村])", rest)
        city = m3.group(1) if m3 else ""
    return pref + "・" + city if pref and city else (pref or city)


def _size_ok(s, size):
    ds = s.get("dogSize") or {}
    return ds.get(size, True) is not False


def card_html(s):
    """一覧1件（2026-11 行き先帳）。js/common.js の spotRowHTML と同じ形。片方だけ直さないこと。
    テーマ別は静的ページなのでハートは出さず、備考の最初の一文を添える"""
    esc = html.escape
    dr = _dog_run(s)
    tags = _tags(s)
    p = s.get("parking") or {}
    parking = ("無料" if p.get("free") else "有料") if p.get("available") else "なし"
    admission = "無料" if (s.get("admission") or {}).get("free") else "有料"
    dogrun = ("あり（大小別）" if dr.get("separated") else "あり") if dr.get("available") else "なし"
    warns = []
    if not _size_ok(s, "medium"):
        warns.append("小型犬のみ")
    elif not _size_ok(s, "large"):
        warns.append("中型犬まで")
    if dr.get("available") and dr.get("maxSize") == "small":
        warns.append("ランは小型犬のみ")
    elif dr.get("available") and dr.get("maxSize") == "medium":
        warns.append("ランは中型犬まで")
    if "stay-only" in tags:
        warns.append("宿泊専用")
    feats = [lbl for key, lbl in (("sakura", "桜"), ("koyo", "紅葉"), ("water", "水遊び"),
                                  ("rain", "雨でもOK"), ("stay-ok", "宿泊可")) if key in tags]
    more = ""
    if warns or feats:
        more = ('\n          <p class="row-more">' + "".join('<span class="row-warn">{}</span>'.format(w) for w in warns)
                + "".join('<span class="row-feat">{}</span>'.format(f) for f in feats) + "</p>")
    ex = excerpt(s.get("remarks"))
    ex_html = '\n          <p class="row-excerpt">{}</p>'.format(esc(ex)) if ex else ""
    visited = ""
    if s.get("visited"):
        v = s.get("visit")
        v = v[0] if isinstance(v, list) and v else v
        note = (v or {}).get("note", "") if isinstance(v, dict) else ""
        memo = '<span class="row-memo">{}</span>'.format(esc(note)) if note else ""
        visited = ('\n          <p class="row-visit"><img src="../images/stamp-visited.png" alt="" class="row-stamp" width="34" height="34">'
                   "運営者が訪問{}</p>".format(memo))
    cls = "spot-row" + (" is-visited" if s.get("visited") else "") + (" is-stay" if "stay-only" in tags else "")
    return (
        '        <article class="{cls}">\n'
        '          <div class="row-head"><h3 class="row-name"><a href="../spots/{id}.html" class="row-link">{name}</a></h3></div>\n'
        '          <p class="row-where">{place}</p>\n'
        '          <p class="row-facts">駐車場 <b>{parking}</b>　入場 <b>{admission}</b>　ドッグラン <b>{dogrun}</b></p>{more}{ex}{visited}\n'
        '        </article>'
    ).format(cls=cls, id=esc(s["id"]), name=esc(s["name"]), place=esc(place(s.get("address", ""))),
             parking=parking, admission=admission, dogrun=dogrun, more=more, ex=ex_html, visited=visited)


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
