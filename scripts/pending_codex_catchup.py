#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Codexの検証が飛んだまま公開された分を洗い出す。

なぜ要るか（2026-09-05）:
Codexが利用上限に達して2AI検証が実行できない日があった。タスクは方針どおり
止まらずに公開を続け、メールにも [codex-skip] を明記していて、そこまでは正しく動いた。
問題はその後で、**上限が解除されたあとに「検証されないまま公開した分を検証し直す」
手順がどこにも無かった**。実際、9/5に検証なしで公開した5項目のうち2項目が誤りだった
（八坂神社のペット可否・大内峠一字観公園の冬季閉園の範囲）。

拾う型は2つ。
  ① Codexを呼んだが失敗した実行 … ログに [codex-skip] が残る
  ② Codexを呼ぶ手前で途絶した実行 … **印は何も残らない**ので、
     開始マーカーがあるのに完了マーカーが無いことで判定する（2026-09-17追加）

★2026-09-17の全面見直し（Codexのコードレビュー7件＋自分のレビュー2件）★
それまでは「日ぶんのテキスト全体」を相手にしていた。ログは前半・後半のタスクが
1ファイルを共有し、同じタスクが1日に2回走ることもある（2026-09-08に実在）。
**日でひとまとめにすると、別の実行の印を自分の印として数えてしまう。**
実際に次の誤りがあった。いずれも実ログで確認したもの。

  1. 危険情報のログには「チェック対象:」行が無いため、途絶を見つけても対象IDが空になり、
     **「未検証なし」と答えて終了コード0を返していた**（見落としの向き）
  2. [codex-skip] を日単位で見ていたため、**同じ日にまだ走っている別の実行の対象**まで
     追いかけに積んでいた。日ぶんのgit差分も足していたので、
     人が対話セッションで一括編集した分まで途絶した実行のせいにしていた
  3. 完了マーカーをファイル全体から探していたため、**同じタスクが2回走った日に、
     2回目の完了で1回目の途絶が打ち消されていた**（済みと誤認＝いちばん危ない向き）
  4. 同じ日の中で、**失敗より前に書かれた検証印**まで済みとして数えていた
  5. IDの照合が部分一致だった。`r-cafe` は `stellar-cafe` の部分文字列なので、
     stellar-cafe を検証すると r-cafe まで済みになる（276件中この1組が実在）
  6. 後の日のログが読めなかった時に空文字で握り潰していた
  7. 窓が14日固定で、**それを過ぎると未検証のまま消えていた**（ログは自動削除されない）
  8. 開始行にタイムスタンプが無いと、実行中かの判定が飛ばされ、
     **走っている最中の自分自身を「途絶」と報告していた**
  9. 開始マーカーの検出だけが行頭判定になっておらず、文章中の言及を拾い得た

いまは**実行（run）を単位**にして、開始行の位置・時刻・その実行の対象・
完了印の有無を組で持つ。済み印も「どの日の何行目か」を持たせ、
**失敗した実行より後にあるものだけ**を済みとして数える。

終了コード: 0=未検証なし / 1=点検そのものに失敗 / 3=未検証あり
使い方:
    python scripts/pending_codex_catchup.py                # 残っているログを全部見る
    python scripts/pending_codex_catchup.py --days 14      # 直近14日だけに絞る
    python scripts/pending_codex_catchup.py --kind danger  # 危険情報だけ
    python scripts/pending_codex_catchup.py --kind spot    # スポットだけ
