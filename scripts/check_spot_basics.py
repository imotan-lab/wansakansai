"""スポットの「基本の値」を機械で点検する。スポット更新タスク（am/pm）が今日の5件に流し、出たものを自分で確かめる。

人やAIが文章を読んで確かめるより、機械のほうが確実に拾えるものだけを見る。
これは関所ではなく「確かめる材料」。要確認が出ても、正しいことはある（大きな公園の住所が事務所の場所、など）。

  1. 座標   … 国土地理院の検索で「名前」と「住所」の位置を引き、spots.json の lat/lng からの距離を測る。
               2026-09-28 小目津公園 1.9km・10-03 赤穂ピクニック公園 4.8km のずれを、それまでの確認項目では拾えていなかった。
               2026-10-06の全件棚卸しでは、橋杭岩 13.8km・ブルーメの丘 10.7km などのずれが見つかった。
               判定の順（Codexとの確認で決めた。精度の低い候補で、精度の高い候補のずれを打ち消さない）:
                 ① 名前が一致した地名が 1.5km 以内 → OK
                 ② 番地・番・号まで引けた住所が 1.5km 以内 → OK
                 ③ ①②の候補があるのにどれも外れ → 要確認
                 ④ ①②の候補が無く、地区までしか引けない → 5km 以内なら「参考」（要確認には数えない）、外なら要確認
               人やタスクが確かめて「この座標で合っている」とした分は Documents/wansakansai/geo_checked.json に残し、座標が変わらない限り再び要確認にしない
               （`--mark-geo-ok ID --reason 理由`）。
  2. 公式URL … 開けるか（404・つながらない）。別のドメインへ飛ばされる場合も知らせる。
               401/403/429 は機械の取得を断っているだけのことがあるので「ブラウザで確認」（開けると決めつけない）
  3. 読み   … aliases に漢字を含まない読みがあるか（スポット名検索のため。CLAUDE.md の運用）
  4. 宿のID … rakutenHotelId / jalanYadId の施設ページ。404/410 なら「ページが無い」、開けてもページ名にスポット名が無ければ
               「別の宿の可能性」、403/429/5xx・通信失敗は「ブラウザで確認」（★この場合はIDを消さない★）

使い方:
  python scripts/check_spot_basics.py --ids id1,id2,...   … 指定のスポットだけ
  python scripts/check_spot_basics.py --ids-file ファイル  … カンマ区切りのIDを書いたファイル
  python scripts/check_spot_basics.py --all               … 全件（棚卸し用・10分前後かかる）
  python scripts/check_spot_basics.py --ids ... --json    … 結果をJSONで出す
  python scripts/check_spot_basics.py --mark-geo-ok ID --reason "広い公園で住所は管理事務所。入口は公式地図で確認"
終了コード: 0＝点検できた（要確認の有無は出力で見る）／ 2＝使い方の誤り
  ★要確認があっても 0 を返す（関所ではないので、呼んだ側の手順を止めない）★
ログ: C:/Users/imao_/.claude/logs/spot_basics_YYYY-MM-DD.log（実行ごとに追記）
"""
import argparse, datetime, html, json, math, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "data" / "spots.json"
# リポジトリの外に置く（中に置くと自動タスクがコミットせず、次の実行が「前の実行が途中で止まった跡」と取り違える）
GEO_OK = Path(r"C:\Users\imao_\Documents\wansakansai\geo_checked.json")
LOG_DIR = Path(r"C:\Users\imao_\.claude\logs")
GEO_LIMIT_KM = 1.5        # 名前が一致した地名・番地まで引けた住所から
GEO_LIMIT_ROUGH_KM = 5.0  # 地区までしか引けない住所から（参考）
PRECISE_ADDR = re.compile(r"[0-9０-９]+(番地|番|号)")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
# 読み＝漢字を含まず、かなを含む別名。括弧書き・英数字・記号が混じっていても検索には効く（部分一致のため）
KANJI = re.compile(r"[\u3400-\u9fff々〆]")
KANA = re.compile(r"[ぁ-ゖァ-ヺ]")
FLAGGED = ("要確認", "取得失敗", "ブラウザで確認")


def now():
    return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")


LOG_LINES = []


def log(msg):
    LOG_LINES.append(f"[{now()}] {msg}")


def flush_log():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / f"spot_basics_{datetime.date.today():%Y-%m-%d}.log", "a", encoding="utf-8") as f:
        f.write("\n".join(LOG_LINES) + "\n")


