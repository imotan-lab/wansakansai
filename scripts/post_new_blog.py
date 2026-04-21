#!/usr/bin/env python3
"""新規ブログ記事公開時の自動X投稿スクリプト。

ブログ追加ワークフローから呼び出す想定。スラッグを指定すると、
blog/<slug>.html を読み取ってタイトル・説明を抽出し投稿する。

使い方:
  python post_new_blog.py <slug>              # 実投稿
  python post_new_blog.py <slug> --dry-run    # 投稿せず本文確認
  python post_new_blog.py <slug> --title "..." --desc "..."  # 明示指定

嘘を流さない原則:
- HTMLのmeta description/og:titleから抽出した事実のみ使用
- サイトの公開URLが本物か確認
"""
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, "C:/Users/imao_/.claude")
from x_poster import post_tweet, count_x_weight, MAX_TWEET_WEIGHT  # noqa: E402
from refresh_x_cookies import refresh_with_auto_chrome  # noqa: E402
from clear_x_cache import clear_account, human_size  # noqa: E402

from x_auto_helpers import (  # noqa: E402
    blog_url,
    load_history,
    save_history,
    record_post,
    apply_random_jitter,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
BLOG_DIR = PROJECT_DIR / "blog"
RESULT_PATH = PROJECT_DIR / "scripts" / "x_post_result.json"

ACCOUNT = "wansakansai"

BLOG_OPENINGS = [
    "【ブログ更新】\n{title}",
    "新しいブログ記事を公開しました🐕\n{title}",
    "ブログを更新しました\n{title}",
    "ブログ記事：{title}",
    "新着記事\n{title}",
]

BLOG_CLOSINGS = [
    "続きはこちら\n{url}",
    "{url}\nで読む",
    "詳しくはブログで\n{url}",
    "読む→ {url}",
    "{url}",
]

BLOG_HASHTAGS = [
    "#わんさかんさい",
    "#犬のいる暮らし",
    "#犬連れブログ",
    "#犬とお出かけ",
]


def extract_meta(html: str, name: str, prop: str | None = None) -> str:
    """meta name="..." または meta property="..." の content を抽出。"""
    if prop:
        m = re.search(
            rf'<meta\s+property=["\']{re.escape(prop)}["\']\s+content=["\']([^"\']+)["\']',
            html,
        )
    else:
        m = re.search(
            rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\']([^"\']+)["\']',
            html,
        )
    return m.group(1) if m else ""


def extract_title_from_html(html: str) -> str:
    """<title>タグから「 - わんさかんさい」を除いたタイトルを返す。"""
    m = re.search(r"<title>([^<]+)</title>", html)
    if not m:
        return ""
    title = m.group(1).strip()
    # 「タイトル - わんさかんさい」の「 - わんさかんさい」を取り除く
    title = re.sub(r"\s*-\s*わんさかんさい\s*$", "", title)
    return title


def build_blog_post_text(title: str, url: str, desc: str = "") -> str:
    opening = random.choice(BLOG_OPENINGS).format(title=title)
    closing = random.choice(BLOG_CLOSINGS).format(url=url)
    hashtags = " ".join(BLOG_HASHTAGS)

    # 本文中段: 説明文（あれば）を短縮して使用
    middle = ""
    if desc:
        # 1文で切る
        first_sentence = re.split(r"[。\n]", desc)[0]
        if first_sentence and len(first_sentence) <= 60:
            middle = first_sentence + "。" if not first_sentence.endswith("。") else first_sentence

    parts = [opening]
    if middle:
        parts.append(middle)
    parts.append("")
    parts.append(closing)
    parts.append("")
    parts.append(hashtags)
    text = "\n".join(parts)

    # 短縮ループ
    while count_x_weight(text) > MAX_TWEET_WEIGHT:
        if middle:
            middle = ""
        elif len(title) > 20:
            title = title[:20] + "…"
            opening = random.choice(BLOG_OPENINGS).format(title=title)
        else:
            break
        parts = [opening]
        if middle:
            parts.append(middle)
        parts.append("")
        parts.append(closing)
        parts.append("")
        parts.append(hashtags)
        text = "\n".join(parts)

    return text


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    slug = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    skip_jitter = "--no-jitter" in sys.argv

    title_arg = ""
    desc_arg = ""
    for i, a in enumerate(sys.argv):
        if a == "--title" and i + 1 < len(sys.argv):
            title_arg = sys.argv[i + 1]
        elif a == "--desc" and i + 1 < len(sys.argv):
            desc_arg = sys.argv[i + 1]

    # blog/<slug>.html を読み込んでメタ情報を取得
    html_path = BLOG_DIR / f"{slug}.html"
    if not html_path.exists():
        print(f"ERROR: {html_path} が存在しません")
        return 1

    html = html_path.read_text(encoding="utf-8")
    title = title_arg or extract_meta(html, "", prop="og:title") or extract_title_from_html(html)
    desc = desc_arg or extract_meta(html, "description")

    if not title:
        print("ERROR: タイトルが取得できませんでした")
        return 1

    url = blog_url(slug)
    print(f"=== ブログ記事投稿 ===")
    print(f"  slug: {slug}")
    print(f"  title: {title}")
    print(f"  desc: {desc[:60]}...")

    text = build_blog_post_text(title, url, desc)
    print(f"\n--- 投稿文 ({count_x_weight(text)} weight) ---\n{text}\n---")

    result_data = {
        "posts": [{
            "slug": slug,
            "title": title,
            "post_type": "new_blog",
            "text": text,
        }],
    }

    if dry_run:
        result_data["posts"][0]["success"] = None
        result_data["posts"][0]["message"] = "dry-run"
        with open(RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print("[dry-run] 投稿せず終了")
        return 0

    if not skip_jitter:
        apply_random_jitter(300, 1200, label="post jitter")

    ok, msg = refresh_with_auto_chrome(ACCOUNT)
    print(f"Cookie refresh: {'OK' if ok else 'SKIP'} - {msg}")

    post_ok, post_msg = post_tweet(ACCOUNT, text)
    print(f"Post: {'OK' if post_ok else 'NG'} - {post_msg}")

    result_data["posts"][0]["success"] = post_ok
    result_data["posts"][0]["message"] = post_msg

    if post_ok:
        history = load_history()
        # ブログはspot_idではなくslugで管理
        record_post(history, f"blog:{slug}", "new_blog", text)
        save_history(history)

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    if post_ok:
        try:
            r = clear_account(ACCOUNT)
            if r["skipped"]:
                print(f"Cache clear: SKIP ({r['reason']})")
            else:
                print(f"Cache clear: OK ({human_size(r['freed_bytes'])} 解放)")
        except Exception as e:
            print(f"Cache clear: ERR ({type(e).__name__}: {e})")

    return 0 if post_ok else 1


if __name__ == "__main__":
    sys.exit(main())
