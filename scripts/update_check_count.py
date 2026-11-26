"""
スポットのチェック回数を進捗ファイルで +1 する。

進捗ファイル: C:\\Users\\imao_\\Documents\\wansakansai\\spot_check_progress.json

使い方:
  python scripts/update_check_count.py --ids "spot-id-1,spot-id-2,..."
  python scripts/update_check_count.py --ids "..." --pending-add "id3,id4"   # レイアウトチェックpendingに追加
  python scripts/update_check_count.py --ids "..." --pending-clear           # pending全クリア
  python scripts/update_check_count.py --ids "..." --season-done "id1" --season-wait "id2"
      # シーズン前の見直しの結果（season_check が付いたスポットだけ。期間外・タグ違いは書かずに知らせる）
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
    parser.add_argument("--season-done", default="", help="今年の季節の決まりを確かめ終えたid（カンマ区切り）")
    parser.add_argument("--season-wait", default="", help="今年の発表がまだ無い・調べきれなかったid（カンマ区切り）")
    parser.add_argument("--progress", default=None, help="進捗ファイルのパスを上書き（試験用）")
    parser.add_argument("--today", default=None, help="今日の日付 YYYY-MM-DD を上書き（試験用）")
    args = parser.parse_args()
    global PROGRESS_JSON
    if args.progress:
        PROGRESS_JSON = Path(args.progress)

    if PROGRESS_JSON.exists():
        progress = json.loads(PROGRESS_JSON.read_text(encoding="utf-8"))
    else:
        progress = {}

    # 壊れた形（null・配列など）でも止まらないように、辞書でなければ作り直す
    for key in ("check_counts", "last_checked"):
        if not isinstance(progress.get(key), dict):
            if key in progress:
                print(f"[warn] 進捗ファイルの {key} が辞書でないので作り直す: {type(progress.get(key)).__name__}")
            progress[key] = {}
    counts = progress.setdefault("check_counts", {})
    # ★最後に見た日も残す（2026-09-20追加）★
    # 期限付き情報の再確認は期限の14日前から毎日割り込んでいたが、同じ公式ページを
    # 毎日見て「延長も中止もなし」を確かめるだけで1日5件の枠を食っていた。
    # get_next_check_targets.py が「前回から3日空いていなければ割り込ませない」判断に使う。
    last = progress.setdefault("last_checked", {})
    today_str = args.today or datetime.now().strftime("%Y-%m-%d")
    ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    for sid in ids:
        counts[sid] = (counts.get(sid) if isinstance(counts.get(sid), int) else 0) + 1
        last[sid] = today_str

    # ---- シーズン前の見直しの結果 ----
    if args.season_done or args.season_wait:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from season_windows import seasons_for_spot, season_key, is_done  # noqa: E402
        spots = {s["id"]: s for s in json.loads(
            (Path(__file__).resolve().parent.parent / "data" / "spots.json").read_text(encoding="utf-8-sig"))}
        today_d = datetime.strptime(today_str, "%Y-%m-%d").date()
        sc = progress.get("season_checks")
        if not isinstance(sc, dict):
            sc = progress["season_checks"] = {}
        done_ids = [x.strip() for x in args.season_done.split(",") if x.strip()]
        wait_ids = [x.strip() for x in args.season_wait.split(",") if x.strip()]
        both = set(done_ids) & set(wait_ids)
        if both:
            # 両方に入っていたら、済みにせず発表待ちにする（見逃す側に倒さない）
            print(f"[season] --season-done と --season-wait の両方にある（発表待ちとして書く）: {','.join(sorted(both))}")
            done_ids = [x for x in done_ids if x not in both]
        for result, idlist in (("done", done_ids), ("wait", wait_ids)):
            for sid in idlist:
                if sid not in ids:
                    print(f"[season] {sid}: --ids に無い（今日見ていない）ので書かない")
                    continue
                ss = seasons_for_spot(spots.get(sid, {}), today_d)
                if not ss:
                    print(f"[season] {sid}: 今日は見直しの期間外かタグが違うので書かない")
                    continue
                for s in ss:
                    bucket = sc.get(season_key(s))
                    if not isinstance(bucket, dict):
                        if bucket is not None:
                            print(f"[warn] season_checks の {season_key(s)} が辞書でないので作り直す")
                        bucket = sc[season_key(s)] = {}
                    prev = bucket.get(sid)
                    if is_done(prev, s, today_d) and result == "wait":
                        # 差し戻し・公開失敗などで wait を渡された時に済みのまま残すと、二度と見に行かない
                        print(f"[season] {sid}: 済みだったが発表待ちを渡されたので発表待ちにする")
                    bucket[sid] = {"date": today_str, "result": result}
                    print(f"[season] {sid} {season_key(s)} {result}")

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
