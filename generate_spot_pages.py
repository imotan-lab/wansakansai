"""
spots.jsonから各スポット用の静的HTMLを spots/{id}.html として事前生成する。

目的: SEO（canonical問題）解決
- 各ページに正しい canonical / title / description / OGP / JSON-LD を静的に埋め込む
- Googleがレンダリング前のHTMLでも正しくインデックスできる

使い方: python generate_spot_pages.py
スポット追加・編集後に必ず実行する。
"""
import json
import re
import html
import math
from pathlib import Path

BASE_URL = "https://wansakansai.com"
PROJECT_DIR = Path(__file__).resolve().parent
SPOTS_DIR = PROJECT_DIR / "spots"
SPOTS_JSON = PROJECT_DIR / "data" / "spots.json"

PREF_RE = re.compile(r"^(大阪府|兵庫県|京都府|奈良県|滋賀県|和歌山県)")

# 一覧ページの表示順（spots/index.html）
PREF_ORDER = ["大阪府", "兵庫県", "京都府", "奈良県", "滋賀県", "和歌山県"]

# 静的内部リンクの本数（各スポットページに載せる「近くのスポット」件数）
NEARBY_COUNT = 6


def _pref_and_rest(addr: str) -> tuple[str, str]:
    """住所を都道府県とそれ以降に分割。"""
    m = PREF_RE.match(addr or "")
    if not m:
        return ("", addr or "")
    pref = m.group(1)
    rest = (addr or "")[len(pref):]
    return (pref, rest)


def _short_pref(pref: str) -> str:
    return pref.rstrip("府県") if pref else "関西"


def build_title(spot: dict) -> str:
    """スポット名｜犬連れOK・特徴（都道府県）- わんさかんさい

    SEO: 「○○ 犬連れ」クエリで上位を狙うため『犬連れOK』を必ず含める。
    全角30文字以内が理想（検索結果で省略されない）。長すぎる場合は特徴を削る。
    """
    pref, _ = _pref_and_rest(spot.get("address", ""))
    pref_short = _short_pref(pref)

    # 優先順位順の特徴リスト
    features = ["犬連れOK"]
    dogrun = spot.get("dogRun") or {}
    if dogrun.get("available"):
        features.append("ドッグラン")
    parking = spot.get("parking") or {}
    if parking.get("available"):
        features.append("駐車場無料" if parking.get("free") else "駐車場あり")
    admission = spot.get("admission") or {}
    if admission.get("free"):
        features.append("入場無料")

    suffix = " - わんさかんさい"
    name = spot["name"]
    # 文字数調整: name + ｜ + 特徴 + （県） + suffix が30文字を超えない範囲で特徴を盛る
    for k in range(len(features), 0, -1):
        feat_text = "・".join(features[:k])
        title = f"{name}｜{feat_text}（{pref_short}）{suffix}"
        if len(title) <= 37:  # 検索結果でほぼ表示される範囲
            return title
    return f"{name}｜犬連れOK（{pref_short}）{suffix}"


def build_description(spot: dict) -> str:
    """スポットの犬連れ情報を120字前後で要約する meta description。

    SEO: 検索結果に表示される説明文。スポット名・特徴・remarks先頭を含める。
    """
    pref, rest = _pref_and_rest(spot.get("address", ""))
    pref_short = _short_pref(pref)

    features = []
    parking = spot.get("parking") or {}
    if parking.get("available") is True:
        features.append("駐車場無料" if parking.get("free") else "駐車場有料")
    dogrun = spot.get("dogRun") or {}
    if dogrun.get("available"):
        dr = "無料ドッグラン" if dogrun.get("free") else "ドッグラン"
        if dogrun.get("separated"):
            dr += "（エリア分離）"
        features.append(dr)
    admission = spot.get("admission") or {}
    if admission.get("free"):
        features.append("入場無料")
    toilet = spot.get("toilet") or {}
    if toilet.get("available"):
        features.append("トイレあり")

    feat_text = "・".join(features) + "。" if features else ""

    # remarks先頭文の最初の1〜2文だけ抜粋
    remarks = (spot.get("remarks") or "").strip()
    remarks_excerpt = ""
    if remarks:
        sentences = [s.strip() for s in remarks.split("。") if s.strip()]
        excerpt_buf = ""
        for s in sentences:
            if len(excerpt_buf) + len(s) + 1 > 60:
                break
            excerpt_buf += s + "。"
        remarks_excerpt = excerpt_buf

    return (
        f"{spot['name']}は{pref_short}の犬連れOKスポット。"
        f"{feat_text}{remarks_excerpt}"
        f"アクセス・地図・周辺情報を掲載。"
    )[:155]


