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

判定のしかた:
  ログに [codex-skip] があり、**その日に検証すべきIDのうち [codex-catchup] 行に
  現れていないものが残っている**日 = 未検証のまま。
  （追いかけ検証をしたら [codex-catchup] にIDを列挙して書く。それが済みの印になる）

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
DONE = "[codex-catchup]"

# ログの「チェック対象: [id(count=N), ...]」行からIDを拾う
TARGET_LINE = re.compile(r"チェック対象:\s*\[([^\]]*)\]")
TARGET_ID = re.compile(r"([A-Za-z0-9][A-Za-z0-9_-]*)\s*\(count=")


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
        ids.update(TARGET_ID.findall(m.group(1)))
    return ids


def done_ids_from_log(text, candidates):
    """[codex-catchup] 行に現れた「候補IDのうちどれか」を返す（＝追いかけ済みの印）。

    ★散文から正規表現でIDを推測しないこと★
    以前は単語境界つきの正規表現で拾っていたが、ログには丸数字（①など）や日本語が
    IDに隣接して並ぶ。Pythonは丸数字を単語文字とみなすため境界がずれ、
    maruyama-park-kyoto が park-kyoto として切り出されて一致しなかった
    （2026-09-07に実データで発覚。合成テストは空白区切りだったので通っていた）。
    候補は分かっているので、素直に部分一致で照合する。
    """
    lines = [l for l in text.split("\n") if DONE in l]
    if not lines:
        return set()
    blob = "\n".join(lines)
    return {c for c in candidates if c in blob}


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
    today = datetime.date.today()
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
            if SKIP not in text:
                continue

            try:
                ids = set(changed_ids(d, path))
            except GitError as ex:
                print("!! {} のgit差分を取れなかった: {}".format(d, ex))
                print("   （握り潰すと『変更なし＝追いかけ不要』と誤判定するため中断する）")
                return 1

            # 変更が無くても、その日の検証対象だったIDは追いかけの対象にする
            ids |= checked_ids_from_log(text)
            # すでに追いかけ済みのIDを除く（候補と照合する方式）
            ids -= done_ids_from_log(text, ids)

            if ids:
                pending.append((d, sorted(ids)))

        if not pending:
            print("{}: 未検証の日なし".format(kind))
            continue

        for d, ids in pending:
            total_days += 1
            room = max(0, a.max_ids - emitted)
            shown = ids[:room]
            rest = len(ids) - len(shown)
            print("{}: {} が未検証（{}件）".format(kind, d, len(ids)))
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
        print("★IDを書かないと、その日は次回も未検証として出続ける★")
        return 3

    print("\n[key] 未検証あり=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
