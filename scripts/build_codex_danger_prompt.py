#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""危険情報の変更点をCodexに検証させるためのプロンプトファイルを作る。

★プロンプトを毎回AIに手書きさせない★
手書きだと「Claudeの結論に引きずられるな」「分からないものは分からないと書け」といった
前提条件を書き忘れる。書き忘れた回だけ検証が甘くなり、それに気づけない。
だからファイル生成にしてある。

★Codexは検証役であって上位の判定者ではない★（CLAUDE.mdの方針）
このプロンプトはCodexに「正解を出させる」ためのものではなく、
**Claudeとは独立にもう一度調べさせて、結論が割れるかどうかを見る**ためのもの。

使い方:
    python scripts/build_codex_danger_prompt.py --out 出力先.md
    python scripts/build_codex_danger_prompt.py --ids danger-025,danger-026 --out 出力先.md
    python scripts/build_codex_danger_prompt.py --round 2 --out 出力先.md   # 2巡目

    cat 出力先.md | codex exec --skip-git-repo-check -
    （★プロンプトはファイルに書いてパイプで渡すこと。コマンド直書きはshell_guardに止められる★）
"""
import argparse
import io
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DANGERS = BASE / "data" / "dangers.json"
PREV = BASE / "scripts" / "dangers_prev.json"

ALLOWED_TYPES = [
    "毒餌", "毒餌の疑い", "感染症", "危険な生き物", "有毒なもの", "気象・暑さ", "その他の注意",
]

HEADER = """あなたは犬連れ向け情報サイト「わんさかんさい」の危険情報を検証する役です。

# 最初に読むこと

- **別のAI（Claude）がすでに一度調べて、下の内容を書きました。その結論に引きずられないでください。**
  合わせにいく必要はありません。違うと思ったら違うと書いてください。
- **実際にページを開いて確認できたことだけを根拠にしてください。** 推測で埋めないこと。
- **分からないものは「確認できず」と書いてください。** それが正しい答えです。
  無理に判定すると、こちらは「2つのAIが一致した」と誤解して採用してしまいます。
- **★「不一致」と「確認できず」を混ぜないでください。ここが一番大事です★**
  - **不一致** … **違う内容を実際に確認できた時だけ**使います。
    例: 公式に「3日から5日」と書いてあるのに、こちらが「3日から8日」と書いている。
  - **確認できず** … 探したが根拠のページに行き当たらなかった時に使います。
  **「探したが見つからなかった」は不一致ではありません。** 必ず「確認できず」と書いてください。
  こちらは不一致を「2つのAIで結論が割れた」として扱い、公式を開き直して調べ直します。
  見つからなかっただけのものを不一致にされると、その時間が丸ごと無駄になります。
  2026年9月3日と4日に、2日続けて実際にこれが起きました。
- **媒体名だけでドメインを決めつけないでください。** 同じ発行元が複数のサイトに記事を出します。
  例: 日本気象協会は jwa.or.jp と tenki.jp の両方に出していて、
  気象予報士の署名記事は tenki.jp 側にあります。片方だけ見て「無い」と判断しないでください。
- 根拠にしたURLを必ず書いてください。

# このサイトの決まり

- 危険情報は毎日自動更新され、そのままサイトに公開され、Xにも自動投稿されます。人の目は入りません。
- 種別（type）は次の7つだけを使います。これ以外は使いません。
{types}
  - 「危険な生き物」はクマ・イノシシ・マムシ・スズメバチなど、生き物そのものが危ないもの
  - 「有毒なもの」はカエンタケ・ヒガンバナ・ぎんなん・アオコなど、口や皮膚から入ると危ないもの
  - 「気象・暑さ」は台風・大雨・熱中症・路面のやけど
  - 「その他の注意」は上のどれにも入らないもの
- `expires` は「この日まで表示してよい」という期限です（YYYY-MM-DD）。
  台風・大雨警報のように**数日で終わる情報にだけ**入れます。
  毒餌や感染症のように「いつまで危険か決められない」ものには入れません。
- `summary` は一覧に出る30〜60字の要約です。裏取りが弱い情報は、要約の側にもその旨が要ります
  （例:「ただし市は毒餌の存在も死因も未確認としている」）。要約だけ読んだ人が事実を誤認しないため。
