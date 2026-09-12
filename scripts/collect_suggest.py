"""Googleサジェストを機械的に集めて、犬連れ需要のある地名・施設名を洗い出す。

使い方:
  python scripts/collect_suggest.py            # 収集して JSON と要約を書く
  python scripts/collect_suggest.py --summary  # 収集済み JSON から要約だけ作り直す

出力:
  C:/Users/imao_/Documents/wansakansai/research/suggest_YYYY-MM-DD.json  … 生データ（seed → 候補）
  C:/Users/imao_/Documents/wansakansai/research/suggest_YYYY-MM-DD.txt   … 要約（候補の出現回数順・spots.json との突き合わせ）

注意: サジェストは「実際に打たれている語」の近似であって検索回数ではない。
      Search Console のクエリ（うちが表示された語）と併せて読むこと。
"""
import json, sys, time, datetime, os, re, urllib.request, urllib.parse
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = r"C:/Users/imao_/Documents/wansakansai/research"
TODAY = datetime.date.today().isoformat()
RAW = os.path.join(OUT_DIR, f"suggest_{TODAY}.json")
SUMMARY = os.path.join(OUT_DIR, f"suggest_{TODAY}.txt")

PLACES = {
    "大阪府": ["大阪", "大阪市", "堺", "岸和田", "和泉市", "泉佐野", "貝塚", "泉大津", "高石", "泉南", "阪南", "岬町",
             "河内長野", "富田林", "大阪狭山", "松原", "羽曳野", "藤井寺", "柏原", "八尾", "東大阪", "大東", "門真", "守口",
             "寝屋川", "枚方", "交野", "四條畷", "高槻", "茨木", "吹田", "豊中", "池田", "箕面", "摂津", "能勢", "太子町",
             "河南町", "千早赤阪", "泉北", "南大阪", "北摂", "南河内", "泉州"],
    "奈良県": ["奈良", "奈良市", "生駒", "橿原", "五條", "吉野", "宇陀", "天理", "大和郡山", "葛城", "曽爾"],
    "京都府": ["京都", "京都市", "宇治", "亀岡", "京丹後", "舞鶴", "京丹波", "南丹", "嵐山", "木津川"],
    "兵庫県": ["兵庫", "神戸", "淡路島", "姫路", "三田", "宝塚", "西宮", "尼崎", "明石", "加古川", "丹波篠山", "豊岡", "六甲", "有馬"],
    "滋賀県": ["滋賀", "大津", "長浜", "彦根", "琵琶湖", "高島", "近江八幡", "甲賀", "守山", "米原"],
    "和歌山県": ["和歌山", "和歌山市", "白浜", "有田", "田辺", "串本", "高野山", "那智勝浦", "串本", "海南", "紀の川"],
}
MODIFIERS_AFTER = ["犬連れ", "ドッグラン", "犬 散歩", "犬 公園", "ペット可", "犬 OK", "犬と"]
MODIFIERS_BEFORE = ["犬連れ"]
THEME_SEEDS = ["犬連れ 公園 大阪", "犬連れ 公園 関西", "犬 水遊び 関西", "犬 川遊び 大阪", "犬連れ 紅葉 関西", "犬連れ 桜 大阪",
               "ドッグラン 無料 大阪", "ドッグラン 無料 関西", "犬 海 関西", "犬連れ 海 大阪", "犬連れ お出かけ 関西",
               "犬連れ お出かけ 大阪", "犬と行ける 大阪", "犬と行ける 関西", "犬 観光 関西", "犬連れ 観光 大阪",
               "犬連れ 道の駅 関西", "犬連れ 神社 関西", "犬連れ お寺 関西", "犬連れ 城 関西", "犬連れ ハイキング 関西",
               "犬連れ 山 関西", "犬連れ 雨の日 大阪", "犬連れ 室内 大阪", "犬連れ ショッピングモール 大阪",
               "犬連れ カフェ 大阪", "犬連れ ランチ 大阪", "犬連れ 温泉 関西", "犬連れ 宿 関西", "犬連れ キャンプ 関西",
               "犬連れ 牧場 関西", "犬連れ 果物狩り 関西", "犬連れ いちご狩り 関西", "犬連れ 花 関西", "犬連れ コスモス 関西",
               "犬連れ 芝桜 関西", "犬連れ ひまわり 関西", "犬連れ 梅 関西", "犬連れ 遊園地 関西", "犬連れ 水族館 関西",
               "犬連れ 動物園 関西", "犬連れ 植物園 関西", "犬連れ 花火 関西", "犬連れ 夜景 関西", "犬連れ 電車 関西",
               "犬連れ 船 関西", "犬連れ ロープウェイ 関西", "犬連れ 秋 関西", "犬連れ 夏 関西", "犬連れ 冬 関西", "犬連れ 春 関西"]
