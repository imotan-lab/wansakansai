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
  1) check_counts の昇順（少ない順）
  2) spots.json 内の元の順番（追加順）の昇順

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
    parser.add_argument(
        "--no-expiry-priority", action="store_true",
        help="期限の再確認による割り込みを行わない（後半タスク用。日次1回で足りるため）",
    )
    args = parser.parse_args()

    spots = json.loads(SPOTS_JSON.read_text(encoding="utf-8"))
    progress_path = Path(args.progress) if args.progress else PROGRESS_JSON
    progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
    counts = progress.get("check_counts", {})
    last_checked = progress.get("last_checked", {})

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
        seen = last_checked.get(sid)
        if seen:
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

    ranked = sorted(
        enumerate(spots),
        key=lambda x: (
            0 if x[1]["id"] in recheck else 1,
            counts.get(x[1]["id"], 0),
            x[0],
        ),
    )

    selected = ranked[args.skip:args.skip + args.count]
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
        result.append(row)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
