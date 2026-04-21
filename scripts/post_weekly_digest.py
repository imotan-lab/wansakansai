#!/usr/bin/env python3
"""週次まとめのX自動投稿スクリプト（日曜20時想定）。

過去7日間のサイト活動をgit logで検出し、ピックアップスポットと併せて投稿する。

- 新規スポット追加があれば言及
- 新規ブログ記事があれば言及
- ピックアップスポット: 90日以上投稿されていないスポットから1件選出

嘘を流さない原則:
- git logから実際の変更だけを抽出
- 件数はコードで数える（盛らない）
- ピックアップは季節判定込み（オフシーズンの桜スポットは除外）

使い方:
  python post_weekly_digest.py              # 実投稿
  python post_weekly_digest.py --dry-run    # 投稿せず文面確認
"""
import json
import random
import subprocess
import sys
import io
from datetime import date
from pathlib import Path

# Windowsコンソールでも絵文字を落とさず表示する
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, "C:/Users/imao_/.claude")
from x_poster import post_tweet, count_x_weight, MAX_TWEET_WEIGHT  # noqa: E402
from refresh_x_cookies import refresh_with_auto_chrome  # noqa: E402
from clear_x_cache import clear_account, human_size  # noqa: E402

from x_auto_helpers import (  # noqa: E402
    has_only_offseason_highlights,
    load_history,
    save_history,
    record_post,
    days_since_last_post,
    spot_url,
    apply_random_jitter,
    SITE_BASE,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
SPOTS_PATH = PROJECT_DIR / "data" / "spots.json"
DANGERS_PATH = PROJECT_DIR / "data" / "dangers.json"
RESULT_PATH = PROJECT_DIR / "scripts" / "x_post_result.json"

ACCOUNT = "wansakansai"


def git_added_files(days: int = 7) -> list[str]:
    """直近days日間で新規追加されたファイルパス一覧を返す。"""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--diff-filter=A",
             "--pretty=format:", "--name-only"],
            cwd=PROJECT_DIR, capture_output=True, text=True, encoding="utf-8",
            timeout=10,
        )
        return [l for l in result.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def detect_weekly_activity() -> dict:
    """過去7日間の活動を検出。"""
    added = git_added_files(7)
    new_blogs = sorted({
        l for l in added
        if l.startswith("blog/")
        and l.endswith(".html")
        and "drafts/" not in l
        and l != "blog/index.html"
    })
    return {
        "new_blogs": new_blogs,
    }


def load_spots() -> list:
    with open(SPOTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_dangers_count() -> int:
    try:
        with open(DANGERS_PATH, encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return 0


def pick_featured_spot(spots: list, history: dict, today: date) -> dict | None:
    """90日以上投稿されていないスポットからピックアップ（オフシーズン除外）。"""
    candidates = []
    for s in spots:
        if "stay-only" in s.get("tags", []):
            continue
        if has_only_offseason_highlights(s, today):
            continue
        days = days_since_last_post(history, s["id"])
        if days is None or days >= 90:
            candidates.append(s)
    if not candidates:
        return None
    return random.choice(candidates)


def build_digest_text(activity: dict, featured: dict | None,
                      total_spots: int, total_dangers: int) -> str:
    lines = []
    opening_patterns = [
        "今週のわんさかんさい",
        "今週のまとめ",
        "1週間のお知らせ",
    ]
    lines.append(random.choice(opening_patterns))
    lines.append("")

    # サイト規模
    lines.append(f"掲載スポット {total_spots}件 / 危険情報 {total_dangers}件")

    # 新規ブログ
    if activity["new_blogs"]:
        lines.append(f"新着ブログ {len(activity['new_blogs'])}本公開")

    # 今週のピックアップ
    if featured:
        lines.append("")
        lines.append(f"今週のピックアップ：{featured['name']}")
        lines.append(spot_url(featured["id"]))

    lines.append("")
    lines.append(f"サイト: {SITE_BASE}/")
    lines.append("")
    lines.append("#わんさかんさい #犬のいる暮らし #関西わんこ #犬とお出かけ")

    text = "\n".join(lines)

    # 短縮
    while count_x_weight(text) > MAX_TWEET_WEIGHT:
        # 末尾のハッシュタグを減らす、最終手段として行を省く
        if "ピックアップ" in text and featured:
            # ピックアップを短縮
            lines = [l for l in lines if not l.startswith("サイト:")]
            text = "\n".join(lines)
        else:
            break

    return text


def main():
    dry_run = "--dry-run" in sys.argv
    skip_jitter = "--no-jitter" in sys.argv

    today = date.today()
    spots = load_spots()
    history = load_history()

    print(f"=== 週次まとめ投稿 ({today}) ===")

    activity = detect_weekly_activity()
    print(f"  新規ブログ: {len(activity['new_blogs'])}本")

    featured = pick_featured_spot(spots, history, today)
    if featured:
        print(f"  ピックアップ: {featured['name']}")

    text = build_digest_text(
        activity, featured,
        total_spots=len(spots),
        total_dangers=load_dangers_count(),
    )
    print(f"\n--- 投稿文 ({count_x_weight(text)} weight) ---\n{text}\n---")

    result_data = {
        "posts": [{
            "post_type": "weekly_digest",
            "featured_spot_id": featured["id"] if featured else None,
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
        apply_random_jitter(0, 1800, label="post jitter")

    ok, msg = refresh_with_auto_chrome(ACCOUNT)
    print(f"Cookie refresh: {'OK' if ok else 'SKIP'} - {msg}")

    post_ok, post_msg = post_tweet(ACCOUNT, text)
    print(f"Post: {'OK' if post_ok else 'NG'} - {post_msg}")

    result_data["posts"][0]["success"] = post_ok
    result_data["posts"][0]["message"] = post_msg

    if post_ok and featured:
        record_post(history, featured["id"], "weekly_digest", text)
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
