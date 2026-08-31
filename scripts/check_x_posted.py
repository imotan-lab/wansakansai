# -*- coding: utf-8 -*-
"""指定スポットがXに投稿済みかを投稿履歴から調べる。

★用途★ スポットを削除・非公開にする前に必ず実行する。
サイトから消してもXのポストは残り続けるため、「犬NGなのに犬連れOKとして
投稿されたまま」という状態を防ぐ（2026-08-31に信貴山 朝護孫子寺を削除した際、
ユーザーの指摘で必要性が判明した）。

Xで検索するより確実:
 - 投稿本文には「場所」しか載らない種別（危険情報）があり、本文検索では拾えない
 - 検索インデックスの遅延・表示制限に影響されない

使い方:
  python scripts/check_x_posted.py shigisan-chogosonshiji
  python scripts/check_x_posted.py 信貴山              # 名前の一部でも可
  python scripts/check_x_posted.py --all               # 履歴の全件を一覧
  python scripts/check_x_posted.py --orphans           # spots.jsonに無いのに投稿済み＝削除漏れ候補
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT = Path(__file__).resolve().parent.parent
HISTORY = PROJECT / "scripts" / "x_post_history.json"
SPOTS = PROJECT / "data" / "spots.json"


def load_history() -> list:
    if not HISTORY.is_file():
        print(f"投稿履歴が見つかりません: {HISTORY}")
        return []
    data = json.loads(HISTORY.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("posts") or data.get("history") or []


def show(items: list) -> None:
    for x in items:
        print(f"  {x.get('date', '?')[:16]}  {x.get('post_type', '?'):<14} {x.get('spot_id', '?')}")
        preview = (x.get("text_preview") or "").replace("\n", " ")[:70]
        if preview:
            print(f"      {preview}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("keyword", nargs="?", help="スポットIDまたは名前の一部")
    ap.add_argument("--all", action="store_true", help="履歴を全件表示")
    ap.add_argument("--orphans", action="store_true",
                    help="spots.jsonに存在しないのに投稿済みのスポットを表示（削除漏れ候補）")
    args = ap.parse_args()

    hist = load_history()
    if not hist:
        return 1

    if args.all:
        print(f"投稿履歴 全{len(hist)}件")
        show(hist)
        return 0

    if args.orphans:
        spots = json.loads(SPOTS.read_text(encoding="utf-8"))
        ids = {s["id"] for s in spots}
        orphans = [x for x in hist if x.get("spot_id") and x["spot_id"] not in ids]
        if not orphans:
            print("削除漏れ候補なし（投稿済みスポットはすべて掲載中）")
            return 0
        print(f"★掲載されていないのに投稿済み: {len(orphans)}件")
        print("  削除したスポットの場合、Xのポストが残っていないか確認すること")
        show(orphans)
        return 0

    if not args.keyword:
        ap.print_help()
        return 1

    kw = args.keyword
    hits = [x for x in hist
            if kw in str(x.get("spot_id", "")) or kw in str(x.get("text_preview", ""))]

    if not hits:
        print(f"「{kw}」のX投稿履歴: なし（Xに残っていないので削除して問題なし）")
        return 0

    print(f"★「{kw}」のX投稿履歴: {len(hits)}件")
    show(hits)
    print()
    print("削除する場合、Xのポストも消すか判断すること。")
    print("該当ポストは https://x.com/wansakansai から日付で探せる。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
