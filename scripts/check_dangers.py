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

# ★種別の語彙（2026-09-03に整理・2026-09-20に気象を外した）★
# それまでは「事故」が何でも入る箱になっていて、クマの出没も熱中症も台風も
# 全部「事故」になっていた（13件）。中身を読んで7つに分けた。
# 新しい種別を足す時は、既存のどれにも入らない時だけにすること。
#
# ★「気象・暑さ」は2026-09-20にユーザー判断で語彙から外した★
# 台風・大雨・残暑は期間がピンポイントで数日で意味が消え、飼い主は天気を自分で見ている。
# 更新のたびにXへ流れて犬連れスポットの投稿に天気が混ざり、2AI検証でいちばん揉め、
# いちばん書き換え回数が多かったのも気象だった。**語彙から外すことで、タスクが
# 間違って足しても機械チェックが弾く。** 肉球のやけど等の犬固有の注意を載せたくなったら、
# 日付で追いかけるエントリではなく、危険情報ページの定型文として置くこと。
ALLOWED_TYPES = {
    "毒餌",
    "毒餌の疑い",
    "感染症",
    "危険な生き物",   # クマ・イノシシ・マムシ・スズメバチ・セアカゴケグモなど
    "有毒なもの",     # カエンタケ・ヒガンバナ・ぎんなん・アオコなど口や皮膚から入るもの
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
        eid = e.get("id") if isinstance(e.get("id"), str) and e.get("id") else "(idなし)"
        for k in ("id", "date", "location", "type", "summary", "description"):
            if k in e and e[k] is not None and not isinstance(e[k], str):
                ng.append(f"{eid}: {k} が文字列でない -> {e[k]!r}")
        if "expires" in e and e["expires"] not in (None, "") and not isinstance(e["expires"], str):
            ng.append(f"{eid}: expires が文字列でない -> {e['expires']!r}")

        for k in REQUIRED:
            if not str(e.get(k) or "").strip():
                ng.append(f"{eid}: 必須項目が空 -> {k}")

        if not re.fullmatch(r"danger-\d{3}", str(e.get("id") or "")):
            ng.append(f"{eid}: idの書式が違う（danger-000 の形）")
        if eid in seen:
            ng.append(f"{eid}: idが重複している")
        seen.add(eid)

        date = str(e.get("date") or "")
        if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", date):
            ng.append(f"{eid}: dateの書式が違う（YYYY-MM・月は01〜12）-> {date!r}")

        exp = str(e.get("expires") or "").strip()
        d = None
        if exp:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", exp):
                ng.append(f"{eid}: expiresの書式が違う（YYYY-MM-DD）-> {exp!r}")
            else:
                try:
                    d = datetime.date.fromisoformat(exp)
                except ValueError:
                    ng.append(f"{eid}: expiresが実在しない日付 -> {exp!r}")
                    d = None
            if exp and d is not None:
                if re.fullmatch(r"\d{4}-\d{2}", date) and exp[:7] < date:
                    ng.append(f"{eid}: expires({exp})がdate({date})より前を向いている")
                if d < today:
                    # 期限切れをそのまま公開している状態。expire_dangers.py の実行漏れ
                    ng.append(f"{eid}: expires({exp})が過ぎている。expire_dangers.py --apply を実行すること")

        # 確かめ直しの項目（2026-11-25）。basis は必須、checked は無ければ「次の実行で確かめ直す」扱い
        basis = str(e.get("basis") or "")
        if basis not in ("official", "report"):
            ng.append(f"{eid}: basis が無いか語彙外 -> {basis!r}（official=公式が出している / report=報道やSNSの報告）")
        chk_raw = e.get("checked")
        if chk_raw is not None and not isinstance(chk_raw, str):
            ng.append(f"{eid}: checked が文字列でない -> {chk_raw!r}")
        chk = chk_raw.strip() if isinstance(chk_raw, str) else ""
        if chk:
            try:
                cd = datetime.date.fromisoformat(chk) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", chk) else None
            except ValueError:
                cd = None
            if cd is None:
                ng.append(f"{eid}: checked が実在する日付（YYYY-MM-DD）でない -> {chk!r}")
            elif cd > today:
                ng.append(f"{eid}: checked({chk})が未来の日付")

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
        # ★import失敗をNGにしないこと★
        # ここは post_danger_to_x 経由で Playwright まわりまで読み込む。
        # 無関係な理由で読み込めなかっただけで危険情報の更新まで止まると、
        # 「投稿の点検ができない」ことを理由に「サイトも更新しない」ことになり本末転倒。
        # 壊れた投稿は x_poster.post_tweet 側の見張りが最後に止めるので、
        # ここは警告に留めて先へ進む。
        print(f"（警告）投稿文の点検を飛ばした: {type(ex).__name__}: {ex}")
        return [], []

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

    try:
        entries = json.load(io.open(a.path, encoding="utf-8-sig"))
    except (OSError, ValueError) as ex:
        print(f"[ERROR] dangers.json を読めない（JSONの書き方の誤りなど）: {ex}")
        return 1
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        print("[NG] dangers.json は「行（{…}）の配列」でなければならない")
        print("[key] 機械チェック=NG 件数=0 投稿予定=0")
        return 1
    ng = check_entries(entries)
    # 台帳（data/dangers_ledger.json）と照らす: 消したidを使い回していないか・next_id より大きい番号を使っていないか
    try:
        led = json.load(io.open(BASE / "data" / "dangers_ledger.json", encoding="utf-8-sig"))
        removed_ids = {r.get("id") for r in led.get("removed", []) if isinstance(r, dict)}
        next_id = int(led.get("next_id"))
        for e in entries:
            i = e.get("id")
            if isinstance(i, str) and re.fullmatch(r"danger-\d{3}", i):
                if i in removed_ids:
                    ng.append(f"{i}: 消した事案のidを使い回している（台帳 data/dangers_ledger.json の removed にある）")
                if int(i[7:]) >= next_id:
                    ng.append(f"{i}: 台帳の next_id（{next_id}）を進めていない。新しいidを振ったら next_id を次の番号にする")
    except Exception as ex:
        ng.append(f"台帳 data/dangers_ledger.json を読めない: {type(ex).__name__}: {ex}")
    if ng:
        # 形が壊れている時は投稿文を組み立てない（組み立てる途中で落ちるため）
        a.no_post_check = True

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
