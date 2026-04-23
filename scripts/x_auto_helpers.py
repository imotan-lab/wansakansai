#!/usr/bin/env python3
"""X自動投稿の共通ヘルパー。

- 季節ウィンドウ判定（桜/紅葉/水遊びタグのシーズン判定）
- 気象庁APIでの天気取得（嘘を流さないための確認用）
- 投稿履歴管理（30日以内の重複回避）
- 文面バリエーション生成（Bot感をなくすための表現ゆらぎ）
- 投稿前の jitter/インターバル計算
"""
import json
import random
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

sys.path.insert(0, "C:/Users/imao_/.claude")
from x_poster import count_x_weight, MAX_TWEET_WEIGHT  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent
HISTORY_PATH = PROJECT_DIR / "scripts" / "x_post_history.json"

SITE_BASE = "https://wansakansai.com"

# ---- 都道府県判定 ----
PREF_KEYWORDS = {
    "大阪": ["大阪府", "大阪", "堺", "羽曳野", "大東", "河内長野", "平野区", "西淀川", "東住吉",
            "城東", "東大阪", "豊中", "吹田", "高槻", "池田", "茨木", "枚方", "岸和田",
            "八尾", "泉大津", "松原", "柏原", "和泉", "藤井寺", "東淀川", "此花",
            "港区", "大正", "天王寺", "浪速", "西成", "旭区", "都島", "福島", "北区",
            "西区", "中央区", "住之江", "住吉", "富田林", "阪南", "泉佐野"],
    "兵庫": ["兵庫県", "神戸", "姫路", "尼崎", "明石", "西宮", "芦屋", "伊丹", "加古川", "宝塚",
            "三木", "川西", "高砂", "丹波", "小野", "加西", "養父", "朝来", "淡路"],
    "京都": ["京都府", "京都", "宇治", "舞鶴", "福知山", "綾部", "亀岡", "城陽", "向日", "長岡京",
            "八幡", "京田辺", "京丹後", "南丹", "木津川"],
    "奈良": ["奈良県", "奈良", "大和", "生駒", "橿原", "桜井", "五條", "御所", "天理", "宇陀"],
    "滋賀": ["滋賀県", "大津", "彦根", "長浜", "近江", "草津", "守山", "栗東", "甲賀", "野洲",
            "湖南", "高島", "東近江", "米原", "蒲生", "竜王"],
    "和歌山": ["和歌山県", "和歌山", "海南", "橋本", "有田", "御坊", "田辺", "新宮", "紀の川",
              "岩出", "白浜", "串本"],
}

# 気象庁のエリアコード（都道府県代表所）
JMA_AREA_CODES = {
    "大阪": "270000",
    "兵庫": "280000",
    "京都": "260000",
    "奈良": "290000",
    "滋賀": "250000",
    "和歌山": "300000",
}


def detect_prefecture(text: str) -> str | None:
    """都道府県判定。
    1段階目: 都府県の完全名（大阪府/兵庫県/京都府/奈良県/滋賀県/和歌山県）を優先
    2段階目: 市町村名のキーワードで判定
    これにより「京都府船井郡京丹波町」が「京都」と正しく判定される
    （兵庫の「丹波」で誤判定されない）
    """
    # Pass 1: 完全な都府県名を優先
    pref_full_names = {
        "和歌山県": "和歌山",  # 「和歌山市」より前に判定
        "大阪府": "大阪",
        "兵庫県": "兵庫",
        "京都府": "京都",
        "奈良県": "奈良",
        "滋賀県": "滋賀",
    }
    for full_name, pref in pref_full_names.items():
        if full_name in text:
            return pref

    # Pass 2: 市町村名等の部分一致
    for pref, keywords in PREF_KEYWORDS.items():
        for k in keywords:
            if k in text:
                return pref
    return None


# ---- 季節ウィンドウ判定 ----
# 関西基準の保守的な期間設定。嘘を流さないため早めに閉じる運用。
SEASONAL_WINDOWS = {
    # (start_month, start_day, end_month, end_day)
    "sakura": (3, 20, 4, 15),
    "koyo": (10, 25, 12, 10),
    "water": (6, 20, 9, 15),
    # rain, small-dog-only, stay-ok, stay-only は通年（オフシーズンなし）
}

