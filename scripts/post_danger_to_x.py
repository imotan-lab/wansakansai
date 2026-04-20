#!/usr/bin/env python3
"""
危険情報のX自動投稿スクリプト

data/dangers.json と scripts/dangers_prev.json を比較し、
追加・更新されたエントリのみXに投稿する。削除は投稿しない。

投稿結果は scripts/x_post_result.json に保存。
タスクはそれをメール通知に渡す。

使い方:
  python post_danger_to_x.py                # 実投稿
  python post_danger_to_x.py --dry-run      # 投稿せず文面だけ出力
"""

import json
import sys
from pathlib import Path

# x_poster.py を import パスに追加
sys.path.insert(0, "C:/Users/imao_/.claude")
from x_poster import post_tweet, count_x_weight, MAX_TWEET_WEIGHT  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent
DANGERS_PATH = PROJECT_DIR / "data" / "dangers.json"
PREV_PATH = PROJECT_DIR / "scripts" / "dangers_prev.json"
RESULT_PATH = PROJECT_DIR / "scripts" / "x_post_result.json"

ACCOUNT = "wansakansai"
SITE_URL = "https://wansakansai.com/danger.html"

# locationキーワード → 都道府県 のマッピング
PREF_KEYWORDS = {
    "大阪": ["大阪", "堺", "羽曳野", "大東", "河内長野", "平野区", "西淀川", "東住吉",
            "城東", "東大阪", "豊中", "吹田", "高槻", "池田", "茨木", "枚方", "岸和田",
            "八尾", "泉大津", "松原", "柏原", "和泉", "藤井寺", "東淀川", "此花",
            "港区", "大正", "天王寺", "浪速", "西成", "旭区", "都島", "福島", "北区",
            "西区", "中央区", "住之江", "住吉"],
    "兵庫": ["神戸", "姫路", "尼崎", "明石", "西宮", "芦屋", "伊丹", "加古川", "宝塚",
            "三木", "川西", "高砂", "丹波", "小野", "加西", "養父", "朝来", "淡路"],
    "京都": ["京都", "宇治", "舞鶴", "福知山", "綾部", "亀岡", "城陽", "向日", "長岡京",
            "八幡", "京田辺", "京丹後", "南丹", "木津川"],
    "奈良": ["奈良", "大和", "生駒", "橿原", "桜井", "五條", "御所", "天理", "宇陀"],
    "滋賀": ["大津", "彦根", "長浜", "近江", "草津", "守山", "栗東", "甲賀", "野洲",
            "湖南", "高島", "東近江", "米原"],
    "和歌山": ["和歌山", "海南", "橋本", "有田", "御坊", "田辺", "新宮", "紀の川",
              "岩出", "白浜", "串本"],
}


def detect_prefecture(location: str) -> str | None:
    for pref, keywords in PREF_KEYWORDS.items():
        for k in keywords:
            if k in location:
                return pref
    return None


def build_hashtags(entry: dict) -> str:
    tags = ["#わんさかんさい", "#犬のいる暮らし"]
    pref = detect_prefecture(entry.get("location", ""))
    tags.append(f"#{pref}わんこ" if pref else "#関西わんこ")
    tags.append("#犬の安全")
    if "毒餌" in entry.get("type", ""):
        tags.append("#毒餌注意")
    return " ".join(tags)


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def diff_entries(current: list, prev: list):
    """(added, updated) を返す。削除は無視。"""
    prev_by_id = {e["id"]: e for e in prev}
    added, updated = [], []
    for e in current:
        p = prev_by_id.get(e["id"])
        if p is None:
            added.append(e)
        elif p.get("description") != e.get("description") or p.get("location") != e.get("location") or p.get("type") != e.get("type"):
            updated.append(e)
    return added, updated


def build_post_text(entry: dict, change_type: str) -> str:
    """危険情報エントリから投稿本文を生成（入口として最低限の情報）。"""
    location = entry.get("location", "")
    type_ = entry.get("type", "")
    hashtags = build_hashtags(entry)

    def build(loc: str) -> str:
        return (
            f"【危険情報{change_type}】\n"
            f"{loc}\n"
            f"種別: {type_}\n\n"
            f"詳しくはサイトをご覧ください\n"
            f"{SITE_URL}\n\n"
            f"{hashtags}"
        )

    # location が長すぎる場合のみ切り詰める
    while count_x_weight(build(location)) > MAX_TWEET_WEIGHT and len(location) > 10:
        location = location[:-1]
    if count_x_weight(build(location)) > MAX_TWEET_WEIGHT:
        location = location.rstrip("・、,") + "…"

    return build(location)


def main():
    dry_run = "--dry-run" in sys.argv

    current = load_json(DANGERS_PATH, [])
    prev = load_json(PREV_PATH, None)

    # 初回実行: prev がなければ現在値をコピーして終了（全件を新規扱いしない）
    if prev is None:
        save_json(PREV_PATH, current)
        save_json(RESULT_PATH, {"initialized": True, "posts": []})
        print("初回実行: dangers_prev.json を初期化しました（投稿なし）")
        return 0

    added, updated = diff_entries(current, prev)

    targets = [(e, "追加") for e in added] + [(e, "更新") for e in updated]

    if not targets:
        save_json(RESULT_PATH, {"posts": []})
        print("投稿対象なし")
        # prev を最新で上書き（削除や順序変更だけだった場合も追従）
        save_json(PREV_PATH, current)
        return 0

    posts = []
    for entry, change_type in targets:
        text = build_post_text(entry, change_type)
        if dry_run:
            posts.append({
                "id": entry["id"],
                "change_type": change_type,
                "location": entry.get("location", ""),
                "text": text,
                "success": None,
                "message": "dry-run",
            })
            print(f"--- [{change_type}] {entry['id']} ---")
            print(text)
            print()
            continue

        ok, msg = post_tweet(ACCOUNT, text)
        posts.append({
            "id": entry["id"],
            "change_type": change_type,
            "location": entry.get("location", ""),
            "text": text,
            "success": ok,
            "message": msg,
        })
        print(f"[{change_type}] {entry['id']}: {'OK' if ok else 'NG'} - {msg}")

    save_json(RESULT_PATH, {"posts": posts})

    # 実投稿モードなら prev を更新（次回以降の差分基準にする）
    if not dry_run:
        save_json(PREV_PATH, current)

    return 0


if __name__ == "__main__":
    sys.exit(main())
