#!/usr/bin/env python3
"""新規スポット追加時の自動X投稿スクリプト。

スポット追加ワークフローから呼び出す想定。スポットID指定で実行すると、
そのスポットの紹介文を投稿する。

使い方:
  python post_new_spot.py <spot_id>              # 実投稿
  python post_new_spot.py <spot_id> --dry-run    # 投稿せず本文確認

嘘を流さない原則:
- 季節フレーズはシーズン中のみ挿入（post_daily_spot.py と同じロジック）
- 施設情報は spots.json の事実のみ
- 天気は気象庁API確認済みのみ

Bot感対策:
- 「新スポット」プレフィックスでdaily投稿とは異なる構文
- 文面バリエーション
- 投稿前のランダム遅延（短め: 5〜20分）
"""
import json
import sys
import random
from datetime import date
from pathlib import Path

sys.path.insert(0, "C:/Users/imao_/.claude")
from x_poster import post_tweet, count_x_weight, MAX_TWEET_WEIGHT  # noqa: E402
from refresh_x_cookies import refresh_with_auto_chrome  # noqa: E402
from clear_x_cache import clear_account, human_size  # noqa: E402

from x_auto_helpers import (  # noqa: E402
    describe_features,
    detect_prefecture,
    fetch_jma_weather,
    is_rainy_weather,
    is_tag_in_season,
    load_history,
    save_history,
    record_post,
    spot_url,
    build_hashtags,
    maybe_seasonal_phrase,
    apply_random_jitter,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
SPOTS_PATH = PROJECT_DIR / "data" / "spots.json"
RESULT_PATH = PROJECT_DIR / "scripts" / "x_post_result.json"

ACCOUNT = "wansakansai"

NEW_SPOT_OPENINGS = [
    "【新スポット追加】\n{name}（{pref}）",
    "新しいスポットを追加しました🐕\n{name}（{pref}）",
    "スポット追加のお知らせ\n{name}（{pref}）",
    "{pref}の{name}を新スポットとして追加",
]

NEW_SPOT_CLOSINGS = [
    "詳しくはこちら\n{url}",
    "詳細→ {url}",
    "こちらから見られます\n{url}",
    "{url}",
]


def load_spots() -> list:
    with open(SPOTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_new_spot_text(spot: dict, url: str, today: date | None = None,
                        weather: dict | None = None) -> str:
    today = today or date.today()
    pref = detect_prefecture(spot.get("address", "")) or "関西"
    name = spot.get("name", "")

    opening = random.choice(NEW_SPOT_OPENINGS).format(name=name, pref=pref)

    features = describe_features(spot)
    random.shuffle(features)
    seasonal = maybe_seasonal_phrase(spot, today)
    if seasonal:
        features.insert(0, seasonal)
    features = features[:3]

    if weather and is_rainy_weather(weather.get("today_weather", "")):
        if "rain" in spot.get("tags", []):
            features.insert(0, "雨の日でもOK")

    middle = "、".join(features) + "。" if features else ""

    closing = random.choice(NEW_SPOT_CLOSINGS).format(url=url)

    extras = []
    if seasonal == "桜スポット":
        extras.append("#お花見")
    elif seasonal == "紅葉スポット":
        extras.append("#紅葉")
    elif seasonal == "水遊びOK":
        extras.append("#犬と水遊び")
    hashtags = build_hashtags(spot, extra=extras)

    parts = [opening]
    if middle:
        parts.append(middle)
    parts.append("")
    parts.append(closing)
    parts.append("")
    parts.append(hashtags)
    text = "\n".join(parts)

    # 短縮
    while count_x_weight(text) > MAX_TWEET_WEIGHT and features:
        features = features[:-1]
        middle = "、".join(features) + "。" if features else ""
        parts = [opening]
        if middle:
            parts.append(middle)
        parts.append("")
        parts.append(closing)
        parts.append("")
        parts.append(hashtags)
        text = "\n".join(parts)

    return text


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    spot_id = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    skip_jitter = "--no-jitter" in sys.argv

    spots = load_spots()
    spot = next((s for s in spots if s.get("id") == spot_id), None)
    if spot is None:
        print(f"ERROR: spot_id={spot_id} が spots.json に見つかりません")
        return 1

    print(f"=== 新規スポット投稿: {spot['name']} ===")

    pref = detect_prefecture(spot.get("address", ""))
    weather = fetch_jma_weather(pref) if pref else None
    if weather:
        print(f"  天気 ({pref}): {weather.get('today_weather')}")

    text = build_new_spot_text(spot, spot_url(spot["id"]), weather=weather)
    print(f"\n--- 投稿文 ({count_x_weight(text)} weight) ---\n{text}\n---")

    result_data = {
        "posts": [{
            "spot_id": spot["id"],
            "name": spot["name"],
            "post_type": "new_spot",
            "text": text,
        }],
    }

    if dry_run:
        result_data["posts"][0]["success"] = None
        result_data["posts"][0]["message"] = "dry-run"
        with open(RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print("[dry-run] 投稿せず終了")
        return 0

    # 短めジッター（5〜20分）
    if not skip_jitter:
        apply_random_jitter(300, 1200, label="post jitter")

    ok, msg = refresh_with_auto_chrome(ACCOUNT)
    print(f"Cookie refresh: {'OK' if ok else 'SKIP'} - {msg}")

    post_ok, post_msg = post_tweet(ACCOUNT, text)
    print(f"Post: {'OK' if post_ok else 'NG'} - {post_msg}")

    result_data["posts"][0]["success"] = post_ok
    result_data["posts"][0]["message"] = post_msg

    if post_ok:
        history = load_history()
        record_post(history, spot["id"], "new_spot", text)
        save_history(history)

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    if post_ok:
        try:
            r = clear_account(ACCOUNT)
            if r["skipped"]:
                print(f"Cache clear: SKIP ({r['reason']})")
            else:
                print(f"Cache clear: OK ({human_size(r['freed_bytes'])} 解放)")
        except Exception as e:
            print(f"Cache clear: ERR ({type(e).__name__}: {e})")

    return 0 if post_ok else 1


if __name__ == "__main__":
    sys.exit(main())
