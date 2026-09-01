#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Search Consoleの画面テキストを読んで、日別データの累積CSVに取り込む。

Search Consoleの「日付」タブは1行が
    日付 + クリック数 + 表示回数 + CTR + % + 掲載順位
の順で並ぶが、画面テキストとして取り出すと区切りが消えて連結される。
    2026/08/29 81 1,976 4.1% 9.2  →  "2026/08/29811,9764.1%9.2"
そこでクリック数と表示回数の切れ目を総当たりし、
「その組み合わせで文字列を組み直したら元と完全一致するか」で正解を一意に決める。
さらに CTR = クリック / 表示 と合うかも確認する。両方を満たす分け方は実際上ひとつしかない。

取り込み先は累積CSV。同じ日付があれば新しい方で上書きする
（Search Consoleの数字は数日かけて確定するため、後から取った値の方が正しい）。
画面に出るのは直近3か月だが、毎週足していけば履歴はそれより長く残る。

使い方:
    python scripts/seo_ingest.py --raw raw.txt --csv C:/.../seo_daily.csv
"""
import argparse
import csv
import datetime
import io
import os
import re
import shutil
import sys

FIELDS = ["date", "clicks", "impressions", "ctr", "position"]


def solve_spaced(rec):
    """区切りが残っている場合。素直に読めるのでこちらを先に試す。

    Chrome MCPの get_page_text は「2026/08/29 81 1,976 4.1% 9.2」のように
    空白区切りで返す。区切りが消えるのは表を画像や別経路から写した場合。
    """
    # 末尾は $ で閉じない。最後の行のうしろにはページ送りの文言が続くため
    # （閉じると最終行だけ区切りなし側に落ち、掲載順位に次の文字の数字がくっつく）
    m = re.match(r"^(\d{4}/\d{2}/\d{2})\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)\s*%\s+([\d.]+)(?=\s|$)",
                 rec)
    if not m:
        return None
    date, c, i, ctr, pos = m.groups()
    c, i = int(c.replace(",", "")), int(i.replace(",", ""))
    if i == 0 or c > i:
        return None
    if abs(c / i * 100 - float(ctr)) > 0.06:      # 区切りがあってもCTRの整合は確認する
        return None
    return {"date": date.replace("/", "-"), "clicks": c, "impressions": i,
            "ctr": float(ctr), "position": float(pos)}


def solve(rec):
    """区切りが消えている場合。1レコード分の文字列を数値に分解する。決まらなければ None。"""
    m = re.match(r"^(\d{4}/\d{2}/\d{2})(.*)%([\d.]+)", rec)
    if not m:
        return None
    date, mid, pos = m.groups()
    try:
        pos = float(pos)
    except ValueError:
        return None
    if not (0 < pos < 200):
        return None

    sols = []
    # CTRは中間部分の末尾。"N" "N.N" "NN" "NN.N" のいずれか
    for n in (1, 2, 3, 4):
        ctr_s = mid[-n:]
        if not re.fullmatch(r"\d+(\.\d)?", ctr_s):
            continue
        head = mid[:len(mid) - n]              # クリック数+表示回数（カンマ入り）
        digits = head.replace(",", "")
        if not digits.isdigit() or len(digits) < 2:
            continue
        for k in range(1, len(digits)):
            if digits[k] == "0":               # 表示回数が0始まりはあり得ない
                continue
            c, i = int(digits[:k]), int(digits[k:])
            if i == 0 or c > i:                # クリックが表示を超えることはない
                continue
            if f"{c}{i:,}" != head:            # カンマの位置まで含めて完全一致するか
                continue
            if abs(c / i * 100 - float(ctr_s)) > 0.06:
                continue
            sols.append({"date": date.replace("/", "-"), "clicks": c,
                         "impressions": i, "ctr": float(ctr_s), "position": pos})
    # 同じ答えが複数の切り方で出ることがあるので中身で重複を除く
    uniq = {(r["clicks"], r["impressions"], r["ctr"]): r for r in sols}
    return list(uniq.values())[0] if len(uniq) == 1 else None


def parse_raw(text):
    """画面テキストからレコードを拾う。読めた行と読めなかった行を返す。"""
    chunks = [p.strip() for p in re.split(r"(?=\d{4}/\d{2}/\d{2})", text) if p.strip()]
    ok, ng = [], []
    for ch in chunks:
        if not re.match(r"^\d{4}/\d{2}/\d{2}", ch):
            continue                            # 表の前にある見出しなど
        # グラフのX軸の目盛りも日付として拾えてしまう。表の行はCTRの % が近くに必ず来るので、
        # 空白を除いた先頭40文字に % が無いものは表の行ではないとみなして黙って飛ばす
        packed = re.sub(r"\s+", "", ch)
        if "%" not in packed[:40]:
            continue
        r = solve_spaced(ch) or solve(packed)
        if r:
            ok.append(r)
        else:
            ng.append(ch[:70])
    return ok, ng


def load_csv(path):
    if not os.path.exists(path):
        return {}
    out = {}
    with io.open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["date"]] = {
                "date": r["date"],
                "clicks": int(r["clicks"]),
                "impressions": int(r["impressions"]),
                "ctr": float(r["ctr"]),
                "position": float(r["position"]),
            }
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="Search Consoleの画面テキストを保存したファイル")
    ap.add_argument("--csv", required=True, help="累積CSVのパス（無ければ新規作成）")
    ap.add_argument("--expect-clicks", type=int, default=0,
                    help="画面に出ている期間合計クリック数。指定すると突き合わせて検算する")
    ap.add_argument("--max-unreadable", type=int, default=3,
                    help="読めない行がこの数を超えたら失敗として終了する")
    a = ap.parse_args()

    text = io.open(a.raw, encoding="utf-8", errors="replace").read()
    rows, bad = parse_raw(text)

    if not rows:
        print("!! 1行も読み取れなかった。画面テキストの取り方を確認すること")
        return 1
    if bad:
        print(f"読み取れなかった行: {len(bad)} 件")
        for b in bad[:8]:
            print("   ", b)
        if len(bad) > a.max_unreadable:
            print(f"!! 読めない行が {a.max_unreadable} 件を超えたため取り込みを中止する")
            return 1

    got = sum(r["clicks"] for r in rows)
    dates = sorted(r["date"] for r in rows)
    print(f"読み取り: {len(rows)}日分（{dates[0]} 〜 {dates[-1]}） クリック合計 {got:,}")

    if a.expect_clicks:
        # 画面の合計と1件でもずれたら、桁の切り分けを間違えている可能性が高い
        diff = abs(got - a.expect_clicks)
        print(f"検算: 画面の合計 {a.expect_clicks:,} との差 {diff}")
        if diff > max(2, a.expect_clicks * 0.005):
            print("!! 合計が合わない。読み取りを見直すこと（取り込みは中止）")
            return 1

    cur = load_csv(a.csv)
    before = len(cur)
    added = updated = 0
    for r in rows:
        old = cur.get(r["date"])
        if old is None:
            added += 1
        elif (old["clicks"], old["impressions"]) != (r["clicks"], r["impressions"]):
            updated += 1
        cur[r["date"]] = r                       # 後から取った値を正とする

    os.makedirs(os.path.dirname(os.path.abspath(a.csv)) or ".", exist_ok=True)
    if os.path.exists(a.csv):
        shutil.copy2(a.csv, a.csv + ".bak")       # 取り込み前の状態を1世代残す

    out = [cur[k] for k in sorted(cur)]
    with io.open(a.csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    first = datetime.date.fromisoformat(out[0]["date"])
    last = datetime.date.fromisoformat(out[-1]["date"])
    print(f"累積CSV: {before}日 → {len(out)}日（新規 {added} / 更新 {updated}）")
    print(f"保持期間: {first} 〜 {last}")
    print(f"[key] 取込={len(rows)}日 新規={added} 更新={updated} 累積={len(out)}日 "
          f"最新={out[-1]['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