def _amenity(name: str, value: bool) -> dict:
    return {
        "@type": "LocationFeatureSpecification",
        "name": name,
        "value": value,
    }


def build_jsonld(spot: dict, url: str, image_url: str = "") -> str:
    """Place構造化データ。リッチリザルト対応のため amenityFeature 等を充実させる。"""
    pref, rest = _pref_and_rest(spot.get("address", ""))

    address: dict = {
        "@type": "PostalAddress",
        "addressCountry": "JP",
    }
    if pref:
        address["addressRegion"] = pref
    if rest:
        address["streetAddress"] = rest

    data = {
        "@context": "https://schema.org",
        "@type": "Place",
        "name": spot["name"],
        "description": (spot.get("remarks") or "").split("。")[0] + "。" if spot.get("remarks") else "",
        "url": url,
        "address": address,
        "petsAllowed": True,
    }
    if image_url:
        data["image"] = image_url
    if spot.get("lat") and spot.get("lng"):
        data["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": spot["lat"],
            "longitude": spot["lng"],
        }

    # 価格帯
    admission = spot.get("admission") or {}
    if admission.get("free"):
        data["priceRange"] = "無料"
    elif admission.get("fee"):
        data["priceRange"] = admission["fee"]

    # 公式URL等は sameAs に
    if spot.get("officialUrl"):
        data["sameAs"] = [spot["officialUrl"]]

    # 設備
    amenities = []
    parking = spot.get("parking") or {}
    if parking.get("available"):
        amenities.append(_amenity("駐車場無料" if parking.get("free") else "駐車場", True))
    elif parking.get("available") is False:
        amenities.append(_amenity("駐車場", False))
    dogrun = spot.get("dogRun") or {}
    if dogrun.get("available"):
        dr_name = "無料ドッグラン" if dogrun.get("free") else "ドッグラン"
        amenities.append(_amenity(dr_name, True))
    toilet = spot.get("toilet") or {}
    if toilet.get("available"):
        amenities.append(_amenity("トイレ（洋式）" if toilet.get("western") else "トイレ", True))
    if amenities:
        data["amenityFeature"] = amenities

    # 識別子（aliases等を別名として）
    aliases = spot.get("aliases") or []
    if aliases:
        # ひらがな読み等は alternateName に
        data["alternateName"] = aliases

    # <script> 内に直接埋め込むため、</script> 等でタグが早期終了しないよう
    # < > & を Unicode エスケープする（JSON-LD としての有効性は保たれる）
    dumped = json.dumps(data, ensure_ascii=False)
    return dumped.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def parking_text(spot: dict) -> str:
    p = spot.get("parking") or {}
    if not p.get("available"):
        return "なし"
    return "あり（無料）" if p.get("free") else "あり（有料）"


def toilet_text(spot: dict) -> str:
    t = spot.get("toilet") or {}
    available = t.get("available")
    # available が None は「無い」ではなく「未確認」。断定せず要確認と表示する
    # （調べても公表情報が見つからない施設がある。false と書くと誤情報になる）
    if available is None:
        return "情報なし（要確認）"
    if not available:
        return "なし"
    western = t.get("western")
    # None は洋式/和式が未確認。断定せず「あり」とだけ表示する
    if western is None:
        return "あり"
    return "あり（洋式）" if western else "あり（和式）"


def dogrun_text(spot: dict) -> str:
    d = spot.get("dogRun") or {}
    if not d.get("available"):
        return "なし"
    base = "あり（無料）" if d.get("free") else "あり（有料）"
    if d.get("detail"):
        base += f" / {d['detail']}"
    return base


