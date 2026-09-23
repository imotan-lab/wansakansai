#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Claudeの修正内容そのものをCodexに再検証させるプロンプトを作る（2026-09-20導入）。

なぜ要るか:
STEP 7（危険情報はSTEP 5.8）のCodex検証は、Codexに**修正前（git HEAD）のデータだけ**を渡す。
Claudeの判断を見せると引きずられて「Claudeが見落とした項目」が出てこなくなるため。
その設計の裏返しで、**Claudeが直した内容そのものは誰も検証していなかった**。

2026-09-20に牛滝山 大威徳寺で実際に起きた:
  HEADの「岸和田市の観光記事が9:00〜16:30としている」は正しかった（9/18の実行が確認元URLをログに残していた）。
  9/20の実行は確認元と別の市の2ページだけを見て「16:30という出典は見つからず、市公式に記載自体が無い」と書き換えた。
  1巡目のCodexはHEADしか見ないので、この書き換えを見る機会が無い。
  存在する記載を「無い」とする文が2日弱サイトに載り、対話セッションが同じURLを取得して戻した。

この2巡目は、1巡目が独立に終わった**あと**に、修正の一覧（前・後・理由・出典）を渡して
「この変更は出典に支持されるか」だけを聞く。順番が後なので、1巡目が引きずられる心配はない。
一覧はメールに載せている --changes-file のJSONそのもの（spot / field / before / after / why / source）。

★一致するまで往復する。回数で打ち切らない（2026-09-20・ユーザー方針）★
  不支持の項目は、Claudeが出典を開き直して答え（撤回・修正・維持のどれかと根拠）を書き、
  --round 2, 3 で再提出する。**3巡で揃わなければその項目は公開せず、両論をメールで人に渡す。**
  「3」は打ち切りの回数ではなく、人に渡す合図。

使い方:
  python scripts/build_codex_change_review_prompt.py --changes C.json --round 1 --out P.md
  python scripts/build_codex_change_review_prompt.py --changes C.json --round 2 --prior R.json --out P.md

  --prior は Claude が Write で書く。形は次のとおり（不支持だった項目だけ載せる）:
    [{"item": 1,
      "codex": "不支持。岸和田市の130031.htmlに9時〜16時30分が現存する",
      "claude": "撤回。130031.htmlを開き直したところ記載が現存していた。前の値に戻す",
      "urls": ["https://…"]}]
  claude の先頭は必ず「撤回」「修正」「維持」のどれかで始める。

終了コード: 0=書いた / 2=渡す項目が無い / 1=入力が読めない
★2026-09-23に「不支持」の定義を直した★
  以前は「修正前の内容が別のページに現存すれば不支持」と書いていた。Codexはこれを字義どおりに当てはめ、
  ①終わった休止期間の日付がお知らせページに残っているだけのもの（黒鳥山公園）
  ②管理者の公式に合わせた修正に、観光案内の古い値が残っているもの（中之島公園の面積）
  ③前の地名を全部残して付け足しただけの修正（危険情報のクマの出没場所）
  をいずれも不支持にした。①は2巡目でも「中身は修正後と一致するが、指定基準ではなお不支持」と答えた。
  **基準の書き方が誤りを生んでいた**ので、「今も有効な現行の情報として」に改め、3つの型を明記した。

"""
import argparse
import io
import json
import sys

PREAMBLE = """# 依頼: サイトの修正内容が出典に支持されるかの再検証

あなたは独立した検証役です。**修正した側の判断に引きずられず、自分で出典を開いて確かめてください。**
根拠にしてよいのは、あなたが**実際に開いて読んだURL**だけです。開いていないページの内容を推測で書かないでください。
分からないものは分からないと書いてください。

**★「不支持」と「確認できず」を必ず分けてください★**
- 不支持 … 出典を開いて、**修正後の内容と違うこと**、または**修正前の内容が今も有効な現行の情報として別の出典に書かれていること**を実際に確認できた時だけ
- 確認できず … 出典が開けない、該当する記載を見つけられなかった（**探したが無かったは「不支持」ではありません**）

**「今も有効な現行の情報」の意味**
- **すでに終わった日付の出来事**（過去の休止期間、終了した工事やキャンペーンなど）が**ページに残っているだけのものは現行ではありません。** 修正前がそれを消しただけなら、それを理由に不支持にしないでください
- **同じ事柄について出典どうしが食い違う時は、施設の管理者・運営者の公式が、観光案内やまとめサイトより優先します。** 管理者の公式に合わせた修正を、二次的な案内に別の値があることだけを理由に不支持にしないでください
- **修正前の内容を残したまま付け足しただけの修正**は、修正前が今も正しいことを理由に不支持にしないでください。前後を並べて、何が消えたのかを確かめてから判定してください

