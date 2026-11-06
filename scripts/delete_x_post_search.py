"""X投稿を、Xの検索（from:wansakansai "文言"）で探して消す（2026-11-06。and F CAFE を消した時に作った）。
2か月以上前の投稿は delete_x_post.py のプロフィールをたどる方式では届かないので、こちらを使う。
使い方: python scripts/delete_x_post_search.py --match "文言"            # 探すだけ
        python scripts/delete_x_post_search.py --match "文言" --delete   # 消す
既定は探すだけ。--delete で、見つけたその場で1件ずつ消し、最後に検索し直して0件を確かめる。
"""
import sys, urllib.parse, datetime
sys.path.insert(0, "C:/Users/imao_/.claude")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from x_poster import storage_path, LAUNCH_ARGS, USER_AGENT, STEALTH_INIT  # noqa: E402
from playwright.sync_api import sync_playwright

if "--match" not in sys.argv:
    print("!! --match \"文言\" が要る"); sys.exit(1)
MATCH = sys.argv[sys.argv.index("--match") + 1]
Q = f'from:wansakansai "{MATCH}"'
URL = "https://x.com/search?q=" + urllib.parse.quote(Q) + "&src=typed_query&f=live"
DELETE = "--delete" in sys.argv


def log(*a):
    print(f"[{datetime.datetime.now():%Y/%m/%d %H:%M:%S}]", *a, flush=True)


def load(page):
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_selector('article[data-testid="tweet"]', timeout=25000)
    except Exception:
        return []
    page.wait_for_timeout(3000)
    out = []
    arts = page.locator('article[data-testid="tweet"]')
    for i in range(arts.count()):
        try:
            t = arts.nth(i).inner_text(timeout=5000)
            tm = arts.nth(i).locator("time").first.get_attribute("datetime", timeout=3000)
        except Exception:
            continue
        out.append((i, tm, t))
    return out


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=LAUNCH_ARGS)
    ctx = browser.new_context(storage_state=str(storage_path("wansakansai")), user_agent=USER_AGENT,
                              locale="ja-JP", viewport={"width": 1280, "height": 1000})
    ctx.add_init_script(STEALTH_INIT)
    page = ctx.new_page()
    try:
        log("検索:", Q)
        found = load(page)
        hits = [(i, tm, t) for i, tm, t in found if MATCH in t and "@wansakansai" in t]
        log(f"検索結果 {len(found)}件 / うち対象 {len(hits)}件")
        for _, tm, t in hits:
            log("  ", tm, "|", t.replace("\n", " / ")[:160])
        if not DELETE or not hits:
            sys.exit(0)
        deleted = 0
        for n in range(len(hits) + 2):
            cur = [(i, tm, t) for i, tm, t in load(page) if MATCH in t and "@wansakansai" in t]
            if not cur:
                break
            i, tm, t = cur[0]
            art = page.locator('article[data-testid="tweet"]').nth(i)
            try:
                art.locator('[data-testid="caret"]').first.click()
                page.wait_for_timeout(1200)
                item = page.get_by_role("menuitem").filter(has_text="削除").first
                item.wait_for(timeout=10000)
                item.click()
                page.wait_for_timeout(1200)
                c = page.locator('[data-testid="confirmationSheetConfirm"]').first
                c.wait_for(timeout=10000)
                c.click()
                page.wait_for_timeout(3000)
                deleted += 1
                log("削除:", tm)
            except Exception as e:
                log("!! 削除に失敗:", tm, type(e).__name__, str(e)[:160])
                break
        log(f"削除した投稿: {deleted}件")
        page.wait_for_timeout(5000)
        left = [x for x in load(page) if MATCH in x[2] and "@wansakansai" in x[2]]
        log(f"検索し直した結果、残り {len(left)}件")
        sys.exit(0 if not left else 1)
    finally:
        ctx.close()
        browser.close()
