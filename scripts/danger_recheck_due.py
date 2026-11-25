#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""危険情報のうち「元の発表を確かめ直す日が来たもの」を出す（2026-11-25導入）。

決まり（運営者と決定。日数は試しの値で、運用を見て直してよい）:
  - basis = report（報道・SNSの報告だけ）… 最後に確かめた日（checked）から 14日 で確かめ直す
  - basis = official（自治体など公式が出している）… 30日 で確かめ直す
  - checked が無いものは、すぐ確かめ直す対象
  - expires の付いたもの（終わる日が分かっている）は対象にしない。expire_dangers.py が期限で消す

このスクリプトは「対象を出す」だけで、消さない・書き換えない。
確かめ直した結果（残す／書き換える／消す）は、自動タスク（wansakansai-danger-update の STEP 4）が
元の発表を開いて判断する。日数が来たことだけを理由に消さない。

使い方:
    python scripts/danger_recheck_due.py              # 対象を表示
    python scripts/danger_recheck_due.py --json       # 機械が読む形
    python scripts/danger_recheck_due.py --today 2026-12-20   # 日付を指定（テスト用）
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
DAYS = {"report": 14, "official": 30}
# 「未確認」（checked が無い）は正常。次のものだけが異常
ABNORMAL = {"行の形が不正", "basisが不正", "checkedが不正", "checkedが未来", "expiresが不正"}


def parse_date(v):
    """YYYY-MM-DD の実在する日付なら date、そうでなければ None（型が違っても落ちない）。"""
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()):
        return None
    try:
        return datetime.date.fromisoformat(v.strip())
    except ValueError:
        return None


def due_list(entries, today):
    out = []
    for e in entries:
        if not isinstance(e, dict):
            out.append({"id": None, "basis": None, "checked": None, "due": "行の形が不正", "summary": ""})
            continue
        eid = e.get("id")
        summary = e.get("summary") if isinstance(e.get("summary"), str) else ""
        exp_raw = e.get("expires")
        if exp_raw not in (None, ""):
            # 期限が正しく付いているものは expire_dangers.py に任せる。期限が壊れていたら確かめ直しに回す
            if parse_date(exp_raw) is not None:
                continue
            out.append({"id": eid, "basis": e.get("basis"), "checked": e.get("checked"), "due": "expiresが不正", "summary": summary})
            continue
        if not (isinstance(e.get("basis"), str) and e.get("basis") in DAYS):
            out.append({"id": eid, "basis": e.get("basis"), "checked": e.get("checked"), "due": "basisが不正", "summary": summary})
            continue
        basis = e["basis"]
        span = DAYS[basis]
        chk_raw = e.get("checked")
        if chk_raw in (None, ""):
            out.append({"id": eid, "basis": basis, "checked": None, "due": "未確認", "summary": summary})
            continue
        chk = parse_date(chk_raw)
        if chk is None:
            out.append({"id": eid, "basis": basis, "checked": chk_raw, "due": "checkedが不正", "summary": summary})
            continue
        if chk > today:
            out.append({"id": eid, "basis": basis, "checked": chk_raw, "due": "checkedが未来", "summary": summary})
            continue
        if (today - chk).days >= span:
            out.append({"id": eid, "basis": basis, "checked": chk_raw, "due": (chk + datetime.timedelta(days=span)).isoformat(), "summary": summary})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--today", default=None)
    ap.add_argument("--path", default=str(DANGERS))
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if a.today:
        today = parse_date(a.today)
        if today is None:
            ap.error(f"--today は YYYY-MM-DD の実在する日付で: {a.today!r}")
    else:
        today = datetime.date.today()
    try:
        entries = json.load(io.open(a.path, encoding="utf-8-sig"))
    except (OSError, ValueError) as ex:
        print(f"[ERROR] dangers.json を読めない（JSONの書き方の誤りなど）: {ex}")
        return 1
    if not isinstance(entries, list):
        print("[ERROR] dangers.json が配列になっていない", file=sys.stderr)
        return 1
    due = due_list(entries, today)
    if a.json:
        print(json.dumps({"today": today.isoformat(), "due": due}, ensure_ascii=False))
        return 2 if any(d["due"] in ABNORMAL for d in due) else 0
    print(f"今日: {today}　全{len(entries)}件　確かめ直す対象: {len(due)}件")
    for d in due:
        print(f"   {d['id']}  basis={d['basis']}  checked={d['checked']}  期日={d['due']}  {d['summary'][:40]}")
    abnormal = [d for d in due if d["due"] in ABNORMAL]
    print(f"[key] 確かめ直し={len(due)} 異常={len(abnormal)}")
    # 異常（行の形・basis・checked・expires の不正）がある日は 2 で終わる。タスクはその日の削除を止める
    return 2 if abnormal else 0


if __name__ == "__main__":
    sys.exit(main())