SEASONAL_ONLY_TAGS = set(SEASONAL_WINDOWS.keys())  # 季節限定の魅力タグ


def is_tag_in_season(tag: str, today: date | None = None) -> bool:
    """タグが現在シーズン中か。通年タグは常にTrue。"""
    if tag not in SEASONAL_WINDOWS:
        return True
    today = today or date.today()
    sm, sd, em, ed = SEASONAL_WINDOWS[tag]
    start = date(today.year, sm, sd)
    end = date(today.year, em, ed)
    return start <= today <= end


def has_only_offseason_highlights(spot: dict, today: date | None = None) -> bool:
    """スポットの魅力が季節限定タグのみで、かつ全てオフシーズンか。

    True の場合、そのスポットを推すと「桜の名所です！」が不適切になる。
    visited:true や通年の駐車場無料などは別途スコアで評価するので、ここでは
    「季節タグのみ持ち通年魅力が薄いスポット」を弾く目的。
    """
    tags = set(spot.get("tags", []))
    seasonal_tags = tags & SEASONAL_ONLY_TAGS
    if not seasonal_tags:
        return False  # 季節タグなし → 通年OK
    # 季節タグのうち1つでもシーズン中なら False
    for t in seasonal_tags:
        if is_tag_in_season(t, today):
            return False
    # 非季節タグ（rain, small-dog-onlyなど）があれば通年魅力あり
    non_seasonal = tags - SEASONAL_ONLY_TAGS
    if non_seasonal:
        return False
    # 訪問済みなら写真・体験があるので通年OK
    if spot.get("visited"):
        return False
    return True


# ---- 気象庁API（天気取得） ----
def fetch_jma_weather(prefecture: str) -> dict | None:
    """気象庁の天気予報を取得。失敗したらNone。
    戻り値: {"today_weather": "くもり 時々 雨", "today_max_temp": 20, ...}
    """
    area = JMA_AREA_CODES.get(prefecture)
    if not area:
        return None
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area}.json"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None

    # data[0]: 短期予報、data[0]["timeSeries"][0]: 天気
    try:
        weather_ts = data[0]["timeSeries"][0]
        weather_today = weather_ts["areas"][0]["weathers"][0]
        # 正規化: 全角スペース除去
        weather_today = re.sub(r"\u3000+", " ", weather_today).strip()
        return {"today_weather": weather_today}
    except (KeyError, IndexError):
        return None


def is_rainy_weather(weather_text: str) -> bool:
    """天気テキストが雨を含むか。"""
    if not weather_text:
        return False
    return any(w in weather_text for w in ["雨", "大雨", "豪雨", "雷雨"])