# 季節語 × 県（いつ・どこで探されるか）
SEASON_WORDS = ["紅葉", "コスモス", "みかん狩り", "ぶどう狩り", "芋掘り", "彼岸花", "すすき", "銀杏", "秋バラ", "ハイキング",
                "イルミネーション", "梅", "水仙", "初詣", "雪", "温泉", "室内",
                "桜", "菜の花", "チューリップ", "芝桜", "ネモフィラ", "藤", "いちご狩り", "バラ", "あじさい", "新緑", "ポピー",
                "水遊び", "川遊び", "海", "ひまわり", "高原", "避暑", "プール", "ラベンダー", "蓮", "花火"]
SEASON_PREFS = ["関西", "大阪", "京都", "奈良", "兵庫", "滋賀", "和歌山"]
for w in SEASON_WORDS:
    for pf in SEASON_PREFS:
        THEME_SEEDS.append(f"犬連れ {w} {pf}")
    THEME_SEEDS.append(f"犬 {w} 関西")
    THEME_SEEDS.append(f"{w} 犬 OK")
    THEME_SEEDS.append(f"{w} ドッグラン")


def fetch(q):
    url = "https://suggestqueries.google.com/complete/search?client=firefox&hl=ja&q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
                return data[1] if len(data) > 1 else []
        except Exception as e:
            time.sleep(2 + attempt * 2)
    return None


