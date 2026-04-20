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
from x_poster import post_tweet, MAX_TWEET_LENGTH  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parent.parent
DANGERS_PATH = PROJECT_DIR / "data" / "dangers.json"
PREV_PATH = PROJECT_DIR / "scripts" / "dangers_prev.json"
RESULT_PATH = PROJECT_DIR / "scripts" / "x_post_result.json"

ACCOUNT = "wansakansai"
SITE_URL = "https://wansakansai.com/danger.html"


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
    """危険情報エントリから投稿本文を生成。280字以内に収める。"""
    location = entry.get("location", "")
    type_ = entry.get("type", "")
    description = entry.get("description", "")

    header = f"【危険情報{change_type}】\n{location}\n種別: {type_}\n\n"
    footer = f"\n\n詳細: {SITE_URL}\n#わんさかんさい #犬連れお出かけ #関西"

    available = MAX_TWEET_LENGTH - len(header) - len(footer)
    if available < 30:
        # location が長すぎる等の異常系。locationを切り詰める
        location = location[:40] + "…"
        header = f"【危険情報{change_type}】\n{location}\n種別: {type_}\n\n"
        available = MAX_TWEET_LENGTH - len(header) - len(footer)

    if len(description) > available:
        description = description[: max(available - 1, 0)] + "…"

    return header + description + footer


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