def admission_text(spot: dict) -> str:
    a = spot.get("admission") or {}
    fee = (a.get("fee") or "").strip()
    if a.get("free"):
        # 入場自体は無料でも fee に駐車場代・一部有料施設などの補足がある場合は捨てずに表示する。
        # fee が既に「無料」を含む場合はそのまま（「無料（〜は無料（〜））」の二重表記を防ぐ）
        if not fee:
            return "無料"
        return fee if "無料" in fee else f"無料（{fee}）"
    return f"有料（{fee}）"


def format_remarks(remarks: str) -> str:
    """spot.jsと同じく30文字以上で改行を入れた整形"""
    if not remarks:
        return ""
    sentences = [s for s in remarks.split("。") if s]
    html_lines = []
    buffer = ""
    for i, s in enumerate(sentences):
        buffer += s + "。"
        if len(buffer) >= 30 or i == len(sentences) - 1:
            html_lines.append(html.escape(buffer))
            buffer = ""
    return "<br>".join(html_lines)


def _distance_km(a: dict, b: dict) -> float:
    """2スポット間の直線距離（km）。ハバサイン公式。"""
    lat1, lng1 = a.get("lat"), a.get("lng")
    lat2, lng2 = b.get("lat"), b.get("lng")
    if None in (lat1, lng1, lat2, lng2):
        return float("inf")
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _format_distance(km: float) -> str:
    if km < 1:
        return f"{int(round(km * 1000))}m"
    return f"{km:.1f}km"


def build_nearby_html(spot: dict, all_spots: list) -> str:
    """近くのスポットへの静的リンク。

    ★SEO上の役割★ spots/{id}.html はサイトマップ以外から辿れない孤立ページだと
    Googleが「検出 - インデックス未登録」のまま放置する（2026-08-25に106ページで実際に発生）。
    スポット同士を静的リンクで結び、クロール経路を作るためのブロック。
    spot.js が #spotDetail を innerHTML で描き直すため、JS実行後はJS版の表示に置き換わる
    （＝見た目は従来どおり。この静的版はレンダリング前のHTMLをbotに読ませるためのもの）。
    """
    others = [s for s in all_spots if s.get("id") != spot.get("id")]
    ranked = sorted(others, key=lambda s: _distance_km(spot, s))
    nearby = [s for s in ranked[:NEARBY_COUNT] if _distance_km(spot, s) != float("inf")]
    if not nearby:
        return ""

    cards = []
    for s in nearby:
        sid = html.escape(s["id"])
        nm = html.escape(s["name"])
        dist = html.escape(_format_distance(_distance_km(spot, s)))
        cards.append(
            f'<a href="{sid}.html" class="nearby-spot-card">'
            f'<span class="nearby-spot-name">{nm}</span>'
            f'<span class="nearby-spot-dist">{dist}</span></a>'
        )
    return f'''<div class="nearby-spots">
          <h3>近くのスポット</h3>
          {"".join(cards)}
        </div>'''


