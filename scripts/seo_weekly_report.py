#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""週次レポート（3ページ・横長PDF）を作る（2026-10-20に入れ替え。旧版は seo_report.py）。

構成はCodexと2巡相談して決めた（Documents/wansakansai/weekly_report_redesign/）:
  1. 今週の状況と次にやること  2. 数字の中身（12週・言葉・ページの動き）  3. 前にやったことの経過・準備の進み具合・アフィリエイトとSNS
数字は seo_week_build.py が作る data JSON、文章はタスクが書いてCodexと突き合わせた notes JSON。

notes の形:
  {"headline": str, "facts": [str, …], "guess": str, "actions": [{"what","why","done"}, …（0〜3件）],
   "no_more_actions": str, "followups": [[日付, やったこと, 今の状態, 言えること・次に見ること], …], "chart_read": str}
  今の状態が「出始めた」「効果あり」なら緑、「まだ」を含めば橙、ほかは灰色で表示する。

使い方:
  python scripts/seo_weekly_report.py --data data.json --notes notes.json --out-dir 出力先
  → wansakansai_weekly_YYYY-MM-DD.pdf（対象週の月曜）。[key] 行を出す
"""
import argparse
import io
import json
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages

CREAM, INK, MUTE, RULE = "#faf7f2", "#3f3a33", "#7a7266", "#dfd7c9"
GREEN, GRAY, ACCENT = "#5c8a5c", "#c4bcae", "#c2703d"
W, H = 13.333, 7.5
NL = chr(10)
plt.rcParams["font.family"] = "Yu Gothic"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.edgecolor"] = "#b9b0a2"
plt.rcParams["xtick.color"] = MUTE
REQUIRED = ("headline", "facts", "guess", "actions", "no_more_actions", "followups", "chart_read")


def T(fig, s, x, y, size=12, color=INK, weight="normal", ha="left"):
    fig.text(x / W, 1 - y / H, s, fontsize=size, color=color, fontweight=weight, va="top", ha=ha, linespacing=1.6)


def HR(fig, x, y, w, color=RULE, lw=1.0):
    fig.add_artist(plt.Line2D([x / W, (x + w) / W], [1 - y / H, 1 - y / H], color=color, lw=lw, transform=fig.transFigure))


def box(fig, x, y, w, h):
    fig.add_artist(plt.Rectangle((x / W, 1 - (y + h) / H), w / W, h / H, transform=fig.transFigure,
                                 facecolor="white", edgecolor=RULE, lw=1.0, zorder=0))


def wrap(s, n):
    return NL.join(textwrap.wrap(str(s), n)) if s else ""


def page(figs, title, sub):
    fig = plt.figure(figsize=(W, H), dpi=150)
    fig.patch.set_facecolor(CREAM)
    figs.append(fig)
    T(fig, title, 0.6, 0.4, size=21, weight="bold")
    T(fig, sub, 0.6, 0.98, size=10.5, color=MUTE)
    HR(fig, 0.6, 1.35, 12.1)
    return fig


def card(fig, x, y, label, pair, unit, src):
    box(fig, x, y, 3.85, 1.45)
    T(fig, label, x + 0.2, y + 0.12, size=11, color=MUTE)
    T(fig, src, x + 3.7, y + 0.15, size=8.5, color=MUTE, ha="right")
    if not pair:
        T(fig, "取れず", x + 0.2, y + 0.45, size=22, weight="bold", color=MUTE)
        return
    now, before = pair
    T(fig, f"{now:,}{unit}", x + 0.2, y + 0.45, size=25, weight="bold", color=GREEN if now >= before else ACCENT)
    T(fig, f"前の週 {before:,}{unit}（{now - before:+,}）", x + 0.2, y + 1.08, size=10, color=MUTE)


def chart(weeks, path):
    labels = [f"{int(w['monday'][5:7])}/{int(w['monday'][8:10])}〜" for w in weeks]
    vals = [w["clicks"] for w in weeks]
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    b = ax.bar(labels, vals, color=[GRAY] * (len(vals) - 1) + [ACCENT], width=0.64)
    ax.bar_label(b, labels=[f"{v:,}" for v in vals], padding=2, fontsize=8.5)
    ax.set_ylim(0, max(vals) * 1.18 or 1)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="x", labelsize=7.5)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def jp(iso):
    return f"{int(iso[5:7])}月{int(iso[8:10])}日"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    d = json.load(io.open(a.data, encoding="utf-8"))
    n = json.load(io.open(a.notes, encoding="utf-8"))
    miss = [k for k in REQUIRED if k not in n]
    if miss:
        print("[error] notes に足りない項目:", miss)
        return 1
    g, ga, s = d["gsc"], d.get("ga4"), d["site"]
    tw, pw = d["period"]["this_week"], d["period"]["prev_week"]
    period = f"{jp(tw[0])}（月）〜{jp(tw[1])}（日）　前の週＝{jp(pw[0])}〜{jp(pw[1])}"
    figs = []
    overflow = []

    # 1 ---------------------------------------------------------------
    fig = page(figs, "今週の状況と、次にやること", period)
    T(fig, wrap(n["headline"], 62), 0.6, 1.55, size=14, weight="bold", color=GREEN)
    card(fig, 0.6, 2.1, "サイトに来た人", ga["users"] if ga else None, "人", "GA4・全部の入口")
    card(fig, 4.7, 2.1, "Google検索から押された回数", [g["this_week"]["clicks"], g["prev_week"]["clicks"]], "回", "Search Console")
    card(fig, 8.8, 2.1, "Yahoo!検索からの訪問", ga["yahoo"] if ga else None, "回", "GA4")
    y = 3.75
    for f in n["facts"][:4]:
        t = textwrap.wrap("・" + f, 92)
        T(fig, NL.join(t), 0.6, y, size=10.5)
        y += 0.32 * len(t) + 0.02
    t = textwrap.wrap(n["guess"], 100)
    T(fig, NL.join(t), 0.6, y + 0.02, size=10, color=MUTE)
    y += 0.3 * len(t) + 0.25
    T(fig, "次にやること", 0.6, y, size=13, weight="bold", color=GREEN)
    y += 0.42
    for i, ac in enumerate(n["actions"][:3], 1):
        why = textwrap.wrap("根拠：" + ac["why"], 88)
        done = textwrap.wrap("終わり：" + ac["done"], 88)
        hh = 0.5 + 0.24 * (len(why) + len(done))
        box(fig, 0.6, y, 12.1, hh)
        T(fig, f"{i}. {ac['what']}", 0.8, y + 0.1, size=12, weight="bold")
        T(fig, NL.join(why), 0.8, y + 0.42, size=9.5)
        T(fig, NL.join(done), 0.8, y + 0.42 + 0.24 * len(why), size=9.5, color=MUTE)
        y += hh + 0.1
    if not n["actions"]:
        T(fig, "今週は、データから勧められる作業はありません。", 0.6, y, size=11)
        y += 0.35
    T(fig, wrap(n["no_more_actions"], 110), 0.6, y, size=9.5, color=MUTE)
    y += 0.3 * max(1, len(textwrap.wrap(n["no_more_actions"], 110)))
    if y > 7.45:
        overflow.append(f"1ページ目（下端 {y:.1f}／7.45インチ）")
    if d.get("ga4_note"):
        T(fig, "※ " + d["ga4_note"], 0.6, 7.1, size=8.5, color=ACCENT)

    # 2 ---------------------------------------------------------------
    fig = page(figs, "数字の中身", "Google検索の数字（Search Console）。Yahoo!検索の分は含みません")
    cp = os.path.join(a.out_dir, "charts_weekly.png")
    chart(g["weeks12_clicks"], cp)
    im = mpimg.imread(cp)
    w = 5.4
    h = w * im.shape[0] / im.shape[1]
    ax = fig.add_axes([0.5 / W, 1 - (1.85 + h) / H, w / W, h / H])
    ax.imshow(im)
    ax.axis("off")
    T(fig, "週ごとの、Google検索から押された回数（オレンジが今週）", 0.6, 1.5, size=10, weight="bold")
    T(fig, "押された回数の多い言葉", 7.0, 1.5, size=10, weight="bold")
    cols = [("言葉", 3.0, False), ("押された", 0.9, True), ("出た", 0.9, True), ("前の週に出た", 1.2, True)]
    cx = 7.0
    for nm, wd, right in cols:
        T(fig, nm, cx + (wd if right else 0), 1.85, size=9, color=MUTE, ha="right" if right else "left")
        cx += wd
    HR(fig, 7.0, 2.12, 6.0)
    yy = 2.2
    for qq in g["queries_top"][:8]:
        pv = qq["prev_impressions"]
        vals = [qq["q"][:18], qq["clicks"], qq["impressions"], "少ない" if pv is None else pv]
        cx = 7.0
        for (nm, wd, right), v in zip(cols, vals):
            T(fig, str(v), cx + (wd if right else 0), yy, size=9.5, ha="right" if right else "left")
            cx += wd
        yy += 0.27
    qs = g["query_summary"]
    T(fig, f"言葉まで分かるのは押された回数の約{qs['known_clicks'] / max(qs['screen_clicks'], 1) * 100:.0f}%"
           f"（{qs['known_clicks']}／{qs['screen_clicks']}回）。残りは表に出てきません（Googleが伏せる・表の上限）。", 7.0, yy + 0.02, size=8, color=MUTE)
    T(fig, "読み取れること", 7.0, 4.75, size=10, weight="bold")
    T(fig, wrap(n["chart_read"].replace(NL, ""), 38), 7.0, 5.05, size=9.5, color=MUTE)
    T(fig, "ページの動き（押された回数　前の週→今週）", 0.6, 5.55, size=10, weight="bold")
    fmt = lambda xs: "、".join(f"{x['name']} {x['prev']}→{x['now']}" for x in xs) or "なし"
    T(fig, wrap("増えた：" + fmt(g["pages_up"][:5]), 105), 0.6, 5.9, size=9.5)
    T(fig, wrap("減った：" + fmt(g["pages_down"][:5]), 105), 0.6, 6.22, size=9.5)
    newp = [x for x in g["pages_new"] if x["impressions"] >= 5][:3]
    T(fig, wrap("新しく出始めた：" + ("、".join(f"{x['name']}（{x['impressions']}回出て{x['clicks']}回押された）" for x in newp) or "なし"), 92),
      0.6, 6.54, size=9.5)
    T(fig, "※「新しく出始めた」は前の週に1回も出ていなかったページ（5回以上出たものだけ）。初めてGoogleに載ったという意味ではありません。", 0.6, 7.05, size=8, color=MUTE)

    # 3 ---------------------------------------------------------------
    fig = page(figs, "前にやったことの経過と、準備の進み具合", "効果は数週間たたないと分からないものが多いので、「判断保留」もそのまま書きます")
    T(fig, n.get("checked_by") or "数字の読み取りは、2つのAI（Claude・Codex）が別々に行い、突き合わせて食い違いを直してから載せています。",
      12.7, 0.98, size=8.5, color=MUTE, ha="right")
    hdr = [("日付", 0.6), ("やったこと", 1.3), ("今の状態", 4.7), ("データから言えること・次に見ること", 6.6)]
    for nm, x in hdr:
        T(fig, nm, x, 1.6, size=9, color=MUTE)
    HR(fig, 0.6, 1.88, 12.1)
    yy = 1.98
    for f in n["followups"][:5]:   # 6件以上は1ページに収まらない（10/23に6件で下端が切れた）。古い・判断の済んだものから外す
        lines = textwrap.wrap(f[3], 46)
        what = textwrap.wrap(f[1], 19)
        st = f[2]
        stl = textwrap.wrap(st, 10)   # 2026-10-23: 長い状態が右の欄に重なった
        col = GREEN if st in ("出始めた", "効果あり") else (ACCENT if "まだ" in st else MUTE)
        T(fig, f[0], 0.6, yy, size=9.5)
        T(fig, NL.join(what), 1.3, yy, size=9.5)
        T(fig, NL.join(stl), 4.7, yy, size=9.5, color=col, weight="bold")
        T(fig, NL.join(lines), 6.6, yy, size=9)
        yy += max(0.3, 0.26 * max(len(lines), len(what), len(stl))) + 0.04
        HR(fig, 0.6, yy - 0.05, 12.1, color="#eee8de", lw=0.8)
    y0 = yy + 0.15
    T(fig, "AdSense再申請に向けた準備（運営者が決めた目標。達成しても合格が約束されるものではありません）", 0.6, y0, size=10.5, weight="bold", color=GREEN)
    tg = s["targets"]
    prog = [("写真のあるスポット", s["spots_with_photo"], tg["spots_with_photo"], "件"),
            ("ブログ", s["blog_posts"], tg["blog_posts"], "本"),
            ("直近4週間のクリック上位10スポットのうち写真あり", s["top10_with_photo"], tg["top10_with_photo"], "件")]
    yy = y0 + 0.45
    for label, now, goal, u in prog:
        T(fig, label, 0.6, yy, size=10.5)
        T(fig, f"{now}{u} ／ 目標{goal}{u}", 7.2, yy, size=10.5, weight="bold", ha="right")
        T(fig, f"あと{max(goal - now, 0)}{u}" if now < goal else "達成", 8.4, yy, size=10.5,
          color=ACCENT if now < goal else GREEN, weight="bold")
        yy += 0.34
    T(fig, "そのほか（数字だけ）", 0.6, yy + 0.2, size=10.5, weight="bold", color=GREEN)
    if ga:
        af, au, x = ga["affiliate_click"], ga["affiliate_users"], ga["x"]
        T(fig, f"・宿や楽天のリンクが押された回数：{af[0]}回（前の週{af[1]}回）。押した人は{au[0]}人。予約や売上までは分かりません。", 0.6, yy + 0.58, size=10)
        T(fig, f"・X（旧Twitter）からの訪問：{x[0]}回（前の週{x[1]}回）　ChatGPTからの訪問：{ga['chatgpt'][0]}回（前の週{ga['chatgpt'][1]}回）", 0.6, yy + 0.9, size=10)
    else:
        T(fig, "・GA4の数字が取れなかったため、今週は載せていません。", 0.6, yy + 0.58, size=10)
    if yy + 1.1 > 7.45:
        overflow.append(f"3ページ目（下端 {yy + 1.1:.1f}／7.45インチ）")

    out = os.path.join(a.out_dir, f"wansakansai_weekly_{tw[0]}.pdf")
    with PdfPages(out) as pdf:
        for f in figs:
            pdf.savefig(f, facecolor=f.get_facecolor())
            plt.close(f)
    print("PDF :", out)
    if overflow:
        print("[layout] はみ出し:", "・".join(overflow), "→ notes の文を短くするか件数を減らして作り直す")
        return 3
    print(f"[key] 期間={tw[0][5:].replace('-', '/')}〜{tw[1][5:].replace('-', '/')} クリック={g['this_week']['clicks']} "
          f"前週={g['prev_week']['clicks']} 人数={ga['users'] if ga else '取れず'} ページ数=3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
