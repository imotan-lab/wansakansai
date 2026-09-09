#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""スポットの期限付き情報（temporary）を点検する。

工事・イベント期間の有料化のように「いつ終わるか分かっている」情報を、
終わったあとも載せ続けないための仕組み。危険情報の expire_dangers.py と対になる。

**危険情報と違って自動削除はしない。** 施設の期間限定運用は延長されることがあり、
機械的に消すと「延長されたのに消えた」という逆向きの誤りが起きるため。
期限の2週間前になったらチェックの順番に割り込ませ（get_next_check_targets.py）、
公式を見たうえで人（タスク）が延長・終了を判断する。

表示側（js/spot.js・generate_spot_pages.py）は until を過ぎた note を出さない。
これは確認がすり抜けた時の保険で、データは消さずに残る。
「止めるのは自動で、消すのは確認してから」という分け方をしている。

データ形式（spots.json の各スポット・任意項目）:

  "temporary": [
    {
      "note": "臨時駐車スペースは9:00〜17:30の利用で2時間を超えると1回500円",
      "until": "2027-01-31",
      "source": "https://www.city.yamatokoriyama.lg.jp/...",
      "onExpire": "parking.free を true（無料）に戻す"
    }
  ]

  note      … 期限内だけ表示する一文。remarksには書かない（remarksは恒常的な内容だけ）。
              表示時に「（2027年1月31日まで）」が後ろに付くので、**note を括弧で終わらせない**
              （括弧が2つ続いて読みにくくなる。補足は句点で区切って地の文で書く）
  until     … この日までは表示する。翌日から非表示
  source    … 根拠URL。再確認の時にここから見る
  onExpire  … 期限が来たら構造化データに戻す作業のメモ（機械は解釈しない・人が読む）

使い方:
    python scripts/check_spot_expiry.py           # 期限切れ・期限接近を一覧
    python scripts/check_spot_expiry.py --json    # 機械可読（タスクから使う）
    python scripts/check_spot_expiry.py --today 2027-01-20   # 日付を指定（テスト用）
"""
import argparse
import datetime
import io
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SPOTS = BASE / "data" / "spots.json"

# 期限の何日前から再確認の対象にするか。
# 2週間前（2026-09-09にユーザーと合意）。自治体の延長告知は期限の直前に出ることが
# 多いため、これより長くしても空振りしやすい。運用しながら調整してよい。
RECHECK_DAYS_BEFORE = 14

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def load_spots(path):
    data = json.load(io.open(path, encoding="utf-8"))
    return data["spots"] if isinstance(data, dict) else data


def parse_until(value):
    """until を date で返す。書式が壊れていれば None。"""
    v = (value or "").strip()
    if not DATE_RE.fullmatch(v):
        return None
    try:
        return datetime.date.fromisoformat(v)
    except ValueError:
        return None


def scan(spots, today):
    """期限切れ・期限接近・書式不正を集める。"""
    expired, due, bad = [], [], []

    for s in spots:
        temps = s.get("temporary")
        if not temps:
            continue
        # 単体で書かれていても配列として扱う（書き間違いで落とさない）
        if isinstance(temps, dict):
            temps = [temps]
        if not isinstance(temps, list):
            bad.append({"id": s.get("id"), "reason": "temporary が配列でもオブジェクトでもない"})
            continue

        for t in temps:
            if not isinstance(t, dict):
                bad.append({"id": s.get("id"), "reason": "temporary の要素がオブジェクトでない"})
                continue
            until = parse_until(t.get("until"))
            if until is None:
                # 書式が壊れている時は消す方に倒さない。人に知らせて直してもらう
                bad.append({
                    "id": s.get("id"),
                    "reason": "until の書式が不正",
                    "until": t.get("until"),
                    "note": t.get("note"),
                })
                continue

            item = {
                "id": s.get("id"),
                "name": s.get("name"),
                "until": until.isoformat(),
                "note": t.get("note"),
                "source": t.get("source"),
                "onExpire": t.get("onExpire"),
                "days_left": (until - today).days,
            }
            if until < today:
                expired.append(item)
            elif (until - today).days <= RECHECK_DAYS_BEFORE:
                due.append(item)

    expired.sort(key=lambda x: x["until"])
    due.sort(key=lambda x: x["until"])
    return expired, due, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="機械可読で出力する")
    ap.add_argument("--today", default=None, help="今日の日付をYYYY-MM-DDで上書き（テスト用）")
    ap.add_argument("--path", default=str(SPOTS))
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    today = (datetime.date.fromisoformat(a.today) if a.today
             else datetime.date.today())

    spots = load_spots(a.path)
    expired, due, bad = scan(spots, today)

    if a.json:
        print(json.dumps({
            "today": today.isoformat(),
            "recheck_days_before": RECHECK_DAYS_BEFORE,
            "expired": expired,
            "due": due,
            "bad": bad,
            "ok": not expired and not bad,
        }, ensure_ascii=False, indent=2))
        return 1 if (expired or bad) else 0

    print(f"今日: {today}　登録{len(spots)}件")

    if bad:
        print(f"\n!! 書式が不正（表示されないまま残る）: {len(bad)}件")
        for b in bad:
            print(f"   {b['id']}: {b['reason']} {b.get('until','')!r}")

    if expired:
        print(f"\n★期限切れ（表示は止まっているがデータが残っている）: {len(expired)}件")
        for e in expired:
            print(f"   {e['id']}  until={e['until']}（{-e['days_left']}日前に終了）")
            print(f"      {e['note']}")
            if e.get("onExpire"):
                print(f"      戻す作業: {e['onExpire']}")
    else:
        print("\n期限切れ: なし")

    if due:
        print(f"\n再確認の対象（期限まで{RECHECK_DAYS_BEFORE}日以内）: {len(due)}件")
        for d in due:
            print(f"   {d['id']}  until={d['until']}（あと{d['days_left']}日）")
            print(f"      {d['note']}")
            if d.get("source"):
                print(f"      根拠: {d['source']}")
    else:
        print(f"再確認の対象（期限まで{RECHECK_DAYS_BEFORE}日以内）: なし")

    print(f"\n[key] 期限切れ={len(expired)} 再確認={len(due)} 書式不正={len(bad)}")
    return 1 if (expired or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
