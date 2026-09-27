#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""spots.json の「表示すると誤情報になる状態」を機械で見つける（2026-09-28導入）。

なぜ要るか:
  2026-09-28、小目津公園（公式が園内の犬の散歩を禁止）で自動タスクが dogSize を全部 false にしたところ、
  表示側は「中型犬が不可なら小型犬のみ入場可」と出す作りだったため、犬が入れない公園に
  「小型犬のみ入場可（中型犬・大型犬は不可）」の札とタイトル「犬連れOK」が本番に出た。
  Codexの変更レビューは事実（散歩禁止）を確かめたが、値がどう表示されるかはサイトの決まりなので見られない。
  だから「この値の組み合わせは公開してはいけない」を機械で止める。

判定:
  NG1 dogSize が small/medium/large すべて false … 犬が入れない施設。掲載しないか、人が判断するまで公開しない
  NG2 small-dog-only タグと dogSize.medium=false が食い違う … フィルターと札が別のことを言う
  NG3 dogArea が outdoor-only / carry-only 以外の値
  NG4 dogRun.maxSize が small/medium/large 以外の値

使い方:
  python scripts/check_spot_data.py            … NGを一覧。NGがあれば終了コード1
  python scripts/check_spot_data.py --json     … {"ok": bool, "ngs": [...]}
スポット更新タスク（am/pm）は書き込み後・コミット前に必ず流し、NGならコミットしない。
"""
import json
import sys
from pathlib import Path

SPOTS = Path(__file__).resolve().parent.parent / "data" / "spots.json"


def check(spots: list) -> list:
    ngs = []
    for s in spots:
        sid, name = s.get("id"), s.get("name")
        ds = s.get("dogSize") or {}
        tags = s.get("tags") or []
        if all(ds.get(k) is False for k in ("small", "medium", "large")):
            ngs.append(f"{sid}（{name}）: dogSize がすべて false＝犬が入れない施設。掲載しないか、公開前に人が判断する（そのまま公開すると誤表示になる）")
        if ("small-dog-only" in tags) != (ds.get("medium") is False):
            ngs.append(f"{sid}（{name}）: small-dog-only タグ（{'あり' if 'small-dog-only' in tags else 'なし'}）と dogSize.medium（{ds.get('medium')}）が食い違う")
        if s.get("dogArea") not in (None, "outdoor-only", "carry-only"):
            ngs.append(f"{sid}（{name}）: dogArea の値が想定外: {s.get('dogArea')!r}")
        mx = (s.get("dogRun") or {}).get("maxSize")
        if mx not in (None, "small", "medium", "large"):
            ngs.append(f"{sid}（{name}）: dogRun.maxSize の値が想定外: {mx!r}")
    return ngs


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    ngs = check(spots)
    if "--json" in sys.argv:
        print(json.dumps({"ok": not ngs, "ngs": ngs}, ensure_ascii=False))
    else:
        print(f"=== スポットデータ点検: {len(spots)}件 / NG {len(ngs)}件 ===")
        for n in ngs:
            print("  NG:", n)
    return 1 if ngs else 0


if __name__ == "__main__":
    sys.exit(main())
