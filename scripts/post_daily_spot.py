#!/usr/bin/env python3
"""今日のおすすめスポットをXに自動投稿する。

選出ロジック（2026-09-25改定。詳しくは score_spot の上の説明）:
- 検索の需要（Search Console のページ別表示回数）が多いスポットと、写真のあるスポットを中心に選ぶ
- 過去30日以内に投稿済みのスポットは除外。その後も間隔が短いほど当たりにくい（掛け算）
- シーズン中の季節タグを持つスポットを優先。季節タグだけで季節外のスポットは、需要か写真がある時だけ出す
- 直前の投稿と同じ府県は当たりにくい
- 試し抽選: python post_daily_spot.py --simulate 90（投稿も履歴の書き換えもしない）
  2026-09-25の90日試算（8回平均）: 表示300回以上か写真ありのスポットが約7割、表示50回未満が約2.5割、
  違うスポット約87/90、同じスポットは最多2回

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


# ★選び方（2026-09-25改定・運営者の依頼）★
# 「需要のありそうなところを中心に、でも同じ場所ばかりにならないように」。
#   点数 = 間隔の係数 × (1 + 需要 + 写真 + 訪問済み + 旬の季節タグ + 施設) × 府県の散らし
# - 需要: Search Console のページ別の表示回数（直近3か月・週次SEOタスクが毎週更新）。対数で効かせ、上限を置く
#   （一部の人気スポットだけが毎回当たるのを防ぐ）
# - 写真: 写真があるとXのリンクカードにその写真が出る（無いとサイトのロゴ画像）。運営者が需要を見て撮りに行った場所でもある
# - 間隔は足し算でなく掛け算。人気のスポットでも最後の投稿から間がないうちは当たりにくい
#   （30日以内は出さない／30〜59日は1/4／60〜89日は1/2／90日以上は3/4／未投稿は1）
# - 府県の散らし: 直前の投稿（おすすめ・新スポット）と同じ府県は0.6倍
DEMAND_PATH = Path("C:/Users/imao_/Documents/wansakansai/spot_demand.json")
DEMAND_SCALE = 50      # 表示回数をこの数で割ってから対数をとる
DEMAND_WEIGHT = 2.0
DEMAND_CAP = 4.0
PHOTO_BONUS = 3.0
VISITED_BONUS = 0.5
SEASON_BONUS = 3.0
SAME_PREF_FACTOR = 0.6
OFFSEASON_DEMAND_MIN = 300  # 季節外でもこれ以上表示されていれば出す（直近3か月の表示回数）


def load_demand() -> dict:
    """スポットID → 表示回数。ファイルが無い・読めない時は空（需要なしで今までどおり選ぶ）。"""
    try:
        d = json.loads(DEMAND_PATH.read_text(encoding="utf-8"))
        return {sid: int(v.get("impressions", 0)) for sid, v in d.get("spots", {}).items()}
    except Exception as e:  # 需要が読めなくても投稿は止めない
        print(f"[demand] 読めないので需要なしで選ぶ: {type(e).__name__}: {e}")
        return {}


def demand_bonus(impressions: int) -> float:
    import math
    if impressions <= 0:
        return 0.0
    return min(DEMAND_CAP, DEMAND_WEIGHT * math.log10(1 + impressions / DEMAND_SCALE))


def interval_factor(days) -> float:
    if days is None:
        return 1.0
    if days < 30:
        return 0.0
    if days < 60:
        return 0.25
    if days < 90:
        return 0.5
    return 0.75


def last_posted_pref(history: dict, spots_by_id: dict) -> str:
    """直前に投稿したスポット（おすすめ・新スポット）の府県。"""
    for p in reversed(history.get("posts", [])):
        if p.get("post_type") in ("daily_spot", "new_spot") and p.get("spot_id") in spots_by_id:
            return detect_prefecture(spots_by_id[p["spot_id"]].get("address", "")) or ""
    return ""


def score_spot(spot: dict, history: dict, today: date, demand: dict = None, prev_pref: str = "") -> float:
    """スポットの投稿適性スコア。高いほど選ばれやすい。0以下は投稿対象外。"""
    # 宿泊限定施設は日常のおすすめ対象外
    if "stay-only" in spot.get("tags", []):
        return 0.0
    # 季節外の単独季節タグスポットは除外。ただし検索で見られている（需要あり）か写真があるなら出す
    # （綾川千本桜は夏の3か月でも3,716回表示されていた。文面は季節外なら季節の言葉を入れないので嘘にならない）
    if has_only_offseason_highlights(spot, today):
        if not ((demand or {}).get(spot["id"], 0) >= OFFSEASON_DEMAND_MIN or spot.get("images")):
            return 0.0

    factor = interval_factor(days_since_last_post(history, spot["id"]))
    if factor <= 0:
        return 0.0

    value = 1.0
    value += demand_bonus((demand or {}).get(spot["id"], 0))
    if spot.get("images"):
        value += PHOTO_BONUS
    if spot.get("visited"):
        value += VISITED_BONUS
    for t in spot.get("tags", []):
        if t in SEASONAL_ONLY_TAGS and is_tag_in_season(t, today):
            value += SEASON_BONUS
    # 施設情報が充実しているスポットをわずかに優先
    if (spot.get("dogRun") or {}).get("available"):
        value += 0.3
    if (spot.get("admission") or {}).get("free"):
        value += 0.2

    score = factor * value
    if prev_pref and detect_prefecture(spot.get("address", "")) == prev_pref:
        score *= SAME_PREF_FACTOR
    return score


def select_spot(spots: list, history: dict, today: date, demand: dict = None) -> dict | None:
    """重み付きランダムで1件選出。候補0件ならNone。"""
    prev_pref = last_posted_pref(history, {s["id"]: s for s in spots})
    scored = [(s, score_spot(s, history, today, demand, prev_pref)) for s in spots]
    candidates = [(s, w) for s, w in scored if w > 0]
    if not candidates:
        return None
    spots_list, weights = zip(*candidates)
    return random.choices(spots_list, weights=weights, k=1)[0]


def simulate(spots: list, history: dict, demand: dict, days: int, seed: int = 0) -> int:
    """投稿せずに、今日から days 日ぶん選び続けた場合の偏りを出す（履歴ファイルは書き換えない）。"""
    import copy
    from collections import Counter
    from datetime import timedelta
    random.seed(seed)
    h = copy.deepcopy(history)
    start = date.today()
    picks = []
    for i in range(days):
        d = start + timedelta(days=i)
        # days_since_last_post は date.today() 基準なので、日付をずらす代わりに履歴の日付を1日ずつ古くする
        if i:
            for p in h["posts"]:
                p["date"] = (datetime.fromisoformat(p["date"]) - timedelta(days=1)).isoformat(timespec="seconds")
        s = select_spot(spots, h, d, demand)
        if not s:
            break
        picks.append(s)
        h["posts"].append({"spot_id": s["id"], "post_type": "daily_spot", "date": datetime.now().isoformat(timespec="seconds"), "text_preview": ""})
    ids = [s["id"] for s in picks]
    n = len(picks)
    print(f"=== {days}日ぶんの試し抽選（seed={seed}）===")
    print(f"表示300回以上か写真あり: {sum(1 for s in picks if demand.get(s['id'], 0) >= 300 or s.get('images'))}/{n}  "
          f"表示1000回以上: {sum(1 for x in ids if demand.get(x, 0) >= 1000)}/{n}  写真あり: {sum(1 for s in picks if s.get('images'))}/{n}  "
          f"表示50回未満: {sum(1 for x in ids if demand.get(x, 0) < 50)}/{n}")
    print(f"違うスポット: {len(set(ids))}/{n}  2回以上: {[k for k, v in Counter(ids).items() if v > 1]}")
    prefs = [detect_prefecture(s.get('address', '')) for s in picks]
    print(f"府県: {dict(Counter(prefs))}  前日と同じ府県: {sum(1 for a, b in zip(prefs, prefs[1:]) if a == b)}/{n - 1}")
    print("最初の20日:", " ".join(ids[:20]))
    return 0


def main():
    dry_run = "--dry-run" in sys.argv
    skip_jitter = "--no-jitter" in sys.argv

    today = date.today()
    spots = load_spots()
    history = load_history()
    demand = load_demand()

    if "--simulate" in sys.argv:
        n = int(sys.argv[sys.argv.index("--simulate") + 1]) if len(sys.argv) > sys.argv.index("--simulate") + 1 else 90
        return simulate(spots, history, demand, n, seed=int(today.strftime("%Y%m%d")))

    print(f"=== 今日のおすすめ投稿 ({today}) ===")
    print(f"スポット総数: {len(spots)}")
    print(f"過去投稿履歴: {len(history.get('posts', []))}件")
    print(f"需要データ: {len(demand)}件")

    spot = select_spot(spots, history, today, demand)
    if spot is None:
        msg = "投稿可能なスポット候補がありません（全件30日以内に投稿済み or オフシーズン）"
        print(msg)
        with open(RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump({"posts": [], "message": msg}, f, ensure_ascii=False, indent=2)
        return 0

    print(f"\n選出: {spot['name']} (id={spot['id']})")
    print(f"  tags={spot.get('tags', [])}, visited={spot.get('visited', False)}, "
          f"写真={len(spot.get('images') or [])}枚, 需要(表示回数)={demand.get(spot['id'], 0)}")

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
    result_data = {
        "posts": [{
            "spot_id": spot["id"],
            "name": spot["name"],
            "text": text,
            "success": post_ok,
            "message": post_msg,
        }],
    }
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    # 失敗時は日付付きで永続保存（後日の調査用、dry-runでも上書きされない）
    if not post_ok:
        from datetime import datetime
        fail_path = PROJECT_DIR / "scripts" / f"x_post_fail_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"失敗詳細を保存: {fail_path}")

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