def km(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 12742.0 * math.asin(math.sqrt(a))


def gsi(q):
    url = "https://msearch.gsi.go.jp/address-search/AddressSearch?q=" + urllib.parse.quote(q)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    time.sleep(0.3)
    return [(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0], f["properties"].get("title", "")) for f in data]


def norm(name):
    # 全角英数を半角・小文字にそろえ、括弧書き・「道の駅」・県立などを外し、空白と中黒を除いて比べる
    name = unicodedata.normalize("NFKC", name or "").lower()
    n = re.sub(r"[（(「].*?[）)」]", "", name or "")
    n = re.sub(r"^(道の駅|兵庫県立|滋賀県立|大阪府立|京都府立|奈良県立|和歌山県立|県立|国営|市立)", "", n.strip())
    return re.sub(r"[\s・　「」]", "", n)


def load_geo_ok():
    try:
        return json.loads(GEO_OK.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def check_geo(s, geo_ok):
    lat, lng = s.get("lat"), s.get("lng")
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return "要確認", "lat/lng が数値でない"
    ok = geo_ok.get(s["id"])
    if ok and abs(ok.get("lat", 0) - lat) < 1e-6 and abs(ok.get("lng", 0) - lng) < 1e-6:
        return "OK", f"確認済み（{ok.get('date')}・{ok.get('reason')}）"
    names = {norm(s["name"])} | {norm(a) for a in s.get("aliases", []) if KANJI.search(a or "")}
    names.discard("")
    strong, rough = [], []
    try:
        for q in dict.fromkeys([s["name"], re.sub(r"[（(].*?[）)]", "", s["name"]).strip()]):
            for h in gsi(q)[:10]:
                if norm(h[2]) in names:
                    strong.append((km(lat, lng, h[0], h[1]), f"名前『{h[2]}』"))
        hits = gsi(s.get("address", ""))
        if hits:
            a = hits[0]
            d = km(lat, lng, a[0], a[1])
            (strong if PRECISE_ADDR.search(a[2]) else rough).append((d, f"住所『{a[2]}』"))
    except Exception as e:
        return "取得失敗", f"国土地理院の検索に失敗: {e}"
    if strong:
        d, src = min(strong)
        if d <= GEO_LIMIT_KM:
            return "OK", f"{src}から{d:.2f}km"
        return "要確認", f"{src}から{d:.1f}km離れている（名前の一致か番地まで引けた位置。許す距離{GEO_LIMIT_KM}km）"
    if rough:
        d, src = min(rough)
        if d <= GEO_LIMIT_ROUGH_KM:
            return "参考", f"名前でも番地でも引けず、地区の中心（{src}）から{d:.1f}km"
        return "要確認", f"地区の中心（{src}）からでも{d:.1f}km離れている"
    return "要確認", "名前でも住所でも位置が引けない"


def fetch(url, want_body=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            cs = (r.headers.get_content_charset() or "utf-8").lower()
            cs = {"windows-31j": "cp932", "shift_jis": "cp932", "x-sjis": "cp932"}.get(cs, cs)
            body = r.read(400_000).decode(cs, errors="replace") if want_body else ""
            return r.status, r.geturl(), body
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", ""


def host(u):
    return re.sub(r"^www\.", "", urllib.parse.urlparse(u).netloc.lower())


def check_url(s):
    u = s.get("officialUrl") or ""
    if not re.match(r"^https?://", u):
        return "要確認", "公式URLが無いか http で始まらない"
    code, final, _ = fetch(u)
    if code is None:
        if "CERTIFICATE_VERIFY_FAILED" in final and "expired" in final:
            return "要確認", "公式サイトの証明書が期限切れ（見る人のブラウザに警告が出る。URLは変えずにログへ）"
        return "要確認", f"つながらない（{final[:120]}）"
    if code in (404, 410):
        return "要確認", f"ページが無い（{code}）"
    if code in (401, 403, 429):
        return "ブラウザで確認", f"{code}（機械の取得を断っている。ブラウザで開けるかを確かめる）"
    if code >= 500:
        return "ブラウザで確認", f"サーバーエラー（{code}）。一時的なこともある"
    if host(final) != host(u):
        return "要確認", f"別のサイトへ飛ばされる（→ {final[:80]}）"
    return "OK", str(code)


def check_reading(s):
    if any(isinstance(a, str) and KANA.search(a) and not KANJI.search(a) for a in s.get("aliases", [])):
        return "OK", ""
    return "要確認", "漢字を含まない読み（ひらがな・カタカナ）が aliases に無い"


def page_title(body):
    m = re.search(r"<title[^>]*>(.*?)</title>", body or "", re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def check_hotels(s):
    jobs = []
    if s.get("rakutenHotelId"):
        jobs.append(("楽天", f"https://travel.rakuten.co.jp/HOTEL/{s['rakutenHotelId']}/"))
    if s.get("jalanYadId"):
        jobs.append(("じゃらん", f"https://www.jalan.net/yad{s['jalanYadId']}/"))
    if not jobs:
        return "対象外", ""
    want = {norm(s["name"])} | {norm(a) for a in s.get("aliases", [])}
    want = {w for w in want if len(w) >= 3}
    worst, notes = "OK", []
    rank = {"OK": 0, "ブラウザで確認": 1, "要確認": 2}
    for label, url in jobs:
        code, final, body = fetch(url, want_body=True)
        if code in (404, 410):
            st, why = "要確認", f"{label}の施設ページが無い（{code}）"
        elif code != 200:
            st, why = "ブラウザで確認", f"{label}の施設ページを機械では開けない（{code if code else final[:80]}）。IDは消さない"
        else:
            t = page_title(body)
            nt = norm(t)
            if any(w in nt for w in want):
                st, why = "OK", f"{label}『{t[:40]}』"
            else:
                st, why = "要確認", f"{label}のページ名『{t[:50]}』にスポット名が見当たらない（別の宿の可能性。施設名・所在地を見比べる）"
        notes.append(why)
        if rank[st] > rank[worst]:
            worst = st
    return worst, "／".join(notes)


def mark_geo_ok(sid, reason):
    spots = {s["id"]: s for s in json.load(open(SPOTS, encoding="utf-8"))}
    if sid not in spots:
        print("spots.json に無いID:", sid)
        return 2
    d = load_geo_ok()
    d[sid] = {"lat": spots[sid]["lat"], "lng": spots[sid]["lng"], "reason": reason, "date": f"{datetime.date.today():%Y-%m-%d}"}
    GEO_OK.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"[geo-ok] {sid} {reason}")
    flush_log()
    print(f"確認済みに記録: {sid}（座標 {spots[sid]['lat']}, {spots[sid]['lng']} が変わらない限り再び要確認にしない）")
    return 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ids")
    g.add_argument("--ids-file", help="カンマ区切りのIDを書いたファイル")
    g.add_argument("--all", action="store_true")
    g.add_argument("--mark-geo-ok", metavar="ID")
    ap.add_argument("--reason", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.mark_geo_ok:
        if not a.reason.strip():
            print("--reason に確かめた根拠を書いてください")
            return 2
        return mark_geo_ok(a.mark_geo_ok, a.reason.strip())
    spots = json.load(open(SPOTS, encoding="utf-8"))
    if a.all:
        targets = spots
    else:
        raw = a.ids if a.ids else Path(a.ids_file).read_text(encoding="utf-8")
        want = [x.strip() for x in raw.split(",") if x.strip()]
        by = {s["id"]: s for s in spots}
        missing = [w for w in want if w not in by]
        if missing:
            print("spots.json に無いID:", ", ".join(missing))
            return 2
        targets = [by[w] for w in want]
    geo_ok = load_geo_ok()
    log(f"=== 開始 対象{len(targets)}件 ===")
    results, flagged = [], 0
    keys = ("座標", "公式URL", "読み", "宿のID")
    for s in targets:
        r = {"id": s["id"], "name": s["name"]}
        for key, fn in (("座標", lambda x: check_geo(x, geo_ok)), ("公式URL", check_url), ("読み", check_reading), ("宿のID", check_hotels)):
            st, why = fn(s)
            r[key] = {"status": st, "detail": why}
        bad = [k for k in keys if r[k]["status"] in FLAGGED]
        r["flag"] = bool(bad)
        flagged += bool(bad)
        results.append(r)
        log(f"{s['id']} " + " / ".join(f"{k}={r[k]['status']}{('（' + r[k]['detail'] + '）') if r[k]['detail'] else ''}" for k in keys))
        if not a.json:
            print(f"- {'要確認' if bad else 'OK'} {s['id']} {s['name']}")
            for k in bad:
                print(f"    {k}: {r[k]['status']} {r[k]['detail']}")
    log(f"=== 終了 要確認{flagged}件 / {len(targets)}件 ===")
    flush_log()
    if a.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        print(f"=== 要確認 {flagged}件 / {len(targets)}件 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
