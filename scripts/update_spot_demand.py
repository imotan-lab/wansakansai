#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""スポットごとの検索需要（Search Console のページ別 表示回数・クリック数）を保存する（2026-09-25導入）。

なぜ要るか:
  Xの「今日のおすすめ」（scripts/post_daily_spot.py）を、需要のあるスポットを中心に選ぶため。
  運営者は休みの日に需要のありそうなスポットを選んで写真を撮りに行っている。投稿も需要に合わせる。

データの取り方（週次SEOタスク wansakansai-weekly-seo が毎週更新する）:
  Search Console の「ページ」タブを期間指定で開くと、表は10行ずつしか見えないが、
  ページの中（DOM）には全行が入っている。JSで `spots/{id}.html` の行だけ
  「id:クリック:表示回数」を空白区切りで取り出し、テキストファイルに書いて渡す。

使い方:
  python scripts/update_spot_demand.py --in rows.txt --start 2026-06-24 --end 2026-09-22
    rows.txt … 「settsu-kyo-park:216:3059 kataonanami-park:204:2224 …」（空白か改行区切り）
  python scripts/update_spot_demand.py --show   … 保存済みの中身を表示回数の多い順に出す

保存先はローカルのみ（Search Console の数字を公開リポジトリに載せない）:
  C:/Users/imao_/Documents/wansakansai/spot_demand.json
直前の状態は .bak に1世代残す。取り込みが少なすぎる（50件未満）時は壊れた取得とみなして保存しない。
"""
import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEMAND_PATH = Path("C:/Users/imao_/Documents/wansakansai/spot_demand.json")
ROW_RE = re.compile(r"^([a-z0-9-]+):(\d+):(\d+)$")
MIN_ROWS = 50


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()

    if a.show:
        d = json.loads(DEMAND_PATH.read_text(encoding="utf-8"))
        print("期間", d["start"], "〜", d["end"], "取得", d["fetched"], len(d["spots"]), "件")
        for sid, v in sorted(d["spots"].items(), key=lambda kv: -kv[1]["impressions"])[:30]:
            print(f"  {v['impressions']:>6} {v['clicks']:>4}  {sid}")
        return 0

    if not (a.infile and a.start and a.end):
        ap.error("--in と --start と --end が要る")
    tokens = Path(a.infile).read_text(encoding="utf-8").split()
    spots, bad = {}, []
    for t in tokens:
        m = ROW_RE.match(t.strip())
        if not m:
            bad.append(t)
            continue
        spots[m.group(1)] = {"clicks": int(m.group(2)), "impressions": int(m.group(3))}
    print(f"読み取り {len(spots)}件 / 読めない {len(bad)}件" + (f"（例: {bad[:3]}）" if bad else ""))
    if len(spots) < MIN_ROWS:
        print(f"★{MIN_ROWS}件未満なので取得が壊れているとみなし、保存しない（前の値をそのまま使う）")
        return 1
    if DEMAND_PATH.exists():
        shutil.copy2(DEMAND_PATH, DEMAND_PATH.with_suffix(".json.bak"))
    DEMAND_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEMAND_PATH.write_text(json.dumps({
        "source": "Search Console ページ別（spots/{id}.html）",
        "start": a.start, "end": a.end,
        "fetched": datetime.now().isoformat(timespec="seconds"),
        "spots": spots,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"保存: {DEMAND_PATH} {len(spots)}件 期間 {a.start}〜{a.end}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
