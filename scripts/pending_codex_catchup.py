#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Codexの検証が飛んだまま公開された日を洗い出す。

なぜ要るか（2026-09-05）:
Codexが利用上限に達して2AI検証が実行できない日があった。タスクは方針どおり
止まらずに公開を続け、メールにも [codex-skip] を明記していて、そこまでは正しく動いた。
問題はその後で、**上限が解除されたあとに「検証されないまま公開した分を検証し直す」
手順がどこにも無かった**。今回は人が気づいて指示したから追いかけられたが、
決まりになっていないと次は抜ける。

実際、9/5に検証なしで公開した5項目のうち2項目が誤りだった
（八坂神社のペット可否・大内峠一字観公園の冬季閉園の範囲）。
飛ばした日をそのままにすると誤りが残り続ける。

★2026-09-07に2AIレビューで見つかった不具合を修正した★
  ① gitの失敗を握り潰していた。git show が失敗すると before が空辞書になり、
     **全スポットが「新規＝変更あり」として報告される**静かな誤りになっていた
  ② 「変更があった日」しか対象にしていなかった。2026-09-07にCodexの検証範囲を
     「修正した分だけ」から「対象5件すべて」に変えたので、**修正0件の日にスキップが
     起きた場合も、5件ぶんの「問題なし」判断が未検証のまま残る**
  ③ 済みの判定が日単位だった。ログは前半・後半で共有しているため、
     片方だけ追いかけても日全体が「済み」になっていた
  ④ 件数上限が表示だけでなく [ids] 行も切っており、**残りは永久に検証されないのに
     日は「済み」になっていた**
  ⑤ 走査が新しい日→古い日の順で、手順書の「古い日から順に消化」と逆だった

★2026-09-17に「Codexを呼ぶ手前で落ちた」型を拾えるようにした★
  9/16の昼の実行が、調査と修正を終えた12:15を最後に途絶した。Codex検証・コミット・
  メール・完了マーカーのすべてが未実行で、**修正2件が未検証・未公開のまま
  作業ツリーに残った**。翌日のpmが作業ツリーの汚れに気づいて拾ったから助かったが、
  このスクリプトは [codex-skip] を手がかりにする作りだったので0件と答えていた。
  [codex-skip] は「呼んだが失敗した」印であって、**呼ぶ前に落ちた日には何も残らない**。
  以後は開始マーカーと完了マーカーの対応も見る（RUNS）。

判定のしかた（次のどちらかに当てはまり、かつ未検証のIDが残っている日）:
  ① ログに [codex-skip] がある（Codexを呼んだが失敗した）
  ② 開始マーカーがあるのに完了マーカーが無い実行がある（途中で途絶した）
     …この場合コミットまで到達していないのでgit差分には出ない。
        拾えるのはその実行の「チェック対象:」行だけ
  済みの印は [codex-catchup]（後日の追いかけ）と [codex-verified]（当日の通常検証）。
  **済みの印は先の日のログに書かれることがある**ので、対象日から今日までを通して見る。

その日に検証すべきID:
  ①gitのコミット差分で変わったID（＝公開内容が変わったもの）
  ②その日のログの「チェック対象:」行に出てくるID（＝変更が無くても検証対象だったもの）
  ログの文面解析は最小限にとどめ、①のgit差分を主に使う。

使い方:
    python scripts/pending_codex_catchup.py              # 未検証の日と対象IDを出す
    python scripts/pending_codex_catchup.py --days 14    # さかのぼる日数（既定7）
    python scripts/pending_codex_catchup.py --kind danger  # 危険情報だけ
    python scripts/pending_codex_catchup.py --kind spot    # スポットだけ

