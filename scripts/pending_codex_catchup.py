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

判定のしかた:
  ログに [codex-skip] があり、かつ [codex-catchup] が無い日 = 未検証のまま
  （追いかけ検証をしたら [codex-catchup] をログに書く。これが済みの印になる）

その日に何を公開したかは git から取る。ログの文面を解析すると書き方に依存して
壊れるので、コミットの差分という機械的な事実だけを見る。

使い方:
    python scripts/pending_codex_catchup.py              # 未検証の日と対象IDを出す
    python scripts/pending_codex_catchup.py --days 14    # さかのぼる日数（既定7）
    python scripts/pending_codex_catchup.py --kind danger  # 危険情報だけ
    python scripts/pending_codex_catchup.py --kind spot    # スポットだけ

終了コード: 0=未検証なし / 3=未検証あり（タスクはこれを見て追いかけ検証に入る）
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


def git(*args):
    r = subprocess.run(["git", "-C", str(BASE)] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout


def changed_ids(date, path):
    """その日のコミットで id が追加・変更されたものを返す。

    その日の最初のコミットの親と、最後のコミットを比べる。
    1日に複数コミットがあっても1回の比較で済む。
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
        return []

    def load(ref):
        out = git("show", "{}:{}".format(ref, path))
        try:
            return {e["id"]: e for e in json.loads(out)}
        except Exception:
            return {}

    before, after = load(parent), load(newest)
    ids = []
    for i, e in after.items():
        if i not in before or before[i] != e:
            ids.append(i)
    return sorted(ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="さかのぼる日数（既定7）")
    ap.add_argument("--kind", choices=sorted(KINDS), help="danger か spot（省略時は両方）")
    ap.add_argument("--max-ids", type=int, default=5,
                    help="1種別あたり報告するIDの上限（既定5）。多すぎるとCodexが終わらないため")
    ap.add_argument("--logdir", default=str(LOGDIR),
                    help="ログの置き場所（動作確認用。通常は指定しない）")
    a = ap.parse_args()

    logdir = Path(a.logdir)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    today = datetime.date.today()
    kinds = [a.kind] if a.kind else sorted(KINDS)
    total = 0

    for kind in kinds:
        pattern, path = KINDS[kind]
        pending = []
        # ★今日を含めること★ range(1, days+1) だと今日を飛ばす。
        # スキップは同じ日の早い時刻に起きることがあり（例: 深夜のverifyが飛んで
        # 朝のdanger-updateが追いかける）、今日を見ないと検知できない。
        # 2026-09-05の実データで、当日のスキップを取りこぼすのを確認して直した。
        for back in range(0, a.days):
            d = (today - datetime.timedelta(days=back)).isoformat()
            f = logdir / pattern.format(date=d)
            if not f.exists():
                continue
            try:
                text = io.open(f, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if SKIP not in text or DONE in text:
                continue
            pending.append((d, changed_ids(d, path)))

        if not pending:
            print("{}: 未検証の日なし".format(kind))
            continue

        for d, ids in pending:
            shown = ids[:a.max_ids]
            more = len(ids) - len(shown)
            print("{}: {} が未検証（{}）".format(
                kind, d,
                "変更 {} 件: {}{}".format(len(ids), ",".join(shown),
                                        " ほか{}件".format(more) if more else "")
                if ids else "その日の公開内容の変更はなし＝追いかけ不要"))
            if shown:
                total += 1
                print("  [ids] {}".format(",".join(shown)))

    if total:
        print("\n[key] 未検証あり={} 件の日".format(total))
        print("上の [ids] を今日のCodex検証にまとめて渡すこと。"
              "済んだらその日のログに {} を書いて印を付ける。".format(DONE))
        return 3

    print("\n[key] 未検証あり=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
