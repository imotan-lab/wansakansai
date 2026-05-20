"""
spots.json のうち、チェック回数が少ない順に次のチェック対象を返す。

進捗ファイル: C:\\Users\\imao_\\Documents\\wansakansai\\spot_check_progress.json
形式: { "check_counts": { "spot-id": N, ... }, "pending_layout_ids": [...], ... }

使い方:
  python scripts/get_next_check_targets.py             # 上位5件をJSONで出力
  python scripts/get_next_check_targets.py --count 5   # 件数指定
  python scripts/get_next_check_targets.py --skip 5    # 先頭N件をスキップ（後半タスク用）

ソート順:
  1) check_counts の昇順（少ない順）
  2) spots.json 内の元の順番（追加順）の昇順
"""

import argparse
import json
import sys
from pathlib import Path

SPOTS_JSON = Path(__file__).resolve().parent.parent / "data" / "spots.json"
PROGRESS_JSON = Path("C:/Users/imao_/Documents/wansakansai/spot_check_progress.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5, help="取得件数（既定: 5）")
    parser.add_argument("--skip", type=int, default=0, help="先頭からスキップする件数")
    args = parser.parse_args()

    spots = json.loads(SPOTS_JSON.read_text(encoding="utf-8"))
    progress = json.loads(PROGRESS_JSON.read_text(encoding="utf-8")) if PROGRESS_JSON.exists() else {}
    counts = progress.get("check_counts", {})

    ranked = sorted(
        enumerate(spots),
        key=lambda x: (counts.get(x[1]["id"], 0), x[0]),
    )

    selected = ranked[args.skip:args.skip + args.count]
    result = [
        {
            "index": i,
            "id": s["id"],
            "name": s["name"],
            "address": s["address"],
            "check_count": counts.get(s["id"], 0),
        }
        for i, s in selected
    ]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
