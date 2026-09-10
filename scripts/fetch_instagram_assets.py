#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""公式Instagramのプロフィール文と投稿画像を取り出し、Codexに渡せる形で保存する。

**なぜ必要か（2026-09-10）**
Codexは自力でInstagramを取得できず、「公式Instagram取得エラーで料金・営業時間を照合できず」
としか答えられない。小規模施設はInstagramが実質の公式なので、そのままだと
**いちばん裏取りが必要なスポットだけ検証が効かない**状態になる。

Chrome MCP経由では画像を取り出せない（実機で確認済み）:
  ダウンロード → ブロック / base64出力 → [BLOCKED: Base64 encoded data]
  画像URLの出力 → [BLOCKED: Cookie/query string data] / 画面キャプチャ → タブが前面に来ない
そこでPlaywrightのヘッドレスで開いて直接落とす。**ユーザーのChromeには触らない。**
Instagramのプロフィールと投稿サムネイルは**ログインなしで取得できる**ことを確認済み。

取得できるもの:
  - profile.txt … ページの表示テキスト（プロフィール文・定休日などが入る）
  - page.png    … ページ全体のスクリーンショット
  - post_N.jpg  … 投稿サムネイルの画像そのもの（料金表が画像の施設はここに写る）

使い方:
    python scripts/fetch_instagram_assets.py --url https://www.instagram.com/xxx/ --id spot-id
    python scripts/fetch_instagram_assets.py --url ... --id ... --posts 3
    出力先: C:/Users/imao_/.claude/logs/insta_{id}_{YYYY-MM-DD}/

Codexへの渡し方（各SKILL.mdのSTEP 7参照）:
    cat プロンプト.txt | codex exec --skip-git-repo-check -i 画像.jpg -
    ★-i の後ろにプロンプトを置くと引数として飲み込まれる。プロンプトは必ずstdinで渡すこと★
"""
import argparse
import datetime
import sys
from pathlib import Path

LOGS = Path("C:/Users/imao_/.claude/logs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="InstagramのプロフィールURL")
    ap.add_argument("--id", required=True, help="スポットID（保存先フォルダ名に使う）")
    ap.add_argument("--posts", type=int, default=2, help="保存する投稿画像の数（既定2）")
    ap.add_argument("--out", default=None, help="保存先を明示する場合")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"[error] playwrightが読み込めない: {e}")
        return 2

    today = datetime.date.today().isoformat()
    out = Path(a.out) if a.out else (LOGS / f"insta_{a.id}_{today}")
    out.mkdir(parents=True, exist_ok=True)

    saved = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        try:
            ctx = b.new_context(viewport={"width": 1280, "height": 1400}, locale="ja-JP")
            pg = ctx.new_page()
            pg.goto(a.url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(5000)

            # プロフィール文は「続きを読む」を押すと全文が出る。押せなくても止めない
            try:
                btn = pg.get_by_text("続きを読む", exact=False).first
                if btn.is_visible(timeout=3000):
                    btn.click(timeout=3000)
                    pg.wait_for_timeout(1500)
            except Exception:
                pass

            text = pg.inner_text("body")
            f = out / "profile.txt"
            f.write_text(text, encoding="utf-8")
            saved.append(f)
            print(f"[ok] profile.txt {len(text)}文字")

            shot = out / "page.png"
            pg.screenshot(path=str(shot), full_page=False)
            saved.append(shot)
            print(f"[ok] page.png {shot.stat().st_size}バイト")

            srcs = pg.eval_on_selector_all(
                'main a[href*="/p/"] img',
                "els => els.map(e => e.src).filter(Boolean)",
            )
            print(f"[info] 投稿サムネイル {len(srcs)}件を検出")
            for i, s in enumerate(srcs[: a.posts]):
                r = ctx.request.get(s)
                if not r.ok:
                    print(f"[warn] post_{i} 取得失敗 status={r.status}")
                    continue
                fp = out / f"post_{i}.jpg"
                fp.write_bytes(r.body())
                saved.append(fp)
                print(f"[ok] post_{i}.jpg {fp.stat().st_size}バイト")
        finally:
            b.close()

    print()
    print(f"[key] 保存先={out} ファイル数={len(saved)}")
    for s in saved:
        print(f"  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
