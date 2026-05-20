"""
spots.json の remarks 文体ルールチェック・自動修正スクリプト。

CLAUDE.md の「remarks（備考）の文体ルール」に基づき、機械的に判定できる
違反を検出する。--fix オプションで自動修正可能なものは置換する。

使い方:
  python scripts/check_writing_style.py           # 違反検出のみ（exit 1 if violations）
  python scripts/check_writing_style.py --fix     # 自動修正可能なものを修正

機械的に自動修正するルール:
  - 半角チルダ「~」「～」→ 全角波ダッシュ「〜」(U+301C)
  - 日本語文章内の半角括弧「()」→ 全角「（）」
  - 時間範囲「HH:MM-HH:MM」→「HH:MM〜HH:MM」

警告のみ（要人間判断）:
  - です・ます調の検出
  - 末尾が「。」で終わっていない
  - 改行文字を含む
  - remarks が空
"""

import argparse
import json
import re
import sys
from pathlib import Path

SPOTS_JSON = Path(__file__).resolve().parent.parent / "data" / "spots.json"


def detect_violations(remarks: str) -> list[str]:
    """機械的に判定できる文体違反を検出して理由のリストで返す。"""
    issues = []
    if not remarks.strip():
        issues.append("remarks が空")
        return issues
    if "\n" in remarks or "\r" in remarks:
        issues.append("改行文字を含む（1段落で完結させる）")
    if re.search(r"(です。|ます。|でした。|ません。|でしょう。)", remarks):
        issues.append("です・ます調を含む（常体＋体言止めに統一）")
    if "～" in remarks:
        issues.append("半角チルダ「～」(U+FF5E) を含む → 全角波ダッシュ「〜」(U+301C) に置換")
    if "~" in remarks:
        issues.append("半角チルダ「~」(U+007E) を含む → 全角波ダッシュ「〜」に置換")
    if re.search(r"[()]", remarks):
        issues.append("半角括弧「()」を含む → 全角「（）」に置換")
    if re.search(r"\d{1,2}:\d{2}-\d{1,2}:\d{2}", remarks):
        issues.append("時間範囲に半角ハイフンを使用 → 全角波ダッシュ「〜」に置換")
    if not remarks.rstrip().endswith("。"):
        issues.append("末尾が「。」で終わっていない")
    return issues


def fix_remarks(remarks: str) -> str:
    """機械的に自動修正可能な違反を修正した文字列を返す。"""
    r = remarks
    r = r.replace("～", "〜")
    r = r.replace("~", "〜")
    r = r.replace("(", "（").replace(")", "）")
    r = re.sub(r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})", r"\1〜\2", r)
    return r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="自動修正可能な違反を修正してファイルを更新")
    parser.add_argument("--json", action="store_true", help="結果をJSONで出力")
    args = parser.parse_args()

    data = json.loads(SPOTS_JSON.read_text(encoding="utf-8"))

    auto_fixed = []
    manual_required = []
    changed = False

    for spot in data:
        name = spot.get("name", "(no name)")
        original = spot.get("remarks", "")
        if not original:
            manual_required.append({"name": name, "issues": ["remarks が空"]})
            continue

        fixed = fix_remarks(original)
        if fixed != original:
            auto_fixed.append({
                "name": name,
                "before": original,
                "after": fixed,
            })
            if args.fix:
                spot["remarks"] = fixed
                changed = True

        check_target = fixed if args.fix else original
        issues = detect_violations(check_target)
        manual_only = [
            i for i in issues
            if not any(kw in i for kw in ["半角チルダ", "半角括弧", "時間範囲に半角ハイフン"])
        ]
        if manual_only:
            manual_required.append({"name": name, "issues": manual_only})

    if args.fix and changed:
        SPOTS_JSON.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.json:
        print(json.dumps({
            "auto_fixed": auto_fixed,
            "manual_required": manual_required,
            "fixed_applied": args.fix and changed,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"=== 自動修正対象: {len(auto_fixed)}件 ===")
        for item in auto_fixed:
            print(f"  - {item['name']}")
        print(f"=== 要人間判断: {len(manual_required)}件 ===")
        for item in manual_required:
            print(f"  - {item['name']}: {', '.join(item['issues'])}")
        if args.fix and changed:
            print("→ spots.json を更新しました")

    if manual_required or (auto_fixed and not args.fix):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