- 1件だけの未確認情報でも、注意喚起なら「SNS上の報告」と明記すれば掲載してよい方針です。
  ただし**公式の発表と、SNSの報告を、区別せずに書くのは不可**です。

# 見てほしいこと

下の各エントリについて、次の4点を判定してください。

1. **種別（type）** … 中身に合っていますか。上の7語のどれが正しいですか。
2. **期限（expires）** … まず**この危険が実際に終わるのはいつごろか**（予報・警報の終了日）を
   調べて、その日付を書いてください。
   **expires はその終了日そのものではありません。** 雨がやんでも河川の増水はしばらく残るため、
   こちらでは**終了日に2〜4日の余裕を足した日付**を入れる決まりです。
   なので判定はこうしてください。
   - 書かれている expires が「あなたの調べた終了日 + 2〜4日」の範囲にある → **一致**
   - その範囲から外れている → **不一致**（あなたの考える終了日を書いてください）
   - 終了日が調べても分からない → **確認できず**
   なお、いつ終わるか決められない情報（毒餌・感染症・危険な生き物）に expires が
   入っている場合は、範囲に関わらず **不一致** としてください。
3. **要約（summary）** … description の内容と矛盾していませんか。
   要約だけ読んだ人が事実を誤解しませんか（裏取りの弱さが隠れていませんか）。
4. **事実関係** … description に書かれている出来事は、実際に確認できますか。
   場所・時期・発表元は合っていますか。

# 書き方

エントリごとに、必ずこの形で書いてください。行頭の記号も含めて守ってください。

```
## danger-0XX
- 種別: 一致 | 不一致 | 確認できず ／ 正しいと思う値 ／ 理由
- 期限: 一致 | 不一致 | 確認できず ／ 正しいと思う値（不要なら「不要」） ／ 理由
- 要約: 一致 | 不一致 | 確認できず ／ 理由
- 事実関係: 一致 | 不一致 | 確認できず ／ 理由
- 根拠URL: （実際に開いたものだけ）
```

「一致」＝Claudeの書いた内容でよい、「不一致」＝直すべき、「確認できず」＝調べたが分からなかった、です。

"""

ROUND2 = """
# ★これは2巡目です★

1巡目でClaudeとあなたの結論が割れました。割れた項目を下に挙げます。
**1巡目のあなたの答えをなぞらないでください。** もう一度、最初から調べ直してください。
1巡目で見たページとは別のページも当たってください。
それでも分からなければ「確認できず」で構いません。無理に決着させないでください。

割れた項目:
{diffs}

"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="プロンプトの出力先")
    ap.add_argument("--ids", default="", help="対象のIDをカンマ区切りで指定（省略時はprevとの差分）")
    ap.add_argument("--round", type=int, default=1, help="1巡目か2巡目か")
    ap.add_argument("--diffs", default="", help="2巡目に渡す「割れた項目」の説明")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    entries = json.load(io.open(DANGERS, encoding="utf-8"))

    if a.ids.strip():
        want = {s.strip() for s in a.ids.split(",") if s.strip()}
        targets = [e for e in entries if e.get("id") in want]
        missing = want - {e.get("id") for e in targets}
        if missing:
            print(f"!! dangers.jsonに無いID: {','.join(sorted(missing))}")
            return 1
    else:
        prev = json.load(io.open(PREV, encoding="utf-8")) if PREV.exists() else []
        pb = {e["id"]: e for e in prev}
        targets = [
            e for e in entries
            if e["id"] not in pb
            or any(pb[e["id"]].get(k) != e.get(k)
                   for k in ("description", "location", "type", "summary", "expires"))
        ]

    if not targets:
        print("[key] Codex検証=不要 対象=0")
        return 2   # 呼ぶ必要なし。SKILL.md側はこの2を見てCodexを起動しない

    body = HEADER.format(types="\n".join(f"  - {t}" for t in ALLOWED_TYPES))
    if a.round >= 2:
        body += ROUND2.format(diffs=a.diffs or "（指定なし）")

    body += "\n# 検証してほしいエントリ\n\n"
    for e in targets:
        body += f"## {e.get('id')}\n\n```json\n"
        body += json.dumps(e, ensure_ascii=False, indent=2)
        body += "\n```\n\n"

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(body)
    print(f"[key] Codex検証=対象あり 件数={len(targets)} ID={','.join(e['id'] for e in targets)}")
    print(f"出力: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
