#!/usr/bin/env python3
"""季節特集のX自動投稿スクリプト（手動トリガー想定）。

季節の変わり目に該当タグのスポットを3〜5件ピックアップしてまとめ投稿する。

使い方:
  python post_seasonal_feature.py sakura          # 桜スポット特集
  python post_seasonal_feature.py koyo            # 紅葉スポット特集
  python post_seasonal_feature.py water           # 水遊びスポット特集
  python post_seasonal_feature.py rain            # 雨OKスポット特集（梅雨入り時など）
  python post_seasonal_feature.py <tag> --dry-run

嘘を流さない原則:
- シーズン外の季節タグは明示しない限り警告して実行を止める（--force で回避）
- 実際にタグを持つスポットのみ紹介
- 件数は実データで数える

Bot感対策:
- 複数スポットを箇条書きで1投稿にまとめる（連投しない）
- 冒頭・末尾にランダムバリエーション
"""
import json
import random
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, "C:/Users/imao_/.claude")
from x_poster import post_tweet, count_x_weight, MAX_TWEET_WEIGHT  # noqa: E402
from refresh_x_cookies import refresh_with_auto_chrome  # noqa: E402
from clear_x_cache import clear_account, human_size  # noqa: E402

from x_auto_helpers import (  # noqa: E402
    detect_prefecture,
    is_tag_in_season,
    load_history,
    save_history,
    record_post,
    apply_random_jitter,
    SITE_BASE,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
SPOTS_PATH = PROJECT_DIR / "data" / "spots.json"
RESULT_PATH = PROJECT_DIR / "scripts" / "x_post_result.json"

ACCOUNT = "wansakansai"

TAG_LABELS = {
    "sakura": {
        "label": "桜",
        "headline_patterns": [
            "【桜シーズン】関西の犬連れお花見スポット",
            "犬と楽しむ関西のお花見スポット",
            "お花見シーズン到来！関西の桜と犬連れ",
        ],
        "hashtags": ["#お花見", "#犬のお花見", "#桜"],
    },
    "koyo": {
        "label": "紅葉",
        "headline_patterns": [
            "【紅葉シーズン】関西の犬連れ紅葉スポット",
            "犬と秋を感じる関西の紅葉スポット",
            "紅葉が見頃！関西の犬連れおすすめ",
        ],
        "hashtags": ["#紅葉", "#犬と紅葉"],
    },
    "water": {
        "label": "水遊び",
        "headline_patterns": [
            "【夏】関西の犬と水遊びできるスポット",
            "暑さ対策に！犬と水遊びできる関西",
            "夏本番！関西で犬と涼めるスポット",
        ],
        "hashtags": ["#犬と水遊び", "#夏のお出かけ"],
    },
    "rain": {
        "label": "雨でもOK",
        "headline_patterns": [
            "【梅雨対策】雨の日でも犬と楽しめる関西",
            "雨の日でもOK！関西の犬連れスポット",
            "雨天でも大丈夫な関西の犬連れスポット",
        ],
        "hashtags": ["#雨の日のお出かけ", "#屋根ありドッグラン"],
    },
}


def load_spots() -> list:
    with open(SPOTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def select_feature_spots(spots: list, tag: str, history: dict, today: date,
                          max_count: int = 5) -> list:
    """指定タグを持つスポットからピックアップ。過去30日投稿済みは優先度低下。"""
    matching = [s for s in spots if tag in s.get("tags", [])
                and "stay-only" not in s.get("tags", [])]
    # visited優先、次に未投稿/古い投稿
    def sort_key(s):
        visited_bonus = 10 if s.get("visited") else 0
        posts = history.get("posts", [])
        last_days = None
        for p in posts:
            if p.get("spot_id") == s["id"]:
                d = p.get("date", "")
                if d:
                    from datetime import datetime
                    last_days = (today - datetime.fromisoformat(d).date()).days
                    break
        recency_penalty = 0 if last_days is None or last_days > 30 else -5
        # ランダム性も少し入れる
        rand = random.random()
        return -(visited_bonus + recency_penalty + rand)
    matching.sort(key=sort_key)
    return matching[:max_count]


def build_feature_text(tag: str, selected: list) -> str:
    conf = TAG_LABELS[tag]
    headline = random.choice(conf["headline_patterns"])

    # 各スポットを "- スポット名（都道府県）" 形式で
    lines = [headline, ""]
    for s in selected:
        pref = detect_prefecture(s.get("address", "")) or "関西"
        lines.append(f"・{s.get('name')}（{pref}）")

    lines.append("")
    lines.append(f"詳細は{SITE_BASE}")
    lines.append("")

    base_tags = ["#わんさかんさい", "#犬のいる暮らし", "#関西わんこ"]
    hashtags = " ".join(base_tags + conf["hashtags"][:2])
    lines.append(hashtags)

    text = "\n".join(lines)

    # 文字数オーバーなら末尾のスポットから削る
    while count_x_weight(text) > MAX_TWEET_WEIGHT and len(selected) > 2:
        selected = selected[:-1]
        lines = [headline, ""]
        for s in selected:
            pref = detect_prefecture(s.get("address", "")) or "関西"
            lines.append(f"・{s.get('name')}（{pref}）")
        lines.append("")
        lines.append(f"詳細は{SITE_BASE}")
        lines.append("")
        lines.append(hashtags)
        text = "\n".join(lines)

    return text


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    tag = sys.argv[1]
    if tag not in TAG_LABELS:
        print(f"ERROR: 未対応のタグ: {tag}")
        print(f"利用可能: {', '.join(TAG_LABELS.keys())}")
        return 1

    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    skip_jitter = "--no-jitter" in sys.argv

    today = date.today()

    # シーズン判定（rainは通年なのでスキップしない）
    if tag in ["sakura", "koyo", "water"] and not is_tag_in_season(tag, today):
        if not force:
            print(f"WARNING: {TAG_LABELS[tag]['label']}は現在オフシーズンです。")
            print("  --force で強制実行できます")
            return 1
        print(f"[--force] オフシーズンですが実行します")

    spots = load_spots()
    history = load_history()

    selected = select_feature_spots(spots, tag, history, today, max_count=5)
    if not selected:
        print(f"ERROR: {tag}タグを持つスポットが見つかりません")
        return 1

    print(f"=== 季節特集投稿: {TAG_LABELS[tag]['label']} ===")
    print(f"  選出スポット数: {len(selected)}")
    for s in selected:
        print(f"    ・{s['name']}")

    text = build_feature_text(tag, selected)
    print(f"\n--- 投稿文 ({count_x_weight(text)} weight) ---\n{text}\n---")

    result_data = {
        "posts": [{
            "post_type": f"seasonal_feature_{tag}",
            "spot_ids": [s["id"] for s in selected],
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

    if not skip_jitter:
        apply_random_jitter(0, 600, label="post jitter")  # 手動実行なので短め

    ok, msg = refresh_with_auto_chrome(ACCOUNT)
    print(f"Cookie refresh: {'OK' if ok else 'SKIP'} - {msg}")

    post_ok, post_msg = post_tweet(ACCOUNT, text)
    print(f"Post: {'OK' if post_ok else 'NG'} - {post_msg}")

    result_data["posts"][0]["success"] = post_ok
    result_data["posts"][0]["message"] = post_msg

    if post_ok:
        for s in selected:
            record_post(history, s["id"], f"seasonal_{tag}", text[:100])
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