def build_body_content(spot: dict, all_spots: list = None) -> str:
    """SEO的にbotがクロール時に読み取れる本文HTML（spot.jsが上書きするが、初期表示でも有意義）"""
    name = html.escape(spot["name"])
    address = html.escape(spot.get("address", ""))
    visited = '<img src="../images/stamp-visited.png" alt="運営が実際に訪問済み" class="detail-visited-stamp">' if spot.get("visited") else ""

    images = spot.get("images") or ([spot["imageUrl"]] if spot.get("imageUrl") else [])
    gallery_html = ""
    if images:
        first_img = html.escape("../" + images[0])
        gallery_html = f'''<div class="spot-gallery">
          <div class="spot-gallery-main">
            <img src="{first_img}" alt="{name}" class="spot-gallery-img" id="galleryMainImg" loading="lazy">
          </div>
        </div>'''

    official = ""
    if spot.get("officialUrl"):
        url_e = html.escape(spot["officialUrl"])
        display = spot["officialUrl"].replace("https://", "").replace("http://", "").rstrip("/")
        official = f'''<div class="detail-info-item">
            <span class="detail-info-label">公式HP</span>
            <span class="detail-info-value"><a href="{url_e}" target="_blank" rel="noopener noreferrer">{html.escape(display)}</a></span>
          </div>'''

    warn = ""
    if "small-dog-only" in (spot.get("tags") or []):
        warn = '<div class="detail-warn">小型犬のみ入場可（大型犬は要確認）</div>'

    remarks_html = ""
    if spot.get("remarks"):
        remarks_html = f'''<div class="detail-remarks">
          <h3>備考・犬連れでのポイント</h3>
          <p>{format_remarks(spot["remarks"])}</p>
        </div>'''

    return f'''<div class="spot-detail">
        {gallery_html}
        <div class="spot-detail-header">
          {visited}
          <h1 class="spot-detail-title">{name}</h1>
        </div>
        <p class="spot-detail-address">{address}</p>

        <div class="detail-info-list">
          <div class="detail-info-item">
            <span class="detail-info-label">駐車場</span>
            <span class="detail-info-value">{html.escape(parking_text(spot))}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-label">トイレ</span>
            <span class="detail-info-value">{html.escape(toilet_text(spot))}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-label">ドッグラン</span>
            <span class="detail-info-value">{html.escape(dogrun_text(spot))}</span>
          </div>
          <div class="detail-info-item">
            <span class="detail-info-label">入場料</span>
            <span class="detail-info-value">{html.escape(admission_text(spot))}</span>
          </div>
          {official}
        </div>

        {warn}
        {remarks_html}
        {build_nearby_html(spot, all_spots or [])}
      </div>'''


def build_html(spot: dict, all_spots: list = None) -> str:
    sid = spot["id"]
    url = f"{BASE_URL}/spots/{sid}.html"
    title = build_title(spot)
    desc = build_description(spot)
    images = spot.get("images") or ([spot["imageUrl"]] if spot.get("imageUrl") else [])
    og_image = f"{BASE_URL}/{images[0]}" if images else f"{BASE_URL}/images/ogp.png"
    jsonld_image = og_image if images else ""  # OGP fallback画像は構造化データには含めない
    jsonld = build_jsonld(spot, url, jsonld_image)
    body_content = build_body_content(spot, all_spots)

    title_e = html.escape(title)
    desc_e = html.escape(desc)
    sid_e = html.escape(sid)
    total_spots = len(all_spots) if all_spots else 0

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{desc_e}">
  <title>{title_e}</title>
  <link rel="canonical" href="{url}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="わんさかんさい">
  <meta property="og:title" content="{title_e}">
  <meta property="og:description" content="{desc_e}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{html.escape(og_image)}">
  <meta property="og:locale" content="ja_JP">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@wansakansai">
  <meta name="twitter:creator" content="@wansakansai">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="icon" href="../favicon.ico">
  <link rel="apple-touch-icon" href="../images/apple-touch-icon.png">
  <link rel="stylesheet" href="../css/style.css">
  <script type="application/ld+json">{jsonld}</script>
</head>
<body>

  <main class="main-content">
    <a href="../index.html" class="back-link">← スポット一覧に戻る</a>
    <div id="spotDetail">
      {body_content}
    </div>
    <p class="all-spots-link"><a href="index.html">関西の犬連れスポット一覧（全{total_spots}件）を見る</a></p>
  </main>

  <script>window.WANSAKA_SPOT_ID = "{sid_e}";</script>
  <script src="../js/common.js"></script>
  <script src="../js/spot.js"></script>
