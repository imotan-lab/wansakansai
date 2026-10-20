#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""週次レポートでCodexに渡すプロンプトを作る（2026-10-20）。手書きしない。

  --mode read  … データだけを渡し、Codexに独立に読ませる（Claudeの文章は見せない）
  --mode check … Claudeの文章（notes）とデータを渡し、1文ずつ「支持／不支持／確認できず」を付けさせる

使い方:
  python scripts/build_codex_weekly_prompt.py --mode read  --data data.json --out prompt_read.md
  python scripts/build_codex_weekly_prompt.py --mode check --data data.json --notes notes.json --out prompt_check.md
  cat prompt.md | codex exec --skip-git-repo-check -c 'windows.sandbox="unelevated"' - > out.txt 2>&1
"""
import argparse
import io
import json
import sys

READER = """週次レポートの中身を、データから独立に読み取ってください。別のAIも同じデータを読んで書いていますが、その答えは見せません。
データに無いことは推測しないこと。推測を書く時は「推測」と明記すること。ファイルの読み書きやコマンドは不要です（データは下に全部あります）。

## 読む人と目的
関西の犬連れお出かけサイト「わんさかんさい」の運営者（SEOに詳しくない）。週1回読んで、次に何をするか（どこを撮りに行くか・何を書くか・何を直すか）を決める。
AdSense再申請に向けて site.targets を自分の準備目標にしている（Googleの条件ではない）。撮影は運営者が大阪から車で行ける範囲で行う。

## データの読み方
- gsc はGoogle検索だけ（Yahoo!検索は含まない）。ga4 はYahoo!なども含む訪問。2つを足したり引いたりしない
- ga4 の値は [今週, 前の週]。users は人数の目安（同じ人の別端末は別に数える）。affiliate_click は押された回数で、予約・売上は分からない
- queries_*.prev_impressions が null は「前の週の表に無かった＝少なかった」で、0とは限らない
- pages_new は前の週に検索結果に1回も出なかったページ。初めてGoogleに載った意味ではない
- top10_spots_last28 は直近28日のGoogle検索クリック上位10スポット（トップページ等を除く）
- actions_log は運営者側で変えたこと。日付が比較期間より後のものは、今回のデータで効果を言えない

## 書いてほしいこと
1. 今週の状況（3〜4行）。数字で確かめられる事実と、原因の推測を分けること
2. 次にやること 0〜3件。それぞれ「対象・データ上の根拠・作業・終わりの条件」。根拠が弱いものは出さない。0件でもよい
3. actions_log の各項目について、データから言える経過（効果あり／判断保留／まだ反映されていない など）と、次にいつ何を見るか
4. このデータを読む時に誤解しやすい点

## データ（JSON）
"""

CHECKER = """週次レポートに載せる文章（notes）を、データ（data）と1文ずつ突き合わせてください。ファイルの読み書きやコマンドは不要です。
- 各文について「支持（データで確かめられる）／不支持（データと違う。どこが違うか）／確認できず（データに無い）」を書く
- 「不支持」と「確認できず」を混ぜないこと。不支持は、データと違う内容を確かめられた時だけ
- 推測として書かれた文は「推測と明記されているか」と「データと矛盾しないか」だけを見る
- 読む人（SEOに詳しくない運営者）が誤解しそうな書き方があれば具体的に
- data の読み方: gsc はGoogle検索だけ、ga4 はYahoo!なども含む訪問で値は [今週, 前の週]。prev_impressions が null は前の週の表に無かった（少なかった）
- 最後の行に、重大な問題（数字の誤り・推測を事実として書いている）の件数を「重大な問題: N件」の形で書く

## notes
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["read", "check"], required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--notes")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = json.load(io.open(a.data, encoding="utf-8"))
    if a.mode == "read":
        text = READER + json.dumps(data, ensure_ascii=False, indent=1)
    else:
        if not a.notes:
            print("--mode check には --notes が要る")
            return 2
        notes = json.load(io.open(a.notes, encoding="utf-8"))
        text = CHECKER + json.dumps(notes, ensure_ascii=False, indent=1) + "\n\n## data\n" + json.dumps(data, ensure_ascii=False, indent=1)
    io.open(a.out, "w", encoding="utf-8").write(text)
    print(f"[codex-weekly-prompt] {a.mode} {len(text)}文字 → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
