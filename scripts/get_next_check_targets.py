"""
spots.json のうち、チェック回数が少ない順に次のチェック対象を返す。

進捗ファイル: C:\\Users\\imao_\\Documents\\wansakansai\\spot_check_progress.json
形式: { "check_counts": { "spot-id": N, ... }, "pending_layout_ids": [...], ... }

使い方:
  python scripts/get_next_check_targets.py             # 上位5件をJSONで出力
  python scripts/get_next_check_targets.py --count 5   # 件数指定
  python scripts/get_next_check_targets.py --skip 5    # 先頭N件をスキップ（後半タスク用）
  python scripts/get_next_check_targets.py --today 2027-01-20   # 日付を上書き（テスト用）

ソート順:
  0) 期限付き情報（temporary）の期限が近いスポット ← カウントを無視して最優先
  1) シーズン前の見直し（紅葉・桜の期間中、まだ見ていない名所を1回に1件まで）
  2) check_counts の昇順（少ない順）
  3) spots.json 内の元の順番（追加順）の昇順

シーズン前の見直しについて（2026-11-26追加・運営者と決定）:
  期間は scripts/season_windows.py（紅葉 10/1〜11/20・桜 3/1〜4/5）。
  期間中、そのタグのスポットのうち「期間に入ってから一度も見ていない」ものを、
  検索から人がよく来る順（spot_demand.json のクリック数）に1回1件まで割り込ませる。
  前半・後半の両方で効くので1日2件。期間中にふだんの順番で回ってきたものも「見た」に数える。
  期間中のそのタグのスポットには、対象に入った理由にかかわらず season_check が付く。
  タスク側はそれを見て、混む時期だけの決まり（臨時の料金・臨時駐車場・入庫を断る・
  交通規制・混む時の犬の扱い）を探す。

期限の割り込みについて（2026-09-09追加）:
  カウント制だけだと263件を一巡するのに約26日かかり、「この日までに確認したい」
  という要求を満たせない。工事やイベント期間の情報は延長されることがあるため、
  期限の2週間前になったら順番を飛び越えて確認しに行く。
  対象になったスポットの出力には reason と expiry_recheck が付く。
  タスク側はそれを見て、公式で延長・終了を確かめること（詳しくは check_spot_expiry.py）。
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

SPOTS_JSON = Path(__file__).resolve().parent.parent / "data" / "spots.json"
PROGRESS_JSON = Path("C:/Users/imao_/Documents/wansakansai/spot_check_progress.json")

# 期限の再確認の判定は check_spot_expiry.py に一本化する（両方に書くと片方だけ直る）
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_spot_expiry import scan  # noqa: E402
from season_windows import (active_seasons, seasons_for_spot, season_note,  # noqa: E402
                            season_status, parse_day, RETRY_DAYS)

DEMAND_JSON = Path("C:/Users/imao_/Documents/wansakansai/spot_demand.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5, help="取得件数（既定: 5）")
    parser.add_argument("--skip", type=int, default=0, help="先頭からスキップする件数")
    parser.add_argument("--today", default=None, help="今日の日付をYYYY-MM-DDで上書き（テスト用）")
    parser.add_argument("--progress", default=None, help="進捗ファイルのパスを上書き（テスト用）")
    # ★期限の再確認は毎日ではなく3日おき（2026-09-20・ユーザー判断）★
    # 期限の14日前から毎日割り込ませていたが、同じ公式ページを毎日見て
    # 「延長も中止もなし」を確かめるだけで1日5件の枠を2つ食い、新しいスポットの点検が
    # 後ろに回っていた（播州清水寺と東部公園で9月30日まで約20枠）。
    # 3日空ければ、期限直前の変更に気づくのが最大3日遅れるだけで、
    # 1か月前から追いかけている情報にその遅れは効かない。
    parser.add_argument("--recheck-interval", type=int, default=3,
                        help="期限の再確認を割り込ませる最短の間隔（日）。前回から未満なら割り込ませない（既定3）")
    parser.add_argument("--near-days", type=int, default=3,
                        help="終わる日の前後この日数の間は、間隔を空けずに毎日割り込ませる（既定3）")
    parser.add_argument("--seasonal-slots", type=int, default=1,
                        help="シーズン前の見直しで割り込ませる件数（既定1。0で止める）")
    parser.add_argument("--demand", default=None, help="需要ファイルのパスを上書き（テスト用）")
    parser.add_argument("--spots", default=None, help="spots.json のパスを上書き（テスト用）")
    parser.add_argument(
        "--no-expiry-priority", action="store_true",
        help="期限の再確認による割り込みを行わない（後半タスク用。日次1回で足りるため）",
    )
    args = parser.parse_args()

    spots = json.loads((Path(args.spots) if args.spots else SPOTS_JSON).read_text(encoding="utf-8"))
    progress_path = Path(args.progress) if args.progress else PROGRESS_JSON
    progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
    # 壊れた形でも止まらないように、辞書でなければ空として扱う
    counts = progress.get("check_counts") if isinstance(progress.get("check_counts"), dict) else {}
    last_checked = progress.get("last_checked") if isinstance(progress.get("last_checked"), dict) else {}
    season_checks = progress.get("season_checks") if isinstance(progress.get("season_checks"), dict) else {}
    counts = {k: v for k, v in counts.items() if isinstance(v, int)}

    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.date.today())

    # 期限が近い／すでに切れているスポットを最優先にする。
    # 期限切れも入れるのは、表示が止まったまま残っているデータを片付けさせるため。
    #
    # 既定はON。前半・後半の両方で割り込むと、期限までの14日間まいにち同じスポットを
    # 2回ずつ見ることになり1日10件の枠を食うため、後半タスクは --no-expiry-priority で切る。
    # 既定をOFFにしなかったのは、付け忘れた時に「二重に確認する」で済む方が、
    # 「誰も確認しないまま期限が過ぎる」より軽いため。
    if args.no_expiry_priority:
        expired, due = [], []
    else:
        expired, due, _bad = scan(spots, today)
    recheck = {}
    skipped_recent = []
    for item in expired + due:
        sid = item["id"]
        # 前回見た日から --recheck-interval 日たっていなければ割り込ませない。
        # 見た日の記録が無いもの（この仕組みより前に見たもの・新規）は割り込ませる。
        seen_d = parse_day(last_checked.get(sid))
        # 未来の日付は壊れた記録として「見ていない」扱いにする（割り込みを止めない側に倒す）
        if seen_d and seen_d > today:
            seen_d = None
        # ★今日すでに見たものは、期限の再確認でも入れない（2026-11-26）★ 深夜の後半で見た名所を昼にまた見ていた
        if seen_d == today:
            if sid not in skipped_recent:
                skipped_recent.append(sid)
            continue
        seen = seen_d.isoformat() if seen_d else None
        # ★終わる日の前後3日は毎日見る（2026-10-24・運営者の提案）★
        # 延長・前倒し終了・再開の告知は終わる日の直前直後に出ることが多く、
        # 3日おきだとちょうどその間を見落とす。前後3日だけなら枠を食う日数も短い。
        near_end = abs(item.get("days_left", 99)) <= args.near_days
        if seen and not near_end:
            try:
                days = (today - datetime.date.fromisoformat(seen)).days
            except ValueError:
                days = None
            if days is not None and days < args.recheck_interval:
                if sid not in skipped_recent:
                    skipped_recent.append(sid)
                continue
        recheck.setdefault(sid, []).append(item)
    if skipped_recent:
        # 標準出力はJSONなので、判断の根拠は標準エラーに出す（ログにはタスクが書く）
        print("[expiry] 前回から{}日未満のため今日は割り込ませない: {}".format(
            args.recheck_interval, ",".join(skipped_recent)), file=sys.stderr)

    # ---- シーズン前の見直し ----
    # 需要（検索から来た回数）は週次SEOタスクが毎週書く。読めなければ全部0で、回数の少ない順になる
    clicks = {}
    try:
        dpath = Path(args.demand) if args.demand else DEMAND_JSON
        d = json.loads(dpath.read_text(encoding="utf-8-sig"))
        bad_clicks = 0
        for k, v in (d.get("spots") or {}).items():
            c = v.get("clicks") if isinstance(v, dict) else None
            if isinstance(c, (int, float)) and not isinstance(c, bool):
                clicks[k] = c
            else:
                bad_clicks += 1
        if bad_clicks:
            print("[season] 需要ファイルのクリック数が読めない行 {}件（0として扱う）".format(bad_clicks), file=sys.stderr)
    except Exception as ex:
        print("[season] 需要ファイルを読めない（回数の少ない順で選ぶ）: {}: {}".format(
            type(ex).__name__, ex), file=sys.stderr)

    season_pick = []
    if args.seasonal_slots > 0:
        for ssn in active_seasons(today):
            # 需要の多い順。まだ見ていないものと、RETRY_DAYS 空いた発表待ちを同じ列に並べる
            # （未確認を先にすると、需要の多い発表待ちが期間の終わりまで押し出されることがある。同点なら未確認が先）
            cands = []
            n = {"unseen": 0, "wait": 0, "done": 0}
            for i, sp in enumerate(spots):
                if ssn["tag"] not in (sp.get("tags") or []):
                    continue
                st, last = season_status(sp["id"], ssn, today, season_checks, last_checked)
                n[st] += 1
                if st == "done" or sp["id"] in recheck:
                    continue
                if st == "wait" and (today - last).days < RETRY_DAYS:
                    continue
                cands.append((-clicks.get(sp["id"], 0), 0 if st == "unseen" else 1,
                              counts.get(sp["id"], 0), i, sp["id"]))
            cands.sort()
            room = args.seasonal_slots - len(season_pick)
            take = [c[4] for c in cands[:max(room, 0)]]
            season_pick += take
            print("[season] {}（{}〜{}・残り{}日）: まだ見ていない {}件 / 発表待ち {}件 / 済み {}件 / 割り込ませる候補: {}".format(
                ssn["label"], ssn["start"].isoformat(), ssn["end"].isoformat(),
                (ssn["end"] - today).days, n["unseen"], n["wait"], n["done"],
                ",".join(take) or "なし"), file=sys.stderr)

    # ★今日すでに見たスポットは後ろへ回す（2026-11-26）★ 深夜の後半で見たものが、
    # 回数がまだ少ないと昼の前半でまた選ばれていた（同じ日に同じスポットを2回見る）。
    # 外すのではなく後ろへ回すだけなので、ほかに候補が無ければ選ばれる。期限の再確認は対象外
    def seen_today(sid):
        return parse_day(last_checked.get(sid)) == today

    ranked = sorted(
        enumerate(spots),
        key=lambda x: (
            0 if x[1]["id"] in recheck else (1 if x[1]["id"] in season_pick else 2),
            season_pick.index(x[1]["id"]) if x[1]["id"] in season_pick else 0,
            0 if x[1]["id"] in recheck else (1 if seen_today(x[1]["id"]) else 0),
            counts.get(x[1]["id"], 0),
            x[0],
        ),
    )

    selected = ranked[args.skip:args.skip + args.count]
    if args.seasonal_slots > 0:
        for ssn in active_seasons(today):
            if today != ssn["end"]:
                continue
            # 期間の最終日に、この回の対象を除いて済みになっていない名所をログに残す（見きれた量を運営者が知るため。
            # 選び方には使わない。翌年の期間は全部「まだ見ていない」から始まり、需要の多い順に選ばれる）
            chosen_ids = {s["id"] for _, s in selected}
            left = [sp["id"] for sp in spots if ssn["tag"] in (sp.get("tags") or [])
                    and sp["id"] not in chosen_ids
                    and season_status(sp["id"], ssn, today, season_checks, last_checked)[0] != "done"]
            print("[season] {}の期間の最終日。この回の対象を除いて済みになっていない名所 {}件: {}".format(
                ssn["label"], len(left), ",".join(left) or "なし"), file=sys.stderr)
    if season_pick:
        # 期限の再確認で枠が埋まると、候補でも入らないことがある（その日は期限の方を先に見る）
        chosen = {s["id"] for _, s in selected}
        got = [x for x in season_pick if x in chosen]
        lost = [x for x in season_pick if x not in chosen]
        print("[season] 今日の対象に入った: {} / 枠が埋まって入らなかった: {}".format(
            ",".join(got) or "なし", ",".join(lost) or "なし"), file=sys.stderr)
    result = []
    for i, s in selected:
        row = {
            "index": i,
            "id": s["id"],
            "name": s["name"],
            "address": s["address"],
            "check_count": counts.get(s["id"], 0),
        }
        if s["id"] in recheck:
            row["reason"] = "期限の再確認"
            row["expiry_recheck"] = recheck[s["id"]]
        elif s["id"] in season_pick:
            row["reason"] = "シーズン前の見直し"
        ss = seasons_for_spot(s, today)
        if ss:
            row["season_check"] = [season_note(x) for x in ss]
        result.append(row)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