対象は、犬連れお出かけ情報サイト「わんさかんさい」の掲載データです。
利用者は現地へ犬を連れて行くので、料金・時間・可否・駐車場の誤りは実害になります。
"""

ASK_ROUND1 = """
# 見てほしいこと

各項目について、次の順で確かめて判定してください。

1. **出典URLを実際に開く。** 「後」の内容がそのページに書いてありますか。
2. **「前」の内容が本当に無いのかも確かめる。** 修正は「前が誤りで後が正しい」という主張ですが、
   **前が正しく後が誤り、という向きも疑ってください。** とくに「前」が別のページを出典にしていたなら、
   そのページが今も存在するかを探してください。**「自分が開いたページに無い」と「どこにも無い」は別です。**
3. 判定を1つ選ぶ:
   - **支持** … 後の内容が出典に書いてあり、前の内容が出典に無い（または古い）と確認できた
   - **不支持** … 後の内容が出典と違う、または前の内容が現存すると確認できた。**何が食い違うかを1点に絞り、根拠URLを添える**
   - **確認できず** … 出典が開けない／該当箇所を見つけられない。**何を試したか**を書く

# 出し方

項目ごとに次の形で。前置きや総評は不要です。

```
### 項目1: 支持／不支持／確認できず
根拠URL: （実際に開いたもの）
理由: （2〜3文。不支持なら食い違いを1点に絞る）
```
"""

ASK_ROUND_N = """
# 見てほしいこと（{n}巡目）

前の巡であなたが「不支持」とした項目に、修正した側が答えを返しました。
**答えを読んだうえで、あなた自身の根拠をもう一度確かめてください。** 相手の答えに合わせるのではなく、
相手が挙げたURLを実際に開いて、自分の前回の根拠と突き合わせてください。

判定は次のどれかです。
- **支持に変更** … 相手の根拠を確認でき、自分の前回の判断が誤りだった、または相手が撤回・修正した内容で正しくなった
- **なお不支持** … 相手の根拠を開いても食い違いが残る。**残っている食い違いを1点に絞って**書く
- **確認できず** … 相手のURLが開けない等。何を試したかを書く

# 出し方

```
### 項目1: 支持に変更／なお不支持／確認できず
根拠URL: （実際に開いたもの）
理由: （2〜3文）
```
"""


def load(path, what):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception as ex:
        print("!! {} を読めない: {}".format(what, ex))
        sys.exit(1)


def fmt_item(n, e):
    return "\n".join([
        "## 項目{}".format(n),
        "- 対象: {}".format(e.get("spot", "")),
        "- 項目: {}".format(e.get("field", "")),
        "- 前: {}".format(e.get("before", "")),
        "- 後: {}".format(e.get("after", "")),
        "- 修正した側の理由: {}".format(e.get("why", "")),
        "- 出典: {}".format(e.get("source", "")),
        "",
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changes", required=True, help="--changes-file と同じJSON")
    ap.add_argument("--round", type=int, default=1, help="何巡目か（既定1）")
    ap.add_argument("--prior", help="2巡目以降: 前巡のCodexの判定とClaudeの答え（JSON）")
    ap.add_argument("--out", required=True, help="プロンプトの出力先")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    changes = load(a.changes, "--changes")
    if not isinstance(changes, list) or not changes:
        print("渡す項目が無い（修正0件）")
        sys.exit(2)

    parts = [PREAMBLE]

    if a.round <= 1:
        parts.append("# 修正の一覧（{}件）\n".format(len(changes)))
        for n, e in enumerate(changes, 1):
            parts.append(fmt_item(n, e))
        parts.append(ASK_ROUND1)
    else:
        if not a.prior:
            print("!! 2巡目以降は --prior が要る")
            sys.exit(1)
        prior = load(a.prior, "--prior")
        disputed = [p for p in prior if isinstance(p, dict) and "item" in p]
        if not disputed:
            print("前巡で不支持の項目が無い＝往復は終わっている")
            sys.exit(2)
        parts.append("# 前の巡で不支持だった項目（{}件）\n".format(len(disputed)))
        for p in disputed:
            n = int(p["item"])
            if not (1 <= n <= len(changes)):
                print("!! --prior の item {} が一覧の範囲外".format(n))
                sys.exit(1)
            parts.append(fmt_item(n, changes[n - 1]))
            parts.append("- 前巡のあなたの判定: {}".format(p.get("codex", "")))
            parts.append("- 修正した側の答え: {}".format(p.get("claude", "")))
            for u in p.get("urls", []) or []:
                parts.append("  - 相手が挙げたURL: {}".format(u))
            parts.append("")
        parts.append(ASK_ROUND_N.format(n=a.round))

    io.open(a.out, "w", encoding="utf-8").write("\n".join(parts))
    print("書いた: {} （{}巡目・{}件）".format(a.out, a.round,
          len(changes) if a.round <= 1 else len(disputed)))
    sys.exit(0)


if __name__ == "__main__":
    main()