</body>
</html>
'''


def build_index_html(spots: list) -> str:
    """spots/index.html — 全スポットの静的一覧ページ。

    ★SEO上の役割★ トップページのスポット一覧は app.js がJSで描画するため、
    レンダリング前のHTMLには spots/*.html へのリンクが1本も無かった。
    その結果Googleが全スポットページを孤立ページ扱いし、サイトマップで検出しても
    インデックスしない状態になっていた（2026-08-25時点で106ページが「検出 - インデックス未登録」）。
    このページが全スポットへの静的リンクを持つクロール経路のハブになる。
    """
    groups: dict[str, list] = {p: [] for p in PREF_ORDER}
    others: list = []
    for s in spots:
        pref, _ = _pref_and_rest(s.get("address", ""))
        if pref in groups:
            groups[pref].append(s)
        else:
            others.append(s)

    sections = []
    for pref in PREF_ORDER:
        items = sorted(groups[pref], key=lambda s: s["name"])
        if not items:
            continue
        links = []
        for s in items:
            sid = html.escape(s["id"])
            nm = html.escape(s["name"])
            _, rest = _pref_and_rest(s.get("address", ""))
            city = html.escape(rest[:12])
            links.append(
                f'<li><a href="{sid}.html">{nm}</a><span class="all-spots-city">{city}</span></li>'
            )
        sections.append(
            f'''<section class="all-spots-group">
        <h2>{html.escape(pref)}（{len(items)}件）</h2>
        <ul class="all-spots-list">
          {"".join(links)}
        </ul>
      </section>'''
        )

    if others:
        links = []
        for s in sorted(others, key=lambda s: s["name"]):
            sid = html.escape(s["id"])
            nm = html.escape(s["name"])
            links.append(f'<li><a href="{sid}.html">{nm}</a></li>')
        sections.append(
            f'''<section class="all-spots-group">
        <h2>その他（{len(others)}件）</h2>
        <ul class="all-spots-list">
          {"".join(links)}
        </ul>
      </section>'''
        )

    total = len(spots)
    url = f"{BASE_URL}/spots/index.html"
    title = f"関西の犬連れスポット一覧（全{total}件）- わんさかんさい"
    desc = (
        f"大阪・兵庫・京都・奈良・滋賀・和歌山の犬連れOKスポット全{total}件を府県別にまとめた一覧。"
        "ドッグラン・公園・海辺・道の駅など、愛犬と行ける場所を一覧から探せます。"
    )
    title_e = html.escape(title)
    desc_e = html.escape(desc)

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{desc_e}">
  <title>{title_e}</title>
  <link rel="canonical" href="{url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="わんさかんさい">
  <meta property="og:title" content="{title_e}">
  <meta property="og:description" content="{desc_e}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{BASE_URL}/images/ogp.png">
  <meta property="og:locale" content="ja_JP">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@wansakansai">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="icon" href="../favicon.ico">
  <link rel="apple-touch-icon" href="../images/apple-touch-icon.png">
  <link rel="stylesheet" href="../css/style.css">
</head>
<body>

  <main class="main-content">
    <a href="../index.html" class="back-link">← トップページに戻る</a>
    <h1 class="all-spots-title">関西の犬連れスポット一覧</h1>
    <p class="all-spots-lead">
      掲載中の全{total}件を府県別に並べています。現在地から近い順に探す場合は
      <a href="../index.html">トップページ</a>、目的や季節から探す場合は
      <a href="../themes/index.html">テーマ別まとめ</a>をご利用ください。
    </p>
    {"".join(sections)}
  </main>

  <script src="../js/common.js"></script>
  <script>
    renderHeader('spots');
    renderFooter();
  </script>
</body>
</html>
'''


def main():
    with open(SPOTS_JSON, encoding="utf-8") as f:
        spots = json.load(f)

    SPOTS_DIR.mkdir(parents=True, exist_ok=True)

    # 既存の html ファイルをクリア（spots.jsonに無いスポットの古いファイル削除）
    # index.html は全スポット一覧ページなので削除対象から除外する
    existing_ids = {s["id"] for s in spots}
    deleted = 0
    for f in SPOTS_DIR.glob("*.html"):
        if f.stem == "index":
            continue
        if f.stem not in existing_ids:
            f.unlink()
            deleted += 1

    generated = 0
    for spot in spots:
        out = SPOTS_DIR / f"{spot['id']}.html"
        out.write_text(build_html(spot, spots), encoding="utf-8", newline="\n")
        generated += 1

    (SPOTS_DIR / "index.html").write_text(
        build_index_html(spots), encoding="utf-8", newline="\n"
    )

    print(
        f"spots/ 生成完了: {generated}件 + 一覧ページ1件"
        + (f" (削除: {deleted}件)" if deleted else "")
    )


if __name__ == "__main__":
    main()
