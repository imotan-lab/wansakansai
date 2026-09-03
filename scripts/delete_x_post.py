#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""@wansakansai の投稿を1件削除する。

投稿が壊れた形で出てしまった時の後始末用（2026-09-03に危険情報の投稿が
文の途中で切れて公開されたため作成）。x_poster.py と同じ storage_state を使う。

**誤削除を防ぐため、本文に含まれる文字列で対象を特定し、
ちょうど1件に絞れた時だけ削除する。** 0件でも2件以上でも何もせず終了する。

--scan-broken を使うと、本文が途中で切れている投稿を機械的に洗い出せる。
判定は「括弧が開いたまま閉じていない」の1点だけにしてある。主観が入らず、
正常な投稿を巻き込まないため。

使い方:
    python scripts/delete_x_post.py --match "とくに紀伊山地周辺"            # 探すだけ（既定）
    python scripts/delete_x_post.py --match "とくに紀伊山地周辺" --delete   # 実際に削除
    python scripts/delete_x_post.py --match "..." --delete --no-headless   # 画面を見ながら
    python scripts/delete_x_post.py --scan-broken                          # 壊れた投稿を一覧
    python scripts/delete_x_post.py --scan-broken --delete                 # 壊れた投稿を全部削除
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, "C:/Users/imao_/.claude")
from x_poster import storage_path, LAUNCH_ARGS, USER_AGENT, STEALTH_INIT  # noqa: E402

ACCOUNT = "wansakansai"
PROFILE_URL = "https://x.com/wansakansai"


def is_broken(text: str) -> bool:
    """投稿本文が途中で切れているか。

    判定は「括弧が開いたまま閉じていない」の1点だけ。主観を入れないための割り切りで、
    2026-09-03に実際に出た事故（場所を1文字ずつ削って括弧の途中で切れた）を捉えられる。
    引用ツイートや画像の説明文まで含んだテキストが来るため、
    本文らしい先頭部分だけを見る。
    """
    body = text.split("\n")
    # 「【…】」で始まる行から下、リンクやハッシュタグの手前までを本文とみなす
    start = next((i for i, l in enumerate(body) if l.startswith("【")), None)
    if start is None:
        return False
    chunk = []
    for l in body[start:]:
        if l.startswith("#") or l.startswith("https://") or l.startswith("詳しく"):
            break
        chunk.append(l)
    s = "".join(chunk)
    return s.count("（") != s.count("）") or s.count("(") != s.count(")")


def collect_all(page, rounds: int) -> list:
    """スクロールしながら投稿本文を集める。

    Xは表示中の十数件しかDOMに残さない（仮想スクロール）ため、
    「スクロールしてから数える」やり方だと常に十数件しか見えない。
    スクロールのたびに読み取って蓄積する必要がある。
    """
    seen = {}
    stall = 0
    for _ in range(max(1, rounds) * 6):
        arts = page.locator('article[data-testid="tweet"]')
        added = 0
        for i in range(arts.count()):
            try:
                t = arts.nth(i).inner_text(timeout=4000)
            except Exception:
                continue
            k = t[:120]
            if k not in seen:
                seen[k] = t
                added += 1
        stall = stall + 1 if added == 0 else 0
        if stall >= 4:
            break
        page.keyboard.press("End")
        page.wait_for_timeout(1600)
    return list(seen.values())


def pick_key(text: str) -> str:
    """その投稿を一意に特定できる文字列を本文から取り出す。"""
    for line in text.split("\n"):
        line = line.strip()
        if len(line) >= 12 and not line.startswith(("【", "#", "https://", "@", "・")):
            return line[:40]
    return ""


