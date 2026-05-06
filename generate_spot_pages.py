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
from pathlib import Path

BASE_URL = "https://wansakansai.com"
PROJECT_DIR = Path(__file__).resolve().parent
SPOTS_DIR = PROJECT_DIR / "spots"
SPOTS_JSON = PROJECT_DIR / "data" / "spots.json"

PREF_RE = re.compile(r"^(大阪府|兵庫県|京都府|奈良県|滋賀県|和歌山県)")


def build_title(spot: dict) -> str:
    """スポット名｜特徴（都道府県）- わんさかんさい"""
    addr = spot.get("address", "") or ""
    m = PREF_RE.match(addr)
    pref_short = m.group(1).rstrip("府県") if m else "関西"

    keywords = []
    parking = spot.get("parking") or {}
    if parking.get("available"):
        keywords.append("駐車場無料" if parking.get("free") else "駐車場")
    dogrun = spot.get("dogRun") or {}
    if dogrun.get("available"):
        keywords.append("ドッグラン")

    if keywords:
        kw_text = f"{'・'.join(keywords)}（{pref_short}）"
    else:
        kw_text = f"{pref_short}の犬連れスポット"
    return f"{spot['name']}｜{kw_text} - わんさかんさい"


def build_description(spot: dict) -> str:
    addr = spot.get("address", "") or ""
    m = PREF_RE.match(addr)
    pref_short = m.group(1).rstrip("府県") if m else "関西"

    features = []
    parking = spot.get("parking") or {}
    if parking.get("available") is True:
        features.append("駐車場無料" if parking.get("free") else "駐車場あり")
    elif parking.get("available") is False:
        features.append("駐車場なし")
    dogrun = spot.get("dogRun") or {}
    if dogrun.get("available"):
        dr = "無料ドッグラン" if dogrun.get("free") else "ドッグラン"
        if dogrun.get("separated"):
            dr += "（エリア分離）"
        features.append(dr)
    toilet = spot.get("toilet") or {}
    if toilet.get("available"):
        features.append("トイレ（洋式）" if toilet.get("western") else "トイレあり")
    admission = spot.get("admission") or {}
    if "free" in admission:
        features.append("入場無料" if admission.get("free") else "有料")

    feat_text = "・".join(features) + "。" if features else ""
    return (
        f"{spot['name']}（{addr}）の犬連れお出かけ情報。"
        f"{feat_text}{pref_short}で犬と楽しめるスポットの詳細・アクセス・地図を掲載。"
    )


def build_jsonld(spot: dict, url: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Place",
        "name": spot["name"],
        "address": {
            "@type": "PostalAddress",
            "addressRegion": spot.get("address", ""),
        },
        "url": url,
    }
    if spot.get("lat") and spot.get("lng"):
        data["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": spot["lat"],
            "longitude": spot["lng"],
        }
    return json.dumps(data, ensure_ascii=False)


def build_html(spot: dict) -> str:
    sid = spot["id"]
    url = f"{BASE_URL}/spots/{sid}.html"
    title = build_title(spot)
    desc = build_description(spot)
    images = spot.get("images") or ([spot["imageUrl"]] if spot.get("imageUrl") else [])
    og_image = f"{BASE_URL}/{images[0]}" if images else f"{BASE_URL}/images/ogp.png"
    jsonld = build_jsonld(spot, url)

    title_e = html.escape(title)
    desc_e = html.escape(desc)
    sid_e = html.escape(sid)

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
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2097489177716087" crossorigin="anonymous"></script>
  <script type="application/ld+json">{jsonld}</script>
</head>
<body>

  <main class="main-content">
    <a href="../index.html" class="back-link">← スポット一覧に戻る</a>
    <div id="spotDetail" class="loading-spinner">読み込み中...</div>
    <div class="ad-slot"></div>
  </main>

  <script>window.WANSAKA_SPOT_ID = "{sid_e}";</script>
  <script src="../js/common.js"></script>
  <script src="../js/spot.js"></script>
</body>
</html>
'''


def main():
    with open(SPOTS_JSON, encoding="utf-8") as f:
        spots = json.load(f)

    SPOTS_DIR.mkdir(parents=True, exist_ok=True)

    # 既存の html ファイルをクリア（spots.jsonに無いスポットの古いファイル削除）
    existing_ids = {s["id"] for s in spots}
    deleted = 0
    for f in SPOTS_DIR.glob("*.html"):
        if f.stem not in existing_ids:
            f.unlink()
            deleted += 1

    generated = 0
    for spot in spots:
        out = SPOTS_DIR / f"{spot['id']}.html"
        out.write_text(build_html(spot), encoding="utf-8", newline="\n")
        generated += 1

    print(f"spots/ 生成完了: {generated}件" + (f" (削除: {deleted}件)" if deleted else ""))


if __name__ == "__main__":
    main()
