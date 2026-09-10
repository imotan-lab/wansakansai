#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Chrome MCPで開いたタブを記録し、閉じ忘れを次回の実行で知らせる。

**なぜ必要か（2026-09-10の実例）**
スポット更新タスク（pm）が4件目 cafe-twotwo-dog-grass-field のInstagramを開いた直後に
途中終了し、タブがユーザーのChromeに残った。翌朝ユーザーが気づいて指摘するまで
誰も知らなかった。

- 後始末のSTEPでタブを閉じる仕組みは入れたが、**途中で死ぬとそのSTEPに到達しない**
- Chrome MCPのタブグループは**セッションごと**で、別セッションからは見えず閉じられない
  （対話セッションから片付けようとしたが `No tab group exists for this session` になった）

つまり**残ってしまったタブは誰にも閉じられない**。だから「閉じる」ではなく
「**次回の実行で気づいて知らせる**」ことを担う。人が手で閉じる判断ができればよい。

使い方:
    python scripts/track_chrome_tabs.py --open 12345 cafe-twotwo --task spot-update-pm
    python scripts/track_chrome_tabs.py --close 12345
    python scripts/track_chrome_tabs.py --check          # 残骸があれば終了コード1
    python scripts/track_chrome_tabs.py --check --json   # 機械可読
    python scripts/track_chrome_tabs.py --clear          # 記録を空にする（人が閉じた後）

記録先: spot_check_progress.json の `open_chrome_tabs`
"""
import argparse
import datetime
import io
import json
import sys
from pathlib import Path

PROGRESS = Path("C:/Users/imao_/Documents/wansakansai/spot_check_progress.json")
KEY = "open_chrome_tabs"


def load():
    if not PROGRESS.exists():
        return {}
    with io.open(PROGRESS, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    # 進捗ファイルは他のスクリプトも読む。壊さないよう全体を読んで書き戻す
    with io.open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", nargs=2, metavar=("TAB_ID", "SPOT_ID"),
                    help="タブを開いた記録を足す")
    ap.add_argument("--close", metavar="TAB_ID", help="閉じた記録を消す")
    ap.add_argument("--check", action="store_true",
                    help="残骸を報告する（あれば終了コード1）")
    ap.add_argument("--clear", action="store_true", help="記録を空にする")
    ap.add_argument("--task", default="", help="どのタスクが開いたか")
    ap.add_argument("--json", action="store_true", help="機械可読で出力")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    data = load()
    tabs = data.get(KEY) or []

    if a.open:
        tab_id, spot_id = a.open
        tabs = [t for t in tabs if str(t.get("tabId")) != str(tab_id)]
        tabs.append({
            "tabId": tab_id,
            "spot": spot_id,
            "task": a.task,
            "opened_at": datetime.datetime.now().isoformat(timespec="seconds"),
        })
        data[KEY] = tabs
        save(data)
        print(f"記録: タブ{tab_id}（{spot_id}）を開いた")
        return 0

    if a.close:
        before = len(tabs)
        tabs = [t for t in tabs if str(t.get("tabId")) != str(a.close)]
        data[KEY] = tabs
        save(data)
        if before == len(tabs):
            # 記録に無いタブを閉じた＝--open を忘れている。気づけるよう明示する
            print(f"注意: タブ{a.close} は記録に無かった（--open の書き忘れ）")
            return 0
        print(f"記録: タブ{a.close} を閉じた（残り{len(tabs)}件）")
        return 0

    if a.clear:
        data[KEY] = []
        save(data)
        print("記録を空にした")
        return 0

    if a.check:
        if a.json:
            print(json.dumps({"leftover": tabs, "ok": not tabs},
                             ensure_ascii=False, indent=2))
            return 1 if tabs else 0
        if not tabs:
            print("[tabs] 前回の閉じ忘れ: なし")
            return 0
        print(f"★前回の閉じ忘れ: {len(tabs)}件")
        for t in tabs:
            print(f"   タブ{t.get('tabId')}  {t.get('spot')}  "
                  f"{t.get('task')}  開いた時刻 {t.get('opened_at')}")
        print()
        print("このタブは別セッションのタブグループにあるため、**このタスクからは閉じられない**。")
        print("メールで人に知らせて手で閉じてもらい、そのうえで --clear すること。")
        return 1

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
