# -*- coding: utf-8 -*-
"""CLAUDE.md肥大化検知（わんさかんさい・2026-07-09導入／2026-09-02に閾値50KB→80KBへ）。

閾値を上げた理由: 50KBでは追記のたびに超え、その都度ルールの説明を削る作業が発生していた。
中身を点検したところ残っているのは運用に必要な現在形のルールばかりで、
肥大というより閾値が実態に合っていなかった。履歴の退避方針そのものは変えない。

うちどころの audit_site.py check_23_claude_md_size の移植。
80KB超でNG＝対話セッションで圧縮する合図（履歴・完了施策の詳細をCLAUDE_history.mdへ退避。
手順はCLAUDE.md冒頭「変更履歴について」の圧縮手順4ステップ参照）。
あわせて履歴退避ルールの生存確認（CLAUDE_history.mdへの参照が消えていないか）も行う。

★このスクリプトは検知と通知のみ。CLAUDE.mdの書き換えは絶対にしない（圧縮は対話セッション専用の作業）★

使い方:
  python scripts/check_claude_md_size.py           # 人間向け出力。NGありなら終了コード1
  python scripts/check_claude_md_size.py --json    # 自動タスク向け {"ok": bool, "ngs": [...]}
  （--path / --threshold-kb はテスト用オーバーライド）
"""

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="CLAUDE.md肥大化検知（検知のみ・書き換えない）")
    parser.add_argument("--path", default=str(BASE / "CLAUDE.md"), help="検査対象（テスト用）")
    parser.add_argument("--threshold-kb", type=int, default=80, help="NG閾値KB（既定80）")
    parser.add_argument("--json", action="store_true", help="JSON出力")
    args = parser.parse_args()

    ngs = []
    path = Path(args.path)
    if not path.is_file():
        ngs.append(f"CLAUDE.mdが見つからない: {path}")
    else:
        size = path.stat().st_size
        if size > args.threshold_kb * 1024:
            ngs.append(
                f"CLAUDE.mdが{size / 1024:.1f}KB（閾値{args.threshold_kb}KB超）"
                "→対話セッションで「圧縮して」を実行（履歴をCLAUDE_history.mdへ退避→欠損検証。無人タスクは書き換え禁止）"
            )
        text = path.read_text(encoding="utf-8", errors="replace")
        if "CLAUDE_history.md" not in text:
            ngs.append(
                "CLAUDE.mdからCLAUDE_history.mdへの参照が消えている（履歴退避ルールの喪失疑い）"
                "→「変更履歴について」セクションを復元する"
            )

    if args.json:
        print(json.dumps({"ok": not ngs, "ngs": ngs}, ensure_ascii=False))
    else:
        if ngs:
            for n in ngs:
                print("NG:", n)
        else:
            print("OK: CLAUDE.mdサイズ・履歴参照とも正常")
    sys.exit(1 if ngs else 0)


if __name__ == "__main__":
    main()
