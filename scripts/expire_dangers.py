#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""期限の切れた危険情報を data/dangers.json から取り除く。

台風・大雨警報のように「数日で終わる情報」を、いつまでも載せておかないための仕組み。
従来の削除基準は「3ヶ月以上前で続報なし」しかなく、数日で終わる気象情報に合わなかった
（2026-09-03、台風24号の情報が11月まで残る状態だったため導入）。

対象は `expires` を持つエントリだけ。`expires` が無いものは従来どおり
人（タスク）の判断で消す。毒餌や事故のように「いつまで危険か決められない」情報を
機械的に消さないため、期限は書いた人が明示した時だけ効く。

  "expires": "2026-09-09"   ← この日までは表示する。翌日から削除対象

使い方:
    python scripts/expire_dangers.py            # 何が消えるか見るだけ
    python scripts/expire_dangers.py --apply    # 実際に削除する
    python scripts/expire_dangers.py --apply --today 2026-09-10   # 日付を指定（テスト用）
"""
import argparse
import datetime
import io
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DANGERS = BASE / "data" / "dangers.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="実際に書き換える（既定は確認のみ）")
    ap.add_argument("--today", default=None, help="今日の日付をYYYY-MM-DDで上書き（テスト用）")
    ap.add_argument("--path", default=str(DANGERS))
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    today = (datetime.date.fromisoformat(a.today) if a.today
             else datetime.date.today())

    entries = json.load(io.open(a.path, encoding="utf-8"))
    keep, drop, bad = [], [], []

    for e in entries:
        exp = (e.get("expires") or "").strip()
        if not exp:
            keep.append(e)
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", exp):
            # 形式がおかしい時は消さない。消す方に倒すと事故になるため
            bad.append((e.get("id"), exp))
            keep.append(e)
            continue
        if datetime.date.fromisoformat(exp) < today:
            drop.append(e)
        else:
            keep.append(e)

    print(f"今日: {today}　全{len(entries)}件")
    if bad:
        print(f"\n!! expires の書式が不正（消さずに残す）: {len(bad)}件")
        for i, v in bad:
            print(f"   {i}: {v!r}")

    if not drop:
        print("\n期限切れ: なし")
        print(f"[key] 削除=0 残り={len(keep)}")
        return 0

    print(f"\n期限切れ: {len(drop)}件")
    for e in drop:
        print(f"   {e.get('id')}  expires={e.get('expires')}  {str(e.get('location',''))[:40]}")

    if not a.apply:
        print("\n（確認のみ。実際に消すには --apply）")
        return 0

    io.open(a.path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(keep, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"\n削除しました。{len(entries)}件 → {len(keep)}件")
    print(f"[key] 削除={len(drop)} 残り={len(keep)} ID={','.join(str(e.get('id')) for e in drop)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
