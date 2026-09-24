#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ブログ記事の <img> に width / height（画像ファイルの実寸）を書き込む（2026-09-25導入）。

なぜ要るか:
  スポットのページから記事の節（#spot-{スポットID}）へ直接飛ぶようにしたところ、
  写真にサイズが書かれていないため、読み込む前は高さ0で並び、ブラウザは見出しへ飛んだあとで
  写真が読み込まれて見出しが大きく下へずれた（平草原公園の節で、飛んだ先が記事の先頭付近になった）。
  サイズを書いておけば、読み込む前から写真の場所が確保され、飛んだ位置がずれない。
  表示中にページがガタつくのも防げる。

css/style.css の img { max-width: 100%; height: auto; } があるので、書いた数値は縦横比として使われ、
表示の大きさは今までどおり（横幅いっぱいの写真が大きくなることはない）。

使い方:
  python scripts/add_blog_img_size.py          … blog/*.html（一覧と下書きを除く）を直す
  python scripts/add_blog_img_size.py --check  … 直さずに、サイズの無い <img> の数だけ出す（終了コード1＝残りあり）
すでに width がある <img> は触らない（何度流しても同じ結果になる）。
記事を足した時・写真を差し替えた時に流すこと。
"""
import argparse
import re
import sys
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
BLOG = PROJECT / "blog"
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
SRC_RE = re.compile(r'\ssrc="([^"]+)"', re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    missing_total = 0
    for f in sorted(BLOG.glob("*.html")):
        if f.stem == "index":
            continue
        text = f.read_text(encoding="utf-8")
        changed = 0
        problems = []

        def fix(m):
            nonlocal changed
            tag = m.group(0)
            if re.search(r"\swidth=", tag, re.I):
                return tag
            s = SRC_RE.search(tag)
            if not s or s.group(1).startswith(("http:", "https:", "data:")):
                problems.append("外部か src 無し: " + tag[:80])
                return tag
            path = (f.parent / s.group(1)).resolve()
            if not path.is_file():
                problems.append("ファイルが無い: " + s.group(1))
                return tag
            with Image.open(path) as im:
                w, h = im.size
            changed += 1
            return tag[:-1].rstrip("/").rstrip() + f' width="{w}" height="{h}">'

        new = IMG_RE.sub(fix, text)
        missing_total += changed
        print(f"{f.name}: サイズを{'足す' if args.check else '足した'} <img> {changed}件"
              + ("" if not problems else " ／ ★" + " ／ ".join(problems)))
        if changed and not args.check:
            f.write_text(new, encoding="utf-8", newline="")
    if args.check:
        return 1 if missing_total else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
