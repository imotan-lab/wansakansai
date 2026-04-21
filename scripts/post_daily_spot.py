#!/usr/bin/env python3
"""今日のおすすめスポットをXに自動投稿する。

選出ロジック (B+C案):
- 過去30日以内に投稿済みのスポットは除外
- 過去60日以内はペナルティ
- シーズン中のタグを持つスポットを優先
- 季節タグのみで通年魅力が薄い & 現在オフシーズンのスポットは除外
- visited:true（写真・体験あり）は軽く優先

嘘を流さない原則:
- 桜/紅葉/水遊びシーズン外のスポットは季節フレーズを入れない
- 気象庁APIで天気確認、rainタグ+雨天時のみ雨関連フレーズを追加
- 施設情報はspots.jsonの事実のみ使用

Bot感対策:
- タスク起動時刻から0〜60分のランダム遅延
- 文面バリエーション（冒頭・中段・末尾すべてランダム選択）
- 絵文字非依存（入れないパターンも混ぜる）

使い方:
  python post_daily_spot.py              # 実投稿
  python post_daily_spot.py --dry-run    # 投稿せず候補と文面だけ出力
"""
import json
import random
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, "C:/Users/imao_/.claude")
from x_poster import post_tweet  # noqa: E402
from refresh_x_cookies import refresh_with_auto_chrome  # noqa: E402
from clear_x_cache import clear_account, human_size  # noqa: E402

from x_auto_helpers import (  # noqa: E402
    build_spot_post_text,
    detect_prefecture,
    fetch_jma_weather,
    has_only_offseason_highlights,
    is_tag_in_season,
    load_history,
    save_history,
    record_post,
    days_since_last_post,
    spot_url,
    apply_random_jitter,
    SEASONAL_ONLY_TAGS,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
SPOTS_PATH = PROJECT_DIR / "data" / "spots.json"
RESULT_PATH = PROJECT_DIR / "scripts" / "x_post_result.json"

ACCOUNT = "wansakansai"


def load_spots() -> list:
    with open(SPOTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def score_spot(spot: dict, history: dict, today: date) -> float:
    """スポットの投稿適性スコア。高いほど選ばれやすい。
    0以下は投稿対象外。"""
    # 宿泊限定施設は日常のおすすめ対象外
    if "stay-only" in spot.get("tags", []):
        return 0.0
    # 季節外の単独季節タグスポットは除外
    if has_only_offseason_highlights(spot, today):
        return 0.0

    days = days_since_last_post(history, spot["id"])
    if days is not None:
        if days < 30:
            return 0.0  # 30日以内の再投稿はNG
        elif days < 60:
            base = 0.5  # 60日以内は控えめ
        elif days < 90:
            base = 1.0
        else:
            base = 1.5
    else:
        base = 2.0  # 未投稿スポット優先

    # シーズン中の季節タグボーナス
    tags = spot.get("tags", [])
    for t in tags:
        if t in SEASONAL_ONLY_TAGS and is_tag_in_season(t, today):
            base += 3.0

    # visited優先（実訪問の強みを活かす）
    if spot.get("visited"):
        base += 0.5

    # 施設情報が充実しているスポットをわずかに優先
    dogrun = spot.get("dogRun") or {}
    if dogrun.get("available"):
        base += 0.3
    admission = (spot.get("admission") or "")
    if "無料" in admission:
        base += 0.2

    return base


def select_spot(spots: list, history: dict, today: date) -> dict | None:
    """重み付きランダムで1件選出。候補0件ならNone。"""
    scored = [(s, score_spot(s, history, today)) for s in spots]
    candidates = [(s, w) for s, w in scored if w > 0]
    if not candidates:
        return None
    spots_list, weights = zip(*candidates)
    return random.choices(spots_list, weights=weights, k=1)[0]


def main():
    dry_run = "--dry-run" in sys.argv
    skip_jitter = "--no-jitter" in sys.argv

    today = date.today()
    spots = load_spots()
    history = load_history()

    print(f"=== 今日のおすすめ投稿 ({today}) ===")
    print(f"スポット総数: {len(spots)}")
    print(f"過去投稿履歴: {len(history.get('posts', []))}件")

    spot = select_spot(spots, history, today)
    if spot is None:
        msg = "投稿可能なスポット候補がありません（全件30日以内に投稿済み or オフシーズン）"
        print(msg)
        with open(RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump({"posts": [], "message": msg}, f, ensure_ascii=False, indent=2)
        return 0

    print(f"\n選出: {spot['name']} (id={spot['id']})")
    print(f"  tags={spot.get('tags', [])}, visited={spot.get('visited', False)}")

    # 天気取得（都道府県別）
    pref = detect_prefecture(spot.get("address", ""))
    weather = fetch_jma_weather(pref) if pref else None
    if weather:
        print(f"  天気 ({pref}): {weather.get('today_weather')}")

    # 文面生成
    text = build_spot_post_text(spot, spot_url(spot["id"]), today=today, weather=weather)
    print(f"\n--- 投稿文 ---\n{text}\n---")

    if dry_run:
        with open(RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "posts": [{
                    "spot_id": spot["id"],
                    "name": spot["name"],
                    "text": text,
                    "success": None,
                    "message": "dry-run",
                }],
            }, f, ensure_ascii=False, indent=2)
        print("[dry-run] 投稿せず終了")
        return 0

    # Bot感対策: タスク起動時刻から0〜60分のランダム遅延
    if not skip_jitter:
        apply_random_jitter(0, 3600, label="post jitter")

    # Cookie refresh
    ok, msg = refresh_with_auto_chrome(ACCOUNT)
    print(f"Cookie refresh: {'OK' if ok else 'SKIP'} - {msg}")

    # 投稿
    post_ok, post_msg = post_tweet(ACCOUNT, text)
    print(f"Post: {'OK' if post_ok else 'NG'} - {post_msg}")

    # 履歴更新（成功時のみ）
    if post_ok:
        record_post(history, spot["id"], "daily_spot", text)
        save_history(history)

    # 結果保存
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "posts": [{
                "spot_id": spot["id"],
                "name": spot["name"],
                "text": text,
                "success": post_ok,
                "message": post_msg,
            }],
        }, f, ensure_ascii=False, indent=2)

    # キャッシュクリア
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
