#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""週次レポートのデータを1つのJSONにまとめる（2026-10-20）。

入力（どれもタスクが画面から取った値を加工せずに書いたもの。取り方は docs/weekly_seo_capture.md）:
  --csv      累積の日別CSV（seo_daily.csv）
  --queries  Search Console 検索語句（今週・前の週の突き合わせ済み）
  --pages    Search Console ページ（今週・前の週・直近28日）
  --ga4      GA4（無ければ省略可。省略・期間違いならGA4の欄は「取れず」になる）
  --actions  前にやったことの記録（Documents/wansakansai/weekly_actions.json）
出力: --out に data JSON。標準出力に [key] と [check] の行。

検算（合わなければ終了コード1。数字を作らないため）:
  - 検索語句の画面の合計クリックが、CSVの今週のクリック合計と2%以内で一致すること
  - GA4の各表の period が今週の日付であること（違えばGA4を使わず warn）
"""
import argparse
import csv
import datetime as dt
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME = {"koyo": "紅葉", "sakura": "桜", "dogrun": "ドッグラン", "dogrun-free": "無料ドッグラン", "water": "水遊び",
         "rain": "雨でもOK", "free": "完全無料", "index": "一覧"}


def load_csv(p):
    rows = {}
    for r in csv.DictReader(io.open(p, encoding="utf-8-sig")):
        rows[dt.date.fromisoformat(r["date"].strip().replace("/", "-"))] = (int(r["clicks"]), int(r["impressions"]))
    return rows


def total(rows, a, b):
    sel = [v for d, v in rows.items() if a <= d <= b]
    return {"days": len(sel), "clicks": sum(v[0] for v in sel), "impressions": sum(v[1] for v in sel)}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    for k in ("csv", "queries", "pages", "actions", "out"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--ga4")
    a = ap.parse_args()

    daily = load_csv(a.csv)
    last = max(daily)
    mon = last - dt.timedelta(days=last.weekday())
    if (last - mon).days < 6:
        mon -= dt.timedelta(days=7)
    sun = mon + dt.timedelta(days=6)
    pmon = mon - dt.timedelta(days=7)
    l28a = sun - dt.timedelta(days=27)
    p28a, p28b = l28a - dt.timedelta(days=28), l28a - dt.timedelta(days=1)

    spots = {s["id"]: s for s in json.load(io.open(os.path.join(ROOT, "data", "spots.json"), encoding="utf-8"))}

    def name(pid):
        if pid == "top": return "トップページ"
        if pid == "index": return "全スポット一覧"
        if pid == "about": return "このサイトについて"
        if pid.startswith("themes/"): return "テーマ別「" + THEME.get(pid.split("/", 1)[1], pid) + "」"
        if pid.startswith("blog/"): return "ブログ：" + pid.split("/", 1)[1]
        return spots.get(pid, {}).get("name", pid)

    def photo(pid):
        return bool(spots[pid].get("images")) if pid in spots else None

    q = json.load(io.open(a.queries, encoding="utf-8"))
    p = json.load(io.open(a.pages, encoding="utf-8"))
    this = total(daily, mon, sun)
    ng = []
    sc = q["summary"]["screen_clicks"]
    if this["days"] != 7:
        ng.append(f"CSVの今週が{this['days']}日しかない")
    if abs(sc - this["clicks"]) > max(3, this["clicks"] * 0.02):
        ng.append(f"検索語句の画面の合計 {sc} とCSVの今週 {this['clicks']} が合わない（期間違いの疑い）")

    pw_days = total(daily, pmon, mon - dt.timedelta(days=1))["days"]
    if pw_days != 7:
        ng.append(f"CSVの前の週が{pw_days}日しかない（比べられない）")
    if p.get("summary", {}).get("prev_rows", 0) >= 1000:
        print("[warn] 前の週のページの表が1,000行の上限に届いた。『新しく出始めた』は表の外のページを含む恐れ")

    weeks12 = []
    for k in range(11, -1, -1):
        m = mon - dt.timedelta(days=7 * k)
        weeks12.append({"monday": m.isoformat(), **total(daily, m, m + dt.timedelta(days=6))})

    ga4, ga4_note = None, None
    if a.ga4 and os.path.exists(a.ga4):
        g = json.load(io.open(a.ga4, encoding="utf-8"))
        want = f"{mon.month}月{mon.day}日～{sun.year}年{sun.month}月{sun.day}日"
        bad = [k for k in ("users", "channels", "sources", "events") if str((g.get(k) or {}).get("period", "")) != want]
        if bad:
            ga4_note = f"GA4の期間が今週（{want}）と違う表がある（{', '.join(bad)}）ので使わない"
        else:
          try:
            src = g["sources"]["rows"]
            ch = g["channels"]["rows"]
            ev = g["events"]["rows"]
            # 行が無い＝その週にその流入元が無かった（GA4は0の行を出さない）。表そのものが無ければ下の except へ
            pick = lambda d, k: [d[k][0][0], d[k][1][0]] if k in d else [0, 0]
            assert g["users"]["total"] and len(g["users"]["total"]) == 2, "users の合計が無い"
            ga4 = {
                "users": g["users"]["total"],
                "sessions": g["channels"]["total"] or [sum(v[0][0] for v in ch.values()), sum(v[1][0] for v in ch.values())],
                "google": pick(src, "google / organic"), "yahoo": pick(src, "yahoo / organic"),
                "bing": pick(src, "bing / organic"), "x": pick(src, "t.co / referral"),
                "sns": pick(ch, "Organic Social"), "chatgpt": pick(src, "openai / organic"),
                "affiliate_click": pick(ev, "affiliate_click"),
                "affiliate_users": [ev["affiliate_click"][0][1], ev["affiliate_click"][1][1]] if "affiliate_click" in ev else [0, 0],
            }
          except (KeyError, IndexError, TypeError, AssertionError) as e:
            ga4, ga4_note = None, f"GA4の表の形が想定と違うので使わない（{type(e).__name__}: {e}）"
    else:
        ga4_note = "GA4のデータが無い（取れなかった）"

    top10 = [r for r in p["last28"] if r[0] in spots][:10]
    data = {
        "period": {"this_week": [mon.isoformat(), sun.isoformat()], "prev_week": [pmon.isoformat(), (mon - dt.timedelta(days=1)).isoformat()],
                   "last28": [l28a.isoformat(), sun.isoformat()], "prev28": [p28a.isoformat(), p28b.isoformat()]},
        "gsc": {
            "this_week": this, "prev_week": total(daily, pmon, mon - dt.timedelta(days=1)),
            "last28": total(daily, l28a, sun), "prev28": total(daily, p28a, p28b),
            "weeks12_clicks": weeks12,
            "query_summary": q["summary"],
            "queries_top": [{"q": r[0], "clicks": r[1], "impressions": r[2], "position": r[3], "prev_impressions": r[4]} for r in q["top"]],
            "queries_noclick": [{"q": r[0], "impressions": r[1], "position": r[2]} for r in q["noclick"]],
            "queries_grow": [{"q": r[0], "prev_impressions": r[1], "impressions": r[2], "clicks": r[3]} for r in q["grow"]],
            "pages_top": [{"id": r[0], "name": name(r[0]), "clicks": r[1], "impressions": r[2], "has_photo": photo(r[0])} for r in p["top"]],
            "pages_up": [{"id": r[0], "name": name(r[0]), "prev": r[1], "now": r[2]} for r in p["summary"]["up"]],
            "pages_down": [{"id": r[0], "name": name(r[0]), "prev": r[1], "now": r[2]} for r in p["summary"]["down"]],
            "pages_new": [{"id": r[0], "name": name(r[0]), "clicks": r[1], "impressions": r[2]} for r in p["new"]],
            "top10_spots_last28": [{"id": r[0], "name": name(r[0]), "clicks": r[1], "has_photo": photo(r[0])} for r in top10],
            "notes": ["Google検索だけの数字（Yahoo!検索は含まない）", "前の週の語句の表は最大1,000行。prev_impressions が null は前の週の表に無かった（少なかった）",
                      "pages_new は前の週に検索結果に1回も出なかったページ（初めてGoogleに載ったという意味ではない）"],
        },
        "ga4": ga4, "ga4_note": ga4_note,
        "site": {
            "spots_total": len(spots), "spots_with_photo": sum(1 for s in spots.values() if s.get("images")),
            "blog_posts": len([x for x in glob.glob(os.path.join(ROOT, "blog", "*.html")) if os.path.basename(x) != "index.html"]),
            "top10_with_photo": sum(1 for r in top10 if photo(r[0])),
            "targets": {"spots_with_photo": 30, "blog_posts": 6, "top10_with_photo": 5,
                        "note": "運営者が決めたAdSense再申請の準備目標（Googleの条件ではない）"},
        },
        "actions_log": json.load(io.open(a.actions, encoding="utf-8")) if os.path.exists(a.actions) else [],
    }
    json.dump(data, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pw = data["gsc"]["prev_week"]
    print(f"[key] 期間={mon:%m/%d}〜{sun:%m/%d} クリック={this['clicks']} 前週={pw['clicks']} "
          f"表示={this['impressions']} 人数={ga4['users'] if ga4 else '取れず'} 28日={data['gsc']['last28']['clicks']}/{data['gsc']['prev28']['clicks']}")
    if ga4_note:
        print("[warn]", ga4_note)
    for x in ng:
        print("[check] NG", x)
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
