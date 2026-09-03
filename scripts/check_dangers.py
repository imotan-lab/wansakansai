#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""危険情報（data/dangers.json）と、そこから作られるX投稿文を機械的に点検する。

★このスクリプトが見るのは「機械で確実に判定できること」だけ★
種別が中身に合っているか、期限を入れるべきかといった**判断が要ることは見ない**。
そちらはCodexとClaudeの2AIで確認する（SKILL.md の STEP 6.3）。

分担をこう決めた理由（2026-09-03）:
2026-09-03に危険情報のX投稿が括弧の途中で切れて公開された。原因はコードのバグで、
「括弧の数が合っているか」を数えれば0秒で確実に分かるものだった。
機械で判定できることをAIに投げると、遅くなるうえに見落としが入る。
逆に、種別が「事故」ばかりになっていた件は文字列では判定できない。だから分ける。

判定するもの:
  - 必須項目の欠け、idの重複・書式
  - date（YYYY-MM）・expires（YYYY-MM-DD）の書式、expiresがdateより前を向いていないか
  - typeが決められた語彙に入っているか
  - summaryの長さ
  - 括弧の対応（location / summary / description / 生成される投稿文）
  - HTMLタグの混入（自動更新のJSONがそのまま画面に出るため）
  - 生成される投稿文がXの上限を超えないか

使い方:
    python scripts/check_dangers.py            # 点検する（NGがあれば終了コード1）
    python scripts/check_dangers.py --quiet    # 問題がある行だけ出す
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

REQUIRED = ("id", "date", "location", "type", "summary", "description")

# ★種別の語彙（2026-09-03に整理）★
# それまでは「事故」が何でも入る箱になっていて、クマの出没も熱中症も台風も
# 全部「事故」になっていた（13件）。中身を読んで7つに分けた。
# 新しい種別を足す時は、既存のどれにも入らない時だけにすること。
ALLOWED_TYPES = {
    "毒餌",
    "毒餌の疑い",
    "感染症",
    "危険な生き物",   # クマ・イノシシ・マムシ・スズメバチ・セアカゴケグモなど
    "有毒なもの",     # カエンタケ・ヒガンバナ・ぎんなん・アオコなど口や皮膚から入るもの
    "気象・暑さ",     # 台風・大雨・熱中症・路面のやけど
    "その他の注意",   # 上のどれでもないもの（わな・花火の音による脱走など）
}

SUMMARY_MIN, SUMMARY_MAX = 25, 70   # SKILL.mdの目安は30〜60字。多少の幅は許す

PAIRS = (("（", "）"), ("(", ")"), ("「", "」"), ("【", "】"), ("『", "』"))
TAG_RE = re.compile(r"<[a-zA-Z/!][^>]*>")


def unbalanced(s: str):
    """対応が取れていない括弧を返す。空なら問題なし。"""
    return [f"{o}{c}" for o, c in PAIRS if (s or "").count(o) != (s or "").count(c)]


