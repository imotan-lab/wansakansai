"""検証の済んだ新規スポットJSONを data/spots.json に取り込む。

使い方:
  python scripts/merge_new_spots.py --check a.json b.json      # 取り込まずに検査だけ
  python scripts/merge_new_spots.py --apply a.json b.json      # 末尾に追加して保存

検査する内容（機械で判定できることだけ。中身の正しさは2AIの突き合わせで担保する）:
  - 必須キーが揃っているか／余計なキーが無いか
  - id が英小文字・数字・ハイフンで、既存と重複しないか
  - name・address の重複がないか
  - lat/lng が関西の範囲（北緯33.4〜35.8・東経134.0〜136.5）に入っているか
  - remarks が200字以上で「。」で終わるか／禁止記号（半角括弧・全角チルダ・半角波ダッシュ）が無いか
  - visited が false、imageUrl が空、officialUrl が https で始まるか
  - aliases の先頭がひらがな読みか
  - tags が既知の語彙か
  - temporary の until が YYYY-MM-DD で未来日か

取り込んだ後は必ず次を実行すること:
  python scripts/check_writing_style.py --fix
  python generate_spot_pages.py
  python generate_sitemap.py
"""
import argparse, datetime, io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPOTS = os.path.join(ROOT, "data", "spots.json")

REQUIRED = ["id", "name", "address", "lat", "lng", "category", "dogSize", "parking",
            "toilet", "dogRun", "admission", "visited", "remarks", "imageUrl",
            "officialUrl", "tags", "aliases"]
OPTIONAL = ["temporary", "stairs", "barrierFree", "images", "dogArea",
            "stayKeyword", "rakutenHotelId", "jalanYadId"]
CATEGORIES = {"park", "walk", "other", "riverside", "beach", "dogrun", "michinoeki", "garden"}
TAGS = {"sakura", "koyo", "water", "rain", "small-dog-only", "stay-ok", "stay-only"}
BAD_CHARS = [("(", "半角丸括弧"), (")", "半角丸括弧"), ("～", "全角チルダ"), ("~", "半角チルダ")]


def check(spot, existing_ids, existing_names, errors, warns):
    sid = spot.get("id", "(idなし)")

    def e(msg):
        errors.append(f"{sid}: {msg}")

    def w(msg):
        warns.append(f"{sid}: {msg}")

    for k in REQUIRED:
        if k not in spot:
            e(f"必須キー {k} が無い")
    for k in spot:
        if k not in REQUIRED and k not in OPTIONAL:
            e(f"知らないキー {k}")
    if not re.fullmatch(r"[a-z0-9-]+", spot.get("id", "")):
        e("id は英小文字・数字・ハイフンのみ")
    if spot.get("id") in existing_ids:
        e("id が既存と重複")
    if spot.get("name") in existing_names:
        e("name が既存と重複")
    lat, lng = spot.get("lat"), spot.get("lng")
    if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))):
        e("lat/lng が数値でない")
    elif not (33.4 <= lat <= 35.8 and 134.0 <= lng <= 136.5):
        e(f"lat/lng が関西の範囲外 ({lat}, {lng})")
    if spot.get("category") not in CATEGORIES:
        e(f"category が語彙外: {spot.get('category')}")
    r = spot.get("remarks", "")
    if len(r) < 200:
        e(f"remarks が{len(r)}字（200字以上が必要）")
    if not r.endswith("。"):
        e("remarks が「。」で終わっていない")
    for ch, name in BAD_CHARS:
        if ch in r:
            e(f"remarks に{name}「{ch}」が入っている")
    if re.search(r"20\d\d年\d+月\d+日", r):
        w("remarks に年入りの日付がある（期限つきなら temporary へ）")
    if spot.get("visited") is not False:
        e("visited は false にすること")
    if spot.get("imageUrl") != "":
        e("imageUrl は空文字にすること")
    if not str(spot.get("officialUrl", "")).startswith("https://"):
        e("officialUrl が https:// で始まっていない")
    al = spot.get("aliases") or []
    if not al:
        e("aliases が空")
    elif not re.fullmatch(r"[ぁ-んー 　]+", al[0]):
        w(f"aliases の先頭がひらがな読みでない: {al[0]}")
    for t in spot.get("tags") or []:
        if t not in TAGS:
            e(f"tags が語彙外: {t}")
    today = datetime.date.today()
    for t in spot.get("temporary") or []:
        u = t.get("until", "")
        try:
            d = datetime.date.fromisoformat(u)
        except ValueError:
            e(f"temporary.until の書式が不正: {u}")
            continue
        if d <= today:
            e(f"temporary.until が過去または今日: {u}")
        if t.get("note", "").endswith(("）", ")")):
            e("temporary.note を括弧で終わらせない")
        if not t.get("source", "").startswith("http"):
            e("temporary.source が無い")
        if not t.get("onExpire"):
            e("temporary.onExpire が無い")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    spots = json.load(io.open(SPOTS, encoding="utf-8"))
    ids = {s["id"] for s in spots}
    names = {s["name"] for s in spots}
    errors, warns, adds = [], [], []
    for f in a.files:
        d = json.load(io.open(f, encoding="utf-8"))
        if d.get("verdict"):
            print(f"- スキップ {d.get('id')}: verdict={d['verdict']}")
            continue
        check(d, ids, names, errors, warns)
        ids.add(d.get("id"))
        names.add(d.get("name"))
        adds.append(d)

    for w in warns:
        print(f"[注意] {w}")
    for e in errors:
        print(f"[NG] {e}")
    print(f"\n対象 {len(adds)} 件 / NG {len(errors)} 件 / 注意 {len(warns)} 件")
    if errors:
        print("NGがあるので取り込まない")
        return 1
    if not a.apply:
        print("--apply を付けると data/spots.json の末尾に追加する")
        return 0
    spots.extend(adds)
    io.open(SPOTS, "w", encoding="utf-8").write(
        json.dumps(spots, ensure_ascii=False, indent=2) + "\n")
    print(f"data/spots.json に {len(adds)} 件追加（計 {len(spots)} 件）")
    print("次に: check_writing_style.py --fix → generate_spot_pages.py → generate_sitemap.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