# ---- 投稿履歴管理 ----
def load_history() -> dict:
    if not HISTORY_PATH.exists():
        return {"posts": []}
    with open(HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_history(history: dict):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def days_since_last_post(history: dict, spot_id: str) -> int | None:
    """スポットIDの最終投稿日から何日経過したか。未投稿ならNone。"""
    today = date.today()
    latest = None
    for p in history.get("posts", []):
        if p.get("spot_id") == spot_id:
            d = datetime.fromisoformat(p["date"]).date()
            if latest is None or d > latest:
                latest = d
    if latest is None:
        return None
    return (today - latest).days


def record_post(history: dict, spot_id: str, post_type: str, text: str):
    """投稿履歴に1件追加し、古いエントリを整理する。"""
    history.setdefault("posts", []).append({
        "spot_id": spot_id,
        "post_type": post_type,
        "date": datetime.now().isoformat(timespec="seconds"),
        "text_preview": text[:60],
    })
    # 180日以上前は削除（履歴肥大化防止）
    cutoff = date.today() - timedelta(days=180)
    history["posts"] = [
        p for p in history["posts"]
        if datetime.fromisoformat(p["date"]).date() >= cutoff
    ]


# ---- 文面バリエーション ----
# Bot感をなくすため、文体・語尾・絵文字・構造をランダムで変える。
# 嘘を流さないため、施設情報はspotデータから動的取得。

OPENING_PATTERNS = [
    "{name}（{pref}）",
    "{pref}の{name}",
    "【{name}】{pref}",
    "{name}（{pref}）を紹介します",
    "今日の一押し：{name}（{pref}）",
    "{pref}にある{name}",
]

CLOSING_PATTERNS = [
    "詳細はサイトから\n{url}",
    "詳しくはこちら\n{url}",
    "もっと見る→ {url}",
    "情報まとめ\n{url}",
    "{url}\nで詳しくチェック",
]

# 特徴説明の語尾ゆらぎ
FEATURE_STYLE = ["facts", "friendly", "mixed"]


def pick_prefecture_hashtag(pref: str | None) -> str:
    return f"#{pref}わんこ" if pref else "#関西わんこ"


def build_hashtags(spot: dict, extra: list[str] | None = None) -> str:
    tags = ["#わんさかんさい", "#犬のいる暮らし"]
    pref = detect_prefecture(spot.get("address", ""))
    tags.append(pick_prefecture_hashtag(pref))
    tags.append("#犬とお出かけ")
    if extra:
        for e in extra:
            if e not in tags:
                tags.append(e)
    return " ".join(tags[:5])  # 最大5個


def describe_features(spot: dict) -> list[str]:
    """スポットの事実情報を短文リストで返す。嘘は書かない。"""
    lines = []
    dogrun = spot.get("dogRun") or {}
    if dogrun.get("available"):
        sep = "エリア分離あり" if dogrun.get("separated") else ""
        lines.append(f"ドッグランあり{('・' + sep) if sep else ''}")
    parking = spot.get("parking") or {}
    if isinstance(parking, dict) and parking.get("available"):
        if parking.get("free"):
            lines.append("駐車場無料")
        else:
            lines.append("駐車場あり（有料）")
    admission = spot.get("admission") or {}
    if isinstance(admission, dict) and admission.get("free"):
        lines.append("入場無料")
    return lines


def maybe_seasonal_phrase(spot: dict, today: date | None = None) -> str | None:
    """シーズン中の季節タグに合う短いフレーズ。シーズン外ならNone。"""
    today = today or date.today()
    tags = spot.get("tags", [])
    if "sakura" in tags and is_tag_in_season("sakura", today):
        return "桜スポット"
    if "koyo" in tags and is_tag_in_season("koyo", today):
        return "紅葉スポット"
    if "water" in tags and is_tag_in_season("water", today):
        return "水遊びOK"
    return None


def build_spot_post_text(
    spot: dict,
    url: str,
    today: date | None = None,
    weather: dict | None = None,
    seed: int | None = None,
) -> str:
    """スポット紹介の投稿文を生成。Bot感を減らすためランダム要素入り。

    嘘を流さない原則:
    - 季節フレーズはシーズン中のみ
    - 天気フレーズは気象庁データがある場合のみ
    - 施設情報はspotデータから直接取得した事実のみ
    """
    rng = random.Random(seed) if seed is not None else random
    today = today or date.today()

    pref = detect_prefecture(spot.get("address", "")) or "関西"
    name = spot.get("name", "")

    # 冒頭
    opening = rng.choice(OPENING_PATTERNS).format(name=name, pref=pref)

    # 特徴（0〜3個をランダムに混ぜる）
    features = describe_features(spot)
    rng.shuffle(features)
    features = features[:3]

    # 季節フレーズ（シーズン中のみ）
    seasonal = maybe_seasonal_phrase(spot, today)
    if seasonal:
        features.insert(0, seasonal)

    # 特徴がなければ備考から1行
    if not features:
        remarks = (spot.get("remarks") or "").strip()
        if remarks:
            first_line = remarks.split("\n")[0].split("。")[0]
            if len(first_line) <= 40:
                features.append(first_line)

    # 天気フレーズ（rainタグ持ち & 今日が雨の日なら一言添える）
    rain_note = None
    if weather and is_rainy_weather(weather.get("today_weather", "")):
        if "rain" in spot.get("tags", []):
            rain_note = rng.choice([
                "雨の日でも楽しめる",
                "雨でも遊べる",
                "屋根ありで雨OK",
            ])

    # 本文中段の組み立て（複数パターン）
    middle_patterns = [
        "、".join(features) + "。" if features else "",
        " / ".join(features) if features else "",
        "\n".join(f"・{f}" for f in features) if len(features) >= 2 else (features[0] if features else ""),
    ]
    middle = rng.choice([m for m in middle_patterns if m]) if features else ""

    if rain_note:
        middle = f"{rain_note}。{middle}" if middle else f"{rain_note}のスポット"

    # 訪問済みなら軽い一言
    visited_note = ""
    if spot.get("visited"):
        visited_note = rng.choice([
            "\n（実際に愛犬こつぶと訪問済み）",
            "\n実際に訪問してきました",
            "",  # 入れない選択肢も
        ])

    # 末尾（URL）
    closing = rng.choice(CLOSING_PATTERNS).format(url=url)

    # ハッシュタグ（季節タグがシーズン中なら追加）
    extras = []
    if seasonal == "桜スポット":
        extras.append("#お花見")
    elif seasonal == "紅葉スポット":
        extras.append("#紅葉")
    elif seasonal == "水遊びOK":
        extras.append("#犬と水遊び")
    hashtags = build_hashtags(spot, extra=extras)

    # 組み立て
    parts = [opening]
    if middle:
        parts.append(middle)
    if visited_note.strip():
        parts.append(visited_note.strip())
    parts.append("")  # 空行
    parts.append(closing)
    parts.append("")
    parts.append(hashtags)

    text = "\n".join(parts)

    # 文字数チェック（140文字相当=280ウェイト）
    while count_x_weight(text) > MAX_TWEET_WEIGHT:
        if middle:
            # middle を削って短縮
            middle_parts = middle.rstrip("。").split("、")
            if len(middle_parts) > 1:
                middle = "、".join(middle_parts[:-1]) + "。"
            else:
                middle = ""
            parts = [opening]
            if middle:
                parts.append(middle)
            if visited_note.strip():
                parts.append(visited_note.strip())
            parts.append("")
            parts.append(closing)
            parts.append("")
            parts.append(hashtags)
            text = "\n".join(parts)
        elif visited_note:
            visited_note = ""
            parts = [opening, "", closing, "", hashtags]
            text = "\n".join(parts)
        else:
            break

    return text


def spot_url(spot_id: str) -> str:
    return f"{SITE_BASE}/spot.html?id={spot_id}"


def blog_url(slug: str) -> str:
    return f"{SITE_BASE}/blog/{slug}.html"


# ---- Bot対策ユーティリティ ----
def apply_random_jitter(min_seconds: int = 0, max_seconds: int = 1800, label: str = "jitter"):
    """投稿前にランダム待機。Bot検出対策。"""
    sec = random.randint(min_seconds, max_seconds)
    print(f"[{label}] {sec}秒待機（{sec // 60}分{sec % 60}秒）")
    time.sleep(sec)
    return sec


if __name__ == "__main__":
    # 簡易テスト
    print("# seasonal window test")
    for tag in ["sakura", "koyo", "water", "rain"]:
        print(f"  {tag}: in_season={is_tag_in_season(tag)}")

    print("\n# weather test (大阪)")
    w = fetch_jma_weather("大阪")
    print(f"  {w}")

    print("\n# sample post text")
    sample_spot = {
        "id": "umi-fureai-hiroba",
        "name": "海とのふれあい広場",
        "address": "大阪府阪南市箱作海岸",
        "parking": "無料",
        "admission": "無料",
        "dogRun": {"available": True, "separated": True},
        "tags": ["rain"],
        "visited": True,
        "remarks": "阪南市の海沿いにある犬連れ歓迎の広場",
    }
    for seed in range(3):
        text = build_spot_post_text(sample_spot, spot_url(sample_spot["id"]), seed=seed)
        print(f"\n--- seed={seed} ({count_x_weight(text)} weight) ---")
        print(text)