def check_entries(entries):
    """dangers.json の中身を点検して (問題のリスト) を返す。"""
    ng = []
    seen = set()
    today = datetime.date.today()

    for e in entries:
        eid = e.get("id") or "(idなし)"

        for k in REQUIRED:
            if not str(e.get(k) or "").strip():
                ng.append(f"{eid}: 必須項目が空 -> {k}")

        if not re.fullmatch(r"danger-\d{3}", str(e.get("id") or "")):
            ng.append(f"{eid}: idの書式が違う（danger-000 の形）")
        if e.get("id") in seen:
            ng.append(f"{eid}: idが重複している")
        seen.add(e.get("id"))

        date = str(e.get("date") or "")
        if not re.fullmatch(r"\d{4}-\d{2}", date):
            ng.append(f"{eid}: dateの書式が違う（YYYY-MM）-> {date!r}")

        exp = str(e.get("expires") or "").strip()
        if exp:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", exp):
                ng.append(f"{eid}: expiresの書式が違う（YYYY-MM-DD）-> {exp!r}")
            else:
                d = datetime.date.fromisoformat(exp)
                if re.fullmatch(r"\d{4}-\d{2}", date) and exp[:7] < date:
                    ng.append(f"{eid}: expires({exp})がdate({date})より前を向いている")
                if d < today:
                    # 期限切れをそのまま公開している状態。expire_dangers.py の実行漏れ
                    ng.append(f"{eid}: expires({exp})が過ぎている。expire_dangers.py --apply を実行すること")

        t = str(e.get("type") or "")
        if t not in ALLOWED_TYPES:
            ng.append(f"{eid}: 種別が語彙にない -> {t!r}（使える語: {'/'.join(sorted(ALLOWED_TYPES))}）")

        s = str(e.get("summary") or "")
        if s and not (SUMMARY_MIN <= len(s) <= SUMMARY_MAX):
            ng.append(f"{eid}: summaryの長さが{len(s)}字（目安{SUMMARY_MIN}〜{SUMMARY_MAX}字）")

        for k in ("location", "summary", "description"):
            v = str(e.get(k) or "")
            bad = unbalanced(v)
            if bad:
                ng.append(f"{eid}: {k} の括弧が閉じていない -> {' '.join(bad)}")
            if TAG_RE.search(v):
                ng.append(f"{eid}: {k} にHTMLタグらしき文字列がある")

    return ng


def check_posts(entries):
    """これから投稿される文面を実際に組み立てて点検する。

    投稿は post_danger_to_x.py が作る。同じ関数を呼んで確かめないと意味がないため、
    文面を作り直さずに import して使う。
    """
    ng = []
    try:
        sys.path.insert(0, str(BASE / "scripts"))
        sys.path.insert(0, "C:/Users/imao_/.claude")
        from post_danger_to_x import build_post_text, load_json, diff_entries, PREV_PATH
        from x_poster import count_x_weight, MAX_TWEET_WEIGHT
    except Exception as ex:
        return [f"投稿文の点検ができなかった（{type(ex).__name__}: {ex}）"], []

    prev = load_json(PREV_PATH, None)
    if prev is None:
        return [], []
    added, updated = diff_entries(entries, prev)
    targets = [(e, "追加") for e in added] + [(e, "更新") for e in updated]

    texts = []
    for e, ct in targets:
        text = build_post_text(e, ct)
        texts.append((e.get("id"), ct, text))
        bad = unbalanced(text)
        if bad:
            ng.append(f"{e.get('id')}: 投稿文の括弧が閉じていない -> {' '.join(bad)}")
        w = count_x_weight(text)
        if w > MAX_TWEET_WEIGHT:
            ng.append(f"{e.get('id')}: 投稿文が上限超え（{w} > {MAX_TWEET_WEIGHT}）")
        if not str(e.get("location") or "").strip():
            ng.append(f"{e.get('id')}: 場所が空のまま投稿されようとしている")
    return ng, texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(DANGERS))
    ap.add_argument("--quiet", action="store_true", help="問題がある行だけ出す")
    ap.add_argument("--no-post-check", action="store_true", help="投稿文の点検をしない")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    entries = json.load(io.open(a.path, encoding="utf-8"))
    ng = check_entries(entries)

    texts = []
    if not a.no_post_check:
        ng2, texts = check_posts(entries)
        ng += ng2

    if not a.quiet:
        print(f"点検した危険情報: {len(entries)}件")
        if texts:
            print(f"これから投稿される文面: {len(texts)}件")
            for eid, ct, t in texts:
                print(f"\n--- [{ct}] {eid} ---")
                print(t)
            print()

    if ng:
        print(f"\n!! 問題 {len(ng)}件")
        for m in ng:
            print(f"   - {m}")
        print(f"\n[key] 機械チェック=NG 問題={len(ng)}")
        return 1

    print(f"\n[key] 機械チェック=OK 件数={len(entries)} 投稿予定={len(texts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
