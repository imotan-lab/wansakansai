"""新規スポットの緯度経度が住所と食い違っていないかを OSM Nominatim の逆ジオコーディングで粗く確かめる。

使い方: python scripts/check_new_spot_geo.py file1.json file2.json ...
  各ファイルの lat/lng を逆ジオコーディングし、返ってきた住所（市区町村）と JSON の address を並べて表示する。
  市区町村が一致しなければ NG を付ける。あくまで粗い検査（施設の中心かどうかまでは分からない）。
Nominatim の利用規約に従い 1秒1件・User-Agent 付き。
"""
import io, json, sys, time, urllib.request, urllib.parse, re
sys.stdout.reconfigure(encoding="utf-8")

def rev(lat, lng):
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}&accept-language=ja&zoom=16"
    req = urllib.request.Request(url, headers={"User-Agent": "wansakansai-geo-check/1.0 (contact via site)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def city_of(addr):
    m = re.search(r"(大阪府|京都府|奈良県|兵庫県|滋賀県|和歌山県)(.+?[市郡区町村])", addr or "")
    return (m.group(1), m.group(2)) if m else (None, None)

ng = 0
for f in sys.argv[1:]:
    d = json.load(io.open(f, encoding="utf-8"))
    if d.get("verdict"):
        print(f"- {d.get('name')}: verdict={d['verdict']}（座標検査は対象外）")
        continue
    try:
        r = rev(d["lat"], d["lng"])
        a = r.get("address", {})
        disp = r.get("display_name", "")
        pref = a.get("province") or a.get("state") or ""
        city = a.get("city") or a.get("town") or a.get("village") or a.get("county") or ""
        want_pref, want_city = city_of(d["address"])
        ok = (want_pref and want_pref in (pref + disp)) and (want_city and (want_city[:2] in (city + disp)))
        flag = "OK" if ok else "NG?"
        if not ok:
            ng += 1
        print(f"- {flag} {d['name']} ({d['lat']}, {d['lng']})\n    JSON住所: {d['address']}\n    逆ジオ  : {pref}{city} / {disp[:90]}")
    except Exception as e:
        print(f"- ?? {d.get('name')}: 逆ジオコーディング失敗 {e}")
    time.sleep(1.1)
print(f"\nNG候補 {ng} 件")
