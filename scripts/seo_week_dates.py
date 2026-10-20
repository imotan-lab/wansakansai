#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""週次レポートの対象週と、開くURLを出す（2026-10-20）。

累積CSV（seo_daily.csv）に7日そろっている最後の月曜〜日曜を「今週」とし、
前の週・直近28日・その前の28日の期間と、Search Console / GA4 の開くURLを1行ずつ出す。
タスクは日付を自分で計算せず、ここに出たURLをそのまま開く。

使い方:
    python scripts/seo_week_dates.py --csv C:/Users/imao_/Documents/wansakansai/seo_daily.csv
    python scripts/seo_week_dates.py --csv ... --json     … 機械向け
"""
import argparse
import csv
import datetime as dt
import io
import json
import sys

GSC = ("https://search.google.com/search-console/performance/search-analytics?resource_id=https%3A%2F%2Fwansakansai.com%2F"
       "&start_date={a}&end_date={b}&breakdown={bd}&metrics=CLICKS%2CIMPRESSIONS%2CCTR%2CPOSITION")
# GA4 のプロパティ（表示名は「犬阪んさい」・アカウント「うちどころ」の下。2026-10-20に確認）
GA4 = ("https://analytics.google.com/analytics/web/#/a388917488p530354793/reports/explorer?params="
       "_u.date00%3D{a}%26_u.date01%3D{b}%26_u.date10%3D{c}%26_u.date11%3D{d}{extra}&r={r}")
SRC = "%26_r.explorerCard..seldim%3D%5B%22sessionSourceMedium%22%5D"


def ymd(d):
    return d.strftime("%Y%m%d")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    days = set()
    for r in csv.DictReader(io.open(a.csv, encoding="utf-8-sig")):
        days.add(dt.date.fromisoformat(r["date"].strip().replace("/", "-")))
    last = max(days)
    mon = last - dt.timedelta(days=last.weekday())
    if (last - mon).days < 6:          # 最後の週が7日そろっていなければひとつ前
        mon -= dt.timedelta(days=7)
    sun = mon + dt.timedelta(days=6)
    pmon, psun = mon - dt.timedelta(days=7), mon - dt.timedelta(days=1)
    l28a, l28b = sun - dt.timedelta(days=27), sun
    p28a, p28b = l28a - dt.timedelta(days=28), l28a - dt.timedelta(days=1)
    out = {
        "this_week": [mon.isoformat(), sun.isoformat()], "prev_week": [pmon.isoformat(), psun.isoformat()],
        "last28": [l28a.isoformat(), l28b.isoformat()], "prev28": [p28a.isoformat(), p28b.isoformat()],
        "url": {
            "gsc_query_prev": GSC.format(a=ymd(pmon), b=ymd(psun), bd="query"),
            "gsc_query_this": GSC.format(a=ymd(mon), b=ymd(sun), bd="query"),
            "gsc_page_prev": GSC.format(a=ymd(pmon), b=ymd(psun), bd="page"),
            "gsc_page_this": GSC.format(a=ymd(mon), b=ymd(sun), bd="page"),
            "gsc_page_last28": GSC.format(a=ymd(l28a), b=ymd(l28b), bd="page"),
            "ga4_users": GA4.format(a=ymd(mon), b=ymd(sun), c=ymd(pmon), d=ymd(psun), extra="", r="lifecycle-user-acquisition-v2"),
            "ga4_channels": GA4.format(a=ymd(mon), b=ymd(sun), c=ymd(pmon), d=ymd(psun), extra="", r="lifecycle-traffic-acquisition-v2"),
            "ga4_sources": GA4.format(a=ymd(mon), b=ymd(sun), c=ymd(pmon), d=ymd(psun), extra=SRC, r="lifecycle-traffic-acquisition-v2"),
            "ga4_events": GA4.format(a=ymd(mon), b=ymd(sun), c=ymd(pmon), d=ymd(psun), extra="", r="top-events"),
        },
    }
    if a.json:
        print(json.dumps(out, ensure_ascii=False))
        return 0
    for k in ("this_week", "prev_week", "last28", "prev28"):
        print(f"{k}: {out[k][0]}〜{out[k][1]}")
    for k, v in out["url"].items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