def delete_one(page, key: str, rounds: int = 30) -> bool:
    """本文に key を含む投稿を1件削除する。見つからなければ False。

    ★上から順にスクロールしながら探すこと★
    Xは表示中の十数件しかDOMに残さないため、下までスクロールした状態で
    現在のDOMだけを見ると、上の方にある対象が見つからず「削除できず」になる
    （2026-09-03に実際に発生）。必ず先頭に戻ってから探し直す。
    """
    page.keyboard.press("Home")
    page.wait_for_timeout(1500)
    for _ in range(max(1, rounds) * 6):
        arts = page.locator('article[data-testid="tweet"]')
        found = None
        for i in range(arts.count()):
            try:
                if key in arts.nth(i).inner_text(timeout=4000):
                    found = arts.nth(i)
                    break
            except Exception:
                continue
        if found is None:
            page.keyboard.press("End")
            page.wait_for_timeout(1600)
            continue
        art = found
        try:
            art.locator('[data-testid="caret"]').first.click()
            page.wait_for_timeout(1200)
            item = page.get_by_role("menuitem").filter(has_text="削除").first
            item.wait_for(timeout=10000)
            item.click()
            page.wait_for_timeout(1200)
            confirm = page.locator('[data-testid="confirmationSheetConfirm"]').first
            confirm.wait_for(timeout=10000)
            confirm.click()
            page.wait_for_timeout(2500)
            return True
        except Exception:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            return False
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", help="投稿本文に含まれる文字列（これで対象を特定する）")
    ap.add_argument("--scan-broken", action="store_true",
                    help="本文が途中で切れた投稿（括弧が閉じていない）を洗い出す")
    ap.add_argument("--scrolls", type=int, default=12,
                    help="scan-broken時に読み込むためのスクロール回数（既定12）")
    ap.add_argument("--delete", action="store_true", help="実際に削除する（既定は探すだけ）")
    ap.add_argument("--no-headless", action="store_true", help="ブラウザを表示する")
    ap.add_argument("--account", default=ACCOUNT)
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if not a.match and not a.scan_broken:
        print("!! --match か --scan-broken のどちらかが要る")
        return 1

    from playwright.sync_api import sync_playwright

    storage = storage_path(a.account)
    if not Path(storage).exists():
        print(f"!! storage_stateが無い: {storage}")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not a.no_headless, args=LAUNCH_ARGS)
        context = browser.new_context(
            storage_state=str(storage), user_agent=USER_AGENT,
            locale="ja-JP", viewport={"width": 1280, "height": 1000},
        )
        context.add_init_script(STEALTH_INIT)
        page = context.new_page()
        try:
            page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)
            page.wait_for_timeout(2500)

            if a.scan_broken:
                texts = collect_all(page, a.scrolls)
                print(f"読み取れた投稿: {len(texts)}件（重複除く）")
                hits = [(i, t) for i, t in enumerate(texts) if is_broken(t)]
            else:
                articles = page.locator('article[data-testid="tweet"]')
                n = articles.count()
                print(f"読み込めた投稿: {n}件")
                hits = []
                for i in range(n):
                    try:
                        txt = articles.nth(i).inner_text(timeout=5000)
                    except Exception:
                        continue
                    if a.match in txt:
                        hits.append((i, txt))

            label = "括弧が閉じていない（途中で切れた）投稿" if a.scan_broken else f"「{a.match}」を含む投稿"
            print(f"\n{label}: {len(hits)}件")
            for i, txt in hits:
                print(f"\n--- {i}番目 ---")
                print(txt[:400])

            if not hits:
                return 0

            if not a.scan_broken and len(hits) != 1:
                print(f"\n!! ちょうど1件に絞れなかったため何もしない（{len(hits)}件）")
                return 1

            if not a.delete:
                print("\n（探すだけのモード。削除するには --delete を付ける）")
                return 0

            # 削除すると並びがずれるので、毎回先頭から探し直す
            deleted = 0
            for _, txt in hits:
                key = pick_key(txt)
                if not key:
                    print(f"\n!! 特定用の文字列を取れず飛ばす: {txt[:60]}")
                    continue
                if not delete_one(page, key):
                    print(f"\n!! 削除できず: {key}")
                    continue
                deleted += 1
                print(f"削除: {key}")
            print(f"\n削除した投稿: {deleted}件")
            page.wait_for_timeout(2000)

            # 消えたか確認
            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)
            page.wait_for_timeout(2500)
            # ★検証も蓄積方式で行うこと★ DOMに残る十数件だけを数えると、
            # 消えていないのに「消えました」と報告してしまう（2026-09-03に実際に発生）
            if a.scan_broken:
                texts2 = collect_all(page, a.scrolls)
                print(f"検証のため読み取った投稿: {len(texts2)}件")
                still = sum(1 for t in texts2 if is_broken(t))
            else:
                still = 0
                arts2 = page.locator('article[data-testid="tweet"]')
                for i in range(arts2.count()):
                    try:
                        if a.match in arts2.nth(i).inner_text(timeout=5000):
                            still += 1
                    except Exception:
                        continue
            if still == 0:
                print("\n削除を確認しました（再読み込み後、該当する投稿は見つかりません）")
                return 0
            print(f"\n!! まだ{still}件残っている（読み込み範囲外か、削除に失敗）")
            return 1
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
