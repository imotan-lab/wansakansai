"""Codexの出力ファイルを見て、判定が返ったか・利用制限で止まったかを見分ける。

使い方:
    python scripts/codex_limit_check.py <codex exec の出力ファイル>

終了コード:
    0  … 最終の答えが返っている（中身を読んで突き合わせへ）
    20 … ★Codexの利用制限★。この実行の残りは代役（Claudeのエージェント2体）に切り替える
         （docs/codex_standin.md）。同じ実行の中でCodexを呼び直さない
    1  … 最終の答えが無い（出力が無い・空・接続エラー等で途中で終わった）。
         1回だけ呼び直し、それでも1なら代役に切り替える

標準出力に1行で結果を書く（タスクはこの行をそのままログへ写す）。

「答えが返った」の見分け方（2026-10-02に過去の出力78件で確かめた）:
codex exec は最後まで走ると `tokens used` の行と使用量の数字を出し、そのあとに最終の答えを書く。
出力の前半にはプロンプトのエコーが入り、そこにも「支持／不支持」などの判定語が含まれるので、
判定語を探すだけでは「答えが無いのに有る」と誤る（接続エラーで終わった回が実際に0を返していた）。
"""
import re
import sys
from pathlib import Path

# codex exec が制限に当たった時の文言。実例（2026-09-07）:
#   ERROR: You've hit your usage limit. Upgrade to Pro ... or try again at 3:01 PM.
# 「rate limit」等は Codex が読んだページの本文にも出うるので、ERROR 行に出た時だけ数える
LIMIT_RE = re.compile(r"hit your usage limit|^\s*ERROR\b.*(usage limit|rate limit|quota exceeded|429 Too Many Requests)", re.I)
WHEN_RE = re.compile(r"(try again (?:at|in) [^.\n]+)", re.I)
TOKENS_RE = re.compile(r"^tokens used\s*$")
NUMBER_RE = re.compile(r"^[\d,]+\s*$")


def final_answer(lines):
    """最後の `tokens used` 行より後ろ（使用量の数字は除く）を返す。無ければ None。"""
    idx = None
    for i, line in enumerate(lines):
        if TOKENS_RE.match(line):
            idx = i
    if idx is None:
        return None
    rest = lines[idx + 1:]
    if rest and NUMBER_RE.match(rest[0]):
        rest = rest[1:]
    body = "\n".join(rest).strip()
    return body or None


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if len(sys.argv) != 2:
        print("[codex-limit-check] 使い方: python scripts/codex_limit_check.py <出力ファイル>")
        return 1
    p = Path(sys.argv[1])
    if not p.exists():
        print(f"[codex-limit-check] 出力ファイルが無い: {p}")
        return 1
    text = p.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        print(f"[codex-limit-check] 出力が空: {p}")
        return 1
    lines = text.splitlines()
    for line in lines:
        if LIMIT_RE.search(line):
            when = WHEN_RE.search(text)
            print(f"[codex-limit-check] USAGE_LIMIT（Codexの利用制限）: {line.strip()[:200]}"
                  f" / 復帰: {when.group(1) if when else '不明'}")
            return 20
    answer = final_answer(lines)
    if answer is None:
        errors = [l.strip() for l in lines if l.lstrip().startswith("ERROR")]
        last_err = errors[-1][:150] if errors else "なし"
        print(f"[codex-limit-check] 最終の答えが無い（途中で終わった）: 最後のERROR={last_err} / {p}")
        return 1
    print(f"[codex-limit-check] OK 最終の答えあり（{len(answer.splitlines())}行）: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
