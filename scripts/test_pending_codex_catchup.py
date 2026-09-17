#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pending_codex_catchup.py の回帰テスト。

2026-09-17に、Codexのコードレビュー7件と自分のレビュー2件で見つかった誤りを、
**もう一度起こさないため**に置いている。1件ずつ「どの向きに間違えるか」を
テスト名に書いてある。誤りの向きは2つあり、害の大きさが違う。

  済みと誤認 … 未検証のまま永久に見えなくなる（いちばん危ない）
  未検証と誤認 … うるさいだけだが、本当に見るべきものが埋もれる

使い方: python scripts/test_pending_codex_catchup.py
終了コード 0=全部通った / 1=落ちたものがある
"""
import datetime
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pending_codex_catchup as m  # noqa: E402

NOW = datetime.datetime.now()
TODAY = NOW.date()
YESTERDAY = (TODAY - datetime.timedelta(days=1)).isoformat()
WEEK_AGO = (TODAY - datetime.timedelta(days=7)).isoformat()

failed = []


def check(name, got, want):
    if got == want:
        print("  OK   " + name)
    else:
        print("  NG   " + name)
        print("       期待: {}".format(want))
        print("       実際: {}".format(got))
        failed.append(name)


def run(kind, files):
    """一時ディレクトリにログを置いて scan を回し、(日付, タスクID, 未検証ID, 対象取得可) を返す。"""
    d = Path(tempfile.mkdtemp())
    try:
        for name, body in files.items():
            p = d / name
            if body is None:          # 読めないファイルを作る（ディレクトリにする）
                os.makedirs(p)
            else:
                io.open(p, "w", encoding="utf-8").write(body)
        out = m.scan(kind, d, 0, TODAY, NOW)
        return [(x[0], x[1], tuple(sorted(x[3])), x[4]) for x in out]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def spot(date):
    return "spot_check_{}.log".format(date)


def danger(date):
    return "wansakansai_{}.log".format(date)


print("pending_codex_catchup.py 回帰テスト")

# 1. 元の事故（2026-09-16の昼が検証前に途絶）を拾えること
check("途絶した実行の対象を拾う",
      run("spot", {spot(YESTERDAY):
                   "[12:03:30] === spot-update-am 開始 ===\n"
                   "[12:03:54] === スポット情報チェック（前半）=== "
                   "チェック対象: [alpha-spot(count=2), beta-spot(count=7)]\n"
                   "[12:15:49] [tabs] タブを閉じた\n"}),
      [(YESTERDAY, "wansakansai-spot-update-am", ("alpha-spot", "beta-spot"), True)])

# 2. 走っている最中の自分自身を途絶と報告しないこと（未検証と誤認の向き）
recent = (NOW - datetime.timedelta(minutes=3)).strftime("%H:%M:%S")
check("実行中（3分前に開始）は報告しない",
      run("spot", {spot(TODAY.isoformat()):
                   "[{}] === spot-update-pm 開始 ===\n"
                   "[{}] チェック対象: [running-spot(count=1)]\n".format(recent, recent)}),
      [])

# 3. 開始行にタイムスタンプが無い場合、今日のぶんは数えない（自分自身の誤報告を防ぐ）
check("タイムスタンプ無しの開始行（今日）は報告しない",
      run("spot", {spot(TODAY.isoformat()):
                   "=== spot-update-pm 開始 ===\n"
                   "[02:40:00] チェック対象: [nots-spot(count=1)]\n"}),
      [])

# 4. 同じ形でも過去の日なら十分古いと言い切れるので報告する（見落としを防ぐ）
check("タイムスタンプ無しの開始行（過去日）は報告する",
      run("spot", {spot(WEEK_AGO):
                   "=== spot-update-pm 開始 ===\n"
                   "[02:40:00] チェック対象: [old-spot(count=1)]\n"}),
      [(WEEK_AGO, "wansakansai-spot-update-pm", ("old-spot",), True)])

# 5. 同じタスクが1日に2回走った日、2回目の完了で1回目の途絶を打ち消さないこと
#    （2026-09-08に実在した形。済みと誤認の向き＝いちばん危ない）
check("同じタスクが2回走った日、1回目の途絶を打ち消さない",
      run("spot", {spot(WEEK_AGO):
                   "[02:40:07] === spot-update-pm 開始 ===\n"
                   "[02:41:00] チェック対象: [first-spot(count=1)]\n"
                   "[15:13:13] === spot-update-pm 開始 ===\n"
                   "[15:14:00] チェック対象: [second-spot(count=1)]\n"
                   "[15:40:00] [codex-verified] second-spot\n"
                   "[15:41:44] === wansakansai-spot-update-pm 完了 ===\n"}),
      [(WEEK_AGO, "wansakansai-spot-update-pm", ("first-spot",), True)])

# 6. 失敗より「前」に書かれた検証印を済みとして数えないこと（済みと誤認の向き）
check("失敗より前の検証印は済みに数えない",
      run("spot", {spot(WEEK_AGO):
                   "[02:59:38] [codex-verified] shared-spot\n"
                   "[03:01:52] === wansakansai-spot-update-pm 完了 ===\n"
                   "[12:03:30] === spot-update-am 開始 ===\n"
                   "[12:04:00] チェック対象: [shared-spot(count=3)]\n"}),
      [(WEEK_AGO, "wansakansai-spot-update-am", ("shared-spot",), True)])

# 7. IDの照合を部分一致にしないこと。r-cafe は stellar-cafe の部分文字列
#    （276件中この1組が実在する。済みと誤認の向き）
check("r-cafe を stellar-cafe の検証で済みにしない",
      run("spot", {spot(WEEK_AGO):
                   "[02:40:07] === spot-update-pm 開始 ===\n"
                   "[02:41:00] チェック対象: [r-cafe(count=1), stellar-cafe(count=1)]\n"
                   "[03:00:00] [codex-verified] stellar-cafe\n"}),
      [(WEEK_AGO, "wansakansai-spot-update-pm", ("r-cafe",), True)])

# 8. 文章の中で開始マーカーに触れただけの行を、実行の開始と見なさないこと
check("文章中の開始マーカーへの言及は実行と見なさない",
      run("spot", {spot(WEEK_AGO):
                   "[02:40:07] === spot-update-pm 開始 ===\n"
                   "[02:41:00] チェック対象: [only-spot(count=1)]\n"
                   "[02:42:00] 補足: 前日は === spot-update-am 開始 === の行までしか無かった\n"
                   "[03:00:00] [codex-verified] only-spot\n"
                   "[03:01:00] === wansakansai-spot-update-pm 完了 ===\n"}),
      [])

# 9. 文章の中で [codex-skip] に触れただけの行を、スキップと見なさないこと
check("文章中の [codex-skip] への言及はスキップと見なさない",
      run("spot", {spot(WEEK_AGO):
                   "[02:40:07] === spot-update-pm 開始 ===\n"
                   "[02:41:00] チェック対象: [only-spot(count=1)]\n"
                   "[02:42:00] 補足: このスクリプトは [codex-skip] を手がかりにする作り\n"
                   "[03:00:00] [codex-verified] only-spot\n"
                   "[03:01:00] === wansakansai-spot-update-pm 完了 ===\n"}),
      [])

# 10. 後の日のログが読めない時、握り潰して「済み」と答えないこと
try:
    run("spot", {spot(WEEK_AGO): "[02:40:07] === spot-update-pm 開始 ===\n",
                 spot(YESTERDAY): None})
    check("読めないログは例外にする", "例外が出なかった", "CheckError")
except m.CheckError:
    print("  OK   読めないログは例外にする")

# 11. 危険情報は「チェック対象:」行を持たない。対象が取れなくても黙って落とさないこと
#     （2026-09-17午後に、報告そのものが消えていた。見落としの向き）
check("危険情報の途絶は対象不明でも報告する",
      run("danger", {danger(WEEK_AGO):
                     "[06:37:02] STEP 0: タスク開始\n"
                     "[06:40:37] STEP 1: 既存データ確認 20件\n"}),
      [(WEEK_AGO, "wansakansai-danger-update", (), False)])

# 12. 危険情報も [codex-targets] を書けば対象が埋まること
check("危険情報も [codex-targets] があれば対象が埋まる",
      run("danger", {danger(WEEK_AGO):
                     "[06:37:02] STEP 0: タスク開始\n"
                     "[06:40:00] [codex-targets] danger-025,danger-017\n"}),
      [(WEEK_AGO, "wansakansai-danger-update", ("danger-017", "danger-025"), True)])

# 13. スキップした実行に、同じ日の別の実行の対象を混ぜないこと
#     （まだ検証前の、走っている最中の実行の対象を積んでしまう向き）
check("スキップした実行に別の実行の対象を混ぜない",
      run("spot", {spot(WEEK_AGO):
                   "[02:40:07] === spot-update-pm 開始 ===\n"
                   "[02:41:00] チェック対象: [pm-spot(count=1)]\n"
                   "[03:00:00] [codex-skip] 上限に達した\n"
                   "[03:01:00] === wansakansai-spot-update-pm 完了 ===\n"
                   "[13:13:21] === spot-update-am 開始 ===\n"
                   "[13:14:00] チェック対象: [am-spot(count=1)]\n"
                   "[13:40:00] [codex-verified] am-spot\n"
                   "[13:42:40] === wansakansai-spot-update-am 完了 ===\n"}),
      [(WEEK_AGO, "wansakansai-spot-update-pm", ("pm-spot",), True)])

# 14. 済みの印が「後の日」のログに書かれていても拾うこと
check("済みの印が翌日のログにあっても拾う",
      run("spot", {spot(WEEK_AGO):
                   "[12:03:30] === spot-update-am 開始 ===\n"
                   "[12:04:00] チェック対象: [late-spot(count=1)]\n",
                   spot(YESTERDAY):
                   "[02:40:00] === spot-update-pm 開始 ===\n"
                   "[02:59:00] [codex-verified] late-spot\n"
                   "[03:01:00] === wansakansai-spot-update-pm 完了 ===\n"}),
      [])

print("")
if failed:
    print("落ちたテスト {}件: {}".format(len(failed), ", ".join(failed)))
    sys.exit(1)
print("全部通った")
sys.exit(0)
