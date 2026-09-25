#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""備考（remarks）の中から「よそのサイトではこうだったらしい」と転載のように読める文と、
出典どうしの食い違いを読む人に説明している文を探す（2026-09-25導入・運営者の指摘）。

なぜ要るか:
  備考は、わんさかんさいが調べて言い切る文にする。
  「〜のブログでは」「口コミによると」「〜との報告もある」「犬連れ訪問ブログあり」「〜らしい」のように
  よその話を持ってくると転載サイトに見え、「公式は〜とする一方、〜としており食い違う」は読む人が結局どうなのか分からない。
  スポット更新タスク（am/pm）が、その日の対象スポットだけを点検して直すのに使う（まとめて全件は直さない）。

使い方:
  python scripts/find_hearsay.py --ids aragijima,oishi-kogen   … 指定したスポットだけ
  python scripts/find_hearsay.py --all                          … 全件（件数の把握用）
終了コード: 0=見つからない / 1=見つかった
語の一覧は目安。拾っても直さなくてよい文もある（例:「公式Instagramで最新情報を確認のこと」のような案内）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

SPOTS = Path(__file__).resolve().parent.parent / "data" / "spots.json"

PATTERNS = [
    ("よその話", r"ブログ|口コミ|クチコミ|レビュー|体験談|訪問記|訪問報告|報告もあ|との報告|という報告|SNS|インスタ|Instagram|X（旧|食べログ|じゃらん|Googleマップの|まとめサイト|紹介記事|観光記事|媒体|によると|によれば|とのこと|との情報|という情報|らしい|そうだ|と言われ|実績多数|実績あり|実績がある"),
    ("出典の説明", r"とする一方|一方で|食い違|記載が割れ|割れる|見解が分かれ|出典によ|サイトによ|情報によ|と幅あり|開きがあ|とされるが|としているが|と案内しているが|公式は「|公式に「|公式サイトは|公式では|公式の案内は|とされ|としている"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ids")
    g.add_argument("--all", action="store_true")
    a = ap.parse_args()
    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    want = None if a.all else {x.strip() for x in a.ids.split(",") if x.strip()}
    found_spots = 0
    found_sents = 0
    for e in spots:
        if want is not None and e["id"] not in want:
            continue
        hits = []
        for sent in (e.get("remarks") or "").split("。"):
            kinds = [k for k, p in PATTERNS if re.search(p, sent)]
            if kinds:
                hits.append((kinds, sent))
        if hits:
            found_spots += 1
            found_sents += len(hits)
            print(f"[{e['id']}] {e['name']}")
            for kinds, sent in hits:
                print(f"  - ({'・'.join(kinds)}) {sent}。")
    print(f"== {found_spots}スポット・{found_sents}文")
    return 1 if found_sents else 0


if __name__ == "__main__":
    sys.exit(main())
