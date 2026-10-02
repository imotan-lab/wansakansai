"""Codexの代役（Claudeのエージェント2体）に渡す指示文を作る。docs/codex_standin.md 参照。

使い方:
    python scripts/build_standin_prompt.py --role a --prompt-file <Codexに渡すはずだったプロンプト> --out <出力先>
    python scripts/build_standin_prompt.py --role b --prompt-file <同じもの> --out <出力先> [--material <パス> ...]

本体（タスク）は指示文を手書きしない。手書きすると、修正内容を知っている本体の一言
（「とくに〇〇の料金を」など）が混ざり、2体の独立が崩れる。Codexのプロンプトを生成スクリプトに
作らせているのと同じ理由（CLAUDE.md「Codexによる独立検証」）。

できた指示文は、Agent ツールの prompt にそのまま貼る（中身を足したり削ったりしない）。
"""
import argparse
import sys
from pathlib import Path

ROLES = {
    "a": ("読む役",
          "公式サイト・自治体など一次情報を実際に開いて、依頼の項目ごとに、書いてある内容を確かめる。"),
    "b": ("崩す役",
          "いま載せている内容（または修正）が、もう違っている根拠を探す。料金改定・営業時間の変更・"
          "犬の禁止・閉鎖・運用変更のお知らせ、新しい日付のページを優先して見る。\n"
          "- 反証が見つからなかった項目は「確認できず」と答える（「反証なし」は肯定の根拠にならない）\n"
          "- 「問題なし」「一致」「支持」と答えてよいのは、現行の記載を自分で実際に開いて確かめた時だけ"),
}

COMMON = """
守ること:
- 依頼ファイルが求める形式で、対象の全件について1件ずつ答える（問題が無いものも省かない）
- 根拠は、実際に開いて確認したURLだけ。開けなかった・読めなかった時は「確認できず」
- 「要修正」「不一致」「不支持」は、違う内容が書かれたページを実際に確認できた時だけ。そのURLと原文を必ず添える。
  探したが見つからないだけなら「確認できず」
- 値は要約ではなく原文で引用する。WebFetch の要約は言い換えが混ざるので、決め手になる値は
  Bash で python の urllib を使って生のHTMLを取り、原文を確かめる（文字化けしたら utf-8 → shift_jis → euc-jp の順で decode を試す）
- 調べるのはWebと、下に挙げた渡されたファイルだけ。このパソコンのほかのファイル
  （わんさかんさいの data/・logs/・git の履歴・作業中の差分など）は開かない。そこには別の判断が書いてあり、読むと独立した検証にならない
- Chrome（mcp__claude-in-chrome__ の道具）は使わない。Instagram は渡された素材だけを見る
- ファイルを作ったり書き換えたりしない。答えはこの返事で返す
- 時間の目安は1件あたり4分・全体で20分。終わらなかった件は「未着手」と書いて、そこまでの答えを返す
- 答えの最後に、開いたURLの一覧を付ける
"""


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True, choices=["a", "b"])
    ap.add_argument("--prompt-file", required=True, help="Codexに渡すはずだったプロンプト（生成スクリプトの出力）")
    ap.add_argument("--material", action="append", default=[], help="Instagram素材など、読んでよい追加のファイル（複数可）")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    pf = Path(a.prompt_file)
    if not pf.exists() or not pf.read_text(encoding="utf-8", errors="replace").strip():
        print(f"[standin-prompt] 依頼ファイルが無いか空: {pf}")
        return 1
    for m in a.material:
        if not Path(m).exists():
            print(f"[standin-prompt] 素材が無い: {m}")
            return 1

    name, duty = ROLES[a.role]
    lines = [
        f"あなたは「わんさかんさい」（関西の犬連れスポットのサイト）の掲載内容を検証する役です（{name}）。",
        f"次のファイルを Read で読み、そこに書かれた依頼に答えてください: {pf.resolve().as_posix()}",
    ]
    if a.material:
        lines.append("あわせて次のファイルも読んでよい（Instagram等から取った原文・画像。こちらの解釈ではない）:")
        lines += [f"- {Path(m).resolve().as_posix()}" for m in a.material]
    lines += ["", f"あなたの役目（{name}）: {duty}", COMMON.strip(), ""]
    out = Path(a.out)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[standin-prompt] 作成 role={a.role}（{name}） → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