終了コード: 0=未検証なし / 1=点検そのものに失敗 / 3=未検証あり
"""
import argparse
import datetime
import io
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOGDIR = Path("C:/Users/imao_/.claude/logs")

# ログ名の頭 → 何のタスクか
KINDS = {
    "danger": ("wansakansai_{date}.log", "data/dangers.json"),
    "spot": ("spot_check_{date}.log", "data/spots.json"),
}

SKIP = "[codex-skip]"
# ★済みの印は2種類ある★
#   [codex-catchup]  … 後日の追いかけ検証で済ませたもの
#   [codex-verified] … その日の実行で通常どおりCodex検証を終えたもの
# 後者を数えないと、同じ日に片方がスキップした時に、
# もう片方が正常に検証した分まで未検証扱いになる（2026-09-08に実際に起きた）。
DONE_MARKS = ("[codex-catchup]", "[codex-verified]")
DONE = DONE_MARKS[0]   # メッセージ表示用


# ★印は「行の先頭にあるもの」だけを印として数える（2026-09-17追加）★
# それまでは本文のどこかに文字列があれば印とみなしていたため、
# **説明の文章の中で印の名前に触れただけの行が、本物の印として数えられていた**。
# 実際に2026-09-17のpmが「pending_codex_catchup.py はログ内の [codex-skip] を
# 証拠に走査する作りなので」と書いた1行で、その日が丸ごと「Codex検証をスキップ」
# と判定され、まだ検証していないだけの当日分3件が追いかけ対象として出た。
# 済みの印（[codex-verified]）側で同じことが起きるともっと悪く、
# **検証していない日を「済み」と誤認して永久に見えなくする**。
# log.py はメッセージをそのまま1行として書くので、本物の印は必ず
# 「[HH:MM:SS] 」の直後に来る。文章中の言及は必ず行の途中に来る。
def has_mark(text, mark):
    """本文の中に、行頭の印としての mark があるか。"""
    return any(line_has_mark(line, mark) for line in text.split("\n"))


def line_has_mark(line, mark):
    """1行が mark で始まっているか（先頭のタイムスタンプは読み飛ばす）。"""
    body = TS.sub("", line, count=1).strip()
    return body.startswith(mark)

# ★「Codexを呼ぶ手前で落ちた」型を拾うための開始／完了マーカー（2026-09-17追加）★
# [codex-skip] は「Codexを呼んだが失敗した」印なので、**呼ぶ前に落ちた日には何も残らない**。
# 2026-09-16の昼の実行が実際にこの形だった。調査と修正を終えた12:15を最後に途絶し、
# Codex検証・コミット・メール・完了マーカーがすべて未実行で、
# 修正2件が未検証・未公開のまま作業ツリーに残った。
# このスクリプトは [codex-skip] だけを手がかりにしていたため0件と答えていた。
# 開始マーカーがあるのに完了マーカーが無い＝途中で途絶した、で判定する。
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

# 走り始めてこれだけ経っていない実行は「まだ動いている最中かもしれない」として数えない。
# ★この猶予が無いと、タスクが自分自身を「途絶した」と報告する★
# （このスクリプトは各タスクの途中から呼ばれる。実測は am 約12分・pm 約30分なので6時間は十分な余裕）
RUNNING_GRACE_HOURS = 6

# ログ行頭の [HH:MM:SS]
TS = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\]")

# ログの「チェック対象: [...]」行からIDを拾う。
# ★IDの直後に (count= が来る前提にしないこと★
# 実行によっては「id 日本語名(count=5)」と日本語名が挟まる。
# 位置で決め打ちすると片方の書き方しか拾えない（2026-09-08に実際に起きた）。
# 括弧の中からIDの形をしたものを全部拾う。日本語は [a-z0-9-] に一致しないので混ざらない。
TARGET_LINE = re.compile(r"チェック対象:\s*\[([^\]]*)\]")
TARGET_ID = re.compile(r"[a-z][a-z0-9-]{3,}")
# 括弧の中に紛れる、IDではない語
NOT_IDS = {"count"}


class GitError(Exception):
    """gitコマンドが失敗した。静かに空の結果を返さないための例外。"""


def git(*args):
    """gitを実行して標準出力を返す。**失敗は必ず例外にする。**

    ★終了コードを捨てないこと★
    捨てると、失敗時に空文字が返って「差分なし」や「全部が新規」と誤解する。
    2026-09-07のレビューで、実際にこの握り潰しが見つかった。
    """
    r = subprocess.run(["git", "-C", str(BASE)] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise GitError("git {} が失敗（終了コード{}）: {}".format(
            " ".join(args[:2]), r.returncode, (r.stderr or "").strip()[:200]))
    return r.stdout


def changed_ids(date, path):
    """その日のコミットで id が追加・変更されたものを返す。

    その日の最初のコミットの親と、最後のコミットを比べる。
    1日に複数コミットがあっても1回の比較で済む。
    読み取りに失敗したら GitError を投げる（空リストを返さない）。
    """
    commits = [c for c in git(
        "log", "--format=%H",
        "--since", "{} 00:00:00".format(date),
        "--until", "{} 23:59:59".format(date),
        "--", path).split() if c]
    if not commits:
        return []
    newest, oldest = commits[0], commits[-1]
    parent = git("rev-parse", oldest + "^").strip()
    if not parent:
        raise GitError("{} の親コミットを取れなかった".format(oldest[:8]))

    def load(ref):
        out = git("show", "{}:{}".format(ref, path))
        try:
            return {e["id"]: e for e in json.loads(out)}
        except Exception as ex:
            raise GitError("{}:{} のJSONを読めなかった: {}".format(ref[:8], path, ex))

    before, after = load(parent), load(newest)
    return sorted(i for i, e in after.items() if i not in before or before[i] != e)


def checked_ids_from_log(text):
    """その日のログの「チェック対象:」行から、検証対象だったIDを拾う。

    ★変更が無かった日も対象にするために要る★
    2026-09-07からCodexは対象5件すべてを見るので、
    **修正0件でもその5件の「問題なし」判断が未検証**になり得る。
    git差分だけを見ていると、この型を取りこぼす。
    """
    ids = set()
    for m in TARGET_LINE.finditer(text):
        ids.update(t for t in TARGET_ID.findall(m.group(1)) if t not in NOT_IDS)
    return ids


def done_ids_in(blob, candidates):
    """済みの印がある行を繋いだ文字列の中に、候補IDが現れるかを素直に部分一致で見る。

    済みの印は [codex-catchup]（後日の追いかけ）と [codex-verified]（当日の通常検証）の2種類。
    **印かどうかの判定は line_has_mark が行い、ここには済みの行だけが渡ってくる。**

    ★散文から正規表現でIDを推測しないこと★
    以前は単語境界つきの正規表現で拾っていたが、ログには丸数字（①など）や日本語が
    IDに隣接して並ぶ。Pythonは丸数字を単語文字とみなすため境界がずれ、
    maruyama-park-kyoto が park-kyoto として切り出されて一致しなかった
    （2026-09-07に実データで発覚。合成テストは空白区切りだったので通っていた）。
    候補は分かっているので、素直に部分一致で照合する。

    ★2026-09-17に done_ids_from_log を削除した★
    同じことをする関数が2つあり、**古い方は「行のどこかに印の文字列があれば済み」**
    という、同日に直したばかりの誤りをそのまま抱えたまま呼ばれずに残っていた。
    使われていない誤りは、次に誰かが呼んだ時に静かに復活する。
    """
    if not blob:
        return set()
    return {c for c in candidates if c in blob}


def done_blob(logdir, pattern, date, today):
    """date から today までの同じ種類のログを集め、済みの印がある行だけを繋いで返す。

    ★済みの印は、その日のログに書かれるとは限らない（2026-09-17に判明）★
    2026-09-16のam分は、翌日のpmが追いかけて 2026-09-17 のログの
    [codex-verified] に並べた。当日のログだけを見ると、
    **済ませたのに毎日「未検証」と出続ける**。
    後から古いログに書き足させるのは無理があるので、読む側が先の日まで見る。

    後の日の通常ローテーションで検証された場合も「済み」として扱ってよい。
    検証されるのはその時点のデータで、そこには過去の修正が含まれているため。
    """
    y, mo, d = (int(x) for x in date.split("-"))
    cur = datetime.date(y, mo, d)
    lines = []
    while cur <= today:
        f = logdir / pattern.format(date=cur.isoformat())
        if f.exists():
            try:
                t = io.open(f, encoding="utf-8", errors="replace").read()
            except Exception:
                t = ""
            lines.extend(l for l in t.split("\n")
                         if any(line_has_mark(l, m) for m in DONE_MARKS))
        cur += datetime.timedelta(days=1)
    return "\n".join(lines)


def run_segments(text, runs):
    """ログ本文を実行ごとに切り分ける。

    ★spot_check ログは am と pm が1つのファイルを共有する★
    だから「チェック対象:」行がどちらの実行のものかは、行の位置でしか分からない。
    返すのは [(タスクID, 開始行, その実行ぶんの本文)] の並び。
    """
    lines = text.split("\n")
    marks = []
    for i, line in enumerate(lines):
        for task_id, start, _done in runs:
            if start in line:
                marks.append((i, task_id, line))
                break
    out = []
    for n, (i, task_id, line) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        out.append((task_id, line, "\n".join(lines[i:end])))
    return out


def start_dt(date, line):
    """開始行の [HH:MM:SS] とログの日付から開始時刻を組み立てる。読めなければ None。"""
    m = TS.match(line)
    if not m:
        return None
    y, mo, d = (int(x) for x in date.split("-"))
    return datetime.datetime(y, mo, d, int(m.group(1)), int(m.group(2)), int(m.group(3)))


def incomplete_runs(date, text, kind, now):
    """開始マーカーがあるのに完了マーカーが無い実行を返す。

    返すのは [(タスクID, その実行の検証対象ID集合)]。
    **まだ走っている最中かもしれないものは除く**（RUNNING_GRACE_HOURS）。

    限界を正直に書いておく: 同じタスクが1日に2回走った場合、
    完了マーカーの有無はファイル全体で見るので「片方だけ途絶」は見分けられない。
    今の運用は1日1回なので実害は無い。
    """
    runs = RUNS.get(kind, [])
    if not runs:
        return []
    done_of = {task_id: done for task_id, _s, done in runs}
    out = []
    for task_id, line, body in run_segments(text, runs):
        if has_mark(text, done_of[task_id]):
            continue
        began = start_dt(date, line)
        if began is not None and (now - began).total_seconds() < RUNNING_GRACE_HOURS * 3600:
            continue
        out.append((task_id, checked_ids_from_log(body)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="さかのぼる日数（既定7）")
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
    total_days = 0
    emitted = 0

    for kind in kinds:
        pattern, path = KINDS[kind]
        pending = []

        # ★古い日から順に見る★ 手順書が「古い日から順に消化する」としているため、
        # 出す順番も古い順に揃える。溜まった時に古いものが後回しになるのを防ぐ。
        for back in range(a.days - 1, -1, -1):
            d = (today - datetime.timedelta(days=back)).isoformat()
            f = logdir / pattern.format(date=d)
            if not f.exists():
                continue
            try:
                text = io.open(f, encoding="utf-8", errors="replace").read()
            except Exception as ex:
                print("!! {} のログを読めなかった: {}".format(d, ex))
                return 1
            # 拾う型は2つ。①Codexを呼んだが失敗した（[codex-skip]）
            # ②Codexを呼ぶ手前で途絶した（開始マーカーだけあって完了マーカーが無い）
            broken = incomplete_runs(d, text, kind, now)
            if not has_mark(text, SKIP) and not broken:
                continue

            ids = set()
            reasons = []

            if has_mark(text, SKIP):
                # ★この型は「Codexを呼んだが失敗した」＝**コミットまで到達している**★
                # だからその日の公開内容の変更（git差分）も追いかけの対象になる。
                try:
                    ids |= set(changed_ids(d, path))
                except GitError as ex:
                    print("!! {} のgit差分を取れなかった: {}".format(d, ex))
                    print("   （握り潰すと『変更なし＝追いかけ不要』と誤判定するため中断する）")
                    return 1
                # 変更が無くても、その日の検証対象だったIDは追いかけの対象にする
                ids |= checked_ids_from_log(text)
                reasons.append("Codex検証をスキップ")

            for task_id, run_ids in broken:
                # ★この型は**コミットまで到達していない**ので git差分を混ぜてはいけない★
                # 拾えるのはその実行の「チェック対象:」行だけ。
                #
                # 2026-09-17に直した誤り: git差分を型によらず先に取っていたため、
                # **その日に対話セッションがやった一括編集まで、途絶した実行のせいにしていた**。
                # 実際に2026-09-10が29件と報告された（内訳はpmの対象5件＝同日amが検証済みと、
                # アフィリエイト項目の一括追加24件）。途絶した実行が触っていないものを
                # 検証待ちに積むと、本当に見るべき数件がその中に埋もれる。
                ids |= run_ids
                reasons.append("{} が完了マーカー無しで途絶".format(task_id))

            # すでに検証済みのIDを除く。**先の日のログまで見る**（done_blob の説明を参照）
            ids -= done_ids_in(done_blob(logdir, pattern, d, today), ids)

            if ids:
                pending.append((d, sorted(ids), reasons))

        if not pending:
            print("{}: 未検証の日なし".format(kind))
            continue

        for d, ids, reasons in pending:
            total_days += 1
            room = max(0, a.max_ids - emitted)
            shown = ids[:room]
            rest = len(ids) - len(shown)
            print("{}: {} が未検証（{}件） 理由: {}".format(
                kind, d, len(ids), " / ".join(reasons)))
            if shown:
                print("  [ids] {}".format(",".join(shown)))
                emitted += len(shown)
            if rest:
                print("  （残り{}件は今回の上限{}を超えるため次回にまわす。"
                      "**この日のログに [codex-catchup] を書く時は、"
                      "実際に検証したIDだけを書くこと**）".format(rest, a.max_ids))

    if total_days:
        print("\n[key] 未検証あり={}日 今回出したID={}件".format(total_days, emitted))
        print("上の [ids] をSTEP 7の --ids に今日の5件と一緒に並べて1回で渡すこと。")
        print("済んだらその日のログに {} と**検証したIDを列挙**して書く。".format(DONE))
        print("（その日の通常検証を終えた分は [codex-verified] にIDを列挙すること）")
        print("★IDを書かないと、その日は次回も未検証として出続ける★")
        return 3

    print("\n[key] 未検証あり=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