"""
import argparse
import datetime
import io
import re
import sys
from pathlib import Path

LOGDIR = Path("C:/Users/imao_/.claude/logs")

# ログ名の頭 → 何のタスクか
KINDS = {
    "danger": "wansakansai_{date}.log",
    "spot": "spot_check_{date}.log",
}

# 各ログに現れる実行の、タスクID・開始マーカー・完了マーカー
RUNS = {
    "danger": [("wansakansai-danger-update",
                "STEP 0: タスク開始",
                "=== wansakansai-danger-update 完了 ===")],
    "spot": [("wansakansai-spot-update-pm",
              "=== spot-update-pm 開始 ===",
              "=== wansakansai-spot-update-pm 完了 ==="),
             ("wansakansai-spot-update-am",
              "=== spot-update-am 開始 ===",
              "=== wansakansai-spot-update-am 完了 ===")],
}

SKIP = "[codex-skip]"
# ★済みの印は2種類ある★
#   [codex-catchup]  … 後日の追いかけ検証で済ませたもの
#   [codex-verified] … その日の実行で通常どおりCodex検証を終えたもの
# 後者を数えないと、同じ日に片方がスキップした時に、
# もう片方が正常に検証した分まで未検証扱いになる（2026-09-08に実際に起きた）。
DONE_MARKS = ("[codex-catchup]", "[codex-verified]")

# 走り始めてこれだけ経っていない実行は「まだ動いている最中かもしれない」として数えない。
# ★この猶予が無いと、タスクが自分自身を「途絶した」と報告する★
# （このスクリプトは各タスクの途中から呼ばれる。実測は am 約12分・pm 約30分）
RUNNING_GRACE_HOURS = 6

TS = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\]")

# ログの「チェック対象: [...]」行からIDを拾う（スポットのみ）。
# ★IDの直後に (count= が来る前提にしないこと★
# 実行によっては「id 日本語名(count=5)」と日本語名が挟まる（2026-09-08に実際に起きた）。
TARGET_LINE = re.compile(r"チェック対象:\s*\[([^\]]*)\]")
# 危険情報のログには「チェック対象:」行が無い。機械で読める対象行を別に用意する
# （SKILL.md STEP 5.8 で Codex を呼ぶ前に書かせる）。無い日は対象不明として扱う。
TARGETS_MARK = "[codex-targets]"

# ★IDは必ず「語の境界」で切り出す★
# Pythonの \b は丸数字などを語の一部とみなすため使わない（2026-09-07に実データで発覚）。
# 部分一致も使わない。r-cafe が stellar-cafe に含まれてしまう（2026-09-17にCodexが発見）。
ID_TOKEN = re.compile(r"(?<![a-z0-9-])([a-z][a-z0-9-]{3,})(?![a-z0-9-])")
# IDの形をしているがIDではない語
NOT_IDS = {"count", "codex-skip", "codex-catchup", "codex-verified", "codex-targets",
           "http", "https", "index", "html", "json"}


class CheckError(Exception):
    """点検そのものに失敗した。**静かに空の結果を返さないための例外。**"""


def line_body(line):
    """行頭のタイムスタンプを取り除いた本体。"""
    return TS.sub("", line, count=1).strip()


def line_has_mark(line, mark):
    """その行が mark で始まっているか。

    ★行のどこかに文字列があるかで判定しないこと★
    log.py はメッセージをそのまま1行として書くので、本物の印は必ず
    「[HH:MM:SS] 」の直後に来る。文章中の言及は必ず行の途中に来る。
    2026-09-17に、説明文の中で [codex-skip] に触れた1行でその日が丸ごと
    スキップ日と判定された。より悪い向きでは、「追いかけに失敗した」と
    書いてある行が済みの印として数えられ、5件が済み扱いになっていた。
    """
    return line_body(line).startswith(mark)


def ids_in(text):
    """文字列からIDの形をした語を、語の境界で切り出す。"""
    return {t for t in ID_TOKEN.findall(text) if t not in NOT_IDS}


def parse_ts(date, line):
    """行頭の [HH:MM:SS] とログの日付から時刻を組み立てる。読めなければ None。"""
    m = TS.match(line)
    if not m:
        return None
    y, mo, d = (int(x) for x in date.split("-"))
    return datetime.datetime(y, mo, d, int(m.group(1)), int(m.group(2)), int(m.group(3)))


class Run(object):
    """1回の実行。開始行の位置と時刻、その実行の対象、完了と失敗の印を持つ。"""

    def __init__(self, kind, date, task_id, idx, started, body_lines):
        self.kind = kind
        self.date = date
        self.task_id = task_id
        self.idx = idx            # 開始行が何行目か（同じ日の前後関係に使う）
        self.started = started    # 開始時刻（読めなければ None）
        self.completed = any(line_has_mark(l, self.done_mark) for l in body_lines)
        self.skipped = any(line_has_mark(l, SKIP) for l in body_lines)
        self.targets = set()
        for l in body_lines:
            for m in TARGET_LINE.finditer(l):
                self.targets |= ids_in(m.group(1))
            if line_has_mark(l, TARGETS_MARK):
                self.targets |= ids_in(line_body(l)[len(TARGETS_MARK):])

    @property
    def done_mark(self):
        for task_id, _start, done in RUNS[self.kind]:
            if task_id == self.task_id:
                return done
        raise CheckError("完了マーカーが引けない: " + self.task_id)


def read_log(path):
    """ログを読む。**読めなければ例外にする（空文字で握り潰さない）。**

    握り潰すと、済みの印があるのに無かったことになり、
    毎回「未検証」と報告し続ける（2026-09-17にCodexが指摘）。
    """
    try:
        return io.open(path, encoding="utf-8", errors="replace").read()
    except Exception as ex:
        raise CheckError("{} を読めなかった: {}".format(path, ex))


def parse_file(kind, date, text):
    """1日ぶんのログを、実行の並びと済み印の並びに分解する。

    ★実行を単位にする理由★
    spot_check ログは am と pm が1ファイルを共有し、**同じタスクが1日に2回
    走ることもある**（2026-09-08に実在）。日でひとまとめにすると、
    2回目の完了マーカーで1回目の途絶が打ち消される。
    返すのは (実行の並び, 済み印の並び)。済み印は (行番号, ID集合)。
    """
    lines = text.split("\n")
    starts = []
    for i, line in enumerate(lines):
        for task_id, start, _done in RUNS.get(kind, []):
            if line_has_mark(line, start):
                starts.append((i, task_id, line))
                break

    runs = []
    for n, (i, task_id, line) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        runs.append(Run(kind, date, task_id, i, parse_ts(date, line), lines[i:end]))

    dones = []
    for i, line in enumerate(lines):
        for mark in DONE_MARKS:
            if line_has_mark(line, mark):
                dones.append((i, ids_in(line_body(line)[len(mark):])))
                break
    return runs, dones


def log_dates(logdir, pattern, days, today):
    """走査する日付を古い順に返す。

    ★既定は「残っているログを全部」★
    2026-09-17まで既定14日だったが、ログはどのスクリプトも消しておらず
    1か月ぶん残っている。窓を過ぎた未検証は**誰にも拾われずに消える**ため、
    証拠がある限り見る。--days で絞れる。
    """
    got = []
    for f in sorted(logdir.glob(pattern.replace("{date}", "*"))):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if not m:
            continue
        d = m.group(1)
        # ★ファイル名が寸分たがわず一致するものだけを採る★
        # `wansakansai_*.log` は `wansakansai_seo_2026-09-12.log` や
        # `wansakansai_daily_spot_2026-09-11.log` にも当たる。日付だけ見て通すと、
        # **別タスクのログを危険情報の実行として読み、完了マーカーが無いので
        # 全部「途絶」と報告する**（2026-09-17に実際にそうなった）。
        if f.name != pattern.format(date=d):
            continue
        if days:
            try:
                y, mo, dd = (int(x) for x in d.split("-"))
            except ValueError:
                continue
            if (today - datetime.date(y, mo, dd)).days > days - 1:
                continue
        got.append((d, f))
    return got


def scan(kind, logdir, days, today, now):
    """未検証が残っている実行を、古い順に返す。

    返すのは [(日付, タスクID, 理由, 未検証ID集合, 対象が取れたか)]。
    """
    pattern = KINDS[kind]
    dated = log_dates(logdir, pattern, days, today)

    parsed = {}
    for d, f in dated:
        parsed[d] = parse_file(kind, d, read_log(f))

    out = []
    for d, _f in dated:
        runs, _dones = parsed[d]
        for run in runs:
            if run.completed and not run.skipped:
                continue

            reasons = []
            if run.skipped:
                reasons.append("Codex検証をスキップ")
            if not run.completed:
                # ★まだ走っている最中かもしれないものは数えない★
                if run.started is None:
                    # 時刻が読めない。過去の日なら十分古いと言い切れるが、
                    # 今日のぶんは走っている最中と区別が付かないので数えない。
                    # （2026-09-17に、タイムスタンプ無しの開始行で
                    #   走行中の自分自身を途絶と報告する形を再現した）
                    if d == today.isoformat():
                        continue
                elif (now - run.started).total_seconds() < RUNNING_GRACE_HOURS * 3600:
                    continue
                reasons.append("{} が完了マーカー無しで途絶".format(run.task_id))

            if not reasons:
                continue

            # ★済みの印は「この実行より後」のものだけ数える★
            # 同じ日の中で、失敗より**前**に書かれた検証印は別の実行のものなので
            # 済みの根拠にならない（2026-09-17にCodexが指摘し、9/17の実ログで確認）。
            done = set()
            for dd, (_r, dones) in sorted(parsed.items()):
                if dd < d:
                    continue
                for idx, got in dones:
                    if dd == d and idx <= run.idx:
                        continue
                    done |= got
            remaining = run.targets - done
            if remaining or not run.targets:
                out.append((d, run.task_id, " / ".join(reasons), remaining, bool(run.targets)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0,
                    help="さかのぼる日数。既定0＝残っているログを全部見る")
    ap.add_argument("--kind", choices=sorted(KINDS), help="danger か spot（省略時は両方）")
    # ★既定を2にしてある★ 今日の5件と合わせて7件が上限の目安。
    # 2026-09-08に「今日の5件＋追いかけ5件＝10件」を1回で渡したところ、
    # Codexが90分かけても判定を1件も返せず、全部無駄になった。
    ap.add_argument("--max-ids", type=int, default=2,
                    help="1回に出すIDの上限（既定2）。今日の5件と合わせて7件を超えさせないため")
    ap.add_argument("--logdir", default=str(LOGDIR),
                    help="ログの置き場所（動作確認用。通常は指定しない）")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    logdir = Path(a.logdir)
    now = datetime.datetime.now()
    today = now.date()
    kinds = [a.kind] if a.kind else sorted(KINDS)

    total = 0
    emitted = 0
    unknown = 0

    for kind in kinds:
        try:
            pending = scan(kind, logdir, a.days, today, now)
        except CheckError as ex:
            print("!! {}: {}".format(kind, ex))
            print("   （握り潰すと『済み』や『未検証なし』と誤って答えるため中断する）")
            return 1

        if not pending:
            print("{}: 未検証の実行なし".format(kind))
            continue

        for d, task_id, reasons, ids, had_targets in pending:
            total += 1
            ids = sorted(ids)
            print("{}: {} の {} が未検証（{}件） 理由: {}".format(
                kind, d, task_id, len(ids), reasons))
            if not had_targets:
                unknown += 1
                print("  ★対象IDがログから取れない。**「未検証なし」ではない**★")
                print("  　{} のログを開いて、その実行がどこまで進んだかを人が確かめること".format(d))
                print("  　（危険情報のログには「チェック対象:」行が無い。"
                      "今後の実行は [codex-targets] を書くのでここが埋まる）")
                continue
            room = max(0, a.max_ids - emitted)
            shown = ids[:room]
            rest = len(ids) - len(shown)
            if shown:
                print("  [ids] {}".format(",".join(shown)))
                emitted += len(shown)
            if rest:
                print("  （残り{}件は今回の上限{}を超えるため次回にまわす。"
                      "**この実行のログに [codex-catchup] を書く時は、"
                      "実際に検証したIDだけを書くこと**）".format(rest, a.max_ids))

    if total:
        print("\n[key] 未検証の実行={} 今回出したID={}件 対象不明={}".format(total, emitted, unknown))
        print("上の [ids] をSTEP 7の --ids に今日の5件と一緒に並べて1回で渡すこと。")
        print("済んだら [codex-catchup] と**検証したIDを列挙**して書く"
              "（当日の通常検証を終えた分は [codex-verified]）。")
        print("★印は今日のログに書いてよい。対象日から先のログを通して探す★")
        print("★IDを書かないと、その実行は次回も未検証として出続ける★")
        return 3

    print("\n[key] 未検証あり=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
