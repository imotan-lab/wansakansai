"""
スポットのチェック回数を進捗ファイルで +1 する。

進捗ファイル: C:\\Users\\imao_\\Documents\\wansakansai\\spot_check_progress.json

使い方:
  python scripts/update_check_count.py --ids "spot-id-1,spot-id-2,..."
  python scripts/update_check_count.py --ids "..." --pending-add "id3,id4"   # レイアウトチェックpendingに追加
  python scripts/update_check_count.py --ids "..." --pending-clear           # pending全クリア
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROGRESS_JSON = Path("C:/Users/imao_/Documents/wansakansai/spot_check_progress.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", required=True, help="チェック完了した spot id のカンマ区切りリスト")
    parser.add_argument("--pending-add", default="", help="レイアウトpendingに追加するid（カンマ区切り）")
    parser.add_argument("--pending-clear", action="store_true", help="レイアウトpendingを空にする")
    args = parser.parse_args()

    if PROGRESS_JSON.exists():
        progress = json.loads(PROGRESS_JSON.read_text(encoding="utf-8"))
    else:
        progress = {}

    counts = progress.setdefault("check_counts", {})
    ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    for sid in ids:
        counts[sid] = counts.get(sid, 0) + 1

    if args.pending_clear:
        progress["pending_layout_ids"] = []
    if args.pending_add:
        existing = set(progress.get("pending_layout_ids", []))
        for sid in args.pending_add.split(","):
            sid = sid.strip()
            if sid:
                existing.add(sid)
        progress["pending_layout_ids"] = sorted(existing)

    progress["last_date"] = datetime.now().strftime("%Y-%m-%d")

    PROGRESS_JSON.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"updated counts for {len(ids)} spots: {','.join(ids)}")
    if args.pending_clear:
        print("cleared pending_layout_ids")
    if args.pending_add:
        print(f"added to pending_layout_ids: {args.pending_add}")


if __name__ == "__main__":
    main()