def collect():
    os.makedirs(OUT_DIR, exist_ok=True)
    seeds = []
    for pref, places in PLACES.items():
        for p in places:
            for m in MODIFIERS_AFTER:
                seeds.append((pref, p, f"{p} {m}"))
            for m in MODIFIERS_BEFORE:
                seeds.append((pref, p, f"{m} {p}"))
    for s in THEME_SEEDS:
        seeds.append(("テーマ", "", s))
    # 重複除去
    seen = set(); uniq = []
    for s in seeds:
        if s[2] not in seen:
            seen.add(s[2]); uniq.append(s)
    seeds = uniq
    print(f"seeds: {len(seeds)}")
    results = []
    failed = 0
    t0 = time.time()
    for i, (pref, place, q) in enumerate(seeds, 1):
        sug = fetch(q)
        if sug is None:
            failed += 1; sug = []
        results.append({"pref": pref, "place": place, "seed": q, "suggestions": sug})
        if i % 50 == 0:
            print(f"{i}/{len(seeds)} ({time.time()-t0:.0f}s, failed={failed})")
            json.dump({"date": TODAY, "results": results}, open(RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(0.4)
    json.dump({"date": TODAY, "results": results}, open(RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"done: {len(results)} seeds, failed={failed}, {time.time()-t0:.0f}s -> {RAW}")


def load_spots():
    spots = json.load(open(os.path.join(ROOT, "data", "spots.json"), encoding="utf-8"))
    names = []
    for s in spots:
        keys = [s["name"]] + list(s.get("aliases") or [])
        names.append((s["id"], s["name"], [k for k in keys if k]))
    return names


def norm(s):
    return re.sub(r"[\s　・\-−ー〜~()（）]", "", s).lower()


def summarize():
    data = json.load(open(RAW, encoding="utf-8"))
    results = data["results"]
    spots = load_spots()
    spot_norm = [(sid, name, [norm(k) for k in keys]) for sid, name, keys in spots]

    # 一般的すぎる別名は照合に使わない（「森林公園」で和歌山と神戸が混ざる等）
    GENERIC_KEYS = {norm(x) for x in ["森林公園", "農業公園", "運動公園", "中央公園", "総合公園", "市民公園", "海浜公園",
                                       "臨海公園", "自然公園", "記念公園", "城公園", "なぎさ公園", "冒険の森", "アグリパーク",
                                       "とれとれ", "東部公園", "山麓公園", "湖岸", "ふれあい広場", "河川敷", "緑地公園",
                                       "ロングパーク", "りんくう公園", "遺跡公園", "道の駅", "公園", "ドッグラン", "海岸", "海水浴場",
                                       "キャンプ場", "牧場", "高原", "渓谷", "神社", "寺", "城", "城跡", "展望台", "温泉"]}
    def match_spot(text):
        t = norm(text)
        hits = []
        for sid, name, keys in spot_norm:
            for k in keys:
                if len(k) >= 3 and k not in GENERIC_KEYS and k in t:
                    hits.append((sid, name)); break
        return hits

    # 候補の出現回数（seedをまたいで同じ候補が出るほど強い）
    cnt = Counter(); by_pref = defaultdict(Counter); seed_of = defaultdict(set)
    for r in results:
        for s in r["suggestions"]:
            if s == r["seed"]:
                continue
            cnt[s] += 1; by_pref[r["pref"]][s] += 1; seed_of[s].add(r["seed"])
    lines = [f"# サジェスト収集 {data['date']}  seeds={len(results)} 候補={len(cnt)}", ""]
    lines.append("## 施設名・地名らしい候補（一般語を除く）と spots.json の突き合わせ")
    generic = re.compile(r"(ランチ|ディナー|カフェ|レストラン|焼肉|居酒屋|ホテル|宿|コテージ|キャンプ|温泉|旅館|求人|里親|トリミング|動物病院|ペットショップ|しつけ|保育|ホテル|譲渡|ブリーダー|散歩コース|おすすめ|人気|ランキング|ブログ|ツアー|バス|電車|レンタカー|グランピング)")
    fac = []
    for s, c in cnt.most_common():
        if generic.search(s):
            continue
        hits = match_spot(s)
        fac.append((s, c, hits))
    have = [f for f in fac if f[2]]
    lack = [f for f in fac if not f[2]]
    lines.append(f"### すでにページがある語（{len(have)}件）")
    for s, c, hits in have[:200]:
        lines.append(f"- {s}  x{c}  -> {', '.join(n for _, n in hits[:2])}")
    lines.append("")
    lines.append(f"### ページが無い語（{len(lack)}件・出現回数順）")
    for s, c, hits in lack[:400]:
        lines.append(f"- {s}  x{c}  [{'/'.join(sorted(seed_of[s]))[:80]}]")
    lines.append("")
    lines.append("## 県別の候補数")
    for pref, c in by_pref.items():
        lines.append(f"- {pref}: {sum(c.values())}件（ユニーク{len(c)}）")
    lines.append("")
    lines.append("## 生データ（seed → 候補）")
    for r in results:
        if r["suggestions"]:
            lines.append(f"- {r['seed']}: " + " / ".join(r["suggestions"]))
    open(SUMMARY, "w", encoding="utf-8").write("\n".join(lines))
    print(f"summary -> {SUMMARY}  (施設語 あり{len(have)} / なし{len(lack)})")


if __name__ == "__main__":
    if "--summary" not in sys.argv:
        collect()
    summarize()
